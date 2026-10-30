# cubby

[English](README.md) | 繁體中文

把不公開列出的靜態頁面放在 Cloudflare Pages 上，就像 HTML 版的私密 gist。只要有完整網址，任何人都能開啟頁面；但沒有任何地方連到它，也會告知搜尋引擎不要建立索引。

> 這只是隱匿，不是存取控制。拿到網址的人都能開啟並轉傳，請不要在這裡發布機密資料。

## 運作方式

- 每個頁面位於 `/p/<id>/`。`<id>` 是由密碼學安全的亂數產生器產生的 32 個十六進位字元（128 位元）。
- `public/_headers` 會在所有路徑送出以下標頭：
  - `X-Robots-Tag: noindex, nofollow, noarchive`
  - `Referrer-Policy: no-referrer`
  - `X-Content-Type-Options: nosniff`
- 每個 HTML 頁面另外帶有 `robots`、`googlebot` 和 `referrer` meta 標籤，以防標頭遺失。
- `robots.txt` 刻意允許爬取。爬蟲必須抓取頁面，才看得到頁面上的 `noindex`。
- 根頁面和 `404.html` 都只顯示單純的「404 Not Found」，網站不會透露自己的用途。
- 網站上沒有 sitemap，也沒有頁面清單。`make list` 會在本機列出頁面。

## 指令

所有操作都透過 `make`。單獨執行 `make` 可列出所有 target。

| 指令 | 用途 |
|---|---|
| `make new SRC=page.html` | 從 HTML 檔案，或含有 `index.html` 的資料夾新增頁面 |
| `make fix ID=<id>` | 替換頁面檔案後，重新補上 doctype 和 meta 標籤；不加 `ID` 則處理所有頁面 |
| `make list` | 列出頁面的新增日期、標題和網址 |
| `make preview` | 在本機提供 `public/`（`PORT=8000`） |
| `make check` | 依 noindex 與隱私規則檢查 `public/` |
| `make deploy` | 執行 `check`，再把 `public/` 部署到 Cloudflare Pages |
| `make pull ID=<id>` | 從網站把頁面下載回 `public/p/`；用 `IDS=<檔案>` 可下載檔案裡列出的所有頁面 |
| `make remove ID=<id>` | 把一個頁面資料夾移到 `.trash/` |
| `make deployments` | 列出專案在 Cloudflare 上的部署 |
| `make delete-deployment DEPLOYMENT=<id>` | 刪除一個部署 |
| `make login` | 讓 Wrangler 登入 Cloudflare，每台機器一次 |
| `make create-project` | 建立 Pages 專案（只需一次），並以 `main` 作為正式環境分支 |

## 目錄結構

```text
Makefile           入口
.env.example       設定範本，複製成 .env.local 使用
.trash/            `make remove` 移出的頁面，git 不追蹤
public/            部署根目錄：這裡的所有內容都能公開存取
  _headers
  robots.txt
  index.html       中性的「404 Not Found」佔位頁
  404.html         未知路徑時回傳
  p/<id>/          每個頁面一個資料夾，git 不追蹤
scripts/
  new-page.sh      供 `make new` 使用
  add-meta.py      補上 doctype 和 meta 標籤，供 `make new` 和 `make fix` 使用
  check.py         供 `make check` 使用
  deploy.sh        供 `make deploy` 使用
  pull.py          供 `make pull` 使用
```

絕對不要在 `public/` 裡放頁面網址清單或相關筆記。

## 系統需求

- macOS 或 Linux，需要 `bash`、`make`、`python3`、`openssl` 和 `rsync`。macOS 上的 `make` 由 Xcode Command Line Tools 提供。
- Node.js 22 以上，供 Wrangler 使用
- 使用 Direct Upload 的 Cloudflare Pages 專案

## 安裝

沒有建置步驟。Clone 這個 repository、讓腳本可執行，並建立設定檔：

```bash
chmod +x scripts/*.sh scripts/*.py
```

```bash
cp .env.example .env.local
```

在 `.env.local` 設定 `CUBBY_PAGES_PROJECT`，再登入 Cloudflare：

```bash
make login
```

如果 Pages 專案還不存在，建立一次即可：

```bash
make create-project
```

