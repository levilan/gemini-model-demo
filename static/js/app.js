/* ══════════════════════════════════════════════════════════
   Google Gemini AI Testing Platform — Frontend Logic
   ══════════════════════════════════════════════════════════ */

'use strict';

// ─── State ───────────────────────────────────────────────────
let apiKey = '';
let models = { text: [], image: [], video: [], music: [] };
let videoTasks = {};   // task_id → { prompt, model, startTime, interval }
let musicTask = null;  // { task_id, interval }

// ─── Helpers ─────────────────────────────────────────────────
function authHeader() {
    return { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' };
}

async function apiPost(path, body) {
    const res = await fetch(path, { method: 'POST', headers: authHeader(), body: JSON.stringify(body) });
    return res.json();
}

function toast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => { el.classList.add('hide'); setTimeout(() => el.remove(), 280); }, 3000);
}

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading
        ? `<span class="spinner"></span> 處理中…`
        : btn.dataset.label;
}

function populateSelect(id, items, labelFn, valueFn = m => m.id) {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = '';
    items.forEach(m => {
        const opt = document.createElement('option');
        opt.value = valueFn(m);
        opt.textContent = labelFn(m);
        sel.appendChild(opt);
    });
}

function fmtTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ─── Auth ─────────────────────────────────────────────────────
async function handleLogin() {
    const input = document.getElementById('apiKeyInput');
    const errEl = document.getElementById('loginError');
    const key = input.value.trim();
    if (!key) { errEl.textContent = '請輸入 API Key'; return; }
    errEl.textContent = '';
    setLoading('loginBtn', true);
    document.getElementById('loginBtn').dataset.label = '登入';

    try {
        const res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key }),
        });
        const data = await res.json();
        if (data.success) {
            apiKey = key;
            sessionStorage.setItem('gemini_api_key', key);
            enterApp();
        } else {
            errEl.textContent = data.error || '登入失敗';
        }
    } catch (e) {
        errEl.textContent = `連線失敗：${e.message}`;
    } finally {
        setLoading('loginBtn', false);
    }
}

function handleLogout() {
    apiKey = '';
    sessionStorage.removeItem('gemini_api_key');
    models = { text: [], image: [], video: [], music: [] };
    videoTasks = {};
    musicTask = null;
    document.getElementById('appLayout').style.display = 'none';
    document.getElementById('loginOverlay').style.display = 'flex';
    document.getElementById('apiKeyInput').value = '';
}

async function enterApp() {
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('appLayout').style.display = 'flex';
    const display = document.getElementById('apiKeyDisplay');
    if (display) display.textContent = apiKey.slice(0, 8) + '…' + apiKey.slice(-4);
    await loadModels();
    switchTab('text');
}

async function loadModels() {
    try {
        const res = await fetch('/api/models', { headers: { 'Authorization': `Bearer ${apiKey}` } });
        if (res.status === 401) { handleLogout(); return; }
        models = await res.json();
        refreshAllModelSelects();
    } catch (e) {
        toast(`載入模型失敗：${e.message}`, 'error');
    }
}

function refreshAllModelSelects() {
    populateSelect('textModel', models.text || [], m => `${m.name} (${m.group}) — ${m.desc}`);
    populateSelect('imgModel',  models.image || [], m => `${m.name} — ${m.desc}`);
    onImgModelChange();
    populateSelect('vidModel',  models.video || [], m => `${m.name} — ${m.desc}`);
    onVidModelChange();
    populateSelect('musModel',  models.music || [], m => `${m.name} — ${m.desc}`);
}

// ─── Tab Switch ───────────────────────────────────────────────
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const tabEl = document.getElementById(`tab-${tab}`);
    if (tabEl) tabEl.classList.add('active');
    const navEl = document.querySelector(`.nav-item[data-tab="${tab}"]`);
    if (navEl) navEl.classList.add('active');
}

