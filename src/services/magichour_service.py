"""
Magic Hour画像生成サービス。

Magic Hour Python SDKを使用して、プロンプトから画像を生成します。
https://magichour.ai/

APIキーのローテーション機能を搭載：
- 複数のAPIキーを環境変数に設定可能
- クレジット不足時に自動で次のキーに切り替え
- ラウンドロビン方式でキーを使用
"""

import logging
import os
from typing import Optional, Dict, Any, List
from magic_hour import Client

logger = logging.getLogger(__name__)


class MagicHourService:
    """Magic Hour SDK を使用した画像生成サービス。"""
    
    # クラスレベルでキーインデックスを保持（インスタンス間で共有）
    _current_key_index = 0
    
    def __init__(self):
        """コンストラクタ。"""
        # 複数のAPIキーを取得（カンマ区切りまたは個別の環境変数）
        self.api_keys = self._load_api_keys()
        self.enabled = len(self.api_keys) > 0
        self.client = None
        
        if not self.enabled:
            logger.warning("MAGICHOUR_API_KEY(S) が設定されていません。画像生成機能は無効です。")
        else:
            # 現在のキーでクライアントを初期化
            self._initialize_client()
            logger.info(f"Magic Hour サービスが初期化されました。（{len(self.api_keys)}個のAPIキー利用可能）")
    
    def _load_api_keys(self) -> List[str]:
        """環境変数からAPIキーを読み込む。"""
        keys = []
        
        # 方式1: MAGICHOUR_API_KEYS（カンマ区切り）
        keys_str = os.getenv('MAGICHOUR_API_KEYS', '')
        if keys_str:
            keys.extend([k.strip() for k in keys_str.split(',') if k.strip()])
        
        # 方式2: MAGICHOUR_API_KEY（単一キー、後方互換性）
        single_key = os.getenv('MAGICHOUR_API_KEY', '')
        if single_key and single_key not in keys:
            keys.append(single_key)
        
        # 方式3: MAGICHOUR_API_KEY_1, MAGICHOUR_API_KEY_2, ... （個別キー）
        for i in range(1, 11):  # 最大10個のキーをサポート
            key = os.getenv(f'MAGICHOUR_API_KEY_{i}', '')
            if key and key not in keys:
                keys.append(key)
        
        return keys
    
    def _initialize_client(self):
        """現在のキーインデックスでクライアントを初期化。"""
        if not self.api_keys:
            return
        current_key = self.api_keys[MagicHourService._current_key_index % len(self.api_keys)]
        self.client = Client(token=current_key)
        logger.debug(f"Magic Hour クライアント初期化: キー #{MagicHourService._current_key_index % len(self.api_keys) + 1}/{len(self.api_keys)}")
    
    def _rotate_key(self) -> bool:
        """次のAPIキーに切り替える。全キーを試した場合はFalseを返す。"""
        if len(self.api_keys) <= 1:
            return False
        
        MagicHourService._current_key_index += 1
        if MagicHourService._current_key_index >= len(self.api_keys):
            MagicHourService._current_key_index = 0  # 一周したらリセット
            return False  # 全キーを試した
        
        self._initialize_client()
        logger.info(f"🔄 Magic Hour APIキーをローテーション: キー #{MagicHourService._current_key_index + 1}/{len(self.api_keys)}")
        return True
    
    def generate_image(self, prompt: str, width: int = 1920, height: int = 1080, 
                      timeout: int = 120) -> Optional[Dict[str, Any]]:
        """
        プロンプトから画像を生成します。
        クレジット不足時は自動的に次のAPIキーにローテーションします。
        
        Args:
            prompt: 画像生成用のプロンプト
            width: 画像の幅（デフォルト: 1920）
            height: 画像の高さ（デフォルト: 1080）
            timeout: API呼び出しのタイムアウト秒数（デフォルト: 120秒）
        
        Returns:
            画像生成結果の辞書:
            {
                'images': [{'url': 'https://...'}],
                'prompt': '使用したプロンプト',
                'id': '生成ID',
                'credits_charged': クレジット消費数
            }
            失敗時はNone
        """
        if not self.enabled:
            logger.warning("Magic Hour APIが無効です（APIキー未設定）。")
            return None
        
        if not prompt or len(prompt.strip()) < 10:
            logger.warning("画像生成プロンプトが短すぎます。")
            return None
        
        # 全キーを試すためのループ
        tried_keys = 0
        max_retries = len(self.api_keys)
        
        while tried_keys < max_retries:
            try:
                logger.info(f"Magic Hour API: 画像生成リクエスト - プロンプト: {prompt[:100]}...")
                
                # 画像のアスペクト比を決定
                if width >= height * 1.5:
                    orientation = "landscape"  # 横長 (16:9など)
                elif height >= width * 1.5:
                    orientation = "portrait"   # 縦長 (9:16など)
                else:
                    orientation = "square"     # 正方形 (1:1)
                
                logger.info(f"🖼️ 画像サイズ: {width}x{height}, オリエンテーション: {orientation}")
                
                # Magic Hour SDKで画像を生成
                result = self.client.v1.ai_image_generator.generate(
                    image_count=1,
                    orientation=orientation,
                    style={
                        "prompt": prompt
                    },
                    wait_for_completion=True,  # レンダリング完了まで待機
                    download_outputs=False,     # ローカルダウンロードは不要（URLのみ取得）
                )
                
                logger.info(f"✅ 画像生成成功: ID={result.id}, クレジット消費={result.credits_charged}")
                
                # 生成された画像のURLを取得
                # Magic Hour SDKは `downloads` 配列にURLを返す
                if not result.downloads or len(result.downloads) == 0:
                    logger.error("生成結果に画像が含まれていません。")
                    return None
                
                image_url = result.downloads[0].url
                logger.info(f"🖼️  画像URL: {image_url}")
                
                return {
                    'images': [{'url': image_url}],
                    'prompt': prompt,
                    'id': result.id,
                    'credits_charged': result.credits_charged
                }
                
            except Exception as e:
                error_message = str(e)
                
                # クレジット不足（422）の場合は次のキーを試す
                if "422" in error_message and "credits" in error_message.lower():
                    logger.info(f"Magic Hour: キー #{MagicHourService._current_key_index + 1} クレジット不足")
                    tried_keys += 1
                    
                    if self._rotate_key():
                        logger.info(f"次のAPIキーで再試行します...")
                        continue
                    else:
                        logger.warning("全てのMagic Hour APIキーでクレジット不足です。")
                        return None
                else:
                    logger.error(f"画像生成中にエラーが発生: {e}", exc_info=True)
                    return None
        
        logger.warning("全てのMagic Hour APIキーを試しましたが、画像生成に失敗しました。")
        return None
    
    def optimize_prompt(self, title: str, content_summary: str) -> str:
        """
        記事タイトルと要約から最適な画像生成プロンプトを作成します。
        
        Args:
            title: 記事タイトル
            content_summary: 記事の要約
        
        Returns:
            最適化された画像生成プロンプト
        """
        # 基本的なプロンプトテンプレート
        prompt = f"""Create a high-quality, professional blog thumbnail image.

Article Title: {title}

Summary: {content_summary}

Style Requirements:
- Professional and polished design
- Vibrant and eye-catching colors
- Modern and clean aesthetic
- No text or typography in the image
- 16:9 aspect ratio (1920x1080)
- Suitable for blog header/thumbnail
- High resolution and sharp details
- Visually represents the article's theme"""
        
        return prompt
