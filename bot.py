import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import random
import sys
import io
import time
import os

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
        print("❌ エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit()

    # ==================================================
    # 1. ネタ元リスト（VIP・ネタ系限定）
    # ==================================================
    rss_urls = [
        "http://blog.livedoor.jp/news23vip/index.rdf",       # VIPPERな俺
        "http://vipper.2chblog.jp/index.rdf",                # VIPPER速報
        "http://minnanohimatubushi.2chblog.jp/index.rdf",    # みんなの暇つぶし
        "http://rajic.2chblog.jp/index.rdf",                 # ライフハックちゃんねる
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # ==================================================
    # 記事選び（リトライ処理付き）
    # ==================================================
    # 3回まで再挑戦します
    for attempt in range(3):
        print(f"--- 記事探し チャレンジ {attempt + 1}回目 ---")
        
        try:
            target_rss = random.choice(rss_urls)
            print(f"ターゲットサイト: {target_rss}")

            # RSS取得
            resp = requests.get(target_rss, headers=headers, timeout=10)
            
            # ★XMLとして正しくパースする（lxmlを使用）
            soup = BeautifulSoup(resp.content, 'xml')
            
            items = soup.find_all('item')
            # サイトによっては 'entry' タグの場合がある
            if not items:
                items = soup.find_all('entry')

            if not items:
                print("記事が見つかりませんでした。別のサイトを試します。")
                continue 

            # ランダムに1記事選ぶ
            chosen_item = random.choice(items)
            
            # タイトル取得
            title_tag = chosen_item.find('title')
            title = title_tag.get_text().strip() if title_tag else "タイトル不明"

            # URL取得
            link_tag = chosen_item.find('link')
            link = link_tag.get_text().strip() if link_tag else ""

            # URLが空っぽならスキップする
            if not link:
                print(f"❌ URLの取得に失敗しました（タイトル: {title}）。スキップします。")
                continue

            # NGワードチェック
            ng_words = ["政治", "首相", "野球", "メジャー", "韓国", "中国", "党", "選手", "大谷"]
            if any(word in title for word in ng_words):
                print(f"NGワードを含むためスキップ: {title}")
                continue

            print(f"候補記事: {title}")
            print(f"URL: {link}")
            time.sleep(2) 

            # 記事本文を取りに行く
            article_resp = requests.get(link, headers=headers, timeout=10)
            
            if article_resp.status_code != 200:
                print(f"❌ アクセスできませんでした (Status: {article_resp.status_code})。")
                continue

            # 記事本文はHTMLなので 'html.parser' でOK
            article_soup = BeautifulSoup(article_resp.content, 'html.parser')

            # 本文抽出
            body_tag = article_soup.find('body')
            if not body_tag:
                 print("❌ 本文が見つかりませんでした。")
                 continue
            
            # テキストのみ抽出して整形
            body_text = body_tag.get_text()
            clean_text = ' '.join(body_text.split())
            
            if len(clean_text) < 100:
                print("❌ 本文が短すぎます。")
                continue

            content_for_ai = clean_text[:3000]
            
            # ここまで来たら成功！ループを抜ける
            break
        
        except Exception as e:
            print(f"エラー発生: {e}")
            continue
    else:
        # ループが3回とも失敗した場合
        print("❌ 3回試行しましたが、有効な記事が見つかりませんでした。")
        sys.exit()

    # ==================================================
    # 2. AIによる要約生成
    # ==================================================
    print("AIが記事を要約中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは「2ch（5ch）のしょうもないスレを紹介する暇つぶしBot」です。
    以下の【Webサイトのテキスト】は、まとめブログの文章です。
    広告やメニューなどのノイズを除去し、スレの「タイトル」と「内容」を面白おかしく紹介してください。

    【Webサイトのテキスト】:
    タイトル：{title}
    本文の一部：{content_for_ai}

    【出力ルール】
    1. 1行目：記事のタイトルをそのまま書く（【】で囲む）。
    2. 2行目以降：スレのあらすじ、イッチの行動、オチなどを「3点の箇条書き」で要約する。
    3. 最後に一言：あなたの感想を「～ワロタ」「～草」などのネットスラングで短く添える。
    4. 政治、スポーツ、真面目なニュースだった場合は、要約せずに「解散！」とだけ出力せよ。
    
    出力例：
    【悲報】ワイ、会社で「お前無能だな」って言われたから言い返した結果ｗｗｗ

    ・上司にミスを指摘されて逆ギレしたイッチ
    ・「お前こそハゲやんけ」と言い放ち会議室が凍りつく
    ・現在は無敵の人となって自宅警備員をしている模様

    さすがにこれはイッチが悪いやろｗ メンタル強すぎワロタ
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, 
        )
        ai_output = response.choices[0].message.content
        print(f"★生成結果:\n{ai_output}")
        
        if "解散！" in ai_output:
            print("AI判定により投稿を見送ります。")
            sys.exit()

    except Exception as e:
        print(f"エラー：AI生成に失敗しました: {e}")
        sys.exit()

    # 3. 投稿
    tweet_content = f"{ai_output}\n\n元記事: {link}\n#2ch #暇つぶし #面白いスレ"

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

if __name__ == "__main__":
    main()
