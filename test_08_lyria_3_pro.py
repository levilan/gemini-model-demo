"""
測試腳本 08：lyria-3-pro-preview
功能：音樂/音頻生成（文字提示 → 本地下載音頻檔）
說明：Lyria 是 Google 的音樂生成 AI 模型
輸出：./output_lyria3.mp3（或 .wav，依 API 回傳格式）
"""
import os
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEN_AI_KEY")
BASE_URL = os.getenv("NEN_AI_BASE_URL", "").rstrip("/")
MODEL = "lyria-3-pro-preview"
OUTPUT_FILE = "./output_lyria3"  # 副檔名依回傳格式決定

MUSIC_PROMPT = (
    "A calm and uplifting piano melody with soft strings, "
    "suitable for meditation and relaxation, 30 seconds duration."
)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def submit_music_generation() -> tuple[str | None, dict]:
    url = f"{BASE_URL}/audio/speech"
    payload = {
        "model": MODEL,
        "input": MUSIC_PROMPT,
        "voice": "alloy",
    }
    print(f"[提交] 傳送音樂生成請求...")
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=120)
    data = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    print(f"[提交] HTTP {resp.status_code}")

    if resp.status_code == 503:
        msg = data.get("message", "")
        print(f"\n[提示] 音樂生成失敗：{msg}")
        print("  lyria-3-pro-preview 在此 NewAPI 實例目前無可用管道（無上游設定）。")
        print("  請聯絡 NewAPI 管理員確認管道設定，或等待模型正式開放。")
        return None, data

    if resp.status_code not in (200, 202):
        resp.raise_for_status()

    # 若直接回傳音頻 bytes
    if resp.headers.get("Content-Type", "").startswith("audio/"):
        return "direct_audio", {"_raw_bytes": resp.content, "_content_type": resp.headers["Content-Type"]}

    task_id = data.get("id") or data.get("task_id")
    return task_id, data

def poll_task(task_id: str, max_wait: int = 300) -> dict:
    url = f"{BASE_URL}/audio/generations/{task_id}"
    elapsed = 0
    interval = 5
    while elapsed < max_wait:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "unknown")
        print(f"[輪詢] 狀態：{status}（已等待 {elapsed} 秒）")
        if status in ("succeeded", "completed", "finished"):
            return data
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"音樂生成失敗：{data}")
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"等待超過 {max_wait} 秒，任務仍未完成")

def save_audio(data: dict):
    audio_url = None
    b64_data = None
    file_ext = "mp3"

    # 嘗試各種可能的回應格式
    audio_list = data.get("data") or data.get("audio") or data.get("results") or []
    if isinstance(audio_list, list) and audio_list:
        item = audio_list[0]
        audio_url = item.get("url") or item.get("audio_url")
        b64_data = item.get("b64_json") or item.get("audio")

    # OpenAI audio speech 格式
    if not b64_data and not audio_url:
        content_type = data.get("content_type", "audio/mpeg")
        if "wav" in content_type:
            file_ext = "wav"
        b64_data = data.get("b64_json") or data.get("audio_content")

    output_path = f"{OUTPUT_FILE}.{file_ext}"

    if b64_data:
        audio_bytes = base64.b64decode(b64_data)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"[完成] 音頻已儲存（base64）：{output_path}")
    elif audio_url:
        resp = requests.get(audio_url, timeout=120)
        resp.raise_for_status()
        # 從 Content-Type 判斷格式
        ct = resp.headers.get("Content-Type", "")
        if "wav" in ct:
            output_path = f"{OUTPUT_FILE}.wav"
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"[完成] 音頻已下載：{output_path}（來源：{audio_url}）")
    else:
        print(f"[警告] 無法從回應中找到音頻資料，完整回應：{data}")

def test_music_generation():
    print(f"[測試] 模型：{MODEL}")
    print(f"[測試] Base URL：{BASE_URL}")
    print(f"[測試] 提示詞：{MUSIC_PROMPT}")
    print("-" * 50)

    task_id, initial_data = submit_music_generation()

    if task_id is None:
        return

    # 直接音頻回傳
    if task_id == "direct_audio":
        raw = initial_data["_raw_bytes"]
        ct = initial_data.get("_content_type", "audio/mpeg")
        ext = "wav" if "wav" in ct else "mp3"
        path = f"{OUTPUT_FILE}.{ext}"
        with open(path, "wb") as f:
            f.write(raw)
        print(f"[完成] 音頻已儲存：{path}（{len(raw)} bytes）")
        return

    status = initial_data.get("status", "")
    if status in ("succeeded", "completed") or initial_data.get("data"):
        print("[完成] 同步回應，直接儲存音頻")
        save_audio(initial_data)
        return

    if task_id:
        print(f"[任務 ID] {task_id}")
        final_data = poll_task(task_id)
        save_audio(final_data)
    else:
        save_audio(initial_data)

if __name__ == "__main__":
    test_music_generation()