// ─── Text Generation ──────────────────────────────────────────
async function sendText() {
    const prompt = document.getElementById('textPrompt').value.trim();
    if (!prompt) { toast('請輸入提示詞', 'error'); return; }
    const model = document.getElementById('textModel').value;
    const systemPrompt = document.getElementById('textSystem').value.trim();
    const temperature = parseFloat(document.getElementById('tempRange').value);
    const topP = parseFloat(document.getElementById('topPRange').value);
    const maxTokens = parseInt(document.getElementById('maxTokensInput').value) || 4096;

    setLoading('textSendBtn', true);
    const respBox = document.getElementById('textResponse');
    respBox.textContent = '';

    try {
        const res = await fetch('/api/text/generate', {
            method: 'POST',
            headers: authHeader(),
            body: JSON.stringify({ model, prompt, system_prompt: systemPrompt, temperature, top_p: topP, max_tokens: maxTokens }),
        });

        if (!res.ok) {
            const err = await res.json();
            toast(err.error || '生成失敗', 'error');
            return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        let full = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true });
            const lines = buf.split('\n');
            buf = lines.pop();
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const d = JSON.parse(line.slice(6));
                    if (d.error) { toast(d.error, 'error'); return; }
                    if (d.content) { full += d.content; respBox.textContent = full; }
                    if (d.done) { toast('生成完成', 'success'); }
                } catch (_) {}
            }
        }
    } catch (e) {
        toast(`請求失敗：${e.message}`, 'error');
    } finally {
        setLoading('textSendBtn', false);
    }
}

function copyTextResponse() {
    const text = document.getElementById('textResponse').textContent;
    if (!text) { toast('沒有可複製的內容', 'info'); return; }
    navigator.clipboard.writeText(text).then(() => toast('已複製到剪貼板', 'success'));
}

function onTempChange(val) { document.getElementById('tempVal').textContent = parseFloat(val).toFixed(1); }
function onTopPChange(val) { document.getElementById('topPVal').textContent = parseFloat(val).toFixed(2); }

// ─── Image Generation ─────────────────────────────────────────
const ASPECT_RATIO_LABELS = {
    '1:1': '1:1 — 正方形', '16:9': '16:9 — 橫向寬螢幕', '9:16': '9:16 — 直向',
    '4:3': '4:3 — 橫向標準', '3:4': '3:4 — 直向標準', '3:2': '3:2 — 橫向',
    '2:3': '2:3 — 直向', '4:5': '4:5 — 直向', '5:4': '5:4 — 橫向', '21:9': '21:9 — 超寬',
};
const IMG_SIZE_LABELS = { '512': '512px（低）', '1K': '1K（標準）', '2K': '2K（高）', '4K': '4K（超高）' };

function onImgModelChange() {
    const modelId = document.getElementById('imgModel')?.value;
    const m = (models.image || []).find(m => m.id === modelId);

    populateSelect('imgAspectRatio',
        m?.aspect_ratios || ['1:1'],
        s => ASPECT_RATIO_LABELS[s] || s, s => s);

    populateSelect('imgResolution',
        m?.image_sizes || ['1K'],
        s => IMG_SIZE_LABELS[s] || s, s => s);

    const group = document.getElementById('imgThinkingGroup');
    if (m?.thinking && m?.thinking_levels?.length) {
        group.style.display = '';
        populateSelect('imgThinkingLevel',
            ['', ...m.thinking_levels],
            s => s === '' ? '不啟用' : s === 'minimal' ? 'Minimal' : 'High',
            s => s);
    } else {
        group.style.display = 'none';
    }
}

function onImgFileChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById('imgPreviewImg').src = e.target.result;
        document.getElementById('imgUploadPlaceholder').style.display = 'none';
        document.getElementById('imgUploadPreview').style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

function removeUploadedImage(event) {
    event.stopPropagation();
    document.getElementById('imgFileInput').value = '';
    document.getElementById('imgPreviewImg').src = '';
    document.getElementById('imgUploadPlaceholder').style.display = 'flex';
    document.getElementById('imgUploadPreview').style.display = 'none';
}

