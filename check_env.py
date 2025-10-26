import os
from dotenv import load_dotenv

# 1. ライブラリの動作確認
try:
    import streamlit
    import sqlalchemy
    import openai
    import llama_index
    print("✅ 主要ライブラリのインポートに成功しました。")
except ImportError as e:
    print(f"❌ 致命的なエラー: ライブラリのインポートに失敗しました。詳細: {e}")
    exit()

# 2. 環境変数（APIキー）の読み込み確認
load_dotenv() 
openai_api_key = os.getenv("OPENAI_API_KEY")

if openai_api_key:
    print("✅ 環境変数（APIキー）の読み込みに成功しました。")
    
    # 3. LLM APIへの接続確認
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        
        # 非常にシンプルなAPI呼び出しを実行
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt="Hello",
            max_tokens=5
        )
        print(f"✅ LLM APIへの接続と通信に成功しました。応答例: {response.choices[0].text.strip()}")
        print("\n=> これで開発の準備は万全です。次のステップに進みましょう！")
    except Exception as e:
        print(f"❌ 警告: API通信に失敗しました。ファイアウォール、APIキーが有効か、または支払い設定を確認してください。詳細: {e}")
else:
    print("❌ 致命的なエラー: .envファイルに OPENAI_API_KEY が設定されていません。")