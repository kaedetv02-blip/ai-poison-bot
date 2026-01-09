import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import sys
import io
import os
import random

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：架空謝罪会見Bot（知恵袋ソース）を開始します...")

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
    # 1. Yahoo!知恵袋からネタ（種）を収集
    # ==================================================
    # 修正：確実に存在する「ランキングトップ」を使用
    chiebukuro_url = "https://chiebukuro.yahoo.co.jp/ranking"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    topics = []

    try:
        print(f"知恵袋ランキングを取得中... ({chiebukuro_url})")
        resp = requests.get(chiebukuro_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            # リンクのテキストから質問タイトルらしきものを抽出
            links = soup.find_all('a')
            for link in links:
                text = link.get_text().strip()
                # 質問タイトルっぽい長さのものだけ拾う（ノイズ除去）
                # 「〜とは？」や「〜ですか？」などの疑問形、またはある程度の長さがあるもの
                if 10 < len(text) < 60:
                    topics.append(text)
            
            if not topics:
                print("⚠️ 知恵袋からうまくテキストが取れませんでした。デモデータを使用します。")
                topics = ["きのこの山とたけのこの里どっちが好き？", "目玉焼きに何をかけますか？", "靴下を裏返しで履いてしまいました"]
            else:
                print("✅ ネタの取得に成功しました！")
        else:
            print(f"⚠️ 知恵袋アクセス失敗: Status {resp.status_code}")
            topics = ["プリンを勝手に食べた", "リモコンの電池を抜いたまま放置した", "トイレットペーパーの芯を替えない"]

    except Exception as e:
        print(f"⚠️ エラー発生: {e}")
        topics = ["賞味期限切れの牛乳を飲んだ", "エレベーターの閉めるボタンを連打した"]

    # 取得したネタからランダムに1つ選ぶ
    selected_topic = random.choice(topics[:20]) # 上位20個くらいから選ぶ
    print(f"★選ばれたネタ（不祥事の種）: {selected_topic}")

    # ==================================================
    # 2. AIによる「架空の謝罪文」生成
    # ==================================================
    print("AIが謝罪文を作成中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは社会的地位のある人物（政治家やCEO）として「緊急謝罪会見」を行ってください。
    以下の【知恵袋の質問・話題】をヒントにして、「あまりにもくだらない架空の不祥事」をでっち上げ、死ぬほど真面目なトーンで謝罪してください。

    【ネタ元（知恵袋の話題）】
    {selected_topic}

    【指示】
    1. **内容**: ネタ元を参考に、「きのこの山をたけのこの里の箱に入れた」「靴下の左右を間違えた」レベルの、**誰も傷つかないどうでもいい罪**を告白してください。
    2. **トーン**: 報道陣のフラッシュが見えるくらい、**重苦しく、誠実で、シリアスな文体**にしてください。
    3. **ギャップ**: 「内容はアホなのに、文章は企業の不祥事謝罪レベル」というギャップで笑わせてください。
    4. **長さ**: 140字ギリギリまで使って状況を説明してください。

    【出力形式】
    以下の形式のみを出力してください。

    【謝罪会見】
    (ここに謝罪文)
    #架空謝罪会見 #誠にごめんなさい
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
        # 詳細なエラー情報を出すように変更
        print(f"❌ 投稿失敗：{e}")

if __name__ == "__main__":
    main()
