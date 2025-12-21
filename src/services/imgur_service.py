"""
Imgur連携サービス。

画像ファイルをImgurにアップロードし、公開URLを取得する機能を提供します。
OAuth 2.0 (Bearer Token) と Client-ID の両方の認証方式に対応しています。
"""
import os
import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ロガーの設定
logger = logging.getLogger(__name__)
# Imgur APIのエンドポイントURL
IMGUR_API_URL = "https://api.imgur.com/3/image"

class ImgurService:
    """
    Imgurへの画像アップロードを管理するサービスクラス。
    認証情報の優先順位: OAuth Bearer Token > Client-ID
    """
    def __init__(self,
                 client_id: Optional[str] = None,
                 access_token: Optional[str] = None,
                 session: Optional[requests.Session] = None):
        """
        コンストラクタ。認証情報とHTTPセッションを初期化します。
        不安定なネットワークに対して堅牢性を高めるため、リトライ処理を設定します。
        """
        self.client_id = client_id or os.getenv("IMGUR_CLIENT_ID")
        self.access_token = access_token or os.getenv("IMGUR_ACCESS_TOKEN")
        self.session = session or requests.Session()

        # ネットワークエラー時にリトライを行うアダプタをセッションに設定
        try:
            retry_strategy = Retry(
                total=3,                # 合計リトライ回数
                connect=3,              # 接続エラーのリトライ回数
                read=3,                 # 読み取りエラーのリトライ回数
                backoff_factor=0.8,     # リトライ間隔の指数増加係数
                status_forcelist=[429, 500, 502, 503, 504], # リトライ対象のHTTPステータスコード
                allowed_methods=["POST", "GET"], # リトライ対象のHTTPメソッド
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("https://", adapter)
        except Exception as e:
            logger.warning(f"Failed to configure retry adapter for ImgurService: {e}")

    def upload_image(self,
                     image_path: str,
                     title: str = "",
                     description: str = "",
                     privacy: str = "hidden") -> Dict[str, Any]:
        """
        指定されたパスの画像をImgurにアップロードします。

        Args:
            image_path (str): アップロードする画像のファイルパス。
            title (str): 画像のタイトル。
            description (str): 画像の説明。
            privacy (str): 公開設定 ('public', 'hidden', 'private')。

        Returns:
            Dict[str, Any]: アップロード結果。成功時は 'success': True と 'link' を含む。

        Raises:
            FileNotFoundError: 指定された画像ファイルが存在しない場合。
            RuntimeError: Imgurの認証情報が設定されていない場合。
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"指定された画像ファイルが見つかりません: {image_path}")

        # 認証ヘッダーを設定 (Bearer Tokenを優先)
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.client_id:
            headers["Authorization"] = f"Client-ID {self.client_id}"
        else:
            raise RuntimeError("Imgurの認証情報（CLIENT_ID または ACCESS_TOKEN）が提供されていません。")

        with open(image_path, "rb") as image_file:
            payload = {
                "title": title or os.path.basename(image_path),
                "description": description or "",
                "privacy": privacy
            }

            try:
                files = {"image": image_file}
                response = self.session.post(IMGUR_API_URL, headers=headers, files=files, data=payload, timeout=45)
                logger.debug(f"Imgur API response status: {response.status_code}")
                logger.debug(f"Imgur API response headers: {response.headers}")
                response.raise_for_status() # 2xx以外のステータスコードで例外を発生

            except requests.exceptions.HTTPError as e:
                if e.response:
                    logger.error(f"Imgur API response body: {e.response.text}")
                logger.error(f"Imgurへのアップロードリクエストに失敗しました: {e}", exc_info=True)
                
                # Bearer Tokenでの失敗時にClient-IDでのフォールバックを試みる
                if self.client_id and "Bearer" in headers.get("Authorization", ""):
                    logger.warning("Bearer Tokenでのアップロードに失敗。Client-IDで再試行します...")
                    try:
                        fallback_headers = {"Authorization": f"Client-ID {self.client_id}"}
                        image_file.seek(0)
                        files = {"image": image_file}
                        response = self.session.post(IMGUR_API_URL, headers=fallback_headers, files=files, data=payload, timeout=45)
                        logger.debug(f"Imgur API fallback response status: {response.status_code}")
                        logger.debug(f"Imgur API fallback response headers: {response.headers}")
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as e2:
                        if e2.response:
                            logger.error(f"Imgur API fallback response body: {e2.response.text}")
                        logger.error(f"Imgurアップロードのフォールバックも失敗しました: {e2}", exc_info=True)
                        raise
                    except requests.RequestException as e2:
                        logger.error(f"Imgurアップロードのフォールバック中にネットワークエラー: {e2}", exc_info=True)
                        raise
                else:
                    raise
            except requests.RequestException as e:
                logger.error(f"Imgurへのアップロードリクエスト中にネットワークエラーが発生しました: {e}", exc_info=True)
                raise

        # レスポンスの解析
        try:
            response_data = response.json()
            if response_data.get("success"):
                link = response_data.get("data", {}).get("link")
                if not link:
                    logger.warning(f"Imgurのレスポンスにリンクが含まれていません: {response_data}")
                return {"success": True, "link": link, "raw": response_data}
            else:
                error_message = response_data.get("data", {}).get("error", "Unknown error")
                logger.error(f"Imgur APIがエラーを返しました: {error_message}")
                return {"success": False, "status": response.status_code, "error": error_message}
        except ValueError: # JSONデコードエラー
            logger.error(f"Imgurからの不正なJSONレスポンス: {response.text}")
            return {"success": False, "status": response.status_code, "error": "Invalid JSON response"}


def upload_image(image_path: str, title: str = "", description: str = "", privacy: str = "hidden") -> Dict[str, Any]:
    """
    ImgurServiceのインスタンスを生成して画像をアップロードする便利な関数。
    """
    try:
        service = ImgurService()
        return service.upload_image(image_path, title=title, description=description, privacy=privacy)
    except Exception as e:
        logger.error(f"upload_image関数でエラーが発生しました: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
