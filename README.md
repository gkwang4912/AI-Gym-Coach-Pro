# README.md

## 1. 專案總覽 (Project Overview)

**AI Gym Coach Pro** 是一個基於網頁的即時健身動作偵測與輔助應用程式。
本專案利用電腦視覺技術（Computer Vision），透過使用者的一般視訊鏡頭（Webcam）即時分析使用者的健身動作（目前專注於啞鈴彎舉 Dumbbell Curls），並提供與專業教練相似的即時數據回饋。

- **解決問題**：提供居家健身者即時的動作標準度檢測、次數計算與速度監控，避免因動作不標準受傷或訓練效率低落。
- **目標用戶**：居家健身愛好者、需要自動化計數的健身人士。
- **專案類型**：Web Application (Browser-based Client + Python Backend)。

## 2. 專案架構總覽 (Architecture Overview)

本專案採用 Client-Server 架構，透過 WebSocket 進行高頻率的雙向影像與數據傳輸。

### 高層次架構
1.  **前端 (Client)**：
    - 負責擷取使用者視訊鏡頭影像（Webcam）。
    - 將影像縮小並轉碼為 Base64 字串，透過 WebSocket (`socket.io`) 發送至後端。
    - 接收後端處理後的「骨架疊加影像」與「分析數據（角度、次數、速度）」。
    - 即時更新儀表板 UI。

2.  **後端 (Server)**：
    - 基於 Flask 與 Flask-SocketIO 運行。
    - 接收影像後，使用 **MediaPipe Pose** 模型進行人體骨架關鍵點偵測。
    - **邏輯運算核心**：計算手肘角度、判斷動作階段（舉起/放下）、計算動作速度。
    - 將繪製好骨架的影像與 JSON 格式的統計數據回傳給前端。

### 資料流 (Data Flow)
1.  **Input**: Browser Webcam Capture -> Canvas Context -> Base64 JPEG.
2.  **Transport**: Socket.IO (`process_frame` event).
3.  **Process**: Python `cv2` decode -> `mediapipe` inference -> State Machine Update -> `cv2` draw.
4.  **Output**: Base64 processed image + JSON Stats -> Socket.IO (`response` event) -> Update Browser DOM & Canvas.

## 3. 資料夾結構說明 (Folder Structure)

```text
.
├── templates/
│   └── index.html      # 前端單頁應用程式入口，包含所有的 HTML/CSS/JS
├── requirements.txt    # Python 相依套件清單
└── web_app.py          # 後端主程式，包含 API、Socket 服務與影像處理邏輯
```

- **`templates/`**: 存放 Flask 的 Jinja2 樣板檔案，目前僅有一個 `index.html` 作為主要介面。
- **`web_app.py`**: 專案的核心入口點，負責啟動 Web Server 與處理所有核心業務邏輯。
- **`requirements.txt`**: 定義專案運行所需的 Python 函式庫版本。

## 4. 核心模組與重要檔案說明 (Key Modules & Files)

### `web_app.py`
後端核心檔案，職責如下：
- **Flask Server 初始化**: 設定 Web Server 與 WebSocket (`Flask-SocketIO`)。
- **`handle_frame(data)`**: 
    - WebSocket 事件處理函式。
    - 負責解碼圖片、呼叫 MediaPipe、計算運動幾何（角度）、更新計數器狀態。
    - 實作「過快警示」與「動作範圍（ROM）」判斷邏輯。
- **`calculate_angle(a, b, c)`**: 
    - 計算三點（肩膀、手肘、手腕）之間的夾角，用於判斷手臂彎曲程度。
- **全域變數 `hands`**: 
    - 儲存左手與右手目前的狀態（次數、是否在頂點、速度計算用的時間戳記）。

### `templates/index.html`
前端單一整合檔案，職責如下：
- **UI 呈現**: 
    - 使用 CSS Grid 佈局，包含霓虹風格（Neon Style）與掃描線特效（Scanline Effect）。
    - 顯示左右手的即時數據卡片（Reps, Angle, Speed）。
- **影像擷取邏輯**: 
    - 使用 `navigator.mediaDevices.getUserMedia` 取得權限。
    - 透過 `Canvas` 進行影像鏡像翻轉（Mirroring）處理。
- **傳輸控制**: 
    - 使用 `setInterval` 以約 12 FPS (80ms) 的頻率發送影像至後端，平衡即時性與頻寬。

## 5. 安裝與環境需求 (Installation & Requirements)

### 系統需求
- **OS**: Windows / macOS / Linux (開發環境為 Windows)。
- **Python**: 建議 Python 3.8 ~ 3.10。
- **硬體**: 必須連接 Webcam。

### 相依套件
請見 `requirements.txt`，主要包含：
- `flask`, `flask-socketio`: Web 框架與 WebSocket 支援。
- `opencv-python`: 影像處理。
- `mediapipe`: 骨架偵測模型。
- `protobuf<4.0.0`: **重要**，MediaPipe 對 Protobuf 版本有特定限制。
- `eventlet`: 用於 SocketIO 的非同步網路庫。

### 安裝指令
```bash
pip install -r requirements.txt
```

