# Gemini AI Model Testing Platform

這是一個基於 FastAPI 與 Web 前端打造的 Google Gemini / Veo / AI 模型測試平台。本系統透過相容於 OpenAI 格式的 NewAPI 代理伺服器，讓您可以輕鬆地在網頁介面上測試文字、圖像、影片及音樂生成模型。

## 🌟 功能特色

- **文字生成**：支援 Gemini 3.1 Pro / Flash 等多種大型語言模型，並提供 Temperature 與 Top-P 等參數調整。
- **圖像生成**：支援 Gemini Imagen 系列模型生成與編輯，支援參考圖片、浮水印開關與長寬比設定。
- **影片生成**：支援 Veo 3.1 影片生成，包含文字轉影片與圖片轉影片（支援自動時長限制與輪詢狀態）。

## 📋 系統需求

- [Docker](https://www.docker.com/get-started) 及 [Docker Compose](https://docs.docker.com/compose/install/) (建議部署方式)
- Python 3.11+ (若採本地端直接執行)
- 有效的 NewAPI API Key

---

## 🚀 部署指南 (使用 Docker)

最簡單且推薦的執行方式是透過 Docker Compose。

### 1. 取得程式碼

```bash
git clone https://github.com/levilan/gemini-model-demo.git
cd gemini-model-demo
```

### 2. 環境變數設定

複製提供的範例環境變數檔案，並根據您的需求進行修改：

```bash
cp .env.example .env
```

編輯 `.env` 檔案（使用 `nano .env` 或您習慣的編輯器）：

```ini
# NewAPI 代理伺服器網址
NEN_AI_BASE_URL="https://nen.com.tw/v1"

# 用於本地測試腳本的 API Key (前端網頁不依賴此變數，使用者需在網頁上登入)
NEN_AI_KEY="sk-您的APIKey"

# 服務啟動的 Port
PORT=5002

# Debug 模式 (true/false)
DEBUG=false
```

### 3. 啟動服務

使用 Docker Compose 在背景建立並啟動服務：

```bash
docker compose up -d --build
```

### 4. 開始使用

打開您的瀏覽器，前往：
👉 **http://localhost:5002**

在網頁登入畫面中，輸入您在 NewAPI 系統上的有效 **API Key**，即可開始測試各項生成模型！

---

## 🛠️ 開發與本地執行 (不使用 Docker)

如果您希望在本地環境直接執行或修改程式碼，請依循以下步驟：

### 1. 建立虛擬環境

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或是 Windows: .venv\Scripts\activate
```

### 2. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 3. 啟動 FastAPI 伺服器

確保您已經設定好 `.env` 檔案後，執行：

```bash
python app.py
```

伺服器預設會運行於 `http://0.0.0.0:5002`。

---

## 📂 目錄結構說明

- `app.py`：FastAPI 後端主程式，處理路由與轉發 API 請求。
- `templates/index.html`：前端介面。
- `static/`：包含前端使用的 CSS 樣式 (`style.css`) 與 JavaScript 邏輯 (`app.js`)。
- `docker-compose.yml` & `Dockerfile`：容器化部署設定。
- `test_*.py`：各類模型的單獨 CLI 測試腳本，可用於診斷 API 連線。

## ⚠️ 注意事項

- **影片生成時長限制**：使用參考圖片生成影片時，Veo API 目前僅支援 8 秒。前端與後端皆已做好強制約束。
- **任務逾時**：Veo 影片生成與 Lyria 音樂生成皆為非同步任務，耗時較長。前端設定最高會輪詢 30 分鐘等待結果。
- **401 Unauthorized**：若在使用過程中或執行 `test_xx.py` 時遇到此錯誤，請檢查您的 API Key 是否正確、是否有對應模型的權限、以及是否餘額充足。

## ⚙️ CI/CD

本專案已配置 GitHub Actions。每當程式碼推送到 `main` 分支時，會自動觸發 Docker Image 編譯檢查，以確保程式碼可以正常建置。