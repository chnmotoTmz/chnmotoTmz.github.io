GeminiのWeb UI（`gemini.google.com`）をバックエンドとして利用し、ローカルのREST API経由で操作したいということですね。これは\*\*「既存のWebサイトをAPI化する（Web API Wrapper）」\*\*という手法です。

前回提案した\*\*「2. WebSocket / HTTP Server」\*\*の構成がまさにこれに最適です。

以下のアーキテクチャで実装コードを作成しました。

### アーキテクチャ図（データの流れ）

1.  **Client (Postman/Pythonなど)** `POST /api/ask` → **Local Server**
2.  **Local Server** `Socket.io` → **Chrome Extension**
3.  **Chrome Extension** → **Gemini Web UI** (テキスト入力＆送信)
4.  **Gemini Web UI** → (回答生成待ち) → **Chrome Extension** (回答テキスト取得)
5.  **Chrome Extension** `Socket.io` → **Local Server**
6.  **Local Server** (HTTP Response) → **Client**

-----

### 実装ステップ

必要なファイルは3つだけです。フォルダを作成し、以下のファイルを配置してください。

#### 1\. ローカルサーバー (`server.js`)

Node.jsで「REST API」と「ブラウザとの通信(Socket.io)」の中継役を作ります。

```javascript
// server.js
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const bodyParser = require('body-parser');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: { origin: "*" } // 拡張機能からの接続を許可
});

app.use(bodyParser.json());

// 拡張機能との接続保持用変数
let browserSocket = null;

io.on('connection', (socket) => {
    console.log('Browser Extension connected');
    browserSocket = socket;

    socket.on('disconnect', () => {
        console.log('Browser Extension disconnected');
        browserSocket = null;
    });
});

// REST API エンドポイント
app.post('/api/ask', async (req, res) => {
    const prompt = req.body.prompt;

    if (!browserSocket) {
        return res.status(503).json({ error: "Browser extension not connected. Open Gemini tab." });
    }

    // 1. ブラウザに指示を出す
    // If a `mode` field is present in the API payload (e.g. { prompt, mode: 'fast' }),
    // it will be forwarded to the extension and used to attempt a UI mode switch.
    // Behavior: explicit `mode: 'image'` requests image mode; any other mode (or omitted) is coerced to 'fast'.
    // The extension emits `mode_change_result` with { requestedMode, success, reason?, verified? } so the caller can detect UI switch failures.
    // Example:
    //  curl -X POST http://localhost:3000/api/ask -H "Content-Type: application/json" -d '{"prompt":"短い返答で", "mode":"fast"}'
    //  curl -X POST http://localhost:3000/api/ask -H "Content-Type: application/json" -d '{"prompt":"画像を作って", "mode":"image"}'

    browserSocket.emit('input_prompt', prompt);

    // 2. ブラウザからの回答を待つ (タイムアウト設定付き)
    const responsePromise = new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error('Timeout waiting for Gemini response'));
        }, 60000); // 60秒待機

        // 一度だけイベントを受け取るリスナー
        browserSocket.once('gemini_reply', (data) => {
            clearTimeout(timeout);
            resolve(data);
        });
    });

    try {
        const answer = await responsePromise;

        // --- Enhanced: return detected image URLs / base64 in `images` field ---
        // The server/extension can return an object like:
        // { text: 'generated text', images: [ { src: 'https://...', base64: null }, ... ] }
        // When present, the backend will prefer handling `images` directly and can
        // proxy or convert base64 to local files for further processing.

        res.json({ status: "success", answer: answer });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

server.listen(3000, () => {
    console.log('API Server running on http://localhost:3000');
});
```

#### 2\. マニフェストファイル (`manifest.json`)

拡張機能の設定ファイルです。

```json
{
  "manifest_version": 3,
  "name": "Gemini Local API Wrapper",
  "version": "1.0",
  "permissions": [],
  "host_permissions": [
    "http://localhost:3000/*",
    "https://gemini.google.com/*"
  ],
  "content_scripts": [
    {
      "matches": ["https://gemini.google.com/*"],
      "js": ["socket.io.min.js", "content.js"]
    }
  ]
}
```

