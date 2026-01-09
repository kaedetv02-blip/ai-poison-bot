import tweepy
from openai import OpenAI
import sys
import io
import os
import datetime

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：架空謝罪会見Bot（共感ネタ強化・連投対策版）を開始します...")

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
        print("❌ エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit()

    # ==================================================
    # 1. 今日の日付を取得
    # ==================================================
    now = datetime.datetime.now()
    month = now.strftime('%m')
    day = now.strftime('%d')
    date_str = f"{month}月{day}日"
    
    print(f"本日の日付: {date_str}")

    # ==================================================
    # 2. AIによる「裏テーマ選定」＆「謝罪文」生成
    # ==================================================
    print("AIが謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # プロンプト：生活感のある「あるあるネタ」をシリアスに謝罪させる
    prompt = f"""
    あなたは社会的地位のある人物（政治家やCEO）として「緊急謝罪会見」を行ってください。
    
    【今日の日付】
    {date_str}

    【指示】
    1. **裏テーマ**: 今日（{date_str}）が何の記念日か検索し、それをネタの着想元にしてください。
    2. **不祥事の内容（重要）**: 
       * 記念日にちなんだ、**「日常によくある些細な失敗」**や**「誰もが共感できる小さな罪」**をなるべく具体的に告白してください。
       * ⚠️ **禁止**: 意味不明な行動、シュールすぎる設定、ファンタジー。（例：「宇宙人と交信した」「ぬいぐるみを会議に出した」などはNG）
       * ⭕️ **推奨**: 「二度寝した」「袋を開けるのを失敗してぶちまけた」「カロリーを気にせず食べた」「人の話を適当に相槌打った」など、**人間味のあるダメな行動**。
    
    3. **禁止事項**: 投稿文やハッシュタグに「〇〇の日」という記念日の名称は入れないでください（匂わせるだけ）。
    4. **トーン**: 内容は庶民的ですが、文章は**「国家の存亡に関わるレベル」に重苦しく、シリアス**に書いてください。
    5. **長さ**: 130字以内（日本語）。

    【出力形式】
    以下の形式のみを出力してください。（余計な挨拶は不要）

    【謝罪会見】
    (ここに謝罪文)
    #架空謝罪会見 #誠にごめんなさい #フォロバ100
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, 
        )
        ai_output = response.choices[0].message.content
        print(f"★生成結果:\n{ai_output}")

    except Exception as e:
        print(f"エラー：AI生成に失敗しました: {e}")
        sys.exit()

    # ==================================================
    # 3. 投稿
    # ==================================================
    # 連投エラー(Status 403/187)回避のため、末尾に「投稿時刻」を付与して差別化する
    now_time = now.strftime("%H:%M")
    tweet_content = f"{ai_output}\n\n(更新: {now_time})"

    try:
        client_x = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        client_x.create_tweet(text=tweet_content)
        print("✅ 投稿成功！")

    except Exception as e:
        print(f"❌ 投稿失敗：{e}")
        if "187" in str(e):
            print("🛑 原因：直前の投稿と同じ内容のため拒否されました（重複エラー）。時間を空けるか内容を変えてください。")
        elif "403" in str(e):
            print("🛑 原因：短時間の連投制限、またはAPI権限の問題です。")

if __name__ == "__main__":
    main()
