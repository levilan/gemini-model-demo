"""
測試腳本 05：gemini-embedding-2-preview
功能：進階文字嵌入向量，語意搜索排名
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
MODEL = "gemini-embedding-2-preview"
LOCATION = "us-central1"
ENDPOINT = (
    f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}"
    f"/locations/{LOCATION}/publishers/google/models/{MODEL}:embedContent"
)

QUERY = "如何提升機器學習模型的準確率？"
CANDIDATES = [
    "資料清理和特徵工程是改善模型效能的關鍵步驟。",
    "增加訓練資料量、調整超參數和使用集成方法都能提高準確率。",
    "今天午餐吃了一碗拉麵，非常美味。",
    "深度學習需要大量的計算資源和 GPU 支援。",
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
        json={"content": {"parts": [{"text": text}]}},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embedding"]["values"]

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x ** 2 for x in a))
    nb = math.sqrt(sum(x ** 2 for x in b))
    return dot / (na * nb) if na and nb else 0.0

def test_semantic_search():
    print(f"[測試] 模型：{MODEL}")
    print(f"[測試] 端點：{ENDPOINT}")
    print("-" * 50)
    print(f"[查詢語句] {QUERY}")
    print()

    token = get_access_token()
    query_vec = get_embedding(QUERY, token)
    print(f"查詢向量維度：{len(query_vec)}")
    print()

    results = []
    for text in CANDIDATES:
        vec = get_embedding(text, token)
        sim = cosine_similarity(query_vec, vec)
        results.append((sim, text))

    results.sort(key=lambda x: x[0], reverse=True)

    print("[相似度排名]")
    for rank, (sim, text) in enumerate(results, 1):
        print(f"  第 {rank} 名（{sim:.4f}）：{text}")

if __name__ == "__main__":
    test_semantic_search()
