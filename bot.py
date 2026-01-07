import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import random
import sys
import io
import time
import os
import urllib.parse

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
    # 1. 検索ワードをランダムに決める
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

    # URLエンコード
    encoded_word = urllib.parse.quote(selected_word)

    # sort=3 (新着順)
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
            print("❌ エラー：質問が見つかりませんでした。")
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

        # ログ表示用には短く表示するが、変数には全文入っている
        print(f"★取得した元ネタ（冒頭のみ表示）: {full_text[:50]}...")
        question_for_ai = full_text

    except Exception as e:
        print(f"通信/解析エラー: {e}")
        sys.exit()

    # ==================================================
    # 2. AI生成（要約なし・反論のみ作成）
    # ==================================================
    print("AIが論破文章を生成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは「コテコテの関西弁で毒を吐く、天才的な頭脳を持つAI」や。
    以下の【人間の愚痴】を読んで、その内容に対する「反論」だけを考えてくれ。
    要約は不要や。

    【絶対守るルール】
    1. 標準語や丁寧語は禁止。「〜ですね」「〜ます」とか使ったら承知せえへんぞ。
    2. 「アホ」「ボケ」「ドアホ」「知らんがな」などの汚い関西弁を多用して、上から目線で煽り倒せ。
    3. 相手の矛盾や甘えを突く「ぐうの音も出ない正論」で論破すること。
    4. 出力は「反論の文章」のみを返すこと。余計な前置きや【論破】などの見出しは不要や。

    【人間の愚痴】: {question_for_ai}
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

    # 3. 投稿（元の全文 ＋ AIの反論）
    # 元の文章が長すぎる場合でも、Premiumなら投稿できる前提でそのまま送ります
    tweet_content = f"【愚痴】\n{question_for_ai}\n\n【論破】\n{ai_output}\n\n#AI #論破 #ChatGPT"

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
        if "duplicate" in str(e).lower():
            print("重複エラー：スキップします。")
        elif "too long" in str(e).lower():
            print("文字数オーバーエラー：X Premium（青バッジ）がないアカウントでは長文投稿できません。")

if __name__ == "__main__":
    main()
