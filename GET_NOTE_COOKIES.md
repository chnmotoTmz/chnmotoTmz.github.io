# note.com Cookie 取得手順

## ステップ 1: ブラウザで note.com にログイン

1. Chrome/Firefox/Edge で https://note.com にアクセス
2. ログイン (メール＋パスワード)
3. ダッシュボードまで進む

## ステップ 2: Cookie を取得

### Chrome/Edge の場合:
1. F12 キーで DevTools を開く
2. **Console** タブを選択
3. 下記のコマンドを貼り付けして実行:

```javascript
const cookies = {};
document.cookie.split('; ').forEach(c => {
  const [name, value] = c.split('=');
  cookies[name] = value;
});
console.log(JSON.stringify(cookies, null, 2));
```

4. 出力された JSON をコピー

### Firefox の場合:
1. F12 キーで DevTools を開く
2. **Storage** → **Cookies** → **https://note.com** を選択
3. すべてのクッキーを右クリック → "Copy All" またはスクリーンショット撮影

## ステップ 3: .env.production を更新

取得した Cookie JSON を下記の形式で `.env.production` に設定:

```bash
NOTE_COOKIES={"fp":"...","_vid_v2":"...","XSRF-TOKEN":"...","_gid":"...","_ga":"..."}
```

## ステップ 4: サーバーを再起動

```powershell
python .\run_app.py
```

---

**重要**: 
- Cookie は個人認証情報です。他者と共有しないでください
- Cookie は有効期限があります (通常 30 日)
- Cookie が変わったら .env.production を更新してサーバーを再起動

