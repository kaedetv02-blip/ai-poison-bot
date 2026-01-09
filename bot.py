import tweepy
from openai import OpenAI
import sys
import io
import os
import datetime

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：架空謝罪会見Bot（学生・青春ネタ特化版）を開始します...")

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
    # 2. AIによる「謝罪文」生成
    # ==================================================
    print("AIが謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # プロンプト：ターゲットを「学生」に絞り、学校生活のディテールを強制する
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
    # 連投エラー回避用スタンプ（秒数まで必須）
    now_time = now.strftime("%H:%M:%S")
    tweet_content = f"{ai_output}\n\n(更新: {now_time})"

    try:
        client_x = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        client_x.create_tweet(text=tweet_content)
        print(f"✅ 投稿成功！ (時刻: {now_time})")

    except Exception as e:
        print(f"❌ 投稿失敗：{e}")
        if "187" in str(e):
            print("🛑 重複エラー：内容を変えてください。")
        elif "403" in str(e):
            print("🛑 権限エラー：GitHubの鍵を確認してください。")

if __name__ == "__main__":
    main()
