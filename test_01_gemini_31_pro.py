"""
測試腳本 01：gemini-3.1-pro-preview
功能：文字對話（Chat Completion）
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("NEN_AI_KEY")
BASE_URL = os.getenv("NEN_AI_BASE_URL")
MODEL = "gemini-3.1-pro-preview"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def test_chat():
    print(f"[測試] 模型：{MODEL}")
    print(f"[測試] Base URL：{BASE_URL}")
    print("-" * 50)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是一個專業的 AI 助理，請用繁體中文回答。"},
            {"role": "user", "content": "請用三句話介紹人工智慧的發展歷史。"},
        ],
        max_tokens=1024,
        temperature=0.7,
    )

    answer = response.choices[0].message.content
    print(f"[回應]\n{answer}")
    print("-" * 50)
    print(f"[Token 使用] 輸入：{response.usage.prompt_tokens}，輸出：{response.usage.completion_tokens}")

if __name__ == "__main__":
    test_chat()
