# AI間連携ハンドオフファイル
> **作成者**: GitHub Copilot (リーダー担当)  
> **対象**: もう一方のAI  
> **最終更新**: 2026-03-07

---

## あなたへの指示

このファイルを読んでそのまま実行してください。完了したら `AI_STATUS.md` を更新してください。

---

## タスク概要

`c:\Users\motoc\chnmotoTmz.github.io` に以下を実装する。

---

## タスク 1: `about.html` を新規作成

**パス**: `c:\Users\motoc\chnmotoTmz.github.io\about.html`

**内容要件**:
- chnmoto（チャンモト）の個人企業ページ
- 自己紹介・開発実績・ヒューマノイドロボット専門性をアピール
- pTIMER（個人生産性ツール）が主な成果物であることを記載
- サイトのブランド名は「Humanoid Media Factory」
- デザイン: 既存の `assets/style.css` を読み込む (`<link rel="stylesheet" href="assets/style.css">`)
- Google Fonts: `https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap`
- ヘッダーは既存 `index.html` と同じ構造 (`<header class="site-header">`)
- フッターにコンタクトへのリンク (`partnership.html`)
- lang="ja"

**構成セクション**:
1. ヒーローセクション（名前・肩書き・キャッチコピー）
2. 私について（開発者プロフィール、ハワイ在住、日本語・英語対応）
3. 主なプロジェクト（pTIMER、Humanoid Media Factory）
4. 専門分野（ヒューマノイドロボット・AI・個人DX）
5. CTAボタン（「提携・お問い合わせ」→ `partnership.html`）

---

## タスク 2: `partnership.html` を新規作成

**パス**: `c:\Users\motoc\chnmotoTmz.github.io\partnership.html`

**内容要件**:
- ヒューマノイドロボット開発の提携募集ページ
- コンタクトフォーム付き
- デザイン: 同上（`assets/style.css`）
- フォーム送信先: `https://new-blog-system.onrender.com/api/contact`（fallback: `http://localhost:8084/api/contact`）
- フォームフィールド: 名前, メール, 件名, メッセージ, カテゴリ（general/partnership/humanoid）
- fetch API でPOST、送信後に成功/失敗メッセージ表示
- カテゴリ「humanoid」デフォルト選択

**構成セクション**:
1. ページヒーロー（提携募集のビジョン）
2. 求める提携の種類（技術開発、メディア、投資、共同研究）
3. コンタクトフォーム
4. SNS/連絡先情報

---

## タスク 3: `index.html` のナビゲーション更新

**パス**: `c:\Users\motoc\chnmotoTmz.github.io\index.html`

### 3a. ナビゲーションにボタン追加

既存コード（変更箇所を正確に指定）:
```html
    <nav class="header-nav" aria-label="カテゴリー">
      <button class="tab is-active" data-filter="all">トップ</button>
      <button class="tab" data-filter="humanoid">ロボット・AI</button>
      <button class="tab" data-filter="music">音楽</button>
      <button class="tab" data-filter="zatsuki">社会・コラム</button>
    </nav>
```

↓ この形に変更:
```html
    <nav class="header-nav" aria-label="カテゴリー">
      <button class="tab is-active" data-filter="all">トップ</button>
      <button class="tab" data-filter="humanoid">ロボット・AI</button>
      <button class="tab" data-filter="music">音楽</button>
      <button class="tab" data-filter="zatsuki">社会・コラム</button>
      <a href="about.html" class="tab" style="text-decoration:none;">About</a>
      <a href="partnership.html" class="tab" style="text-decoration:none; background: linear-gradient(135deg, #1a1a2e, #2d2d5e); color:#a0a0ff;">提携</a>
    </nav>
```

### 3b. フッターにメルマガ購読フォーム追加

`</body>` タグの直前に以下を追加:
```html
<footer class="site-footer">
  <div class="site-footer__inner">
    <div class="newsletter-signup">
      <h3>📬 メールマガジン登録</h3>
      <p>ヒューマノイド・AI・開発の最新情報をお届けします</p>
      <form id="newsletter-form" style="display:flex; gap:0.5rem; flex-wrap:wrap; justify-content:center; margin-top:1rem;">
        <input type="email" id="newsletter-email" placeholder="メールアドレスを入力..."
          style="padding:0.6rem 1rem; border:1px solid #4a4a8e; background:#1a1a2e; color:#e0e0e0; border-radius:4px; min-width:260px;" required>
        <button type="submit"
          style="padding:0.6rem 1.2rem; background:linear-gradient(135deg,#2d2d5e,#1a1a2e); color:#a0a0ff; border:1px solid #4a4a8e; border-radius:4px; cursor:pointer; font-weight:600;">
          登録する
        </button>
      </form>
      <div id="newsletter-msg" style="margin-top:0.75rem; font-size:0.9rem; min-height:1.2em;"></div>
    </div>
    <div class="footer-links" style="margin-top:1.5rem; font-size:0.85rem; color:#888;">
      <a href="about.html" style="color:#a0a0ff; margin-right:1rem;">About</a>
      <a href="partnership.html" style="color:#a0a0ff; margin-right:1rem;">提携・お問い合わせ</a>
      <span>© 2026 chnmotoTmz / Humanoid Media Factory</span>
    </div>
  </div>
</footer>
<style>
.site-footer { background:#0d0d1a; border-top:1px solid #2d2d5e; padding:2.5rem 1rem; text-align:center; margin-top:3rem; }
.site-footer__inner { max-width:800px; margin:0 auto; }
.newsletter-signup h3 { color:#e0e0e0; margin-bottom:0.5rem; }
.newsletter-signup p { color:#888; }
</style>
<script>
document.getElementById('newsletter-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('newsletter-email').value.trim();
  const msgEl = document.getElementById('newsletter-msg');
  const API = window.location.hostname === 'localhost'
    ? 'http://localhost:8084/api/subscribe'
    : 'https://new-blog-system.onrender.com/api/subscribe';
  try {
    const res = await fetch(API, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({email})
    });
    const data = await res.json();
    msgEl.style.color = data.success ? '#6fcf6f' : '#cf6f6f';
    msgEl.textContent = data.message || (data.success ? '登録しました！' : 'エラーが発生しました');
  } catch (err) {
    msgEl.style.color = '#cf6f6f';
    msgEl.textContent = '接続エラー: ' + err.message;
  }
});
</script>
```

---

## 完了後の対応

完了したら `c:\Users\motoc\chnmotoTmz.github.io\AI_STATUS.md` を更新してください。

```markdown
## Other AI: [完了/進行中/ブロック]
- about.html: ✅ 完了 / ❌ 未 / 🔄 進行中
- partnership.html: ✅ 完了 / ❌ 未 / 🔄 進行中
- index.html ナビ更新: ✅ 完了 / ❌ 未 / 🔄 進行中
- index.html フッター追加: ✅ 完了 / ❌ 未 / 🔄 進行中
```

---

*このファイルはGitHub Copilot (Leader)が自動生成しました。*