`public/p/` 已列在 `.gitignore` 中，因為底下的資料夾名稱就是秘密網址。頁面永遠不會進入 git，請自行備份。只要還留著頁面 id，就能用 `make pull` 從網站下載回來，詳見[從網站拉回頁面](#從網站拉回頁面)。

## 設定

Makefile 會讀取 `.env.local`，git 會忽略這個檔案。請從 `.env.example` 開始，每行寫成單純的 `KEY=value`，不要加引號或 `export`。

| 變數 | 用途 |
|---|---|
| `CUBBY_PAGES_PROJECT`，或在 make 命令列傳入 `PROJECT=` | Cloudflare Pages 專案名稱。`deploy`、`deployments`、`delete-deployment` 和 `create-project` 都需要它。 |
| `CUBBY_BASE_URL`，或 `BASE_URL=` | `make list` 印出、`make pull` 下載時使用的基本網址，預設為 `https://<project>.pages.dev`。使用自訂網域，或 Cloudflare 給專案的 pages.dev 子網域不同時，請設定此值。 |
| `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID` | 選用。不透過 `make login` 讓 Wrangler 驗證身分，例如在 CI 中。請在 shell 中 export；Makefile 不會把 `.env.local` 的值傳給 Wrangler。絕對不要 commit 這些值。 |

`.env.local` 的值會覆蓋 shell 中 export 的變數，而 make 命令列上的 `PROJECT=` / `BASE_URL=` 又會覆蓋兩者。執行 `make` 可看到目前生效的值。

如果 pages.dev 子網域已被使用，Cloudflare 會在後面加上後綴。執行 `make create-project` 後請確認網域。

專案名稱會成為 `<name>.pages.dev`，並出現在每個分享出去的網址中，所以請取一個不會透露內容的中性名稱。

## 新增頁面

```bash
make new SRC=path/to/page.html
```

- **單一 HTML 檔案**會變成 `public/p/<id>/index.html`。
- **資料夾**必須包含 `index.html`。除了 `.DS_Store`，所有檔案都會複製到 `public/p/<id>/`。引用資源時請使用相對路徑，例如 `style.css` 或 `img/logo.png`，而不是 `/style.css`。
- **Meta 標籤**：每個複製進來的 HTML 檔案，都會補上 doctype 以及缺少的 `charset`、`robots`、`googlebot` 和 `referrer` meta 標籤。沒有 `<html>` 或 `<head>` 的 HTML 片段也能用，例如 Claude artifact 匯出的檔案，瀏覽器會自動補上這些元素。
- **警告**：如果頁面已經有不含 `noindex` 的 `robots` meta 標籤，`make new` 只會發出警告而不會改寫，而 `make check` 會一直失敗，直到你手動修正該標籤。

新增頁面後，執行 `make deploy`。之後要查頁面網址，執行 `make list`，它會以頁面資料夾的修改時間作為新增日期。

### 更新頁面

要修改已部署的頁面，直接覆蓋 `public/p/<id>/` 裡的檔案，例如 `index.html`。手動複製檔案不會經過 `make new` 補 meta 標籤的步驟，所以覆蓋後請執行：

```bash
make fix ID=<page id>
```

它會為頁面資料夾裡的每個 HTML 檔案補上 doctype 和缺少的 meta 標籤，已經齊全的檔案不會被改動。不加 `ID` 時會處理所有頁面。接著執行 `make deploy`。頁面的 id、網址和新增日期都不變。

## 本機預覽

```bash
make preview
```

預覽不會套用 `_headers` 或 Cloudflare 的路由規則，只適合用來檢查頁面外觀。

## 檢查

```bash
make check
```

`make deploy` 會先執行這項檢查，任何一項失敗就會停止。它會檢查：

- `_headers` 中的 `/*` 規則會送出上述三個標頭
- `robots.txt` 沒有 `Disallow: /`，也沒有 `Sitemap`
- `404.html` 存在
- `public/p/` 中的每個資料夾都是 32 字元的十六進位 id，且含有 `index.html`
- 每個 HTML 檔案都有 doctype、charset，以及 `noindex` / `no-referrer` meta 標籤
- `public/p/` 以外的公開檔案都沒有提到頁面路徑

它也會對 `.DS_Store` 檔案發出警告，因為從 dashboard 上傳時會把它們一起發布。

## 部署

```bash
make deploy
```

`make check` 通過後，`scripts/deploy.sh` 會：

- 上傳一份排除 `.DS_Store` 檔案的 `public/` 副本
- 以目前的 git 分支與 commit 標記這次部署
- 當 `public/` 中被追蹤的檔案有未 commit 的變更時發出警告

從 `main` 部署會更新正式網站，因為 `make create-project` 把 `main` 設為正式環境分支。其他分支則會建立預覽部署。如果你是在 dashboard 建立專案，請到那裡確認它的正式環境分支。

你也可以在 dashboard 上傳 `public` 資料夾：在 Workers & Pages 中開啟專案，選擇 **Create a new deployment**。Dashboard 上傳不會過濾 `.DS_Store` 檔案，所以請先執行 `make check`。

每次都部署到同一個 Pages 專案。換新專案就是換新網域，所有已分享出去的網址都會失效。

## 部署後驗證

回應中應包含 `x-robots-tag: noindex, nofollow, noarchive` 和 `referrer-policy: no-referrer`：

```bash
curl -sI https://<project>.pages.dev/p/<id>/
```

未知路徑應回傳 404：

```bash
curl -sI https://<project>.pages.dev/p/
```

## 移除頁面

```bash
make remove ID=<page id>
```

這會把頁面資料夾移到 `.trash/<id>/`。git 會忽略這個資料夾，`make deploy` 也不會上傳它。接著執行 `make deploy`。如果 `.trash/<id>` 已經存在，`make remove` 會停止，不做任何變更。

要復原頁面，把它移回去再部署一次：

```bash
mv .trash/<page id> public/p/
```

`.trash/` 不會自動清空，不再需要時請自行刪除裡面的資料夾。

每個 Pages 部署都保有自己的 `https://<hash>.<project>.pages.dev` 網址。在你移除頁面之前建立的部署，仍然可以存取到已刪除的頁面。要完全下架，請找出這些部署並刪除：

```bash
make deployments
```

```bash
make delete-deployment DEPLOYMENT=<deployment id>
```

Cloudflare 不允許刪除某個分支的最新部署。

## 從網站拉回頁面

`make pull` 會從網站把頁面下載回 `public/p/`，例如換了新電腦，或本機檔案遺失的時候：

```bash
make pull ID=<page id>
```

```bash
make pull IDS=<檔案>
```

Cloudflare Pages 無法列出或下載某次部署的檔案，所以你必須提供頁面 id。`IDS=` 會讀取檔案中所有的頁面網址，以及只有一個 id 的行，所以 `make list` 的輸出可以直接使用。新增頁面後請把它存起來，放在 `public/` 以外的私密位置，也不要 commit。

- 從每個頁面的 `index.html` 開始，順著 HTML 和 CSS 中的相對連結找出檔案：`src`、`href`、`srcset`、`poster`、`style`、`url()` 和 `@import`。只會下載該頁面自己的 `/p/<id>/` 路徑底下的檔案。
- 沒有被任何地方連結的檔案，以及只由 JavaScript 載入的檔案，都不會被下載。
- 頁面的所有檔案都下載完成後才會寫入 `public/p/`，所以拉取失敗不會留下只有一半的頁面。
- 本機已經存在的頁面會被跳過。加上 `FORCE=1` 會用網站上的版本覆蓋它們的檔案，網站沒有回傳的本機檔案會保留。
- `make list` 會以拉回的那天作為頁面的新增日期。使用 `FORCE=1` 時，已存在的頁面會保留原本的日期。
- 要從較舊的部署拉取，例如某個仍提供你已移除頁面的部署，請加上 `BASE_URL=https://<hash>.<project>.pages.dev`。

## 疑難排解

- **未知路徑顯示根頁面，而不是 404**。請保留 `public/404.html`。如果最上層沒有 `404.html`，Cloudflare Pages 會把網站當成單頁應用程式，對所有未知路徑都回傳根頁面。
- **`public/` 裡出現 `.DS_Store` 檔案**。Finder 會建立這些檔案，而它們會列出檔名，也就是頁面 id。`make deploy` 會排除它們，`make check` 也會在你從 dashboard 上傳前發出警告。
- **部署後資源載入失敗**。頁面資料夾內請使用相對路徑。因為有 `X-Content-Type-Options: nosniff`，以錯誤類型提供的樣式表或腳本會被封鎖。
- **頁面中出現第三方腳本**。啟用 Cloudflare Web Analytics 時會注入腳本，請在這個專案中保持停用。
- **限制**。Dashboard 上傳最多接受 1,000 個檔案，Wrangler 最多 20,000 個。每個檔案最大 25 MiB。

## 授權

[MIT](LICENSE)
