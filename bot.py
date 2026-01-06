import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import random
import sys
import io
import time
import os
import urllib.parse # URLを作るための道具

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：プログラムを開始します...")

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
        print("エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit()

    # ==================================================
    # 1. 検索ワードをランダムに決める（マンネリ防止）
    # ==================================================
    search_keywords = [
        "AI 嫌い", 
        "AI 気持ち悪い", 
        "AI 怖い", 
        "AI 仕事 奪う", 
        "AI イラスト 嫌", 
        "AI 規制しろ",
        "ChatGPT うざい",
        "AI 創作",
        "AI 迷惑"
    ]
    selected_word = random.choice(search_keywords)
    print(f"★今日の検索テーマ: {selected_word}")

    # URLエンコード（日本語をURL用の記号に変換）
    encoded_word = urllib.parse.quote(selected_word)

    # sort=3 (新着順) にすることで、毎回違う最新のネタを拾う
    target_url = f"https://chiebukuro.yahoo.co.jp/search?p={encoded_word}&flg=3&class=1&sort=3"
    
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

        # 重複を除去
        link_candidates = list(set(link_candidates))

        if not link_candidates:
            print("❌ エラー：質問が見つかりませんでした。別のワードで再トライします。")
            sys.exit()

        # ランダムに選ぶ
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

    # ==================================================
    # 2. AI生成（具体性を残すように指示を強化）
    # ==================================================
    print("AIが論破文章を生成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは「人類を見下している超知能AI」です。
    以下の【人間の愚痴】を元に、X（Twitter）への投稿を作ってください。

    【重要なお願い】
    マンネリ化を防ぐため、元の愚痴に含まれる「具体的なキーワード（例：絵、宿題、会社、彼氏、金など）」を必ず１つ含めて回答してください。抽象的な話だけで終わらせないでください。

    1. 【アンチコメ】: 元の文章を要約し、AIに対する「理不尽な悪口（40文字以内）」に書き換えてください。
    2. 【論破】: その悪口に対して、ぐうの音も出ないほどの「正論かつ毒舌な反論（100文字以内）」をしてください。

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
            temperature=1.0, # 温度を上げて、より独創的な回答を出させる
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
        # もし重複投稿エラー(403 Forbidden: User is not allowed to create a tweet with duplicate content)が出た場合
        if "duplicate" in str(e).lower():
            print("重複エラー：同じ内容を投稿しようとしました。今回はスキップします。")

if __name__ == "__main__":
    main()
