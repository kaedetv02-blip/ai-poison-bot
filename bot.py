import tweepy
from openai import OpenAI
import sys
import io
import os
import datetime

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：架空謝罪会見Bot（脱マンネリ版）を開始します...")

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

    # プロンプト修正：具体的な例文を削除し、「罪のジャンル」を指定して多様性を出す
    prompt = f"""
    あなたは社会的地位のある人物（政治家やCEO）として「緊急謝罪会見」を行ってください。
    
    【今日の日付】
    {date_str}

    【指示】
    1. **裏テーマ**: 今日（{date_str}）が何の記念日か知識から検索し、それをネタの着想元にしてください。（投稿には記念日名は出さないでください）
    2. **不祥事の内容（最重要）**: 
       * 記念日に絡めつつ、以下の**「人間味のあるダメな行動リスト」**からランダムに1つの要素を選んで、具体的なエピソードを作ってください。
       
       **【人間味のあるダメな行動リスト】**
       * **怠惰**: 二度寝、後回し、面倒くさがって手抜きをした。
       * **食欲**: カロリー無視、夜食、人の分まで食べた、つまみ食い。
       * **虚勢**: 知ったかぶり、見栄を張った、話を盛った。
       * **不注意**: スマホを見ながら歩いた、足の小指をぶつけた、保存し忘れた。
       * **社会的気まずさ**: 挨拶を無視したふりをした、名前を忘れて誤魔化した。
       * **物欲**: 無駄遣いした、限定品に釣られた、課金した。

    3. **禁止事項**: 
       * シュールすぎるファンタジー（宇宙人、魔法など）はNG。
       * 例文に引っ張られないよう、**毎回全く違うシチュエーション**で書いてください。
    
    4. **トーン**: 内容は上記のような「しょうもないこと」ですが、文章は**「国家の存亡に関わるレベル」に重苦しく、シリアス**に書いてください。
    5. **長さ**: 130字以内（日本語）。

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
    # 連投エラー回避用スタンプ
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
            print("🛑 重複エラー：内容を変えてください。")
        elif "403" in str(e):
            print("🛑 権限エラー：GitHubの鍵を確認してください。")

if __name__ == "__main__":
    main()
