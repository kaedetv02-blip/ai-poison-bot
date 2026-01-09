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
            # jitter: 0..delay*0.1
            jitter = random.uniform(0, delay * 0.1)
            sleep_for = delay + jitter
            logging.warning("Rate limited (attempt %d/%d). Retrying after %.1f seconds...", attempt, max_attempts, sleep_for)
            time.sleep(sleep_for)

def main():
    logging.info("開始：架空謝罪会見Bot を起動します...")

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
        logging.error("❌ エラー：鍵が見つかりません。環境変数の設定を確認してください。")
        sys.exit(1)

    # モデルは環境変数で上書き可能（デフォルトはより高性能な gpt-4o）
    MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

    # ==================================================
    # 今日の日付を取得
    # ==================================================
    now = datetime.datetime.now()
    month = now.strftime('%m')
    day = now.strftime('%d')
    date_str = f"{month}月{day}日"
    logging.info("本日の日付: %s", date_str)

    # ==================================================
    # AIによる「謝罪文」生成（リトライ付き）
    # ==================================================
    logging.info("AIが謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # シンプルで幅広い層に受けるプロンプト
    system_prompt = (
        "あなたは親切でウィットに富んだアシスタントです。"
        "命令に従って、短くユーモアのある「架空の謝罪会見」文を生成してください。"
        "出力は日本語で、フォーマルな口調とユーモアのギャップで笑いを誘うものにしてください。"
    )

    user_instructions = f"""
今日の日付（ネタの着想元）：{date_str}

指示（簡潔）:
- 架空の公的人物が「ピザにパイナップルを乗せた」レベルのしょうもない罪を犯して謝罪するという設定で書くこと(例はあくまでも参考程度で内容はまったく異なるものにしてください)
- 誰でも共感できるように、学生だけでなく若者〜大人まで幅広く楽しめる内容にすること。
- 実在の人物・団体・個人名は使わない。特定の個人や団体を中傷しない。
- 今日の日付をヒントにするが、記念日名や実際のイベント名は書かない。
- 文字数は140字以内（日本語）。読みやすいように改行を適度に入れる。
- 出力形式は以下の通り（厳守）:

【謝罪会見】
(ここに謝罪文)
#架空謝罪会見 #誠にごめんなさい
"""

    def call_openai():
        return client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_instructions},
            ],
            temperature=0.7,
            max_tokens=200,
        )

    try:
        response = retry_with_backoff(call_openai, max_attempts=6, base_delay=1.0, factor=2.0)
        ai_output = response.choices[0].message.content
        logging.info("★生成結果:\n%s", ai_output)
    except Exception as e:
        logging.error("エラー：AI生成に失敗しました: %s", e)
        sys.exit(1)

    # ==================================================
    # 投稿（リトライ付き）
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
        return client_x.create_tweet(text=tweet_content)

    try:
        result = retry_with_backoff(call_tweet, max_attempts=6, base_delay=2.0, factor=2.0)
        logging.info("✅ 投稿成功！ (時刻: %s) result: %s", now_time, result)
    except Exception as e:
        text = str(e).lower()
        logging.error("❌ 投稿失敗：%s", e)
        if "187" in text:
            logging.error("🛑 重複エラー：内容を変えてください。")
        elif "403" in text:
            logging.error("🛑 権限エラー：Twitterの鍵を確認してください。")
        elif ("429" in text) or ("too many requests" in text):
            logging.error("🛑 レート上限に達しました。投稿間隔を開けるか、利用制限を確認してください。")
        else:
            logging.error("予期しないエラーです。詳細を確認してください。")

if __name__ == "__main__":
    main()
