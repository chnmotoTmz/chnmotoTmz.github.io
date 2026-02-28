import os
import glob
import requests
import time
from typing import Dict, Any

from lib.llm import LLMService

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
            metaprompt = (
                f"あなたは優秀なプロンプトエンジニアです。以下のブログ記事の内容を面白おかしく表現した、"
                f"4コマ漫画風のイラストを画像生成AIに描かせるための英語のプロンプトを1つ作成してください。\n"
                f"英語のプロンプト「のみ」を出力し、説明や装飾は一切不要です。\n\n"
                f"【記事のタイトル】: {title}\n"
                f"【記事の内容（抜粋）】: {content_snippet}"
            )
            
            try:
                print("Step 1: 画像生成用プロンプトをLLMで生成中...")
                llm = LLMService()
                thumbnail_prompt = llm.generate_text(metaprompt)
                print(f"=> 生成された画像プロンプト: {thumbnail_prompt}")
            except Exception as e:
                print(f"LLMによる画像プロンプト生成に失敗しました: {e}")
                # フォールバック: 元の簡易的なプロンプトをそのまま使う
                thumbnail_prompt = (
                    f"4-panel comic style, funny illustration representing blog article. "
                    f"Title: {title}. Focus on the main keywords."
                )
                print(f"=> フォールバック用プロンプトを使用: {thumbnail_prompt}")
        
        # Step 2: APIを叩いてサムネイル生成をトリガーする
        print("Step 2: サムネイル画像生成を開始します...")
        start_time = time.time()
        self._trigger_image_generation(thumbnail_prompt)
        
        thumbnail_url = self._scavenge_latest_image(after_time=start_time)
        
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
                # ループによる待機は _scavenge_latest_image 側で行うため、ここではスリープしません。
            else:
                print(f"サムネイル生成指示エラー (HTTP {response.status_code}): {response.text}")
                
        except Exception as e:
            print(f"サムネイル生成トリガー中にエラー: {e}")

    def _scavenge_latest_image(self, after_time: float):
        """
        ローカルのDownloads等のフォルダから最も新しい画像ファイルを拾い上げ、
        Catboxに泥臭くアップロードしてURLを返す。
        """
        # ダウンロードフォルダ等を想定
        search_dirs = [
            os.path.expanduser('~/Downloads'),
            os.path.join(os.getcwd(), 'data')
        ]
        
        print("新しい画像がダウンロードされるのを待機しています...")
        poll_interval = 2
        max_wait = 60
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait:
            valid_files = []
            for d in search_dirs:
                if os.path.exists(d):
                    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
                        for f in glob.glob(os.path.join(d, ext)):
                            # 処理開始後に作成または更新されたファイルのみを拾う
                            if os.path.getmtime(f) >= after_time or os.path.getctime(f) >= after_time:
                                valid_files.append(f)
            
            if valid_files:
                # 最も新しいファイルを取得
                latest_file = max(valid_files, key=os.path.getctime)
                print(f"泥臭く拾い上げたサムネイル候補: {latest_file}")
                # Catboxアップロード
                return self._upload_to_catbox(latest_file)
                
            time.sleep(poll_interval)
            
        print("指定時間(60秒)内に新しい画像ファイルが見つかりませんでした。")
        return None

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
