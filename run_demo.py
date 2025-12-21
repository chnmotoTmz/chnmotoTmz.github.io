"""
Demo Workflow Runner - ワークフローエンジンのデモ実行スクリプト
このスクリプトを実行すると、ワークフローエンジンの動作を確認できます。
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.framework.task_runner import TaskRunner
from src.services.framework.workflow_visualizer import WorkflowVisualizer
from demo_tasks import register_demo_tasks, DemoDataProcessor


def main():
    """デモワークフローを実行"""
    
    print("="*70)
    print("🚀 Workflow Engine Demo")
    print("="*70)
    print()
    
    # デモタスクを登録
    print("📦 Registering demo tasks...")
    register_demo_tasks()
    print()
    
    # リトライカウンターをリセット
    DemoDataProcessor.reset_attempt_count()
    
    # ワークフロー定義のパス
    workflow_path = 'demo_workflow.yaml'
    
    # 実行前の可視化
    print("="*70)
    print("📊 Workflow Visualization (Before Execution)")
    print("="*70)
    WorkflowVisualizer.print_to_console(workflow_path)
    print()
    
    # ワークフローを実行
    print("="*70)
    print("🚀 Starting Workflow Execution")
    print("="*70)
    print()
    
    runner = TaskRunner(workflow_path, enable_visualization=False)
    
    # 初期入力
    initial_inputs = {
        'user_name': 'Alice',
        'topic': 'Workflow Automation with Python'
    }
    
    print(f"📥 Initial Inputs:")
    print(f"   User: {initial_inputs['user_name']}")
    print(f"   Topic: {initial_inputs['topic']}")
    print()
    
    # 実行
    result = runner.run(initial_inputs=initial_inputs)
    
    print()
    print("="*70)
    print("📋 Execution Summary")
    print("="*70)
    print()
    
    # 結果サマリー
    summary = WorkflowVisualizer.get_execution_summary(result)
    
    print(f"✅ Total Output Variables: {summary['total_variables']}")
    print(f"❌ Has Error: {summary['has_error']}")
    print(f"⏱️  Execution Time: {runner.execution_end_time - runner.execution_start_time:.2f}s")
    print()
    
    if summary['output_variables']:
        print(f"📦 Output Variables: {', '.join(summary['output_variables'][:5])}")
        if len(summary['output_variables']) > 5:
            print(f"   ... and {len(summary['output_variables']) - 5} more")
    print()
    
    # 実行後の可視化
    print("="*70)
    print("📊 Workflow Visualization (After Execution)")
    print("="*70)
    WorkflowVisualizer.print_to_console(workflow_path, execution_context=result)
    print()
    
    print("="*70)
    print("🎉 Demo Completed Successfully!")
    print("="*70)
    print()
    print("💡 Tips:")
    print("   - YAMLファイルを編集してワークフローをカスタマイズできます")
    print("   - 新しいタスクモジュールを追加して機能拡張できます")
    print("   - Mermaid図をコピーして https://mermaid.live/ で表示できます")
    print()
    
    return result


if __name__ == '__main__':
    try:
        result = main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
