"""
バッチ処理サービス。

ユーザーごとのメッセージを一定期間バッファリングし、タイマーを使って
遅延バッチ処理を行うサービスです。
このサービスはスレッドセーフに設計されています。

主な機能:
- ユーザーからのメッセージをスレッドセーフなバッファに追加します。
- メッセージが追加されるたびに、ユーザーごとのタイマーをリセットします。
- タイマーが発火すると、収集されたメッセージを指定されたコールバック関数に渡して処理を実行します。
- 手動での即時処理や、安全なシャットダウン機能も提供します。
"""
from __future__ import annotations
import threading
from collections import defaultdict
from typing import Dict, List, Any, Callable
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class BatchService:
    """ユーザーごとのメッセージバッファリングと遅延処理を管理します。"""

    def __init__(self, interval_sec: int, process_callback: Callable[[str, List[Dict[str, Any]]], None]):
        """
        コンストラクタ。

        Args:
            interval_sec (int): メッセージをバッファリングする時間（秒）。
            process_callback (Callable): バッチ処理を実行するコールバック関数。
                                         引数として (user_id, messages) を受け取ります。
        """
        self.interval = interval_sec
        self.process_callback = process_callback
        self.app = current_app._get_current_object() if current_app else None
        self.buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock() # バッファとタイマーへのアクセスを保護するロック

    def add_message(self, user_id: str, message: Dict[str, Any]):
        """
        メッセージをユーザーのバッファに追加し、処理タイマーをリセットします。
        このメソッドはスレッドセーフです。
        """
        with self.lock:
            self.buffers[user_id].append(message)

            # ログ出力用にバッファ内のメッセージタイプを集計
            types_summary = defaultdict(int)
            for msg in self.buffers[user_id]:
                types_summary[msg.get('message_type', 'unknown')] += 1

            logger.info(
                "BatchService: メッセージをキューに追加しました (ユーザー: %s, 現在のサイズ: %d, タイプ: %s)",
                user_id, len(self.buffers[user_id]), dict(types_summary)
            )
            self._reset_timer_locked(user_id)

    def flush_now(self, user_id: str):
        """指定されたユーザーのバッチを手動で即時処理します。"""
        with self.lock:
            # バッファからメッセージを取得し、タイマーをキャンセル
            messages = self.buffers.pop(user_id, [])
            timer = self.timers.pop(user_id, None)
            if timer:
                timer.cancel()

        if messages:
            self._invoke(user_id, messages)

    def shutdown(self):
        """
        サービスを安全にシャットダウンします。
        全ての実行中タイマーをキャンセルし、保留中のバッチを処理します。
        """
        with self.lock:
            for timer in self.timers.values():
                timer.cancel()
            pending_batches = list(self.buffers.items())
            self.buffers.clear()
            self.timers.clear()
            logger.info("BatchServiceはシャットダウンを開始します。保留中のバッチを処理します。")

        for user_id, messages in pending_batches:
            self._invoke(user_id, messages)

    # --- 内部メソッド ---

    def _reset_timer_locked(self, user_id: str):
        """
        指定されたユーザーのタイマーをリセットします。
        このメソッドはロック内で呼び出す必要があります。
        """
        # 既存のタイマーがあればキャンセル
        if user_id in self.timers:
            self.timers[user_id].cancel()

        # 新しいタイマーを作成して開始
        timer = threading.Timer(self.interval, self._timer_fire, args=[user_id])
        timer.daemon = True # メインスレッドが終了したらタイマーも終了させる
        timer.start()
        self.timers[user_id] = timer
        logger.debug(f"BatchService: ユーザー {user_id} のタイマーを {self.interval}秒でセットしました。")

    def _timer_fire(self, user_id: str):
        """タイマーが発火したときに呼び出されるメソッド。"""
        with self.lock:
            messages = self.buffers.pop(user_id, [])
            self.timers.pop(user_id, None)

        if not messages:
            logger.info(f"BatchService: タイマーが発火しましたが、ユーザー {user_id} の処理対象メッセージはありませんでした。")
            return

        self._invoke(user_id, messages)

    def _invoke(self, user_id: str, messages: List[Dict[str, Any]]):
        """
        登録されたコールバック関数を呼び出してバッチ処理を実行します。
        例外は捕捉せず、呼び出し元に伝播させます。
        """
        logger.info(
            "BatchService: バッチ処理を実行します (ユーザー: %s, メッセージ数: %d)",
            user_id, len(messages)
        )
        try:
            if self.app:
                with self.app.app_context():
                    self.process_callback(user_id, messages)
            else:
                self.process_callback(user_id, messages)
        except Exception as e:
            logger.error(
                "BatchServiceのコールバック処理中にエラーが発生しました (ユーザー: %s): %s",
                user_id, e, exc_info=True
            )

__all__ = ['BatchService']
