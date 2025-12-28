"""
LINE Bot連携サービス。

LINE Messaging APIとの通信、メッセージの送受信、ユーザープロファイルの取得、
コンテンツのダウンロードなど、LINE Botに関連する一連の機能を提供します。

マルチチャンネル対応: 複数のLINEチャンネルからのリクエストを処理できます。
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from requests.exceptions import SSLError, ConnectionError, Timeout

from src.config import Config
from src.database import db, Message, User
from src.services.multi_channel_line_manager import multi_channel_manager

logger = logging.getLogger(__name__)

class LineService:
    """LINE Messaging APIとの連携を管理するサービスクラス。"""

    def __init__(self, channel_access_token: Optional[str] = None, channel_id: Optional[str] = None):
        """
        コンストラクタ。
        
        Args:
            channel_access_token: LINEチャンネルアクセストークン（オプション）
                                 指定されない場合はConfig.LINE_CHANNEL_ACCESS_TOKENを使用
            channel_id: チャンネルID（オプション）- 指定された場合は該当チャンネルの設定を使用
        """
        # アップロードディレクトリの準備
        self.upload_dir = Path(Config.UPLOAD_FOLDER)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # チャンネル選択用の状態
        self.channel_info = None
        self.channel_id = None
        self.test_users = []
        self.owner_user_id = None
        self._active_token: Optional[str] = None
        self._default_token = Config.LINE_CHANNEL_ACCESS_TOKEN

        # 初回設定
        self._apply_channel(channel_id=channel_id, explicit_token=channel_access_token)

    def _apply_channel(self, channel_id: Optional[str], explicit_token: Optional[str] = None) -> None:
        """指定されたチャンネルID/トークンでLineBotApiを構成する。"""
        info = None
        token = explicit_token

        if channel_id and channel_id.strip():  # 空文字でない場合のみチャンネル検索
            info = multi_channel_manager.get_channel(channel_id)
            if not info:
                logger.warning("LineService: チャンネルID %s は未登録です。フォールバックトークンを使用します。", channel_id)
            else:
                token = token or info.get('access_token')

        if not token:
            token = self._default_token

        if not token:
            self.line_bot_api = self._create_dummy_api()
            self._active_token = None
            logger.warning("LineServiceはダミーモードで初期化されました (利用可能なLINE_CHANNEL_ACCESS_TOKENが見つかりません)。")
        else:
            if token != self._active_token:
                self.line_bot_api = LineBotApi(token)
                self._active_token = token
                logger.info("LineService initialized with token: %s...", token[:10])

        # チャンネル情報を更新（存在しない場合はリセット）
        self.channel_info = info
        self.channel_id = info.get('channel_id') if info else None
        self.test_users = info.get('test_users', []) if info else []
        self.owner_user_id = info.get('owner_user_id') if info else None
    # 送信は常に試みる方針のため、追加の送信許可フラグは不要

    def set_channel(self, channel_id: Optional[str]) -> None:
        """後からチャンネルを切り替えるためのヘルパー。"""
        if channel_id == self.channel_id:
            return
        self._apply_channel(channel_id=channel_id)

    def get_user_profile(self, user_id: str) -> dict:
        """
        LINE APIからユーザープロファイルを取得します。
        失敗した場合は、デフォルトの情報を返します。
        """
        try:
            profile = self.line_bot_api.get_profile(user_id)
            return {
                'displayName': getattr(profile, 'display_name', 'LINE User'),
                'pictureUrl': getattr(profile, 'picture_url', None),
                'statusMessage': getattr(profile, 'status_message', None),
            }
        except LineBotApiError as e:
            # 404はBotを友だち追加していない場合の正常な応答なのでWARNINGレベル
            if e.status_code == 404:
                logger.warning(f"ユーザープロファイルが取得できませんでした (ユーザーID: {user_id}): Botが友だち追加されていない可能性があります")
            else:
                logger.error(f"LINE APIからプロファイル取得中にエラーが発生しました (ユーザーID: {user_id}): {e}")
        except Exception as e:
            logger.error(f"プロファイル取得中に予期せぬエラーが発生しました (ユーザーID: {user_id}): {e}", exc_info=True)

        # エラー時は汎用的な情報を返す
        return {'displayName': 'LINE User', 'pictureUrl': None, 'statusMessage': None}

    def send_message(self, user_id: str, text: str) -> bool:
        """指定されたユーザーにテキストメッセージを送信します。
        
        Returns:
            bool: 送信成功時はTrue、失敗時はFalse
        """
        if not user_id or not isinstance(user_id, str):
            logger.error(f"無効なユーザーIDです: {user_id}")
            return False
        # ポリシーに関係なく常に送信を試みる（ユーザー要件）
            
        try:
            message = TextSendMessage(text=text)
            self.line_bot_api.push_message(user_id, message)
            logger.info(f"メッセージをユーザー({user_id})に送信しました。")
            return True
        except LineBotApiError as e:
            # e.error may be an object or dict depending on SDK version; handle both
            err_obj = getattr(e, 'error', None)
            if isinstance(err_obj, dict):
                err_msg = err_obj.get('message')
                err_details = err_obj.get('details')
            else:
                err_msg = getattr(err_obj, 'message', None)
                err_details = getattr(err_obj, 'details', None)

            logger.error(f"LINE APIへのメッセージ送信でエラーが発生しました (ユーザーID: {user_id}): {getattr(e, 'status_code', 'N/A')} {err_msg}")
            if err_details:
                logger.error(f"LINE APIエラーの詳細: {err_details}")
            # 完全なエラー情報を追加でログ出力
            logger.error(f"LINE APIエラー完全情報: status_code={getattr(e, 'status_code', 'N/A')}, error={err_obj}, message='{text[:200]}...'")
            
            # 400エラーの場合、ユーザーがBotを友だち追加していない可能性が高い
            if e.status_code == 400:
                logger.warning(f"ユーザー({user_id})へのメッセージ送信が拒否されました。Botが友だち追加されていないか、ブロックされている可能性があります。")
                # 400エラーは通知失敗として扱うが、例外を投げない（ワークフローを失敗させない）
                return False

            # 429 (Rate Limit) はフォールバックでメール送信
            if e.status_code == 429:
                logger.warning(f"LINE API レート制限（429）検出。フォールバックメールを送信します。ユーザーID={user_id}")
                try:
                    recipient = Config.FALLBACK_EMAIL_RECIPIENT
                    subject = f"[Fallback] LINE delivery failed (user={user_id})"
                    body = f"LINE push_message to {user_id} failed with status 429 (rate limit).\n\nOriginal message:\n{text}\n\nError: {e}"
                    self._send_email_fallback(recipient, subject, body)
                except Exception as mail_e:
                    logger.error(f"フォールバックメール送信中にエラー: {mail_e}", exc_info=True)
                return False
            
            return False
        except Exception as e:
            logger.error(f"メッセージ送信中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return False

    def validate_user_id(self, user_id: str) -> bool:
        """指定されたユーザーIDが有効かどうかを確認します。
        
        Returns:
            bool: ユーザーIDが有効な場合はTrue、無効な場合はFalse
        """
        if not user_id or not isinstance(user_id, str):
            logger.error(f"無効なユーザーIDです: {user_id}")
            return False

        # テスト用のユーザーIDは有効とみなす
        if user_id.startswith(('test_', 'ULOCALTESTUSER', 'TESTUSER')):
            return True

        try:
            # プロファイルを取得してユーザーIDの有効性を確認
            profile = self.line_bot_api.get_profile(user_id)
            logger.info(f"ユーザーID {user_id} は有効です (表示名: {profile.display_name})")
            return True
        except LineBotApiError as e:
            logger.error(f"ユーザーID {user_id} の検証でLINE APIエラーが発生しました: {e.status_code} {e.error.message}")
            if e.status_code == 404:
                logger.warning(f"ユーザーID {user_id} は無効です: ユーザーが見つからないか、Botがブロックされています")
            else:
                logger.error(f"ユーザーID {user_id} の検証で予期せぬAPIエラーが発生しました: {e.status_code} {e.error.message}")
            return False
        except Exception as e:
            logger.error(f"ユーザーID {user_id} の検証中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return False
    def validate_message_content(self, text: str) -> bool:
        """メッセージの内容がLINE APIの制限に適合するかを確認します。
        
        Returns:
            bool: メッセージが有効な場合はTrue、無効な場合はFalse
        """
        if not text or not isinstance(text, str):
            logger.error("メッセージが空または文字列ではありません")
            return False

        # メッセージ長のチェック (LINEの制限: 2000文字)
        if len(text) > 2000:
            logger.error(f"メッセージが長すぎます: {len(text)}文字 (最大2000文字)")
            return False

        # 問題のある文字のチェック
        problematic_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', '\x1c', '\x1d', '\x1e', '\x1f']
        for char in problematic_chars:
            if char in text:
                logger.error(f"メッセージに問題のある制御文字が含まれています: {repr(char)}")
                return False

        return True

    def _send_email_fallback(self, recipient: str, subject: str, body: str) -> bool:
        """フォールバック用にメールを送信するヘルパー。

        SMTP設定は `src.config.Config` から取得します。
        Returns True on success, False otherwise.
        Additionally logs every attempt to `logs/fallback_emails.log` (JSONL) and queues failed sends to `data/email_queue.json`.
        """
        from email.message import EmailMessage
        import smtplib, json
        from datetime import datetime

        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'recipient': recipient,
            'subject': subject,
            'body_preview': (body[:100] + '...') if body and len(body) > 100 else body,
            'result': None,
            'error': None,
            'smtp_refusal': None,
        }

        if not Config.SMTP_HOST:
            logger.error("SMTP_HOSTが設定されていません。フォールバックメールを送信できません。")
            log_entry.update({'result': False, 'error': 'SMTP_HOST not configured'})
            # persist log
            Path('logs').mkdir(exist_ok=True)
            with open('logs/fallback_emails.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            return False

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = Config.EMAIL_FROM or Config.SMTP_USER or 'no-reply@example.com'
        msg['To'] = recipient
        msg.set_content(body)

        host = Config.SMTP_HOST
        port = Config.SMTP_PORT
        user = Config.SMTP_USER
        pwd = Config.SMTP_PASSWORD

        logger.info(f"Sending fallback email to {recipient} via SMTP {host}:{port}")
        try:
            with smtplib.SMTP(host, port, timeout=30) as s:
                try:
                    s.starttls()
                except Exception:
                    logger.debug("STARTTLS failed or unsupported, proceeding without STARTTLS")
                if user and pwd:
                    s.login(user, pwd)
                # send_message may raise or return a dict of refused recipients when using sendmail
                refusal = s.send_message(msg)

            log_entry.update({'result': True, 'smtp_refusal': refusal})
            Path('logs').mkdir(exist_ok=True)
            with open('logs/fallback_emails.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            logger.info(f"フォールバックメールを送信しました: {recipient}")
            return True

        except Exception as e:
            logger.error(f"フォールバックメール送信に失敗しました: {e}", exc_info=True)
            log_entry.update({'result': False, 'error': str(e)})
            # persist log
            Path('logs').mkdir(exist_ok=True)
            with open('logs/fallback_emails.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            # queue for retry
            try:
                qpath = Path('data/email_queue.json')
                qpath.parent.mkdir(parents=True, exist_ok=True)
                if qpath.exists():
                    with open(qpath, 'r', encoding='utf-8') as qf:
                        queue = json.load(qf)
                else:
                    queue = []
                queue.append({
                    'recipient': recipient,
                    'subject': subject,
                    'body': body,
                    'first_failed_at': log_entry['timestamp'],
                    'attempts': 1,
                })
                with open(qpath, 'w', encoding='utf-8') as qf:
                    json.dump(queue, qf, ensure_ascii=False, indent=2)
                logger.info(f"フォールバックメールをキューに格納しました: {qpath}")
            except Exception as qe:
                logger.error(f"キュー保存中にエラーが発生しました: {qe}", exc_info=True)

            return False

    def save_message(self, line_message_id: str, user_id: int, message_type: str, content: str = None) -> dict:
        """受信したメッセージをデータベースに保存します。"""
        try:
            # 重複保存を防ぐ
            if Message.query.filter_by(line_message_id=line_message_id).first():
                logger.info(f"メッセージ {line_message_id} は既にデータベースに存在します。")
                return
            
            new_message = Message(
                line_message_id=line_message_id,
                user_id=user_id,
                message_type=message_type,
                content=content
            )
            db.session.add(new_message)
            db.session.commit()
            logger.info(f"メッセージ {line_message_id} をデータベースに保存しました。")
            return new_message.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"メッセージのデータベース保存中にエラーが発生しました: {e}", exc_info=True)
            raise

    def download_content(self, message_id: str, content_type: str = 'image', timeout: int = 30) -> str:
        """LINEサーバーから画像や動画などのコンテンツをダウンロードします（v2 API使用）。"""
        message_id = (message_id or "").strip()
        if not message_id:
            raise ValueError("メッセージIDが空のため、コンテンツをダウンロードできません。")

        # テスト用のメッセージID（'test_'または'dummy-'を含む）を検出し、ダミーファイルを返す
        if 'test_' in message_id or 'dummy-' in message_id:
            logger.info(f"テストメッセージID '{message_id}' を検出しました。ダミーコンテンツを返します。")
            dummy_file_map = {
                'image': 'dummy_image.jpg',
                'video': 'dummy_video.mp4',
            }
            dummy_filename = dummy_file_map.get(content_type, 'dummy_file.bin')
            dummy_path = self.upload_dir / dummy_filename
            dummy_path.touch(exist_ok=True) # ファイルが存在しない場合は作成
            return str(dummy_path)

        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                extension = self._get_extension(content_type)
                filename = f"{timestamp}_{message_id}{extension}"
                file_path = self.upload_dir / filename
                
                # v2 APIを使用してコンテンツをダウンロード
                logger.info(f"v2 APIでコンテンツダウンロード開始 (試行 {attempt + 1}/{max_retries}): message_id={message_id}")
                message_content = self.line_bot_api.get_message_content(message_id, timeout=timeout)
                
                with open(file_path, 'wb') as f:
                    for chunk in message_content.iter_content():
                        f.write(chunk)
                
                logger.info(f"コンテンツをダウンロードしました: {file_path}")
                
                return str(file_path)
                
            except LineBotApiError as e:
                if e.status_code == 400:
                    logger.warning(f"コンテンツのダウンロードで400エラー。有効期限が切れているか、トークンが正しくない可能性があります。(message_id={message_id})")
                logger.error(
                    f"LINE APIからのコンテンツダウンロードでエラーが発生しました: {e} (message_id={message_id}, content_type={content_type})"
                )
                raise
                
            except (SSLError, ConnectionError, Timeout) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"SSL/接続エラーが発生しました。{retry_delay}秒後に再試行します (試行 {attempt + 1}/{max_retries}): {e}")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数バックオフ
                    continue
                else:
                    logger.error(f"最大リトライ回数に達しました。コンテンツダウンロードに失敗: {e}", exc_info=True)
                    raise
                    
            except IOError as e:
                logger.error(f"ファイルの書き込み中にエラーが発生しました: {e}", exc_info=True)
                raise
                
            except Exception as e:
                logger.error(f"コンテンツダウンロード中に予期せぬエラーが発生しました: {e}", exc_info=True)
                raise

    def _get_extension(self, content_type: str) -> str:
        """コンテンツタイプに応じたファイル拡張子を返します。"""
        return {'.jpg': '.jpg', '.jpeg': '.jpeg', '.png': '.png', '.gif': '.gif', '.bmp': '.bmp', '.tiff': '.tiff', 'image': '.jpg', 'video': '.mp4', 'audio': '.m4a'}.get(content_type, '.bin')

    def _create_dummy_api(self) -> object:
        """ローカル開発用のダミーAPIクライアントを生成します。"""
        upload_dir = self.upload_dir  # クロージャでキャプチャ
        class DummyAPI:
            def push_message(self, *args, **kwargs):
                logger.info("DummyAPI.push_message called (skipped).")
            def get_profile(self, user_id):
                logger.info(f"DummyAPI.get_profile called for {user_id} (skipped).")
                class DummyProfile:
                    display_name = "LINE User"
                    picture_url = None
                    status_message = None
                return DummyProfile()
            def get_message_content(self, message_id):
                logger.info(f"DummyAPI.get_message_content for {message_id} (skipped).")
                # テスト用の画像データを返す
                test_image_path = upload_dir / "20250814_082331_574277571605430326.jpg"
                if test_image_path.exists():
                    class DummyContent:
                        def __init__(self, path):
                            self.path = path
                        def iter_content(self):
                            with open(self.path, 'rb') as f:
                                while chunk := f.read(8192):
                                    yield chunk
                    return DummyContent(test_image_path)
                else:
                    class DummyContent:
                        def iter_content(self): return []
                    return DummyContent()
        return DummyAPI()