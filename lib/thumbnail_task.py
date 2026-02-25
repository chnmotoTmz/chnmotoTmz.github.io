import os
import glob
import requests
from typing import Dict, Any

class ThumbnailGeneratorTask:
    """
    スカベンジャー・プロトコルに従い、ローカルの特定フォルダから
    最新の画像ファイル（ダウンロードされた副作用）を拾い上げてCatboxにアップロードし、
    記事の先頭にプレンドする泥臭いタスク。
    Fail-Fast原則に従い、異常時は即座に例外を投げて遮断する。
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get('title', 'サムネイル')
        content = inputs.get('content', '')
        
        if not self.config.get('enabled', True):
            return {"enhanced_content": content}
            
        # 1. すでにサムネイル（先頭の画像タグ）があるかチェック
        if content.strip().startswith("!["):
            print("既にサムネイルが存在するためスキップします。")
            return {"enhanced_content": content}
            
        thumbnail_prompt = inputs.get('thumbnail_prompt')
        if not thumbnail_prompt or thumbnail_prompt == title:
            # 記事の内容を面白おかしく表現する4コマ漫画風のプロンプトを生成
            content_snippet = content[:800] if content else title
            thumbnail_prompt = (
                f"ブログ記事の内容を面白おかしく表現した、4コマ漫画風のイラストを生成してください。\n"
                f"【記事のタイトル】: {title}\n"
                f"【記事の内容（抜粋）】: {content_snippet}"
            )
        
        # 0. APIを叩いてサムネイル生成をトリガーする
        self._trigger_image_generation(thumbnail_prompt)
        
        thumbnail_url = self._scavenge_latest_image()
        
        if not thumbnail_url:
            raise RuntimeError("【Fail-Fast】 拾い上げ可能なサムネイル画像が見つからなかった、またはアップロードに失敗しました。処理を遮断します。")
            
        # 2. 成果物の物理的保護・強制結合
        thumbnail_markdown = f"![{title}]({thumbnail_url})\n\n"
        enhanced_content = thumbnail_markdown + content
        
        return {"enhanced_content": enhanced_content}

    def _trigger_image_generation(self, prompt: str):
        """
        localhost:3000 にImageモードでプロンプトを投げ、サムネイルの生成を開始させる。
        実際の画像のダウンロード（副作用）はこの呼び出しによってブラウザ拡張等で行われる前提。
        """
        import time
        api_url = os.environ.get('CUSTOM_THUMBNAIL_API_URL', 'http://localhost:3000/api/ask')
        bearer_token = os.environ.get('CUSTOM_LLM_API_BEARER')
        
        print(f"サムネイル生成をトリガー中: {api_url} (Prompt: {prompt[:30]}...)")
        
        headers = {"Content-Type": "application/json"}
        if bearer_token:
            headers['Authorization'] = f"Bearer {bearer_token}"
            
        try:
            # モード設定 (Imageモードを想定。必要に応じて変更)
            api_root = api_url.split('/api', 1)[0]
            requests.post(f"{api_root}/api/set_mode", json={"mode": "Image"}, timeout=10)
            
            # 生成指示
            payload = {"prompt": prompt.replace('\n', '\\n')}
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=120  # 画像生成は時間がかかるため長めに設定
            )
            
            if response.status_code == 200:
                print("サムネイル生成指示完了（ブラウザ等でのダウンロード待機に入ります...）")
                # ダウンロードが完了するまでのバッファとして数秒〜十数秒待機
                # 完全に泥臭いアプローチですが、副作用ベースのため固定ウェイトを入れます
                time.sleep(15) 
            else:
                print(f"サムネイル生成指示エラー (HTTP {response.status_code}): {response.text}")
                
        except Exception as e:
            print(f"サムネイル生成トリガー中にエラー: {e}")

    def _scavenge_latest_image(self):
        """
        ローカルのDownloads等のフォルダから最も新しい画像ファイルを拾い上げ、
        Catboxに泥臭くアップロードしてURLを返す。
        """
        # ダウンロードフォルダ等を想定
        search_dirs = [
            os.path.expanduser('~/Downloads'),
            os.path.join(os.getcwd(), 'data')
        ]
        
        image_files = []
        for d in search_dirs:
            if os.path.exists(d):
                image_files.extend(glob.glob(os.path.join(d, '*.png')))
                image_files.extend(glob.glob(os.path.join(d, '*.jpg')))
                image_files.extend(glob.glob(os.path.join(d, '*.jpeg')))
                image_files.extend(glob.glob(os.path.join(d, '*.webp')))
        
        if not image_files:
            return None
            
        # 最も新しいファイルを取得
        latest_file = max(image_files, key=os.path.getctime)
        print(f"泥臭く拾い上げたサムネイル候補: {latest_file}")
        
        # Catboxアップロード
        return self._upload_to_catbox(latest_file)

    def _upload_to_catbox(self, file_path: str):
        print(f"Catboxへアップロード中: {file_path}")
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    'https://catbox.moe/user/api.php',
                    data={'reqtype': 'fileupload'},
                    files={'fileToUpload': f},
                    timeout=30
                )
            if response.status_code == 200:
                print(f"Catboxアップロード成功: {response.text.strip()}")
                return response.text.strip()
            else:
                print(f"Catboxアップロード失敗 (HTTP {response.status_code}): {response.text}")
                return None
        except Exception as e:
            print(f"Catboxアップロード中例外エラー: {e}")
            return None