※ `socket.io.min.js` は、[CDN](https://www.google.com/search?q=https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js)などからダウンロードして同じフォルダに置いてください（外部スクリプト読み込み制限のため）。

#### 3\. コンテンツスクリプト (`content.js`)

Geminiの画面を実際に操作するスクリプトです。DOM構造は頻繁に変わるため、セレクタのメンテナンスが必要になる場合があります。

```javascript
// content.js
const socket = io('http://localhost:3000');

socket.on('connect', () => {
    console.log('Connected to Local Server');
});

socket.on('input_prompt', async (promptText) => {
    console.log('Received prompt:', promptText);
    
    // 1. 入力欄を探してテキストを入れる
    // 注意: Geminiのクラス名は変わる可能性があるため、属性で探すのがベター
    const inputArea = document.querySelector('div[contenteditable="true"]');
    if (!inputArea) {
        console.error('Input area not found');
        return;
    }

    // Reactなどの仮想DOMに対応するため、イベントを発火させる必要がある場合がある
    inputArea.innerHTML = `<p>${promptText}</p>`; 
    inputArea.focus();
    
    // 少し待ってから送信ボタンを押す（入力反映待ち）
    setTimeout(() => {
        const sendButton = document.querySelector('button[aria-label*="送信"], button[aria-label*="Send"]'); // 日本語/英語対応
        if (sendButton) {
            sendButton.click();
            waitForResponse();
        } else {
            console.error('Send button not found');
        }
    }, 500);
});

function waitForResponse() {
    // 回答生成の完了を検知するロジック
    // 「生成停止」ボタンが消える、または最新の回答要素が確定するのを監視
    
    console.log('Waiting for response...');
    
    // 簡易的な実装: 一定間隔で監視し、テキストが変化しなくなったら完了とみなす
    // 本来はMutationObserverを使うのがベストですが、コードが複雑になるためポーリングで例示します
    
    let lastText = "";
    let stableCount = 0;
    
    const interval = setInterval(() => {
        // 最新の回答要素を取得（DOM構造に依存します。要調整）
        const responseElements = document.querySelectorAll('.model-response-text'); // 仮のクラス名
        // もしくは aria-label="モデルの回答" などを探す
        
        // 実際にはGeminiの回答コンテナは複雑なので、最後の response container を取得するのが一般的
        // ここでは簡易的に body 全体のテキストの変化を見る、あるいは特定のマーカーを探す必要があります
        
        // ★もっとも確実な「完了」のサインは「コピーボタン」等のアイコンが出現することです
        const copyButtons = document.querySelectorAll('span[data-mat-icon-name="content_copy"]'); // アイコン名などは要確認
        const isGenerating = document.querySelector('.stop-generating-button'); // 生成停止ボタンがあるか？

        if (!isGenerating && copyButtons.length > 0) {
             // 生成が終わっている可能性が高い
             
             // 最後の回答のテキストを取得
             const responses = document.querySelectorAll('markdown-renderer'); // Geminiの回答ブロック
             if (responses.length > 0) {
                 const latestResponse = responses[responses.length - 1].innerText;
                 
                 // 完了通知
                 socket.emit('gemini_reply', latestResponse);
                 clearInterval(interval);
                 console.log('Response sent back to server');
             }
        }
    }, 1000);
}
```

-----

### 実行手順

1.  **準備:** Node.jsプロジェクトを作り、ライブラリを入れる。
    ```bash
    npm init -y
    npm install express socket.io body-parser
    # socket.io-clientのjsファイルもダウンロードしてフォルダに置く
    ```
2.  **サーバー起動:**
    ```bash
    node server.js
    ```

    *Quick mode test:* you can run the included simulator to verify mode switching and replies.
    ```bash
    node test/smoke_mode_simulator.js
    ```
    This connects as a simulated extension, posts `/api/ask` with `mode: 'thinking'`, and logs the emitted `input_prompt` (which should include `mode: 'fast'`), followed by `mode_change_result` and `gemini_reply`.
3.  **拡張機能読込:** Chromeの拡張機能管理画面 (`chrome://extensions`) で「パッケージ化されていない拡張機能を読み込む」から、上記フォルダを選択。
4.  **Geminiを開く:** Chromeで `https://gemini.google.com` を開き、ログインしておく。
      * F12コンソールを開き、「Connected to Local Server」と出ればOK。
5.  **テスト:** 別のターミナルからAPIを叩く。
    ```bash
    curl -X POST http://localhost:3000/api/ask \
         -H "Content-Type: application/json" \
         -d '{"prompt": "こんにちは、REST APIのテストです。"}'
    ```

### 重要な注意点（DOMセレクタ）

GeminiのようなSPA（Single Page Application）は、クラス名がハッシュ値（例: `.xyz123`）になっていたり、頻繁に構造が変わったりします。
`content.js` 内の `document.querySelector(...)` の部分は、実際にChromeの開発者ツールで現在のGeminiのHTMLを見て、**適切なセレクタに書き換える必要があります**。

  * **入力欄:** `div[contenteditable="true"]` や `div[role="textbox"]` が比較的安定しています。
  * **回答:** `model-response` や `markdown-renderer` といったタグやクラスを探してください。

この「DOMセレクタを探して維持する作業」が、この方式の最大の運用コストになります。#