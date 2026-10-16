# 西濱南下出發日

幫使用者挑「從新竹南寮騎單車到高雄左營」最適合出發的日子，以**風向和風速**為主要考量。

- 網站：https://azchen2002.github.io/bike-south/
- 使用者是程式新手：用**繁體中文**回覆，一步一步說明，避免沒解釋的術語
- 使用者會在真的網站上確認、截圖回報；改完要請他用 Ctrl + F5 重新整理

## 檔案

- `index.html`：整個網站就這一個檔（HTML + CSS + JS），沒有建置步驟。程式碼的註解用中文，寫法維持簡單的原生 JS
- `tools/prep_route.py`：從 GPX 產生路線資料（`ROUTE_PTS`、`CHECKPOINTS`）
- `tools/fetch_forecast.py`：GitHub Actions 用，抓 Open-Meteo 存成 `forecast.json`、`ensemble.json`（只用 Python 內建功能）。檢查點座標從 `index.html` 的 `ROUTE_PTS`、`CHECKPOINTS`、`ENS_CPS` 用跟網頁一樣的方法算，所以改路線不用改它
- **GitHub 規則：公開倉庫 60 天沒有任何提交，排程會被自動停用**（GitHub 會寄信通知）。停用後網站還是能用（網頁會自己去抓 Open-Meteo），重新啟用：Actions 頁面點這個工作流程 → Enable workflow，或推送任何提交
- `.github/workflows/pages.yml`：每 3 小時（`17 */3 * * *` UTC）、推送到 `main`、或手動，執行 `fetch_forecast.py`，把 `index.html` 和兩個 JSON 一起發布到 GitHub Pages
- 外部資源：Google Fonts、Leaflet 1.9.4（cdnjs）、OpenStreetMap 底圖、Open-Meteo API（不需要金鑰）、Windy 嵌入地圖（`embed.windy.com/embed2.html`，免費、不用金鑰）
- **Windy 只用來給使用者對照，不拿它的數字算分數**：Windy 的資料 API 要付費，免費試用金鑰會回傳隨機打亂的假資料，而且金鑰放在公開網頁會外流；它的資料來源（ECMWF、GFS、ICON）Open-Meteo 都有免費提供。嵌入地圖預設收起來，打開 `#windy-box` 才放進 iframe。能不能用網址參數跳到指定日期時間還沒確認，目前用 `calendar=now`，請使用者自己拖時間軸

## 更新網站

推送到 `main`，GitHub Actions 會抓預報並發布網站（約 1～3 分鐘）。GitHub Pages 的 Source 要設成「GitHub Actions」（不是 main 分支）。部署狀態可以這樣查：
`gh api repos/AzChen2002/bike-south/actions/runs --jq '.workflow_runs[0] | .status, .conclusion'`
（GitHub Pages 的設定 API 在雲端環境被擋，只能請使用者自己去 Settings → Pages 調整。）

提交時**一定要用 GitHub 的匿名 email**，不要用使用者的 Gmail（倉庫是公開的）：
`git config user.name "AzChen2002" && git config user.email "99375218+AzChen2002@users.noreply.github.com"`
- 使用者已在 GitHub 打開「Block command line pushes that expose my email」，用 Gmail 提交的推送會被擋
- 之前 8 次提交裡有使用者的 Gmail，使用者決定保留、不改寫歷史

## 路線

- 來源：使用者提供的「TBA一日北高360」GPX，從最接近南寮漁港的點截到終點（高鐵左營站附近），簡化後約 293.5 km，走**西部沿海**，不是台1線
- GPX 沒有放進倉庫；要改路線，請使用者重新上傳 GPX，再跑 `tools/prep_route.py`
- `CHECKPOINTS`：沿路每 ~20 km 一個天氣檢查點（16 個），名稱是最近的鄉鎮，畫面上顯示成「X附近」

## 計算方式（這些是和使用者一起決定的，改之前要先問）

- **兩種行程**：一日（預設）；兩日（第 1 天騎到 `SPLIT_CP` = 大城附近）
- **出發時間**：預設「自動」。一日試 03:00～07:00、兩日每天試 05:00～08:00，每半小時一個，選分數最高的；同分時選最接近預設（一日 05:00、兩日 06:00）的。也可以在選單指定（`prefs.start`）
- **模擬騎乘**：路線切成約 1 km 的 `STEPS`，從出發時間逐段推進。每段用最近檢查點、當下那個小時的天氣，算出時速和到達時間。每騎 1 小時休息 10 分鐘
- **速度模型**：輕裝公路車（`RIDER`：85 kg、crr 0.005、CdA 0.40）。用「無風時速」（選單 20～30，預設 25）反推功率，再算順風、逆風下的時速。預報的 10 公尺風速 × 0.7 當作騎車高度的風；時速上限是無風時速 × 1.6
- **風的分數**：整條路一直吹 20 km/h 順風（`FULL_SCORE_TAILWIND`）= 100 分，比無風每省 1% 騎乘時間 +1、每多 1% −1。無風的基準 `windBase(無風時速)` = 100 − 20 km/h 順風能省的 %，所以會跟著無風時速變（20 km/h 約 70、25 km/h 約 74、30 km/h 約 77）。使用者選了「基準降低」而不是「基準維持 80、加分變平緩」，知道無風的好天氣會只剩「可以考慮」
- **扣分**（依騎乘時間加權平均）：
  - 下雨：機率 × 0.35，加上雨量（mm，最多算 4）× 15
  - 體感溫度 > 31°C：每度 −5（最多 −40）；< 12°C：每度 −3
  - 側風 > 25 km/h、陣風 > 40 km/h 另外扣分
  - 空氣品質（AQI）是**選用**，預設不勾，因為預報只有約 5 天
