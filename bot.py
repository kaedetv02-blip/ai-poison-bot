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
    指数バックオフによるリトライ処理（レート制限・一時エラー対策）
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return func()
        except Exception as e:
            text = str(e).lower()
            is_rate_limit = ("429" in text) or ("too many requests" in text) or ("rate limit" in text)
            if not is_rate_limit or attempt >= max_attempts:
                logging.exception("Operation failed (no more retries or non-rate-limit): %s", e)
                raise
            
            delay = base_delay * (factor ** (attempt - 1))
            jitter = random.uniform(0, delay * 0.1)
            sleep_for = delay + jitter
            logging.warning("Rate limited (attempt %d/%d). Retrying after %.1f seconds...", attempt, max_attempts, sleep_for)
            time.sleep(sleep_for)

def main():
    logging.info("開始：架空謝罪会見Bot (2段階生成版・改) を起動します...")

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

    # モデル設定
    MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

    # ==================================================
    # 今日の日付を取得
    # ==================================================
    now = datetime.datetime.now()
    month = now.strftime('%m')
    day = now.strftime('%d')
    date_str = f"{month}月{day}日"
    logging.info("本日の日付: %s", date_str)

    client = OpenAI(api_key=OPENAI_API_KEY)

    # ==================================================
    # ステップ1：AIによる「下書き」生成
    # ==================================================
    logging.info("Step 1: AIがネタ（下書き）を作成中...")

    draft_system_prompt = (
        "あなたはユーモアのある脚本家です。"
        "命令に従って、短く面白い「架空の謝罪会見」の原稿を作成してください。"
    )

    draft_instructions = f"""
今日の日付（ネタの着想元）：{date_str}

指示（簡潔）:
- 架空の公的人物が「ピザにパイナップルを乗せた」レベルのしょうもない罪を犯して謝罪するという設定。
- 誰でも共感できるように、学生だけでなく若者〜大人まで幅広く楽しめる内容にする。
- 実在の人物・団体・個人名は使わない。
- 形式:
【謝罪会見】
(ここに謝罪文)
#架空謝罪会見 #誠にごめんなさい
"""

    def call_draft():
        return client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": draft_system_prompt},
                {"role": "user", "content": draft_instructions},
            ],
            temperature=0.7,
            max_tokens=250,
        )

    try:
        response_draft = retry_with_backoff(call_draft, max_attempts=6)
        draft_text = response_draft.choices[0].message.content
        logging.info("★ Step 1 生成結果 (下書き):\n%s", draft_text)
    except Exception as e:
        logging.error("エラー：下書き生成に失敗しました: %s", e)
        sys.exit(1)

    # ==================================================
    # ステップ2：AIによる「推敲・修正」
    # ==================================================
    logging.info("Step 2: AIが文章をより自然で面白く修正中...")

    # ★ここを変更しました：より面白く、自然にするための強力な指示
    refine_system_prompt = (
        "あなたは超一流の放送作家兼コメディアンです。"
        "渡された原稿を、人間味あふれる自然な言葉遣いに直し、より面白く魅力的な文章に仕上げてください。"
    )

    refine_instructions = f"""
以下の文章はAIが生成した「架空の謝罪会見」の下書きです。
これを元に、**より自然で、かつ面白い文章**に修正してください。

【修正のポイント】
1. **自然さ**: 「AIっぽさ」や「翻訳調」を完全に排除し、人間が本当に謝罪会見で喋っているような（あるいはSNSでつぶやいているような）リアルな口語にする。
2. **面白さ**: ユーモアのキレを上げ、読み手が思わずクスッとするような言葉選びやリズムにする。
3. **形式維持**: 以下のフォーマットは崩さないこと。

【原稿】
{draft_text}
"""

    def call_refine():
        return client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": refine_system_prompt},
                {"role": "user", "content": refine_instructions},
            ],
            temperature=0.9, # 面白さを出すために創造性を少し高めに設定
            max_tokens=250,
        )

    try:
        response_refine = retry_with_backoff(call_refine, max_attempts=6)
        final_output = response_refine.choices[0].message.content
        logging.info("★ Step 2 生成結果 (完成版):\n%s", final_output)
    except Exception as e:
        logging.error("エラー：推敲生成に失敗しました: %s", e)
        sys.exit(1)

    # ==================================================
    # 投稿（リトライ付き）
    # ==================================================
    now_time = now.strftime("%H:%M:%S")
    tweet_content = final_output 

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
        result = retry_with_backoff(call_tweet, max_attempts=6, base_delay=2.0)
        logging.info("✅ 投稿成功！ (時刻: %s) result: %s", now_time, result)
    except Exception as e:
        text = str(e).lower()
        logging.error("❌ 投稿失敗：%s", e)
        if "187" in text:
            logging.error("🛑 重複エラー：内容を変えてください。")
        elif "403" in text:
            logging.error("🛑 権限エラー：Twitterの鍵を確認してください。")
        elif ("429" in text) or ("too many requests" in text):
            logging.error("🛑 レート上限に達しました。")
        else:
            logging.error("予期しないエラーです。詳細を確認してください。")

if __name__ == "__main__":
    main()