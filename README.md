# 💻💕 工程師的浪漫 — 終端機 ASCII 動畫

一個工程師用程式碼寫給女朋友的驚喜：在黑色的終端機裡，用一個個字元畫出聖誕樹、大阪城、
東京晴空塔、釜山、首爾、台北 101 跨年煙火，還有我們家的貓咪陪著說出想說的話。
程式是「多場景」架構，之後還可以再加婚禮、七夕、情人節……

## 執行方式

需要 Python 3（不需安裝任何套件，只用標準函式庫）。

```powershell
python main.py --menu              # 開始選單：選場景、勾選貓咪（推薦）
python main.py                     # 直接播預設場景：聖誕節
python main.py --scene christmas   # 指定場景
python main.py --with 摸摸,逗逗     # 只讓這幾隻貓出場（名字用逗號分開）
python main.py --list-scenes       # 列出所有場景
```

或直接雙擊 `run.bat`（會打開開始選單）。

### Mac 版 🍎

程式本身 Windows / Mac / Linux 通用，Mac 用 `run.command` 啟動（等同 Windows 的 `run.bat`）。

**1. 在 Windows 打包**（打包後 `run.command` 會帶著「可執行」權限）：

```powershell
python tools\make_mac_zip.py      # 產生 dist\工程師的浪漫-mac.zip
```

**2. 在 Mac 上**：把 zip 傳過去（AirDrop、隨身碟、雲端都可以），雙擊解壓縮，
打開「工程師的浪漫」資料夾，**雙擊 `run.command`** → 會開啟「終端機」並顯示開始選單。

- 第一次打開時，Mac 可能會說「無法打開，因為它來自未識別的開發者」：
  請改成在 `run.command` 上**按右鍵 → 打開 → 打開**，之後就能直接雙擊。
- 如果顯示沒有權限執行（沒用上面的 zip、直接複製檔案過去時會發生），在終端機輸入一次：
  `chmod +x run.command`
- 需要 Python 3.7 以上。Mac 沒有時，`run.command` 會提示安裝方式
  （到 python.org 下載，或在終端機輸入 `xcode-select --install`）。
- `run.command` 會請終端機把視窗調成 90 × 30（放得下開始選單）。
- 也可以在終端機直接執行：`python3 main.py --menu`

### 開始選單

```
                     ♥  工程師的浪漫  ♥
  場景                                    |-----------------------------|
    (*) 聖誕節            christmas       | 聖誕節                      |
    ( ) 大阪城            osaka           |           /#\.@             |
    ( ) 東京晴空塔        tokyo           |         /\===/\             |
    ...                                   |         (o . o)   ← 游標所在的貓，
  貓咪（最多 3 隻）  已選 2 隻             |        / > w < \    戴著所選場景的配件
    [x] 摸摸      tabby     穩重          |     ,  (~:::::~)            |
  > [x] 沐沐      patches   調皮          |   (~~~-`u-----u'            |
    [ ] 逗逗      tuxedo    穩重          |        沐沐  (調皮)         |
    ...
    [  開始播放  ]
      上下鍵 移動   空白鍵 選擇/勾選   Enter 開始   a 清除勾選   q 離開
