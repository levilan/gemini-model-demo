"""
Google Gemini AI Model Testing Platform
FastAPI Backend - newapi (OpenAI-compatible) per-user API Key authentication
"""
import os, json, re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI
import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(title="Gemini AI Testing Platform")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

NEWAPI_BASE_URL = os.getenv("NEWAPI_BASE_URL", "https://nen.com.tw/v1")
PORT = int(os.getenv("PORT", 5002))

for d in ["outputs/images", "outputs/videos"]:
    Path(d).mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ─── Model Registry ───────────────────────────────────────────
MODELS = {
    "text": [
        {"id": "gemini-3.1-pro-preview",      "name": "Gemini 3.1 Pro",        "group": "3.1",  "desc": "最強推理旗艦",      "thinking": True},
        {"id": "gemini-3.1-flash-lite-preview","name": "Gemini 3.1 Flash Lite", "group": "3.1",  "desc": "3.1 極速輕量",      "thinking": False},
        {"id": "gemini-2.5-pro",               "name": "Gemini 2.5 Pro",        "group": "2.5",  "desc": "強大推理旗艦",      "thinking": True},
        {"id": "gemini-2.5-flash",             "name": "Gemini 2.5 Flash",      "group": "2.5",  "desc": "速度與品質均衡",    "thinking": True},
        {"id": "gemini-2.5-flash-lite",        "name": "Gemini 2.5 Flash Lite", "group": "2.5",  "desc": "最低延遲低成本",    "thinking": False},
    ],
    "image": [
        {
            "id": "gemini-3-pro-image-preview", "name": "Gemini 3 Pro Image", "group": "Gemini 3",
            "desc": "旗艦圖像生成",
            "aspect_ratios": ["1:1","16:9","9:16","4:3","3:4","3:2","2:3","4:5","5:4","21:9"],
            "image_sizes": ["1K","2K","4K"],
            "thinking": False,
        },
        {
            "id": "gemini-3.1-flash-image-preview", "name": "Gemini 3.1 Flash Image", "group": "Gemini 3.1",
            "desc": "3.1 快速圖像生成",
            "aspect_ratios": ["1:1","16:9","9:16","4:3","3:4","3:2","2:3","4:5","5:4","21:9"],
            "image_sizes": ["512","1K","2K","4K"],
            "thinking": True,
            "thinking_levels": ["minimal","high"],
        },
        {
            "id": "gemini-2.5-flash-image", "name": "Gemini 2.5 Flash Image", "group": "Gemini 2.5",
            "desc": "快速圖像生成",
            "aspect_ratios": ["1:1","16:9","9:16","4:3","3:4","3:2","2:3"],
            "image_sizes": ["1K","2K"],
            "thinking": False,
        },
    ],
    "video": [
        {
            "id": "veo-3.1-generate-001",      "name": "Veo 3.1",      "group": "Veo",
            "desc": "旗艦影片生成", "min_dur": 4, "max_dur": 8,
        },
        {
            "id": "veo-3.1-fast-generate-001", "name": "Veo 3.1 Fast", "group": "Veo",
            "desc": "快速影片生成", "min_dur": 4, "max_dur": 8,
        },
        {
            "id": "veo-3.1-lite-generate-001", "name": "Veo 3.1 Lite", "group": "Veo",
            "desc": "輕量影片生成", "min_dur": 4, "max_dur": 8,
        },
    ],
}


# ─── Auth ─────────────────────────────────────────────────────
def get_api_key(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授權，請先登入")
    key = authorization[7:].strip()
    if not key:
        raise HTTPException(status_code=401, detail="API Key 不能為空")
    return key


def make_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=NEWAPI_BASE_URL, timeout=60.0)


# ─── Routes ───────────────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


class LoginBody(BaseModel):
    api_key: str = ""


@app.post("/login")
async def login(body: LoginBody):
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="API Key 不能為空")
    return {"success": True}


@app.get("/api/models")
async def get_models(api_key: str = Depends(get_api_key)):
    return MODELS


# ─── Text Generation ──────────────────────────────────────────
class TextGenerateBody(BaseModel):
    model: str = "gemini-3.1-pro-preview"
    prompt: str = ""
    system_prompt: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 8000