function onImgDragOver(event) {
    event.preventDefault();
    document.getElementById('imgUploadZone').classList.add('drag-over');
}
function onImgDragLeave() {
    document.getElementById('imgUploadZone').classList.remove('drag-over');
}
function onImgDrop(event) {
    event.preventDefault();
    document.getElementById('imgUploadZone').classList.remove('drag-over');
    const file = event.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById('imgFileInput').files = dt.files;
    onImgFileChange({ target: { files: [file] } });
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function sendImage() {
    const prompt = document.getElementById('imgPrompt').value.trim();
    if (!prompt) { toast('請輸入提示詞', 'error'); return; }

    const model         = document.getElementById('imgModel').value;
    const aspectRatio   = document.getElementById('imgAspectRatio').value;
    const imageSize     = document.getElementById('imgResolution').value;
    const sampleCount   = parseInt(document.getElementById('imgSampleCount').value) || 1;
    const style         = document.getElementById('imgStyle').value;
    const guidanceScale = parseFloat(document.getElementById('imgGuidance').value);
    const safety        = document.getElementById('imgSafety').value;
    const seedRaw       = document.getElementById('imgSeed').value.trim();
    const seed          = seedRaw !== '' ? parseInt(seedRaw) : null;
    const enhancePrompt = document.getElementById('imgEnhancePrompt').checked;
    const addWatermark  = document.getElementById('imgAddWatermark').checked;
    const includeRai    = document.getElementById('imgIncludeRai').checked;
    const includeText   = document.getElementById('imgIncludeText').checked;
    const negPrompt     = document.getElementById('imgNegPrompt').value.trim();
    const thinkingLvl   = document.getElementById('imgThinkingLevel')?.value || '';

    const fileInput = document.getElementById('imgFileInput');
    let inputImage = null, inputImageMime = null;
    if (fileInput.files[0]) {
        inputImageMime = fileInput.files[0].type;
        inputImage = await fileToBase64(fileInput.files[0]);
    }

    setLoading('imgSendBtn', true);
    const grid       = document.getElementById('imgGrid');
    const textResult = document.getElementById('imgTextResult');
    grid.innerHTML = `<div class="img-loading"><span class="spinner"></span><span>圖像生成中，請稍候…</span></div>`;
    textResult.textContent = '';
    textResult.style.display = 'none';

    try {
        const data = await apiPost('/api/image/generate', {
            model, prompt,
            negative_prompt:    negPrompt,
            aspect_ratio:       aspectRatio,
            image_size:         imageSize,
            sample_count:       sampleCount,
            sample_image_style: style,
            guidance_scale:     guidanceScale,
            safety_setting:     safety,
            seed,
            enhance_prompt:     enhancePrompt,
            add_watermark:      addWatermark,
            include_rai_reason: includeRai,
            include_text:       includeText,
            thinking_level:     thinkingLvl || null,
            input_image:        inputImage,
            input_image_mime:   inputImageMime || "image/jpeg",
        });

        grid.innerHTML = '';
        if (!data.success) { toast(data.error || '圖像生成失敗', 'error'); return; }

        (data.images || []).forEach((img, i) => {
            const src = `data:${img.mime || 'image/png'};base64,${img.data}`;
            const div = document.createElement('div');
            div.className = 'img-result';
            const imgEl = document.createElement('img');
            imgEl.src = src;
            imgEl.alt = `Generated image ${i + 1}`;
            imgEl.addEventListener('click', () => openLightbox(src));
            const overlay = document.createElement('div');
            overlay.className = 'dl-overlay';
            overlay.innerHTML = `<button class="btn btn-dl" onclick="downloadImage(this)">下載</button>`;
            overlay.querySelector('button').dataset.src = src;
            overlay.querySelector('button').dataset.idx = i;
            div.appendChild(imgEl);
            div.appendChild(overlay);
            grid.appendChild(div);
        });

        if (data.text) {
            textResult.textContent = data.text;
            textResult.style.display = 'block';
        }
        toast('圖像生成成功', 'success');
    } catch (e) {
        grid.innerHTML = '';
        toast(`請求失敗：${e.message}`, 'error');
    } finally {
        setLoading('imgSendBtn', false);
    }
}

function downloadImage(btn) {
    const a = document.createElement('a');
    a.href = btn.dataset.src;
    a.download = `imagen_${Date.now()}_${btn.dataset.idx}.png`;
    a.click();
}

// ─── Lightbox ─────────────────────────────────────────────────
function openLightbox(src) {
    document.getElementById('lightboxImg').src = src;
    document.getElementById('lightbox').classList.add('open');
    document.body.style.overflow = 'hidden';
}
function closeLightbox() {
    document.getElementById('lightbox').classList.remove('open');
    document.body.style.overflow = '';
}

// ─── Video File Upload ────────────────────────────────────────
function onVidFileChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById('vidPreviewImg').src = e.target.result;
        document.getElementById('vidUploadPlaceholder').style.display = 'none';
        document.getElementById('vidUploadPreview').style.display = 'flex';
        updateVidDurationConstraints();
    };
    reader.readAsDataURL(file);
}

