"""
測試腳本 03：gemini-3-pro-image-preview
功能：多模態圖像理解（本地圖片 base64 上傳 + 文字提示 → 文字/圖片回應）
      回應中的 base64 圖片會自動解析並儲存至 output/ 資料夾
用法：
  python test_03_gemini_3_pro_image.py                              # 互動模式（提示輸入）
  python test_03_gemini_3_pro_image.py -i image.jpg                 # 圖片 + 預設提示
  python test_03_gemini_3_pro_image.py -i image.jpg -t "描述這張圖" # 圖片 + 自訂文字
  python test_03_gemini_3_pro_image.py -t "你好，請自我介紹"        # 純文字模式
"""
import os
import sys
import re
import base64
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("NEN_AI_KEY")
BASE_URL = os.getenv("NEN_AI_BASE_URL")
MODEL = "gemini-3-pro-image-preview"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

DEFAULT_TEXT = "請分析這張圖片的內容、色彩和構圖，用繁體中文詳細說明。"
OUTPUT_DIR = Path(__file__).parent / "output"

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def save_image_from_data_uri(data_uri: str, index: int = 0) -> str | None:
    """解析 data URI 中的 base64 圖片並儲存到 output/，回傳儲存路徑。"""
    match = re.match(r"data:(image/[^;]+);base64,(.+)", data_uri, re.DOTALL)
    if not match:
        return None
    mime_type, b64_data = match.group(1), match.group(2)
    ext = MIME_TO_EXT.get(mime_type, ".png")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_DIR / f"output_{timestamp}_{index}{ext}"
    image_bytes = base64.b64decode(b64_data)
    with open(filename, "wb") as f:
        f.write(image_bytes)
    return str(filename)


def extract_and_save_images(content) -> list[str]:
    """從回應 content（字串或 list）中提取並儲存所有 base64 圖片，回傳儲存路徑清單。"""
    saved = []
    if isinstance(content, str):
        # 掃描字串中的 data URI
        for i, match in enumerate(re.finditer(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", content)):
            path = save_image_from_data_uri(match.group(0), i)
            if path:
                saved.append(path)
    elif isinstance(content, list):
        img_idx = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "image_url":
                url = block.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    path = save_image_from_data_uri(url, img_idx)
                    if path:
                        saved.append(path)
                        img_idx += 1
    return saved


def encode_image(image_path: str) -> tuple[str, str]:
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def run(image_path: str | None, text: str):
    print(f"[測試] 模型：{MODEL}")
    if image_path:
        print(f"[測試] 圖片路徑：{image_path}")
    print(f"[測試] 文字提示：{text}")
    print("-" * 50)

    content = []

    if image_path:
        if not Path(image_path).exists():
            print(f"[錯誤] 找不到圖片：{image_path}")
            return
        b64_data, mime_type = encode_image(image_path)
        data_uri = f"data:{mime_type};base64,{b64_data}"
        content.append({"type": "image_url", "image_url": {"url": data_uri}})

    content.append({"type": "text", "text": text})

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        max_tokens=1024,
    )

    raw_content = response.choices[0].message.content

    # 提取並儲存 base64 圖片
    saved_images = extract_and_save_images(raw_content)

    # 顯示文字回應
    if isinstance(raw_content, list):
        text_parts = [b.get("text", "") for b in raw_content if isinstance(b, dict) and b.get("type") == "text"]
        display_text = "\n".join(text_parts) if text_parts else "(無文字回應)"
    else:
        # 將字串中的 data URI 替換為 [image] 佔位符以避免刷屏
        display_text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[base64 image]", raw_content or "")

    print(f"[回應]\n{display_text}")
    print("-" * 50)

    if saved_images:
        print(f"[圖片輸出] 共儲存 {len(saved_images)} 張圖片：")
        for p in saved_images:
            print(f"  → {p}")
        print("-" * 50)

    print(f"[Token 使用] 輸入：{response.usage.prompt_tokens}，輸出：{response.usage.completion_tokens}")


def interactive_mode():
    print(f"[互動模式] 模型：{MODEL}")
    print("直接按 Enter 跳過圖片（純文字模式）")
    print("-" * 50)

    image_path = input("圖片路徑（留空跳過）：").strip() or None
    default_hint = f"（留空使用預設：'{DEFAULT_TEXT}'）" if image_path else "（留空使用預設：'你好'）"
    default_text = DEFAULT_TEXT if image_path else "你好，請自我介紹。"
    text = input(f"文字提示 {default_hint}：").strip() or default_text

    print()
    run(image_path, text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini 3 Pro 圖像理解測試")
    parser.add_argument("-i", "--image", help="本地圖片路徑", default=None)
    parser.add_argument("-t", "--text", help="文字提示", default=None)
    args = parser.parse_args()

    if args.image is None and args.text is None:
        interactive_mode()
    else:
        text = args.text or (DEFAULT_TEXT if args.image else "你好，請自我介紹。")
        run(args.image, text)
