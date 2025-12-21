"""
Demo Task Modules for Workflow Engine Testing
デモ用タスクモジュール - ワークフローエンジンの動作確認用
"""
from typing import Dict, Any
import time
import random
from src.services.framework.base_task import BaseTaskModule


class DemoDataPreparer(BaseTaskModule):
    """デモ用データ準備タスク"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """データを準備"""
        user_name = inputs.get('user_name', 'Unknown User')
        topic = inputs.get('topic', 'General Topic')
        
        print(f"📦 Preparing data for user: {user_name}")
        print(f"📝 Topic: {topic}")
        
        # シミュレーション用のデータ生成
        prepared_data = {
            'user': user_name,
            'topic': topic,
            'timestamp': time.time(),
            'items': ['Item A', 'Item B', 'Item C']
        }
        
        return {
            "prepared_data": prepared_data,
            "data_count": len(prepared_data['items'])
        }
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "DemoDataPreparer",
            "description": "Prepares demo data",
            "inputs": {"user_name": "str", "topic": "str"},
            "outputs": {"prepared_data": "Dict", "data_count": "int"}
        }


class DemoDataProcessor(BaseTaskModule):
    """デモ用データ処理タスク（リトライのテスト用）"""
    
    # クラス変数でリトライ回数を管理
    _attempt_count = 0
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """データを処理（最初は失敗する可能性あり）"""
        data = inputs.get('data', {})
        count = inputs.get('count', 0)
        
        DemoDataProcessor._attempt_count += 1
        
        print(f"⚙️ Processing data (attempt {DemoDataProcessor._attempt_count})...")
        print(f"   Items to process: {count}")
        
        # 最初の試行では50%の確率で失敗（リトライのデモ）
        if DemoDataProcessor._attempt_count == 1 and random.random() < 0.5:
            print("⚠️ Simulated processing failure!")
            raise RuntimeError("Simulated API error (will retry)")
        
        # 処理のシミュレーション
        time.sleep(0.5)
        
        processed_result = {
            'original_topic': data.get('topic', ''),
            'processed_items': [f"Processed {item}" for item in data.get('items', [])],
            'status': 'completed',
            'attempts': DemoDataProcessor._attempt_count
        }
        
        processing_time = 0.5
        
        print(f"✅ Processing completed after {DemoDataProcessor._attempt_count} attempt(s)")
        
        return {
            "processed_result": processed_result,
            "processing_time": processing_time
        }
    
    @classmethod
    def reset_attempt_count(cls):
        """テスト用: リトライカウンターをリセット"""
        cls._attempt_count = 0
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "DemoDataProcessor",
            "description": "Processes data with retry support",
            "inputs": {"data": "Dict", "count": "int"},
            "outputs": {"processed_result": "Dict", "processing_time": "float"}
        }


class DemoOutputFormatter(BaseTaskModule):
    """デモ用出力フォーマットタスク"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """結果をフォーマット"""
        result = inputs.get('result', {})
        proc_time = inputs.get('time', 0)
        original_topic = inputs.get('original_topic', '')
        
        print(f"📊 Formatting output...")
        
        # 結果のフォーマット
        final_output = f"""
========================================
🎉 Workflow Execution Result
========================================
Topic: {original_topic}
Status: {result.get('status', 'unknown')}
Processing Time: {proc_time:.2f}s
Attempts: {result.get('attempts', 1)}

Processed Items:
{chr(10).join(f"  • {item}" for item in result.get('processed_items', []))}
========================================
"""
        
        print(final_output)
        
        return {
            "final_output": final_output.strip()
        }
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "DemoOutputFormatter",
            "description": "Formats the final output",
            "inputs": {"result": "Dict", "time": "float", "original_topic": "str"},
            "outputs": {"final_output": "str"}
        }


class DemoErrorHandler(BaseTaskModule):
    """デモ用エラーハンドラー"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """エラーを処理"""
        error_msg = inputs.get('error_message', 'Unknown error')
        
        print(f"❌ Error occurred: {error_msg}")
        print(f"🔧 Error has been logged and handled gracefully.")
        
        return {
            "error_handled": True
        }
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "DemoErrorHandler",
            "description": "Handles workflow errors",
            "inputs": {"error_message": "str"},
            "outputs": {"error_handled": "bool"}
        }


# タスクモジュールの登録
def register_demo_tasks():
    """デモタスクをサービスレジストリに登録"""
    from src.services.framework.service_registry import service_registry
    
    service_registry.register_module("DemoDataPreparer", DemoDataPreparer)
    service_registry.register_module("DemoDataProcessor", DemoDataProcessor)
    service_registry.register_module("DemoOutputFormatter", DemoOutputFormatter)
    service_registry.register_module("DemoErrorHandler", DemoErrorHandler)
    
    print("✅ Demo tasks registered successfully!")


if __name__ == '__main__':
    # デモタスクのテスト
    print("Testing demo tasks...")
    
    # Data Preparer
    preparer = DemoDataPreparer()
    prep_result = preparer.execute({'user_name': 'Alice', 'topic': 'AI Workflows'})
    print(f"Preparer result: {prep_result}")
    
    # Data Processor
    DemoDataProcessor.reset_attempt_count()
    processor = DemoDataProcessor()
    try:
        proc_result = processor.execute({
            'data': prep_result['prepared_data'],
            'count': prep_result['data_count']
        })
        print(f"Processor result: {proc_result}")
    except RuntimeError as e:
        print(f"Expected retry error: {e}")
    
    print("\n✅ Demo tasks test completed!")