@app.post("/api/text/generate")
async def text_generate(body: TextGenerateBody, api_key: str = Depends(get_api_key)):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="提示詞不能為空")

    messages = []
    if body.system_prompt.strip():
        messages.append({"role": "system", "content": body.system_prompt})
    messages.append({"role": "user", "content": body.prompt})

    def generate():
        yield ": ping\n\n"
        try:
            client = make_client(api_key)
            stream = client.chat.completions.create(
                model=body.model,
                messages=messages,
                temperature=body.temperature,
                top_p=body.top_p,
                max_tokens=body.max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Image Generation ─────────────────────────────────────────
class ImageGenerateBody(BaseModel):
    model: str = "gemini-3-pro-image-preview"
    prompt: str = ""
    negative_prompt: str = ""
    aspect_ratio: str = "1:1"
    image_size: str = "1K"
    sample_count: int = 1
    sample_image_style: str = ""
    guidance_scale: Optional[float] = None
    enhance_prompt: bool = False
    add_watermark: bool = True
    safety_setting: str = "block_medium_and_above"
    include_rai_reason: bool = False
    seed: Optional[int] = None
    include_text: bool = False
    thinking_level: Optional[str] = None
    input_image: Optional[str] = None
    input_image_mime: str = "image/jpeg"


@app.post("/api/image/generate")
async def image_generate(body: ImageGenerateBody, api_key: str = Depends(get_api_key)):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="提示詞不能為空")

    # Build message content — include uploaded image when provided
    if body.input_image:
        content: object = [
            {"type": "text", "text": body.prompt.strip()},
            {"type": "image_url", "image_url": {"url": f"data:{body.input_image_mime};base64,{body.input_image}"}},
        ]
    else:
        content = body.prompt.strip()

    # Build extra_body — both Vertex AI (camelCase) and Gemini API (snake_case) styles for proxy compatibility
    extra_body: dict = {
        "sampleCount":      body.sample_count,
        "aspectRatio":      body.aspect_ratio,
        "sampleImageSize":  body.image_size,
        "enhancePrompt":    body.enhance_prompt,
        "addWatermark":     body.add_watermark,
        "safetySetting":    body.safety_setting,
        "includeRaiReason": body.include_rai_reason,
        "image_config": {"aspect_ratio": body.aspect_ratio, "image_size": body.image_size},
        "response_modalities": ["TEXT", "IMAGE"] if body.include_text else ["IMAGE"],
    }
    if body.negative_prompt.strip():
        extra_body["negativePrompt"] = body.negative_prompt.strip()
    if body.guidance_scale is not None:
        extra_body["guidanceScale"] = body.guidance_scale
    if body.seed is not None:
        extra_body["seed"] = body.seed
    if body.sample_image_style:
        extra_body["sampleImageStyle"] = body.sample_image_style
    if body.thinking_level:
        extra_body["thinking_config"]  = {"thinking_level": body.thinking_level}
        extra_body["thinkingConfig"]   = {"thinkingLevel":  body.thinking_level}

    try:
        client = make_client(api_key)
        response = client.chat.completions.create(
            model=body.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
            n=max(1, min(body.sample_count, 4)),
            extra_body=extra_body,
        )

        images = []
        for choice in response.choices:
            raw = choice.message.content or ""
            for match in re.finditer(r"data:image/([^;]+);base64,([A-Za-z0-9+/=]+)", raw):
                images.append({"type": "base64", "data": match.group(2), "mime": f"image/{match.group(1)}"})

        if not images:
            first_raw = response.choices[0].message.content or "" if response.choices else ""
            return JSONResponse(
                {"success": False, "error": f"模型未返回圖像資料。回應：{first_raw[:300]}"},
                status_code=500,
            )

        first_raw = response.choices[0].message.content or "" if response.choices else ""
        text = re.sub(r"!\[.*?\]\(data:image/[^)]+\)", "", first_raw)
        text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "", text).strip()

        return {"success": True, "images": images, "text": text if body.include_text else ""}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ─── Video Generation ─────────────────────────────────────────
