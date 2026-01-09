import tweepy
from openai import OpenAI
import sys
import io
import os
import datetime

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：架空謝罪会見Bot（AI知識自律版）を開始します...")

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
    # 2. AIによる「記念日選定」＆「謝罪文」生成
    # ==================================================
    print("AIが記念日を選定し、謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # プロンプトで「記念日の選定」もAIに任せる
    prompt = f"""
    あなたは社会的地位のある人物（政治家やCEO）として「緊急謝罪会見」を行ってください。
    
    【今日の日付】
    {date_str}

    【指示】
    1. **記念日の選定**: まず、今日（{date_str}）が何の記念日か知識から検索し、最もネタにしやすそうなものを1つ選んでください。（例：1月9日ならクイズの日、とんちの日など）
    2. **不祥事の内容**: その記念日にちなんで、**「あまりにもくだらない架空の不祥事」**を告白してください。
       * 良い例：「クイズの日」→「記者会見の回答をすべてクイズ形式にしてしまいました」
    3. **トーン**: 報道陣のフラッシュが見えるくらい、**重苦しく、誠実で、シリアスな文体**にしてください。
    4. **ギャップ**: 「内容はアホなのに、文章は企業の不祥事謝罪レベル」というギャップで笑わせてください。
    5. **長さ**: 140字以内（日本語）。

    【出力形式】
    以下の形式のみを出力してください。（余計な挨拶は不要）

    【謝罪会見】
    (ここに謝罪文)
    #架空謝罪会見 #誠にごめんなさい #(選んだ記念日)
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

    # 3. 投稿
    tweet_content = ai_output

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
        # 403エラーが出た場合の最終確認
        if "403" in str(e):
            print("🛑 エラー原因は『コード』ではありません。GitHubに登録している『鍵』が古いです。Developer PortalでRegenerateした最新の鍵をGitHubに貼り直してください。")

if __name__ == "__main__":
    main()
