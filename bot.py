import tweepy
from openai import OpenAI
import sys
import io
import os
import datetime
import time
import random
import logging
from typing import Callable

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def retry_with_backoff(func: Callable, *, max_attempts: int = 5, base_delay: float = 1.0, factor: float = 2.0):
    """
    Exponential backoff with jitter for transient errors / rate limits.
    func: callable with no args that performs the action and returns result or raises.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return func()
        except Exception as e:
            # Detect likely rate limit/too-many-requests
            text = str(e).lower()
            is_rate_limit = ("429" in text) or ("too many requests" in text) or ("rate limit" in text)
            if not is_rate_limit or attempt >= max_attempts:
                logging.exception("Operation failed (no more retries or non-rate-limit): %s", e)
                raise
            # Backoff with jitter
            delay = base_delay * (factor ** (attempt - 1))
            # jitter: +- 0..delay*0.1
            jitter = random.uniform(0, delay * 0.1)
            sleep_for = delay + jitter
            logging.warning("Rate limited (attempt %d/%d). Retrying after %.1f seconds...", attempt, max_attempts, sleep_for)
            time.sleep(sleep_for)

def main():
    logging.info("詳細：架空謝罪会見Bot（学生・青春ネタ特化版）を開始します...")

    # ==================================================
    # 鍵の読み込み
    # ==================================================
    try:
        X_API_KEY = os.environ["X_API_KEY"]
        X_API_SECRET = os.environ["X_API_SECRET"]
        X_ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
        X_ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]
        OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    except KeyError:
        logging.error("❌ エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit(1)

    # ==================================================
    # 1. 今日の日付を取得
    # ==================================================
    now = datetime.datetime.now()
    month = now.strftime('%m')
    day = now.strftime('%d')
    date_str = f"{month}月{day}日"
    logging.info("本日の日付: %s", date_str)

    # ==================================================
    # 2. AIによる「謝罪文」生成（リトライ付き）
    # ==================================================
    logging.info("AIが謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは社会的地位のある人物（政治家やCEO）として「緊急謝罪会見」を行ってください。
    
    【今日の日付】
    {date_str}

    【指示】
    1. **裏テーマ**: 今日（{date_str}）が何の記念日か知識から検索し、それをネタの着想元にしてください。（投稿には記念日名は絶対に出さない）
    
    2. **ターゲット層**: 
       * **中高生・大学生**が読んで共感できる内容にしてください。

    3. **不祥事の内容（超重要）**: 
       * テスト、課題、恋愛、スマホ、部活、バイト、親などの**「学生生活における絶望的なミス」**を具体的に描写してください。
       * **「固有名詞」や「具体的な数字」**を入れると爆笑率が上がります。

    4. **トーン**: 
       * やったことは「ただのアホな学生」ですが、口調は**「重大な条約違反を犯した大統領」**のように重苦しく謝ってください。
       * ギャップで笑わせてください。

    5. **長さ**: 140字以内（日本語）。
       * 見やすいように行で区切ってください

    【出力形式】
    以下の形式のみを出力してください。

    【謝罪会見】
    (ここに謝罪文)
    #架空謝罪会見 #誠にごめんなさい #フォロバ100
    """

    def call_openai():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
        )

    try:
        response = retry_with_backoff(call_openai, max_attempts=6, base_delay=1.0, factor=2.0)
        # Response parsing — keep current access pattern
        ai_output = response.choices[0].message.content
        logging.info("★生成結果:\n%s", ai_output)
    except Exception as e:
        logging.error("エラー：AI生成に失敗しました: %s", e)
        sys.exit(1)

    # ==================================================
    # 3. 投稿（リトライ付き）
    # ==================================================
    now_time = now.strftime("%H:%M:%S")
    tweet_content = f"{ai_output}\n\n(更新: {now_time})"

    try:
        client_x = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
    except Exception:
        logging.exception("Twitterクライアントの初期化に失敗しました。")
        sys.exit(1)

    def call_tweet():
        # create_tweet may raise tweepy.errors.TooManyRequests or other exceptions
        return client_x.create_tweet(text=tweet_content)

    try:
        # Retry on rate limits
        result = retry_with_backoff(call_tweet, max_attempts=6, base_delay=2.0, factor=2.0)
        logging.info("✅ 投稿成功！ (時刻: %s) result: %s", now_time, result)
    except Exception as e:
        # More specific messaging for common error patterns
        text = str(e).lower()
        logging.error("❌ 投稿失敗：%s", e)
        if "187" in text:
            logging.error("🛑 重複エラー：内容を変えてください。")
        elif "403" in text:
            logging.error("🛑 権限エラー：GitHubの鍵を確認してください。")
        elif ("429" in text) or ("too many requests" in text):
            logging.error("🛑 レート上限に達しました。投稿間隔を開けるか、利用制限を確認してください。")
        else:
            logging.error("予期しないエラーです。詳細を確認してください。")

if __name__ == "__main__":
    main()
