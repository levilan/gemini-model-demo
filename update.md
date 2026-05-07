# Google AI Lab — 更新紀錄

---

## 2026-05-02 — NewAPI 8 模型功能測試腳本

### 新增檔案

| 檔案 | 模型 | 功能 |
|------|------|------|
| `test_01_gemini_31_pro.py` | gemini-3.1-pro-preview | 文字對話（Chat Completion） |
| `test_02_gemini_31_flash_image.py` | gemini-3.1-flash-image-preview | 圖像理解（本地圖片 base64 上傳） |
| `test_03_gemini_3_pro_image.py` | gemini-3-pro-image-preview | 圖像分析（Pro 模型） |
| `test_04_gemini_embedding_001.py` | gemini-embedding-001 | 文字嵌入向量 |
| `test_05_gemini_embedding_2.py` | gemini-embedding-2-preview | 語意搜索排名 |
| `test_06_veo_31_generate.py` | veo-3.1-generate-preview | 影片生成（輪詢下載） |
| `test_07_veo_31_fast.py` | veo-3.1-fast-generate-preview | 快速影片生成 |
| `test_08_lyria_3_pro.py` | lyria-3-pro-preview | 音樂生成 |

### .env 新增

```
NEN_AI_BASE_URL="http://192.168.0.245/v1"
```

### 測試結果

| 模型 | 狀態 | 說明 |
|------|------|------|
| gemini-3.1-pro-preview | ✅ 正常 | 中文對話回應正常 |
| gemini-3.1-flash-image-preview | ✅ 正常 | 圖像理解正確（3072 dim） |
| gemini-3-pro-image-preview | ✅ 正常 | 圖像分析詳細 |
| gemini-embedding-001 | ✅ 正常 | 3072 維向量，cosine similarity 正確 |
| gemini-embedding-2-preview | ✅ 正常 | 語意排名合理 |
| veo-3.1-generate-preview | ⚠️ 受阻 | 專案未獲 Veo 存取授權 |
| veo-3.1-fast-generate-preview | ⚠️ 受阻 | 同上 |
| lyria-3-pro-preview | ⚠️ 受阻 | NewAPI 無上游管道設定 |

### 技術備註

**Embedding 端點差異**
- `gemini-embedding-001`：NewAPI `/embeddings` 端點無效，改用 Vertex AI `predict` API
  - 端點：`/v1/projects/{project}/locations/us-central1/publishers/google/models/gemini-embedding-001:predict`
  - 請求格式：`{"instances": [{"content": "..."}]}`
- `gemini-embedding-2-preview`：使用 Vertex AI `embedContent` API
  - 端點：`/v1beta1/projects/{project}/locations/us-central1/publishers/google/models/gemini-embedding-2-preview:embedContent`
  - 請求格式：`{"content": {"parts": [{"text": "..."}]}}`
- 兩者均需 `GOOGLE_APPLICATION_CREDENTIALS` 服務帳戶認證

**影片生成端點**
- NewAPI 正確端點：`/video/generations`（非 `/videos/generations`）
- 目前受阻原因：Veo 3.1 為 preview 模型，需 Google Cloud 申請存取白名單

**Lyria 音樂生成**
- NewAPI 端點：`/audio/speech`
- 目前受阻原因：NewAPI 管理後台尚未設定 lyria-3-pro-preview 上游管道

### 待辦事項

- [ ] 申請 Google Cloud Veo 3.1 存取白名單（tests 06/07）
- [ ] NewAPI 管理員設定 lyria-3-pro-preview 上游管道（test 08）
- [ ] 待 Veo/Lyria 啟用後驗證影片/音頻下載輸出

---

## 2026-05-08 — FastAPI 影片生成邏輯與 UI 修正

### 修改檔案
| 檔案 | 說明 |
|------|------|
| `app.py` | 修正 Veo 影片生成 API 請求邏輯。當請求包含參考圖片（`input_image`）時，強制將 `duration` 覆寫為 `8` 秒，以符合 API 限制。 |
| `static/js/app.js` | 修改影片生成的前端邏輯。上傳參考圖片時，自動將時長鎖定為 8 秒並禁用選單；移除圖片時恢復。同時將輪詢逾時時間從 15 分鐘延長至 30 分鐘。 |
| `templates/index.html` | 將影片時長的 UI 輸入控制項從滑桿（range）改為下拉選單（select），僅允許選擇 4 秒、6 秒或 8 秒，防止使用者輸入無效時長。 |

### 解決的問題
1. **參考圖片生成影片卡住**：之前若未強制設定時長為 8 秒，Veo Image-to-Video API 會因參數不符導致任務失敗或卡住。
2. **無效時長輸入**：防止使用者輸入 API 不支援的影片時長（如 5 秒或 7 秒）。
3. **輪詢超時**：影片生成耗時較長，延長前端輪詢等待時間，改善使用者體驗。

### 待解決問題
- **Veo 影片生成仍報 401 錯誤**：目前測試中，發往 `https://nen.com.tw/v1` 的影片生成請求返回 `401 Unauthorized: 无效的令牌`。該 API Key 可成功呼叫文字模型，但無法使用影片模型。推測是代理伺服器（NewAPI）權限或路由設定問題。