function removeUploadedVideoImage(event) {
    event.stopPropagation();
    document.getElementById('vidFileInput').value = '';
    document.getElementById('vidPreviewImg').src = '';
    document.getElementById('vidUploadPlaceholder').style.display = 'flex';
    document.getElementById('vidUploadPreview').style.display = 'none';
    updateVidDurationConstraints();
}

function onVidDragOver(event) {
    event.preventDefault();
    document.getElementById('vidUploadZone').classList.add('drag-over');
}
function onVidDragLeave() {
    document.getElementById('vidUploadZone').classList.remove('drag-over');
}
function onVidDrop(event) {
    event.preventDefault();
    document.getElementById('vidUploadZone').classList.remove('drag-over');
    const file = event.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById('vidFileInput').files = dt.files;
    onVidFileChange({ target: { files: [file] } });
}

// ─── Video Generation ─────────────────────────────────────────
function updateVidDurationConstraints() {
    const select = document.getElementById('vidDuration');
    if (!select) return;
    
    const hasImage = document.getElementById('vidFileInput').files.length > 0;
    
    if (hasImage) {
        select.value = "8";
        select.disabled = true;
    } else {
        select.disabled = false;
        const val = select.value;
        if (val !== "4" && val !== "6" && val !== "8") {
            select.value = "8";
        }
    }
}

function onVidModelChange() {
    updateVidDurationConstraints();
}

function onVidDurChange(val) { }

async function sendVideo() {
    const prompt = document.getElementById('vidPrompt').value.trim();
    if (!prompt) { toast('請輸入提示詞', 'error'); return; }

    const model          = document.getElementById('vidModel').value;
    let duration         = parseInt(document.getElementById('vidDuration').value);
    const aspectRatio    = document.getElementById('vidAspectRatio').value;
    const resolution     = document.getElementById('vidResolution').value;
    const fpsRaw         = document.getElementById('vidFps').value.trim();
    const fps            = fpsRaw ? parseInt(fpsRaw) : null;
    const seedRaw        = document.getElementById('vidSeed').value.trim();
    const seed           = seedRaw ? parseInt(seedRaw) : null;
    const negPrompt      = document.getElementById('vidNegPrompt').value.trim();
    const enhancePrompt  = document.getElementById('vidEnhancePrompt').checked;
    const generateAudio  = document.getElementById('vidGenerateAudio').checked;
    const compression    = document.getElementById('vidCompression').value;
    const personGen      = document.getElementById('vidPersonGeneration').value;
    const refType        = document.getElementById('vidRefType').value;

    const vidFileInput = document.getElementById('vidFileInput');
    let inputImage = null, inputImageMime = "image/jpeg";
    if (vidFileInput.files[0]) {
        inputImageMime = vidFileInput.files[0].type || "image/jpeg";
        inputImage = await fileToBase64(vidFileInput.files[0]);
        duration = 8;
    }

    setLoading('vidSendBtn', true);
    try {
        const data = await apiPost('/api/video/generate', {
            model, prompt, duration,
            negative_prompt:    negPrompt,
            aspect_ratio:       aspectRatio,
            resolution,
            fps,
            seed,
            enhance_prompt:     enhancePrompt,
            generate_audio:     generateAudio,
            compression_quality: compression,
            person_generation:  personGen,
            input_image:        inputImage,
            input_image_mime:   inputImageMime,
            reference_type:     refType,
        });
        if (!data.success) { toast(data.error || '影片提交失敗', 'error'); return; }

        const taskId = data.task_id;
        const startTime = Date.now();
        addVideoTask(taskId, model, prompt, startTime, { aspectRatio, resolution });
        toast(`影片任務已提交，輪詢中…`, 'info');
        startVideoPoll(taskId, startTime);
    } catch (e) {
        toast(`請求失敗：${e.message}`, 'error');
    } finally {
        setLoading('vidSendBtn', false);
    }
}

