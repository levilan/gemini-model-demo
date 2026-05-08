"""
測試腳本 04：gemini-embedding-001
功能：文字嵌入向量（Embeddings）
說明：NewAPI proxy 的 /embeddings 端點尚未正確對應此模型，
      改用 Vertex AI 原生 OAuth2 方式直接呼叫
"""
import os
import math
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account
from dotenv import load_dotenv
import requests

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.getenv("PROJECT_ID")
MODEL = "gemini-embedding-001"
LOCATION = "us-central1"
ENDPOINT = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}"
    f"/locations/{LOCATION}/publishers/google/models/{MODEL}:predict"
)

TEST_TEXTS = [
    "人工智慧正在改變世界的每一個角落。",
    "機器學習是人工智慧的重要分支。",
    "今天天氣非常晴朗，適合出門散步。",
]

def get_access_token() -> str:
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token

def get_embedding(text: str, token: str) -> list[float]:
    resp = requests.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"instances": [{"content": text}], "parameters": {}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["predictions"][0]["embeddings"]["values"]

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x ** 2 for x in a))
    nb = math.sqrt(sum(x ** 2 for x in b))
    return dot / (na * nb) if na and nb else 0.0

def test_embeddings():
    print(f"[測試] 模型：{MODEL}")
    print(f"[測試] 端點：{ENDPOINT}")
    print("-" * 50)

    token = get_access_token()
    vectors = []
    for i, text in enumerate(TEST_TEXTS):
        vec = get_embedding(text, token)
        vectors.append(vec)
        print(f"[文本 {i+1}] {text}")
        print(f"  向量維度：{len(vec)}")
        print(f"  前 5 個值：{[round(v, 6) for v in vec[:5]]}")
        print()

    print("-" * 50)
    print("[相似度計算]")
    for i in range(len(TEST_TEXTS)):
        for j in range(i + 1, len(TEST_TEXTS)):
            sim = cosine_similarity(vectors[i], vectors[j])
            print(f"  文本{i+1} vs 文本{j+1}：{sim:.4f}")

if __name__ == "__main__":
    test_embeddings()
