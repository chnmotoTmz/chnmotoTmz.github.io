"""
Saved legacy GeminiService implementation before migration.

This file preserves the previous, larger implementation so that
we can migrate callers incrementally. Do not modify in normal flow.
"""
"""
Gemini API直接連携サービス。

ChromeのCookieを使ってGeminiにアクセスします。
カスタムLLM API（/api/ask）が設定されている場合はそちらを優先利用します。
"""

import logging
import os
import time
import requests
import json
from gemini import Gemini
from src.services.claude_service import ClaudeService
from typing import Optional, Dict, Any
from PIL import Image
from src.utils import gemini_logger

logger = logging.getLogger(__name__)

# グローバル除外リスト（プロセス全体で共有）
_GLOBAL_EXCLUDED_COOKIES = set()

class GeminiService:
	"""
	ChromeのCookieを使ってGemini APIと直接連携し、テキスト生成や画像解析機能を提供します。
	複数のCookieセットを自動でローテーションします。
	"""

	def __init__(self, blog_config: Optional[Dict[str, Any]] = None):
		"""
		コンストラクタ。
		環境変数からCookie設定を読み込みます。
		"""
		global _GLOBAL_EXCLUDED_COOKIES
        
		self._test_mode = False
		self._current_cookie_index = 0
        
		# 複数のCookieセットを取得
		cookies_list_str = os.getenv('GEMINI_COOKIES_LIST', '')
		if cookies_list_str:
			try:
				self._cookies_list = json.loads(cookies_list_str)
			except json.JSONDecodeError:
				raise ValueError("GEMINI_COOKIES_LIST が正しいJSON形式ではありません")
		else:
			# フォールバック: 単一Cookie
			single_psid = os.getenv('GEMINI_1PSID', '')
			single_psidts = os.getenv('GEMINI_1PSIDTS', '')
			if single_psid and single_psidts:
				self._cookies_list = [{
					'__Secure-1PSID': single_psid,
					'__Secure-1PSIDTS': single_psidts
				}]
			else:
				raise ValueError("GEMINI_COOKIES_LIST または GEMINI_1PSID/GEMINI_1PSIDTS が設定されていません")
        
		if not self._cookies_list:
			raise ValueError("Cookieが設定されていません")
        
		# Deprecated: Cookie-based Gemini path. Default behaviour is to use the
		# local/custom LLM API (eg. http://localhost:3000/api/ask). If that fails,
		# fall back to Claude via `ClaudeService`.
		self.client = None
		self._available = True
		# Initialize Claude client for fallbacks and image analysis
		try:
			self.claude = ClaudeService()
			logger.info("ClaudeService initialized for fallback/image analysis")
		except Exception as e:
			logger.warning(f"Failed to initialize ClaudeService: {e}")
			self.claude = None
    
	def _rotate_cookie(self):
		"""次のCookieセットに切り替え"""
		self._current_cookie_index = (self._current_cookie_index + 1) % len(self._cookies_list)
		self.client = Gemini(cookies=self._cookies_list[self._current_cookie_index])
		logger.info(f"Cookieを切り替えました: {self._current_cookie_index + 1}/{len(self._cookies_list)}")
    
	def analyze_image_from_path(self, image_path: str, prompt: str = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。") -> str:
		"""
		画像を解析し、説明文を生成します。
		Quota超過したCookieは除外リストに追加され、以降は使用されません。
		"""
		logger.info(f"画像解析開始: {image_path}")

		# Use Claude for image analysis (cookie-based vision path deprecated)
		logger.info(f"画像解析 (Claude) 開始: {image_path}")

		if not self.claude:
			logger.error("ClaudeService が利用不可です。CLAUDE_API_KEY を確認してください。")
			raise RuntimeError("ClaudeService が利用不可です。CLAUDE_API_KEY を確認してください。")

		# Construct an instruction that references the local image path.
		img_prompt = f"{prompt}\n\n画像ファイルパス: {image_path}\n\n上記の画像をブログ記事向けに説明してください。短く要点をまとめ、例示的なリード文1段落と3つの箇条書きポイントを出してください。"

		result = self.claude.generate_text(img_prompt, max_tokens=800, temperature=0.0)
		if result and isinstance(result, str) and result.strip():
			caller = gemini_logger.get_caller_module_name()
			gemini_logger.log_gemini_interaction(caller, f"[Image: {image_path}] {prompt}", result, "claude_image")
			logger.info(f"画像解析(Claude)成功: {image_path}")
			return result.strip()

		logger.error("画像解析に失敗しました (Claude) %s", image_path)
		raise RuntimeError("画像解析に失敗しました")

	def generate_text(self, prompt: str, model_name: Optional[str] = None, max_tokens: int = 3500, temperature: float = 0.4, task_priority: str = "normal") -> str:
		"""
		テキストを生成します。複数のCookieで自動リトライします。
		Quota超過したCookieは除外リストに追加され、以降は使用されません。
        
		カスタムLLM API（CUSTOM_LLM_API_URL）が設定されている場合はそちらを優先利用し、
		失敗した場合のみGemini APIにフォールバックします。
        
		Args:
			prompt: 生成プロンプト
			model_name: 使用するモデル名（指定しない場合は自動選択）- Cookieベースでは無視
			max_tokens: 最大トークン数 - Cookieベースでは無視
			temperature: 生成温度 - Cookieベースでは無視
			task_priority: タスク優先度 - Cookieベースでは無視
		"""
		logger.info(f"テキスト生成開始")

		# Default: use custom/local API (eg. http://localhost:3000/api/ask)
		custom_api_url = os.getenv('CUSTOM_LLM_API_URL', os.getenv('LOCAL_GEMINI_API_URL', 'http://localhost:3000/api/ask'))
		if custom_api_url:
			logger.info(f"カスタムLLM APIを優先利用します: {custom_api_url}")
			custom_result = self._generate_text_via_custom_api(prompt, custom_api_url, max_tokens, temperature)
			if custom_result:
				return custom_result
			else:
				logger.warning("カスタムLLM APIが失敗しました。Claudeにフォールバックします。")

		# Fallback: Claude
		if self.claude:
			claude_result = self.claude.generate_text(prompt, max_tokens=max_tokens if max_tokens else 2000, temperature=temperature if temperature else 0.0)
			if claude_result:
				# Log interaction
				caller = gemini_logger.get_caller_module_name()
				gemini_logger.log_gemini_interaction(caller, prompt, claude_result, "claude")
				logger.info("✅ Claudeによりテキスト生成成功")
				return claude_result
			else:
				logger.warning("Claudeでのテキスト生成に失敗しました")

		raise RuntimeError("テキスト生成に失敗しました（カスタムAPIとClaudeの両方で失敗）")

	def _generate_text_via_custom_api(self, prompt: str, api_url: str, max_tokens: int = 3500, temperature: float = 0.4) -> Optional[str]:
		"""
		Groq API経由でテキストを生成します。
        
		仕様:
		- POST /openai/v1/chat/completions にOpenAI互換リクエストを送信
		- 同期的にレスポンスを待機（タイムアウト付き）
		- レスポンスからテキストを取得して返す
        
		Args:
			prompt: 生成プロンプト
			api_url: Groq APIのURL
			max_tokens: 最大トークン数
			temperature: 生成温度
        
		Returns:
			生成されたテキスト（失敗時はNone）
		"""
		try:
			logger.info(f"🌐 カスタムLLM API呼び出し: {api_url}")
            
			headers = {"Content-Type": "application/json"}
			bearer = os.getenv('CUSTOM_LLM_API_BEARER')
			if bearer:
				headers["Authorization"] = f"Bearer {bearer}"
			else:
				# ローカルのラッパー (http://localhost:3000) などでは Bearer を要求しない場合があるため、
				# 必須とはせずヘッダを付与しない。
				logger.debug("CUSTOM_LLM_API_BEARER が未設定のため Authorization ヘッダは付与しません")
            
			# Gemini Web UI形式のリクエストボディ
			payload = {
				"prompt": prompt
			}
            
			# タイムアウト設定（長文生成があるため長め）
			timeout = int(os.getenv('CUSTOM_LLM_API_TIMEOUT', '300'))  # デフォルト5分
            
			# Log outgoing request for debugging the wrapper behavior
			try:
				logger.debug(f"Custom LLM API request url={api_url} headers={headers} payload={json.dumps(payload)[:2000]}")
			except Exception:
				logger.debug("Custom LLM API request built (could not stringify payload)")

			# Also print to stdout for quick test visibility
			try:
				print(f"DEBUG_CUSTOM_API -> url={api_url} headers={headers} payload={json.dumps(payload)}")
			except Exception:
				print("DEBUG_CUSTOM_API -> payload build failed")

			resp = requests.post(
				api_url,
				json=payload,
				timeout=timeout,
				headers=headers,
			)
            
			if resp.status_code == 200:
				data = resp.json()
                
				# Gemini Web UI形式のレスポンス処理
				if 'answer' in data and 'text' in data['answer']:
					answer = data['answer']['text']
				else:
					# フォールバック
					answer = data.get('answer') or data.get('text') or data.get('response') or data.get('content')
                
				# answerがオブジェクトの場合、textフィールドを抽出
				if answer and isinstance(answer, dict):
					answer = answer.get('text') or answer.get('content') or ''
                
				if answer and isinstance(answer, str) and answer.strip():
					result_text = answer.strip()
					# エラーレスポンスをチェック
					if result_text.startswith("Error:") or result_text.lower().startswith("error"):
						logger.warning(f"Gemini Web UIがエラーレスポンスを返しました: {result_text}")
						return None
					logger.info(f"✅ Gemini Web UIからテキスト生成成功 (長さ: {len(result_text)}文字)")
                    
					# Log interaction
					caller = gemini_logger.get_caller_module_name()
					gemini_logger.log_gemini_interaction(caller, prompt, result_text, "gemini_web_ui")
                    
					return result_text
				else:
					logger.warning(f"Gemini Web UIが空または不正なレスポンスを返しました: {data}")
					return None
			elif resp.status_code == 429:
				# レートリミット超過の場合、リトライ
				retry_after = resp.headers.get('Retry-After')
				if retry_after:
					try:
						wait_seconds = int(retry_after)
						logger.warning(f"Gemini Web UIレートリミット超過。{wait_seconds}秒待機してリトライします。")
						time.sleep(wait_seconds)
						# リトライ
						resp = requests.post(
							api_url,
							json=payload,
							timeout=timeout,
							headers=headers,
						)
						if resp.status_code == 200:
							data = resp.json()
							if 'answer' in data and 'text' in data['answer']:
								answer = data['answer']['text']
							else:
								answer = data.get('answer') or data.get('text') or data.get('response') or data.get('content')
							if answer and isinstance(answer, dict):
								answer = answer.get('text') or answer.get('content') or ''
							if answer and isinstance(answer, str) and answer.strip():
								result_text = answer.strip()
								if result_text.startswith("Error:") or result_text.lower().startswith("error"):
									logger.warning(f"Gemini Web UIがエラーレスポンスを返しました: {result_text}")
									return None
								logger.info(f"✅ Gemini Web UIからテキスト生成成功 (リトライ後、長さ: {len(result_text)}文字)")
								caller = gemini_logger.get_caller_module_name()
								gemini_logger.log_gemini_interaction(caller, prompt, result_text, "gemini_web_ui")
								return result_text
						else:
							logger.warning(f"Gemini Web UIリトライ失敗: status={resp.status_code}")
							return None
					except ValueError:
						logger.warning(f"Retry-Afterヘッダーが不正: {retry_after}")
						return None
				else:
					logger.warning(f"Gemini Web UIレートリミット超過ですが、Retry-Afterヘッダーがありません")
					return None
			elif resp.status_code == 503:
				logger.warning(f"Gemini Web UIが利用不可 (503)")
				return None
			else:
				logger.warning(f"Gemini Web UI呼び出し失敗: status={resp.status_code}, body={resp.text[:200]}")
				return None
                
		except requests.exceptions.Timeout:
			logger.warning(f"Gemini Web UIタイムアウト ({timeout}秒超過)")
			return None
		except requests.exceptions.ConnectionError:
			logger.warning(f"Gemini Web UIに接続できません: {api_url}")
			return None
		except Exception as e:
			logger.error(f"Gemini Web UI呼び出し中にエラー: {e}")
			return None

	def set_test_mode(self, enabled: bool):
		"""
		テストモードを有効/無効にします。
		"""
		self._test_mode = enabled
		logger.info(f"GeminiService test mode set to: {enabled}")
<COPY_OF_CURRENT_GEMINI>