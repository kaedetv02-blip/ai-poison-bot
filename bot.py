import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import sys
import io
import os
import random
import datetime

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：架空謝罪会見Bot（雑学ネタ帳ソース）を開始します...")

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
    # 1. 雑学ネタ帳からネタ（記念日）を収集
    # ==================================================
    target_url = "https://zatsuneta.com/category/anniversary.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    topics = []

    try:
        print(f"ネタ元にアクセス中... ({target_url})")
        resp = requests.get(target_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 記事タイトル（h2やliなど）から記念日っぽい文字列を抽出
            # サイト構造に合わせて調整：リンクテキストから「〜の日」を含むものを探す
            links = soup.find_all('a')
            for link in links:
                text = link.get_text().strip()
                if "の日" in text and len(text) < 30:
                    topics.append(text)
            
            if len(topics) < 3:
                print("⚠️ 取得できたネタが少ないため、予備データを使用します。")
                topics = ["きのこの山の日", "プリンの日", "愛妻家の日", "ショートケーキの日"]
            else:
                # 重複削除
                topics = list(set(topics))
                print(f"✅ {len(topics)}個の記念日データを取得しました！")
        else:
            print(f"⚠️ サイトアクセス失敗: Status {resp.status_code}")
            topics = ["ポッキーの日", "いい肉の日", "サウナの日"]

    except Exception as e:
        print(f"⚠️ エラー発生: {e}")
        topics = ["猫の日", "カレーの日"]

    # ランダムに1つ選ぶ
    selected_topic = random.choice(topics)
    print(f"★選ばれたネタ（記念日）: {selected_topic}")

    # ==================================================
    # 2. AIによる「架空の謝罪文」生成
    # ==================================================
    print("AIが謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは社会的地位のある人物（政治家やCEO）として「緊急謝罪会見」を行ってください。
    
    【今回のお題（記念日）】
    {selected_topic}

    【指示】
    1. **内容**: 今日は「{selected_topic}」ですが、それに関連して**「あまりにもくだらない架空の不祥事」**を告白し、謝罪してください。
       * 例：「プリンの日」→「国民の皆様のプリンをすべて食べてしまいました」
       * 例：「猫の日」→「会議中に猫語で喋ってしまいました」
    2. **トーン**: 報道陣のフラッシュが見えるくらい、**重苦しく、誠実で、シリアスな文体**にしてください。
    3. **ギャップ**: 「内容はアホなのに、文章は企業の不祥事謝罪レベル」というギャップで笑わせてください。
    4. **長さ**: 140字以内（日本語）。

    【出力形式】
    以下の形式のみを出力してください。

    【謝罪会見】
    (ここに謝罪文)
    #架空謝罪会見 #誠にごめんなさい #{selected_topic}
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
        if "403" in str(e):
            print("⚠️ 403エラーが続く場合、原因はコードではなく『XのAPI権限』に確定します。")
            print("再確認: Developer PortalでUser authentication settingsが編集画面で『Read and Write』になっているかもう一度だけ確認してください。")

if __name__ == "__main__":
    main()
