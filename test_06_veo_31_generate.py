"""
測試腳本 06：veo-3.1-generate-001
功能：影片生成（文字提示 → 本地下載 MP4）
說明：Veo 影片生成是非同步任務，需要輪詢狀態直到完成
輸出：./output_veo31.mp4
"""
import os
import time
import json
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEN_AI_KEY")
BASE_URL = os.getenv("NEN_AI_BASE_URL", "").rstrip("/")
MODEL = "veo-3.1-generate-001"
OUTPUT_FILE = "./output_veo31.mp4"

VIDEO_PROMPT = (
    "A serene mountain lake at sunrise, with mist rising from the water, "
    "pine trees reflected on the glassy surface, cinematic 4K quality."
)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def submit_video_generation() -> tuple[str, dict]:
    url = f"{BASE_URL}/video/generations"
    payload = {
        "model": MODEL,
        "prompt": VIDEO_PROMPT,
        "n": 1,
    }
    print(f"[提交] 傳送影片生成請求...")
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=120)
    data = resp.json()
    print(f"[提交] HTTP {resp.status_code} 回應：{json.dumps(data, ensure_ascii=False)[:400]}")

    if resp.status_code == 404 and "NOT_FOUND" in data.get("message", ""):
        print("\n[提示] 影片生成失敗：專案尚未獲得 Veo 3.1 模型的存取權限。")
        print("  請聯絡 Google Cloud 申請 Veo API 存取，或確認 NewAPI 管道設定。")
        return None, data

    if resp.status_code not in (200, 202):
        resp.raise_for_status()

    task_id = data.get("id") or data.get("task_id") or (data.get("data") or [{}])[0].get("id")
    return task_id, data

def poll_task(task_id: str, max_wait: int = 600) -> dict:
    url = f"{BASE_URL}/video/generations/{task_id}"
    elapsed = 0
    interval = 10
    while elapsed < max_wait:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "unknown")
        print(f"[輪詢] 狀態：{status}（已等待 {elapsed} 秒）")
        if status in ("succeeded", "completed", "finished"):
            return data
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"影片生成失敗：{data}")
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"等待超過 {max_wait} 秒，任務仍未完成")

def save_video(data: dict):
    # 嘗試各種可能的回應格式
    video_url = None
    b64_data = None

    videos = data.get("data") or data.get("videos") or data.get("results") or []
    if isinstance(videos, list) and videos:
        item = videos[0]
        video_url = item.get("url") or item.get("video_url")
        b64_data = item.get("b64_json") or item.get("video")

    if b64_data:
        video_bytes = base64.b64decode(b64_data)
        with open(OUTPUT_FILE, "wb") as f:
            f.write(video_bytes)
        print(f"[完成] 影片已儲存（base64）：{OUTPUT_FILE}")
    elif video_url:
        resp = requests.get(video_url, timeout=120)
        resp.raise_for_status()
        with open(OUTPUT_FILE, "wb") as f:
            f.write(resp.content)
        print(f"[完成] 影片已下載：{OUTPUT_FILE}（來源：{video_url}）")
    else:
        print(f"[警告] 無法從回應中找到影片資料，完整回應：{data}")

def test_video_generation():
    print(f"[測試] 模型：{MODEL}")
    print(f"[測試] Base URL：{BASE_URL}")
    print(f"[測試] 提示詞：{VIDEO_PROMPT}")
    print("-" * 50)

    task_id, initial_data = submit_video_generation()

    if task_id is None:
        return

    # 若同步直接返回影片
    status = initial_data.get("status", "")
    if status in ("succeeded", "completed") or initial_data.get("data"):
        print("[完成] 同步回應，直接儲存影片")
        save_video(initial_data)
        return

    if not task_id:
        print(f"[錯誤] 無法取得任務 ID，完整回應：{initial_data}")
        return

    print(f"[任務 ID] {task_id}")
    final_data = poll_task(task_id)
    save_video(final_data)

if __name__ == "__main__":
    test_video_generation()