- **強陣風安全上限**（`GUST_CAPS`）：騎乘途中最強陣風 ≥ 60 km/h，那天最多 59 分；≥ 75 km/h，最多 39 分。陣風看預估經過時間的**前後各 1 小時**，避免「剛好在強風前幾分鐘到」被算成安全。推薦卡出現強陣風時，提醒使用者去中央氣象署確認颱風或強風特報（真實資料曾出現陣風 84～101 km/h、順風省 4 小時卻還有 70 幾分的情況，所以才加這條）
- **整天扣分**：最高體感 > 35°C 每度 −4（最多 −20）；摸黑（日出前、日落後）每小時 −4（最多 −24）
- **兩日合併**：(2 × 較差那天 + 較好那天) / 3，但只要有一天被強陣風上限壓分，整趟也不能超過那個上限（`tripScore`）。等級：80 適合出發、60 可以考慮、40 勉強
- **推薦日**：從 7 天內挑最高分；有勾空品時，優先挑整趟都有空品預報的日子
- **預報可信度**（不影響分數，只是另外顯示）：用 Open-Meteo 系集預報（先試 `ecmwf_ifs025` 51 種預測，失敗改 `gfs_seamless`；只抓 10 天，比較省使用次數），只抓 `ENS_CPS` 這 5 個點的風。每種預測都用選定的出發時間跑一次「純騎乘時間」模擬：
  - 順風機率 = 比無風更快的預測比例
  - 騎乘時間範圍取第 10～90 百分位
  - 範圍寬度 ≤ 無風時間的 10% 是「一致」，≤ 25% 是「普通」，其他是「分歧」

## 騎乘中定位（📍 我在哪）

- 使用者要求：南下途中在手機上打開網頁，用 GPS 找出在路線的哪裡，再重新預估剩下的路
- 按一下才定位（`locate`，`getCurrentPosition`），可勾「每 5 分鐘自動更新」（網頁不在畫面上時跳過）。網頁不能在背景追蹤
- `locateOnRoute`：把 GPS 投影到 `ROUTE_PTS` 上最近的點，得到第幾公里和離路線多遠；超過 1.5 km 提醒可能走錯路
- `simulateFrom`：從現在的位置和台灣時間，用**已經存下來的預報**重新模擬到終點（兩日行程第 1 天騎到大城），不會多抓 Open-Meteo
- 顯示剩下公里數、預估到達時間、日落位置、接下來的風（`windAhead` 把同一種風的路段合併），地圖已騎過的路段變灰色
- **沒有做「跟原本預估比快或慢」**：網頁不知道使用者實際幾點出發，比較容易誤導
- 位置只在手機上計算，不會傳出去。LINE 內建瀏覽器可能不能定位，要用 Safari 或 Chrome
- 測試時用 Playwright 的 `geolocation` 模擬位置；「拒絕定位」要用 `addInitScript` 改寫 `getCurrentPosition`，因為測試瀏覽器只會一直等權限

## 資料抓取

- Open-Meteo 預報（16 天、每小時、日出日落）和空氣品質（7 天、`us_aqi`），檢查點每 4 個一組分批抓，失敗的組會再試一次
- 多個地點時回傳陣列，只有一個地點時回傳物件（程式已處理）
- 用 `parseJSONLoose` 解析：會把 `nan`、`inf` 換成 null。之前真實資料出現過一次解析錯誤，原因還沒確定
- 系集預報：每個點抓一次。欄位名稱是 `wind_speed_10m`、`wind_speed_10m_member01`……，常常每 3～6 小時才有值，用 `fillGaps` 補中間的值。**實際的欄位格式還沒用真實資料確認過**
- 時速用 `speedCache` 存起來重複使用（順風速度取到 0.5 km/h），不然自動找出發時間加上系集預報會算很久
- **共用預報**（使用者的主意，為了不再出現「抓不到天氣預報」）：網頁先讀網站上的 `forecast.json`（6 小時內）和 `ensemble.json`（12 小時內），所有訪客共用，不碰 Open-Meteo 的次數。JSON 裡的 `points` 跟網頁算的座標差超過 0.001 就不用。共用的太舊或沒有，才走下面原本的做法；自己也抓不到時，改用手上最新的一份（就算太舊）
- **Open-Meteo 免費版有使用次數上限**（使用者遇過「暫時限制使用次數」，HTTP 429），系集預報特別耗次數。所以：
  - 1 小時內重新打開網頁，直接用存下來的預報（`FRESH_MS`）；按「重新整理」才強制重抓天氣
  - 系集預報 3 小時內不重抓（`ENS_FRESH_MS`），而且是在天氣顯示之後才抓，抓到再補上可信度
  - 遇到 429 不重試、也不改試別的模型
- 瀏覽器存的資料：`bike-south-forecast-v2`（上次的預報）、`bike-south-ensemble-v2`（上次的系集預報，`{fetchedAt, ens}`）、`bike-south-prefs`（行程、時速、出發時間、空品勾選）

## 測試

- 雲端環境**連不到** Open-Meteo、cdnjs 和地圖底圖，只能用假資料測試
- 做法：在 `index.html` 所在資料夾跑 `python3 -m http.server 8765`，用 Playwright（`/opt/pw-browsers` 裡的 Chromium）攔截 `open-meteo` 的請求、回傳假資料
- Leaflet 可以用 `npm pack leaflet@1.9.4` 下載，攔截 cdnjs 的請求時回傳本機檔案
- 要檢查：電腦版和手機版（390px）、淺色和深色、頁面不會左右捲動、主控台沒有錯誤
- 用假資料測完之後，要跟使用者說哪些部分還沒用真實資料驗證