## 6. 使用方式 (How to Use)

### 1. 啟動伺服器
在專案根目錄執行：
```bash
python web_app.py
```
成功啟動後，終端機將顯示：`啟動 Web AI Gym Coach on port 5001...`

### 2. 開啟應用程式
1. 開啟瀏覽器（建議 Chrome 或 Edge）。
2. 前往 `http://localhost:5001 /` 或 `http://127.0.0.1:5001`。
3. 瀏覽器會詢問「使用相機權限」，請點選「允許」。

### 3. 開始運動
1. 站在距離鏡頭約 1.5 ~ 2 公尺處，確保上半身與手臂完整入鏡。
2. 系統會自動偵測並在畫面上繪製骨架。
3. 開始做「啞鈴彎舉」動作：
    - 手臂放下（角度 > 140度）。
    - 手臂舉起（角度 < 130度，且手腕高於鼻子水平線）。
4. 介面將即時更新次數、速度與動作建議（如 "Too Fast!", "Too Low!"）。

## 7. 設定說明 (Configuration)

目前專案採 **Code-First Configuration**，設定值直接定義於 `web_app.py` 頂部常數中：

- **動作門檻值**:
    - `ARM_UP_ANGLE = 140`: 手臂伸直的角度判定點。
    - `ARM_DOWN_ANGLE = 130`: 手臂彎曲的角度判定點。
    - **注意**: 程式碼邏輯中，變數命名可能與直觀相反（UP/DOWN 對應角度數值），需參考 `calculate_angle` 的回傳值。
- **速度限制**:
    - `SPEED_LIMIT = 1.8`: 若動作速度數值超過此值，會觸發 "太快!" 警告。
- **字型設定**:
    - `FONT_CANDIDATES`: 支援 `msjh.ttc` (微軟正黑體) 等，若找不到會自動 fallback 到預設字型。
- **連線設定**:
    - 預設 Port: `5001`
    - 預設 Host: `0.0.0.0` (允許區網連線)

## 8. 開發者指南 (Developer Guide)

### 給新人的建議
1. **鏡像問題**: 
    - 前端在 `ctx.scale(-1, 1)` 做了鏡像翻轉顯示給使用者看。
    - 傳給後端的影像也是鏡像後的。
    - 後端 MediaPipe 偵測到的 `Left` 實際上是使用者的「左手」（因為是鏡像），但若沒有鏡像，通常畫面左邊是使用者的右手。請注意左右手標籤在 UI 上的對應。
2. **字型路徑**:
    - `web_app.py` 中寫死了一些 Windows 常見字型路徑 (`C:\Windows\Fonts`)。若在 Linux docker 中部署，中文顯示可能會失效，需確認字型檔存在或修改路徑。

### 常見修正建議
- 若要調整判定嚴格度，請修改 `web_app.py` 第 48-50 行的 `ANGLE` 常數。
- 若要修改前端 UI 更新頻率，請修改 `index.html` 第 362 行的 `80` (毫秒)。

## 9. 已知限制與待辦事項 (Limitations & TODO)

### 已知限制 (Confirmed Limitations)
1.  **狀態並發問題 (Concurrency Issue)**:
    - **嚴重**: 後端使用全域變數 `hands` (`global hands`, line 65) 儲存運動狀態。
    - **影響**: 若同時有多個瀏覽器開啟網頁，所有人的動作會混雜計算在同一個變數中，導致計數亂跳。
    - **解法**: 需將狀態改為 `session` based 或以 `socket.id` 為 key 的字典來隔離不同使用者。
2.  **效能瓶頸**:
    - 每一幀圖片都經過 Base64 編碼/解碼並透過 WebSocket 傳輸，頻寬消耗極大且延遲較高。
    - 較好的做法是：前端僅傳送 Landmarks 或後端僅回傳數據，影像由前端自行繪製。
3.  **依賴版本**:
    - `metrics` 計算依賴 `time.time()`，若系統時間跳變可能導致速度計算異常（出現極大值）。

### TODO / FIXME
- **FIXME**: 將全域 `hands` 變數重構為 Session-scoped 變數，支援多人同時使用。
- **TODO**: 將硬編碼的參數（角度、Port、速度限制）移至 `.env` 或獨立 config 檔。
- **TODO**: 前端 `video` 元素目前是 `opacity: 0` 隱藏，僅用 Canvas 繪圖，可考慮 WebGL 優化渲染效能。
- **尚未實作**: `cv2_add_chinese_text` 雖然有定義，但在主要繪圖邏輯中大部分被註解或只使用英文 (OpenCV `putText` / `line`)，目前中文回饋主要依賴前端 DOM 顯示。

## 10. 補充說明 (Notes)

- **環境變數**: 程式碼中強制設定了 `os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"` (Line 4)，這是為了解決某些版本 protobuf 與 mediapipe 的相容性崩潰問題，**請勿移除**。
- **中文字型**: 程式碼嘗試載入系統中文字型，主要是為了在 OpenCV 圖片上壓上中文浮水印，但目前主要資訊回饋已移至 HTML UI 層，圖片上的文字非必要功能。