function addVideoTask(taskId, model, prompt, startTime, params = {}) {
    const list = document.getElementById('videoTaskList');
    const card = document.createElement('div');
    card.className = 'task-card';
    card.id = `vtc-${taskId}`;
    const metaExtra = [params.aspectRatio, params.resolution].filter(Boolean).join(' · ');
    card.innerHTML = `
        <div class="task-card-header">
            <div class="task-prompt">${escapeHtml(prompt)}</div>
            <div class="task-meta">${model}${metaExtra ? ' · ' + metaExtra : ''}<br><span id="vtimer-${taskId}">0s</span></div>
        </div>
        <div class="task-status">
            <div class="status-dot pending" id="vdot-${taskId}"></div>
            <span class="status-text" id="vstatus-${taskId}">生成中…</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" id="vprog-${taskId}" style="width:2%"></div></div>
        <div class="task-video" id="vresult-${taskId}"></div>`;
    list.prepend(card);

    videoTasks[taskId] = { prompt, model, startTime };
    const timerInterval = setInterval(() => {
        const el = document.getElementById(`vtimer-${taskId}`);
        if (el) el.textContent = fmtTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    videoTasks[taskId].timerInterval = timerInterval;
}

function startVideoPoll(taskId, startTime) {
    let tries = 0;
    const maxTries = 180;

    const poll = async () => {
        if (tries >= maxTries) {
            updateVideoTask(taskId, 'TIMEOUT', null, '等待超時（15 分鐘）');
            return;
        }
        tries++;
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const prog = elapsed < 30
            ? 5 + (elapsed / 30) * 15
            : Math.min(20 + ((elapsed - 30) / 600) * 70, 90);
        const progEl = document.getElementById(`vprog-${taskId}`);
        if (progEl) progEl.style.width = prog.toFixed(0) + '%';

        try {
            const res = await fetch(`/api/video/status/${taskId}`, { headers: { 'Authorization': `Bearer ${apiKey}` } });
            const data = await res.json();
            if (data.status === 'SUCCEEDED') {
                updateVideoTask(taskId, 'SUCCEEDED', data.video_url, null);
            } else if (data.status === 'FAILED') {
                updateVideoTask(taskId, 'FAILED', null, data.error_message || '生成失敗');
            } else {
                videoTasks[taskId].pollTimer = setTimeout(poll, 5000);
            }
        } catch (_) {
            videoTasks[taskId].pollTimer = setTimeout(poll, 5000);
        }
    };

    videoTasks[taskId].pollTimer = setTimeout(poll, 5000);
}

function updateVideoTask(taskId, status, videoUrl, errorMsg) {
    const task = videoTasks[taskId];
    if (!task) return;
    clearInterval(task.timerInterval);
    clearTimeout(task.pollTimer);

    const dot = document.getElementById(`vdot-${taskId}`);
    const statusEl = document.getElementById(`vstatus-${taskId}`);
    const progEl = document.getElementById(`vprog-${taskId}`);
    const resultEl = document.getElementById(`vresult-${taskId}`);

    if (status === 'SUCCEEDED') {
        if (dot) { dot.className = 'status-dot success'; }
        if (statusEl) statusEl.textContent = '生成完成';
        if (progEl) progEl.style.width = '100%';
        if (resultEl && videoUrl) {
            resultEl.innerHTML = `
                <video controls><source src="${videoUrl}" type="video/mp4">您的瀏覽器不支援影片播放</video>
                <button class="btn btn-dl" onclick="downloadVideo('${videoUrl}', '${taskId}')">下載 MP4</button>`;
        }
        toast('影片生成完成！', 'success');
    } else if (status === 'FAILED') {
        if (dot) dot.className = 'status-dot error';
        if (statusEl) statusEl.textContent = `失敗：${errorMsg || '未知錯誤'}`;
        if (progEl) { progEl.style.width = '100%'; progEl.style.background = 'var(--status-err)'; }
    } else {
        if (dot) dot.className = 'status-dot timeout';
        if (statusEl) statusEl.textContent = '超時，請稍後刷新頁面確認結果';
    }
}

function downloadVideo(url, taskId) {
    const a = document.createElement('a');
    a.href = url; a.download = `veo_${taskId}.mp4`;
    a.click();
}

// ─── Music Generation ─────────────────────────────────────────
function onMusicInput() {
    const textarea = document.getElementById('musPrompt');
    const count = document.getElementById('musCharCount');
    const len = textarea.value.length;
    if (count) {
        count.textContent = `${len} / 500`;
        count.className = 'char-count' + (len > 450 ? ' warn' : '');
    }
}

async function sendMusic() {
    const desc = document.getElementById('musPrompt').value.trim();
    if (!desc) { toast('請輸入音樂描述', 'error'); return; }
    if (desc.length > 500) { toast('描述不能超過 500 字元', 'error'); return; }
    const model = document.getElementById('musModel').value;

    setLoading('musSendBtn', true);
    document.getElementById('musResult').innerHTML = '';

    try {
        const data = await apiPost('/api/music/generate', { model, description: desc });
        if (!data.success) { toast(data.error || '音樂生成失敗', 'error'); return; }

        if (data.mode === 'sync') {
            showAudioResult(data.audio_data, data.format);
            toast('音樂生成完成！', 'success');
        } else {
            toast('音樂任務已提交，輪詢中…', 'info');
            startMusicPoll(data.task_id);
        }
    } catch (e) {
        toast(`請求失敗：${e.message}`, 'error');
    } finally {
        setLoading('musSendBtn', false);
    }
}

function showAudioResult(audioData, format) {
    const result = document.getElementById('musResult');
    result.innerHTML = `
        <div class="audio-result">
            <audio controls><source src="${audioData}" type="audio/${format}">您的瀏覽器不支援音頻播放</audio>
            <button class="btn btn-dl" onclick="downloadAudio('${audioData}', '${format}')">⬇ 下載 ${format.toUpperCase()}</button>
        </div>`;
}

function startMusicPoll(taskId) {
    let tries = 0;
    const maxTries = 60;
    const resultEl = document.getElementById('musResult');
    resultEl.innerHTML = `<div class="status-text"><span class="status-dot pending"></span> 生成中，請稍候…</div>`;

    const poll = async () => {
        if (tries >= maxTries) {
            resultEl.innerHTML = '<div style="color:var(--status-err)">等待超時</div>';
            return;
        }
        tries++;
        try {
            const res = await fetch(`/api/music/status/${taskId}`, { headers: { 'Authorization': `Bearer ${apiKey}` } });
            const data = await res.json();
            if (data.status === 'SUCCEEDED' && data.audio_data) {
                showAudioResult(data.audio_data, data.format || 'mp3');
                toast('音樂生成完成！', 'success');
            } else if (data.status === 'FAILED') {
                resultEl.innerHTML = `<div style="color:var(--status-err)">失敗：${data.error_message || '未知錯誤'}</div>`;
            } else {
                setTimeout(poll, 5000);
            }
        } catch (_) {
            setTimeout(poll, 5000);
        }
    };
    setTimeout(poll, 5000);
}

function downloadAudio(src, format) {
    const a = document.createElement('a');
    a.href = src; a.download = `lyria_${Date.now()}.${format}`;
    a.click();
}

// ─── Utility ──────────────────────────────────────────────────
function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Store button labels for setLoading
    document.querySelectorAll('.btn[id]').forEach(btn => {
        btn.dataset.label = btn.innerHTML;
    });

    // Login input enter key
    document.getElementById('apiKeyInput')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') handleLogin();
    });

    // Auto-login from sessionStorage
    const savedKey = sessionStorage.getItem('gemini_api_key');
    if (savedKey) {
        apiKey = savedKey;
        enterApp();
    }
});