```

- 場景是單選 `( )`，貓咪是複選 `[ ]`；預設勾選 `cats.json` 裡沒有關閉（`enabled`）的貓。
- 在選單勾選的貓會直接出場，不受 `cats.json` 的 `enabled` 影響（不會改到設定檔）。
- **最多 3 隻貓**一起出場：已勾 3 隻時再勾會提示「最多只能選 3 隻貓咪」；一隻都沒勾時不能開始。
- 按 `a` 清除所有勾選，再按一次勾選前 3 隻。

- 建議使用 **Windows Terminal**（PowerShell 5/7 皆可）。
- **任何視窗大小都可以**，執行中拉大、縮小視窗也會即時跟著變：
  - 視窗**比 78 × 27 大**（例如全螢幕）：畫面會填滿整個視窗。主角（聖誕樹、大阪城、晴空塔…）
    留在中間、站在底部，往左右延伸更多城市／海面／櫻花樹／小松樹，上方多出星空，貓咪也會走到兩側。
  - 想讓畫面本身變大，可以放大終端機的字體：`Ctrl + 滑鼠滾輪`（Mac：`⌘ +`）。
  - 視窗**比 78 × 27 小**：最小可到 **64 × 24**，會裁掉畫面左右邊緣和天空頂端，祝福語會自動移到看得到的位置。
    再小就會提示放大視窗。開始選單仍需要 78 × 27。
- `Ctrl+C` 或 `q` / `Esc` 優雅離開；按 `s` 可立刻跳到驚喜橋段；按 `n` 切換到下一個場景。

### 網頁版 🌐

**`web/`** 資料夾就是網頁版：雙擊 **`web/index.html`**，在首頁選「ASCII 動畫」或「傅立葉聖誕樹」。
不用 Python、不用網路；要給別人看就把**整個 `web` 資料夾**（約 12 MB）壓縮傳過去，手機也能看。

```
web/
├─ index.html     首頁：選模式
├─ ascii.html     ASCII 動畫（資料在 ascii/ 裡，每個場景一個檔，選到才載入）
├─ ascii/         christmas.js、osaka.js …（tools/build_ascii_html.py 產生）
└─ fourier.html   傅立葉聖誕樹（一筆畫，fourier_gui/build_html.py 產生）
```

**ASCII 動畫**

- 上方選場景（聖誕節、大阪城、東京晴空塔、釜山、浦項、首爾、台北 101），`暫停`、`重播`、`驚喜 ♥`（直接跳到驚喜橋段），
  拉桿可以前後跳。鍵盤：空白鍵暫停、`R` 重播、`S` 驚喜、`N` 下一個場景。
- 第二排**勾選貓咪**（最多 3 隻，也可以都不勾），播放中勾選也會立刻換。預設勾 `cats.json` 開啟的貓。
- 做法：用**真正的 Python 程式**（和 `main.py` 同一套）把每個場景播一遍、錄下每一格畫面
  （120 × 34 字、每秒 15 格、從開頭到祝福語結束），顏色用終端機的 256 色，所以畫面和終端機版一模一樣：
  - 先錄一次**沒有貓**的背景（天空、景物、雪、祝福語…）；
  - 再為**每一種貓的組合**（5 隻選 1～3 隻，共 25 種）各錄一次，只留下和背景不同的格子（貓、貓的愛心和 zZ）；
  - 錄的時候貓和祝福語的愛心用自己的亂數，所以不管選哪幾隻貓，背景都完全一樣；網頁把選到的那層疊在背景上。
  - 每格只存跟上一格不同的字，再壓縮。
- 手機直拿時只顯示中間的主畫面，橫放看起來更大。播完會從頭再播。
- 改了場景、貓或祝福語後，重新錄（約 3 分鐘）：

```powershell
python tools\build_ascii_html.py
```

`web/ascii/` 的錄影資料是產生出來的（約 11 MB），不放進 git，clone 下來後先跑一次上面的指令。

## 傅立葉聖誕樹（一筆畫）🌀

另外一支**視窗程式**（不是終端機 ASCII）：聖誕樹、樹頂星星、三條金色彩帶、吊飾（圓球、愛心、鈴鐺、拐杖糖）、
樹幹、地面、4 個禮物（盒子、緞帶、蝴蝶結），整張圖接成**一條封閉曲線**、只有**一組**傅立葉係數，
由**同一串旋轉圓一口氣**畫完。畫完後圓圈淡出，每個部分填上顏色，星星發光、下雪，最後打出祝福語。

```powershell
python fourier_gui\app.py
```

或雙擊 **`run_fourier.bat`**（Mac：`run_fourier.command`）。只用 Python 內建的 tkinter，不用另外安裝。

**一筆畫怎麼接**（`fourier_gui/onestroke.py`）：從地面左邊出發 → 左邊的禮物（盒子、橫緞帶去了又回、
8 字蝴蝶結、直緞帶下去又上來）→ 沿樹幹爬上樹 → 樹的左緣往上（經過彩帶時沿彩帶上緣畫到右邊、再沿下緣回來，
下緣掛著的吊飾順著細線下去畫一圈再回來；樹枝尖端也掛著吊飾）→ 樹頂繞星星一圈 → 右緣往下 → 樹幹下來 →
右邊的禮物 → 沿地面回到起點。來回的線重疊在一起，看起來就像掛吊飾的細線。
畫的時候線條會換成正在畫的部分的顏色，畫完後每個部分用重建曲線上屬於自己的那一段填色。

| 操作 | 說明 |
|---|---|
| 上方按鈕 `200` `500` `1000` `1500` `全部`（或鍵盤 `1`–`5`） | 傅立葉項數（幾個圓），越多越準 |
| 速度滑桿 | 畫多快（預設約 45 秒畫完） |
| 大圓在前／依頻率 | 圓的排列順序（大小排序，或 0, ±1, ±2 …） |
| 顯示圓（`C`） | 只看軌跡、不看圓 |
| 暫停（空白鍵）、重播（`R`）、離開（`Esc`） | |

**數學**（`fourier_gui/fourier.py`）：

1. 整條路徑依**弧長**均勻取樣 2048 點，每點是複數 `z = x + iy`，並記下每點屬於哪個部分（樹、彩帶、某個吊飾、禮物…）。
2. 用標準函式庫寫的 FFT 算出係數 `c_n`（索引 `k > N/2` 對應負頻率 `k − N`），只在啟動時算一次（約 0.003 秒）。
3. `z(t) = Σ c_n · exp(i2πnt)`：只取最低的 N 個頻率，每一項是半徑 |c_n|、每圈轉 n 次的旋轉向量，首尾相接，末端畫出整張圖。
4. 畫面上的曲線用反向 FFT 重建（8192 點），所以 1000 項以上也能即時畫。

| 項數 | 最大誤差 |
|---|---|
| 200 | 吊飾會糊掉 |
| 1000（預設） | 約 2 像素 |
| 2048（全部） | 0（完全還原取樣點） |

命令列：`python fourier_gui\app.py --terms 1500 --seconds 12`。
祝福語沿用 `settings.json` 裡聖誕節場景的 `greeting` / `wish`。測試：`python fourier_gui\test_fourier.py`。

**網頁版：** 雙擊 **`web/fourier.html`**（或從 `web/index.html` 進去）就會用瀏覽器打開，跟視窗版一樣是一筆畫（項數、速度、顯示圓都能調），手機也能看；
不用 Python、不用網路，可以直接把這個檔案傳給別人。路徑由 Python 產生、寫進網頁，傅立葉轉換和
旋轉圓在瀏覽器裡用 JavaScript 算。改了形狀、`fourier_gui/web_template.html` 或 settings.json 的祝福語後，重新產生：

```powershell
python fourier_gui\build_html.py
```

## 場景

| 場景 | 內容 |
|---|---|
| `christmas`（預設） | 聖誕樹、燈串、星星、禮物、雪花；貓戴聖誕帽 |
| `osaka` | 大阪城：綠屋頂白牆天守閣、金鯱、窗戶一格格亮起、兩棵盛開櫻花樹、櫻花瓣飄落、石燈籠；貓戴櫻花花圈 |
| `tokyo` | 東京晴空塔：鐵塔在「粹」（水藍）與「雅」（紫）兩種點燈之間切換、光帶往上掃、辦公大樓窗戶明滅、紅色航空燈、流星、自動販賣機與郵筒；貓戴毛線帽 |
| `busan` | 韓國釜山：廣安里海灘與廣安大橋（吊橋彩燈變換）、海浪與倒影、海雲台高樓、海上煙火、沙堡與海灘傘；貓戴草帽 |
| `pohang` | 韓國浦項：虎尾串「相生之手」從海裡伸出、海鷗停在指尖、燈塔閃爍；太陽從海面升起、半露在海平面上，海上映出金色光路；左邊是九龍浦日式老屋街和上山的石階（《山茶花開時》拍攝地，有 Camellia 酒吧招牌），山茶花整朵掉落、在地上停留一陣子；貓戴山茶花 |
| `seoul` | 韓國首爾：南山上的 N 首爾塔（變色）、樂天世界塔、城市燈火、漢江與盤浦大橋月光彩虹噴泉、愛情鎖圍欄、青紗燈籠；貓戴韓國傳統笠帽（갓） |
| `taipei101` | 台北 101 跨年：101 依星期幾亮顏色；驚喜前 10 秒出現大字倒數 10→1、101 一節節閃白；歸零時 101 每一節兩側噴出煙火、滿天煙火、出現新年年份大字；貓戴派對帽 |
| `demo` | 極簡示範場景（星空＋月亮，貓戴蝴蝶結），用來示範怎麼新增場景 |

每個場景的祝福語都在 `settings.json` 的 `"scenes"` 裡，可以直接改。播放中按 `n` 可以依序切換場景。

## 劇情流程

1. 雪花開始飄落
2. 聖誕樹由上而下慢慢亮起（葉子、彩球、燈串）
3. 樹頂金色星星閃亮
4. 禮物一個一個掉下來
5. 活潑的白底橘斑貓先衝進來
6. 圓滾滾的虎斑貓慢慢走進來
7. 兩隻貓在樹下互動（躲在禮物後探頭、撲禮物、互相蹭蹭、追逐……）
8. 約 70 秒後，兩隻貓坐到樹下，顯示 **Merry Christmas, My Love! ♥** 和你的專屬祝福，愛心飄上來
9. 停留一段時間後回到自由互動，之後會再度重複（無限循環）

## 兩隻貓

| | 虎斑貓（摸摸） | 白底橘斑貓（沐沐） |
|---|---|---|
| 外觀 | 橘色虎斑條紋、白胸口、白腳掌、圓滾滾 | 白底橘塊、修長輕巧 |
| 個性 | 穩重、呆萌、療癒 | 調皮、機靈、活潑 |
| 動作 | 慢慢走、坐著搖尾巴、縮成一團打盹、呆呆看樹、偶爾小跑 | 衝刺、跳躍、躲禮物後探頭、潛行撲禮物、找胖貓玩 |

每隻貓都是獨立的**狀態機**（`CalmCat` / `PlayfulCat`，在 `engine/cats.py`），移動有加減速，面向會左右鏡像，
會在禮物前方或後方走動（躲在禮物後面時會被禮物遮住），不會走進樹幹。

## 設定有哪些貓 🐱（`cats.json`）

```json
{
  "skins_dir": "skins",
  "cats": [
    { "name": "摸摸",   "skin": "tabby",   "personality": "calm",    "enter_from": "left",  "enter_at": 22 },
    { "name": "沐沐", "skin": "patches", "personality": "playful", "enter_from": "right", "enter_at": 18 },
    { "name": "逗逗",    "skin": "tuxedo",  "personality": "calm",    "enter_from": "left",  "enter_at": 27, "enabled": false },
    { "name": "妃妃",     "skin": "spots",   "personality": "playful", "enter_from": "right", "enter_at": 25, "enabled": false },
    { "name": "波波",   "skin": "ginger",  "personality": "playful", "enter_from": "left",  "enter_at": 30, "enabled": false }
  ]
}
```

| 造型 | 貓咪 |
|---|---|
| `tabby` | 摸摸：圓滾滾的橘虎斑，白臉中線、白胸口、白腳掌 |
| `patches` | 沐沐：橘色頭頂與背、白臉中線、白肚子長白腿、橘條紋尾巴白尾尖 |
| `tuxedo` | 逗逗（黑白貓）：黑頭頂黑背、白臉白胸白腳、全黑尾巴、黃綠眼睛 |
| `spots` | 妃妃（白底橘點貓）：橘色頭頂、白身體幾個橘點、橘白相間尾巴 |
| `ginger` | 波波（全橘虎斑幼貓）：只有嘴邊肚子淡奶油色、大圓眼睛 |

| 欄位 | 說明 |
|---|---|
| `skin` | 造型，對應 `skins/<名字>.cat` |
| `personality` | `calm`（穩重）或 `playful`（調皮） |
| `enter_from` / `enter_at` | 從哪邊、第幾秒進場 |
| `speed` / `jump` | 速度、跳躍力倍率（1.0 = 正常） |
| `enabled` | `false` = 暫時不出場（逗逗、妃妃、波波預設關閉，改成 `true` 就會出現） |

- 驚喜時，貓咪依清單順序輪流坐到樹的左、右兩側；**同時最多 3 隻**（`cats.json` 裡可以放更多隻，但沒關閉的不能超過 3 隻）。
- 要用另一份設定：`python main.py --cats 我的貓.json`
- 自己畫新造型：請看 [`skins/README-skins.md`](skins/README-skins.md)

## 自訂祝福語與播放設定 ✏️（`settings.json`）

```json
{
  "scene": "christmas",

  "heart": "♥",
  "stay": false,
  "skip_intro": false,
  "fps": 30,
  "cats": "cats.json",

  "scenes": {
    "christmas": {
      "greeting": "Merry Christmas, My Love!",
      "wish": "Every day with you feels like Christmas.",
      "surprise_at": 70,
      "every": 75,
      "hold": 30
    }
  }
}
```

- 最外層的設定套用到**所有場景**；`"scenes"` 裡的設定只套用到那個場景。
- 優先順序（後面的蓋前面的）：場景內建預設 → 最外層 → `scenes.<場景名>` → 命令列參數。
- 舊格式（`greeting`、`wish` 直接寫在最外層）也還能用，只是會套用到每個場景。

| 設定 | 說明 |
|---|---|
| `scene` | 預設播放哪個場景（只能寫在最外層） |
| `greeting` | 第一行大標題（後面會自動接上 `heart`） |
| `wish` | 第二行，你的專屬祝福 |
| `heart` | 句尾的愛心；顯示不出來就改成 `"<3"`，不要愛心就填 `""` |
| `surprise_at` / `every` / `hold` | 第一次驚喜的秒數、之後每隔幾秒一次、祝福停留秒數 |
| `stay` | `true` = 祝福出現後就一直留著 |
| `skip_intro` / `fps` | 跳過開場、影格率 |
| `cats` | 要用哪份貓咪設定 |

- 支援中文祝福語（會自動以 2 格寬置中）；太長會自動以 `...` 截斷，畫面一行約 76 個英文字、38 個中文字。
- 用另一份設定：`python main.py --settings 給她的.json`
- 命令列參數會蓋過 `settings.json`，例如臨時試一句：`python main.py --wish "試試看"`
- 打錯設定名稱或型別時，程式會在開始前直接告訴你哪裡錯。

## 命令列參數（會蓋過 settings.json）

| 參數 | 說明 |
|---|---|
| `--menu` | 先開啟開始選單，選場景、勾選貓咪 |
| `--scene 名稱` | 選擇場景（`christmas`、`osaka`…） |
| `--with 名字,名字` | 只讓這幾隻貓出場（`cats.json` 裡的名字，最多 3 隻） |
| `--list-scenes` | 列出所有場景 |
| `--settings 檔案` | 使用另一份設定檔 |
| `--wish "文字"` | 自訂第二行祝福語 |
| `--greeting "文字"` | 自訂第一行大標題 |
| `--surprise-at 70` | 第一次驚喜出現的秒數 |
| `--every 75` | 之後每隔幾秒再出現一次 |
| `--hold 30` | 祝福停留秒數 |
| `--stay` | 祝福出現後一直留在畫面上 |
| `--skip-intro` | 跳過開場動畫 |
| `--ascii` | 愛心顯示不出來時，改用 `<3` |
| `--fps 30` | 影格率 |
| `--cats 檔案` | 使用另一份貓咪設定 |
| `--preview-skin 造型` / `--preview-cats` | 預覽貓咪造型（會戴上目前場景的配件） |

## 程式結構

```
X_mas/
├─ main.py               入口：python main.py [--scene 名稱]
├─ run.bat               Windows：雙擊執行（開啟選單）
├─ run.command           Mac：雙擊執行（開啟選單）
├─ run_fourier.bat       雙擊：傅立葉聖誕樹視窗版（Mac：run_fourier.command）
├─ web/                 網頁版：index.html 首頁、ascii.html + ascii/ 終端機動畫、fourier.html 傅立葉聖誕樹
├─ fourier_gui/          傅立葉聖誕樹（一筆畫）：fourier.py 數學、onestroke.py 路徑、app.py 視窗、build_html.py 網頁版、test_fourier.py
├─ tools/build_ascii_html.py 產生 web/ascii.html 和 web/ascii/（ascii_web_template.html 是網頁本體）
├─ tools/make_mac_zip.py 打包 Mac 版 zip（run.command 帶可執行權限）
├─ settings.json         祝福語、時間、預設場景（可分場景設定）
├─ cats.json             有哪些貓
├─ skins/                貓咪造型 *.cat（只畫貓本身，不含帽子等配件）
├─ engine/               共用底層，不含任何節日邏輯
│  ├─ render.py          Canvas 字元畫布、256 色、寬字元處理
│  ├─ effects.py         Fx 粒子、Starfield 星空、Fireworks 煙火、Banner 打字機祝福語
│  ├─ sprites.py         Art 多行 ASCII 圖、Prop 地上的道具（貓可以躲在後面）、sym 左右對稱
│  ├─ cats.py            Skin 造型、Accessory 配件、Cat / CalmCat / PlayfulCat
│  ├─ scene.py           BaseScene：場景生命週期（進場→自由玩→集合→祝福）
│  ├─ manager.py         SceneManager：自動註冊、選擇、切換場景
│  ├─ menu.py            開始選單：場景單選、貓咪複選、配件預覽
│  ├─ settings.py        settings.json + 命令列 → 每個場景的設定
│  └─ terminal.py        唯一的動畫主迴圈（畫面跟著視窗大小）、選單迴圈、按鍵（含方向鍵）、視窗太小提示
├─ scenes/               一個檔案 = 一個場景
│  ├─ christmas.py       ChristmasScene：樹、禮物、燈、雪、聖誕帽、開場時間軸
│  ├─ osaka.py           OsakaScene：大阪城、櫻花
│  ├─ tokyo.py           TokyoScene：東京晴空塔、夜景
│  ├─ busan.py           BusanScene：廣安大橋、海灘、煙火
│  ├─ seoul.py           SeoulScene：N 首爾塔、漢江、彩虹噴泉
│  ├─ taipei101.py       Taipei101Scene：101 跨年倒數與煙火
│  └─ demo.py            DemoScene：最小範例
└─ tests/                自動化測試
```

### 誰負責什麼

| 部分 | 負責 |
|---|---|
| `terminal.run` | 唯一的畫面更新迴圈：固定影格率、每幀**一次寫出**整張畫面（不閃爍）、處理按鍵 |
| `BaseScene` | 所有場景共用的故事：貓進場、自由互動、集合坐好、打出祝福語、愛心飄起、循環 |
| 各個 Scene | 自己的背景、裝飾、特效、時間軸、貓的配件、祝福語顏色與預設文字 |
| `Cat` 系列 | 貓的外觀（造型檔）、動畫、移動與個性；**不知道**自己在哪個節日 |
| `Accessory` | 場景給貓戴的東西（聖誕帽、蝴蝶結…），畫在造型檔標記的位置 |

貓咪跟場景之間只透過幾個介面溝通：`hideouts()`（可以躲在後面的東西，聖誕節是禮物）、
`GAZE`（穩重貓發呆看的地方，聖誕節是樹，會閃星光）、`CAT_ACCESSORY`（配件）。

## 新增一個場景

1. 複製 `scenes/demo.py`，改名成例如 `scenes/valentine.py`。
2. 改 `name = "valentine"`，在 `build()` 建立裝飾、`update_scene()` 讓它動、
   `draw_background()` 畫背景；要讓貓在物件前後穿梭就用 `depth_items()`，要讓調皮貓躲就回傳 `hideouts()`。
3. 設定 `CAT_ACCESSORY`（貓的配件）、`SETTINGS`（預設祝福語與時間）、`BANNER`（祝福語顏色）。
4. 執行 `python main.py --scene valentine`。

**視窗大小**：場景一律畫在 78 × 27 的「舞台」座標上（x 0–77、y 0–26），引擎會把舞台放在視窗中間、貼齊底部。
寬視窗時，舞台外的座標（x < 0、x ≥ 78、y < 0）也看得到，所以：

- 地面、海面這類橫跨整個畫面的東西，用 `for x in cv.xs():` 畫，不要用 `range(CW)`。
- `Starfield` 會自己把星星補滿舞台外的天空。
- 需要在兩側多放東西（城市、樹…）就實作 `on_view(view)`，`view = (x0, y0, x1, y1)` 是看得到的範圍；
  `engine.render.lay_out()` 可以幫你一棟一棟往左／往右排過去。

**不用改任何其他檔案**：`SceneManager` 會自動找到 `scenes/` 裡的新場景，主迴圈也不用動。

## 測試

```powershell
python -m unittest discover -s tests -v
```

- **聖誕動畫回歸測試**：用固定亂數種子跑 180 秒，逐格比對畫面字元與顏色（`tests/golden/`）。
  重構前後比對過：除了沐沐的聖誕帽多了一個帽尖 `.`（現在兩隻貓戴同一頂帽子）之外完全一樣。
- 場景自動註冊、切換、每個場景都能跑完整個故事、`engine/` 裡沒有節日邏輯、場景之間互不引用、
  設定優先順序與錯誤訊息、命令列（不加 `--scene` 與 `--scene christmas` 輸出相同）、配件跟著場景換。
- 刻意改了聖誕畫面時，執行 `python tests/golden.py` 重新產生基準（記得先確認差異）。

## 小提醒

- 愛心使用 `♥`（U+2665）。若你的終端機字型顯示不出來，請加上 `--ascii`。
- 程式使用 ANSI 256 色，Windows Terminal / VS Code Terminal / macOS Terminal 都能正常顯示。
