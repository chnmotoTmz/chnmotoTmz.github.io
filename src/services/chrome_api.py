#!/usr/bin/env python3
"""
Chromeブラウザ経由でAPIにリクエストを送るモジュール。
ブラウザのセッションとクッキーを使ってAPIアクセスを行う。
"""

import os
import time
import json
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ChromeAPICaller:
    """Chromeブラウザを使ってAPIリクエストを行うクラス。"""
    
    def __init__(self, headless: bool = True):
        """
        Chromeドライバーの初期化。
        
        Args:
            headless: ヘッドレスモードで実行するか
        """
        self.headless = headless
        self.driver = None
    
    def __enter__(self):
        self.start_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_driver()
    
    def start_driver(self):
        """Chromeドライバーを起動。"""
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # ユーザーのChromeプロファイルを使用（クッキーなどを共有）
        user_data_dir = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data'
        if os.path.exists(user_data_dir):
            options.add_argument(f'--user-data-dir={user_data_dir}')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def stop_driver(self):
        """Chromeドライバーを停止。"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def call_api_via_browser(self, url: str, method: str = 'POST', 
                           headers: Optional[Dict[str, str]] = None, 
                           data: Optional[Dict[str, Any]] = None, 
                           timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Chromeブラウザ経由でAPIを呼び出す。
        
        Args:
            url: APIのURL
            method: HTTPメソッド
            headers: リクエストヘッダー
            data: リクエストボディ（JSON）
            timeout: タイムアウト秒
        
        Returns:
            APIレスポンスのJSONデータ
        """
        if not self.driver:
            raise RuntimeError("Chromeドライバーが起動していません")
        
        try:
            # JavaScriptでfetchを実行
            headers_js = json.dumps(headers or {})
            data_js = json.dumps(data or {})
            
            script = f"""
            return fetch('{url}', {{
                method: '{method}',
                headers: {headers_js},
                body: {data_js} ? JSON.stringify({data_js}) : null
            }})
            .then(response => response.json())
            .catch(error => {{ return {{ error: error.message }}; }});
            """
            
            # 適当なページを開いてスクリプト実行
            self.driver.get('about:blank')
            
            # スクリプト実行
            result = self.driver.execute_script(script)
            
            return result
            
        except Exception as e:
            print(f"API呼び出しエラー: {e}")
            return None

def call_gemini_api_via_chrome(prompt: str, api_url: str, bearer: Optional[str] = None) -> Optional[str]:
    """
    Chrome経由でGemini APIを呼び出し、画像URLを取得する。
    
    Args:
        prompt: 画像生成プロンプト
        api_url: API URL
        bearer: Bearerトークン
    
    Returns:
        画像URLまたはNone
    """
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    
    # FIX: Escape newlines to prevent early submission in browser automation
    full_prompt = f"以下のプロンプトで画像を1枚生成してください。生成した画像はダウンロードしてください。\n\n{prompt}"
    data = {"prompt": full_prompt.replace('\n', '\\n')}
    
    with ChromeAPICaller(headless=True) as caller:
        result = caller.call_api_via_browser(api_url, 'POST', headers, data, timeout=300)
        
        if result and 'answer' in result and 'images' in result['answer']:
            images = result['answer']['images']
            if images:
                first = images[0]
                if isinstance(first, dict) and 'src' in first:
                    return first['src']
                elif isinstance(first, str):
                    return first
    
    return None