class VideoGenerateBody(BaseModel):
    model: str = "veo-3.1-generate-preview"
    prompt: str = ""
    negative_prompt: str = ""
    duration: int = 5
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    fps: Optional[int] = None
    seed: Optional[int] = None
    enhance_prompt: bool = False
    generate_audio: bool = True
    compression_quality: str = "optimized"
    person_generation: str = "allow_adult"
    input_image: Optional[str] = None
    input_image_mime: str = "image/jpeg"
    reference_type: str = "asset"


@app.post("/api/video/generate")
async def video_generate(body: VideoGenerateBody, api_key: str = Depends(get_api_key)):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="提示詞不能為空")

    try:
        url = f"{NEWAPI_BASE_URL}/video/generations"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload: dict = {
            "model":    body.model,
            "prompt":   body.prompt,
            "n":        1,
            "duration": body.duration,
        }
        if body.aspect_ratio:
            payload["aspectRatio"] = body.aspect_ratio
        if body.enhance_prompt:
            payload["enhancePrompt"] = True
        # generateAudio API default is true — only send when user disables it
        if not body.generate_audio:
            payload["generateAudio"] = False
        if body.compression_quality and body.compression_quality != "optimized":
            payload["compressionQuality"] = body.compression_quality
        if body.person_generation and body.person_generation != "allow_adult":
            payload["personGeneration"] = body.person_generation
        if body.negative_prompt.strip():
            payload["negativePrompt"] = body.negative_prompt.strip()
        if body.fps:
            payload["fps"] = body.fps
        if body.seed is not None:
            payload["seed"] = body.seed
        if body.input_image:
            payload["referenceImages"] = [{
                "data":          body.input_image,
                "mimeType":      body.input_image_mime,
                "referenceType": body.reference_type,
            }]
            payload["task"] = "imageToVideo" if body.reference_type == "asset" else "referenceToVideo"
            payload["duration"] = 8  # Enforce 8s when using reference image

        resp = http_requests.post(url, headers=headers, json=payload, timeout=120)
        try:
            result = resp.json()
        except Exception:
            return JSONResponse({"success": False, "error": f"API 回應非 JSON ({resp.status_code})：{resp.text[:400]}"}, status_code=500)

        if not resp.ok:
            err_obj = result.get("error") or {}
            if isinstance(err_obj, dict):
                msg = err_obj.get("message") or err_obj.get("msg") or str(err_obj)
            else:
                msg = str(err_obj) or result.get("message") or str(result)
            return JSONResponse({"success": False, "error": f"[{resp.status_code}] {msg}"}, status_code=500)

        task_id = result.get("id") or result.get("task_id")
        if not task_id and isinstance(result.get("data"), list):
            task_id = result["data"][0].get("id")

        if not task_id:
            return JSONResponse({"success": False, "error": f"未獲得 task_id：{result}"}, status_code=500)

        return {"success": True, "task_id": task_id, "status": result.get("status", "pending")}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/video/status/{task_id}")
async def video_status(task_id: str, api_key: str = Depends(get_api_key)):
    try:
        url = f"{NEWAPI_BASE_URL}/video/generations/{task_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = http_requests.get(url, headers=headers, timeout=30)
        result = resp.json()

        raw_status = (result.get("status") or result.get("state") or "pending").lower()
        status_map = {
            "succeeded": "SUCCEEDED", "success": "SUCCEEDED", "completed": "SUCCEEDED", "finished": "SUCCEEDED",
            "failed": "FAILED", "error": "FAILED", "cancelled": "FAILED",
            "pending": "PENDING", "processing": "PENDING", "running": "PENDING", "queued": "PENDING",
        }
        status = status_map.get(raw_status, "PENDING")

        video_url = None
        if status == "SUCCEEDED":
            data_list = result.get("data") or result.get("videos") or result.get("results") or []
            if isinstance(data_list, list) and data_list:
                item = data_list[0]
                video_url = item.get("url") or item.get("video_url")
                if not video_url and isinstance(item.get("video"), dict):
                    video_url = item["video"].get("url")
            if not video_url:
                video_url = result.get("url") or result.get("video_url")

        error_msg = (result.get("error") or result.get("message")) if status == "FAILED" else None
        return {"status": status, "video_url": video_url, "error_message": error_msg}
    except Exception as e:
        return {"status": "PENDING", "error_message": str(e)}


# ─── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT,
                reload=os.getenv("DEBUG", "false").lower() == "true")
