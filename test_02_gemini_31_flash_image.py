"""
測試腳本 02：gemini-3.1-flash-image-preview
功能：多模態圖像理解（本地圖片 base64 上傳 + 文字提示 → 文字回應）
用法：python test_02_gemini_31_flash_image.py [圖片路徑]
      預設圖片路徑：./test_image.jpg
"""
import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("NEN_AI_KEY")
BASE_URL = os.getenv("NEN_AI_BASE_URL")
MODEL = "gemini-3.1-flash-image-preview"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def encode_image(image_path: str) -> tuple[str, str]:
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    mime_type = mime_map.get(suffix, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type

def test_image_understanding(image_path: str):
    print(f"[測試] 模型：{MODEL}")
    print(f"[測試] 圖片路徑：{image_path}")
    print("-" * 50)

    if not Path(image_path).exists():
        print(f"[錯誤] 找不到圖片：{image_path}")
        print("請提供有效的本地圖片路徑作為參數，例如：")
        print("  python test_02_gemini_31_flash_image.py /path/to/image.jpg")
        return

    b64_data, mime_type = encode_image(image_path)
    data_uri = f"data:{mime_type};base64,{b64_data}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": "請詳細描述這張圖片裡有什麼？用繁體中文回答。"},
                ],
            }
        ],
        max_tokens=1024,
    )

    answer = response.choices[0].message.content
    print(f"[回應]\n{answer}")
    print("-" * 50)
    print(f"[Token 使用] 輸入：{response.usage.prompt_tokens}，輸出：{response.usage.completion_tokens}")

if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "./test_image.jpg"
    test_image_understanding(image_path)
