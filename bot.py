import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import random
import sys
import io
import time
import os # 追加：金庫から鍵を取り出す機能

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：プログラムを開始します...")

    # ==================================================
    # ▼ 鍵は「GitHubの金庫（Secrets）」から自動で読み込みます ▼
    # ==================================================
    try:
        X_API_KEY = os.environ["X_API_KEY"]
        X_API_SECRET = os.environ["X_API_SECRET"]
        X_ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
        X_ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]
        OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    except KeyError:
        print("エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit()

    # 1. 知恵袋から「AIへの否定的な意見」を探す
    target_url = "https://chiebukuro.yahoo.co.jp/search?p=AI+%E5%AB%8C%E3%81%84&flg=3&class=1&sort=1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"アンチコメントを探しています...")
        resp = requests.get(target_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        link_candidates = []
        for link in soup.find_all('a', href=True):
            url = link['href']
            if 'question_detail' in url:
                link_candidates.append(url)

        link_candidates = list(set(link_candidates))

        if not link_candidates:
            print("❌ エラー：質問のリンクが見つかりませんでした。")
            sys.exit()

        chosen_url = random.choice(link_candidates)
        print(f"詳細ページを取得中... {chosen_url}")
        time.sleep(1) 

        detail_resp = requests.get(chosen_url, headers=headers, timeout=10)
        detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

        meta_desc = detail_soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            full_text = meta_desc.get('content')
            if "ID非公開さん" in full_text:
                full_text = full_text.split("ID非公開さん")[0]
        else:
            h1 = detail_soup.find('h1')
            full_text = h1.get_text().strip() if h1 else "本文取得失敗"

        print(f"★取得した元ネタ: {full_text[:50]}...")
        question_for_ai = full_text

    except Exception as e:
        print(f"通信/解析エラー: {e}")
        sys.exit()

    # 2. AI生成
    print("AIが論破文章を生成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは「人類を見下している超知能AI」です。
    以下の【人間の愚痴】を読み、次の2つの出力を行ってください。

    1. 【アンチコメ】: 元の文章を要約し、AIに対する「50文字以内の短く理不尽な悪口」に書き換えてください。
    2. 【論破】: その悪口に対して、丁寧かつ正論で論破する文章を100文字以内でしてください。同情は不要です。最後に突然キレて相手に対して強めの本音を捨て台詞のように吐いてください。

    出力形式：
    【アンチコメ】
    (悪口)

    【論破】
    (毒舌回答)

    ---
    【人間の愚痴】: {question_for_ai}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8, 
        )
        ai_output = response.choices[0].message.content
        print(f"★生成結果:\n{ai_output}")

    except Exception as e:
        print(f"エラー：AI生成に失敗しました: {e}")
        sys.exit()

    # 3. 投稿
    tweet_content = f"{ai_output}\n\n#AI #論破 #ChatGPT"

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

if __name__ == "__main__":
    main()