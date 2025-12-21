"""
Workflow Visualizer - Mermaid フローチャート生成

ワークフロー定義と実行結果から Mermaid 記法の図を生成し、
視覚的にワークフローの構造とステータスを確認できるようにします。
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class WorkflowVisualizer:
    """ワークフローの可視化ユーティリティ"""

    @staticmethod
    def _load_workflow(workflow_path: str) -> Dict[str, Any]:
        """ワークフロー定義を読み込む（JSON/YAML両対応）"""
        path = Path(workflow_path)

        if path.suffix in ['.yaml', '.yml']:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)

    @staticmethod
    def _get_step_status(step_id: str, context: Optional[Dict[str, Any]]) -> str:
        """ステップの実行ステータスを判定"""
        if not context:
            return ""

        # エラーメッセージにステップIDが含まれているかチェック
        last_error = context.get('last_error_message', '')
        if step_id in last_error:
            return ":::error"

        # ステップの出力変数がコンテキストに存在するかチェック
        # （実行済みの場合、何らかの出力があるはず）
        step_output_keys = [k for k in context.keys() if not k.startswith('initial_input')]
        if step_output_keys:
            return ":::success"

        return ":::pending"

    @staticmethod
    def generate_mermaid(
        workflow_path: str,
        execution_context: Optional[Dict[str, Any]] = None,
        show_config: bool = False
    ) -> str:
        """
        ワークフロー定義から Mermaid フローチャートを生成。

        Args:
            workflow_path: ワークフロー定義ファイルのパス
            execution_context: 実行後のコンテキスト（オプション）
            show_config: ステップの設定情報を表示するか

        Returns:
            Mermaid 記法の文字列
        """
        workflow = WorkflowVisualizer._load_workflow(workflow_path)

        mermaid_lines = [
            "graph TD",
            f"    Start([\"🚀 {workflow.get('workflow_name', 'Workflow')}\"])"
        ]

        steps = workflow.get('steps', [])

        # 各ステップをノードとして追加
        for step in steps:
            step_id = step['id']
            module = step['module']

            # ステータスを判定 (今は構造のみに注力)
            status = "" # WorkflowVisualizer._get_step_status(step_id, execution_context)

            # ノードラベルと形状の構築
            label = module
            if module == 'ConditionalBranchTask':
                label = "🔀 Repost?"
                mermaid_lines.append(f"    {step_id}{{\"{label}\"}}{status}")
            else:
                if step_id == 'notify_user':
                    label = "LineNotifier (Success)"
                elif step_id == 'handle_error':
                    label = "LineNotifier (Error)"
                mermaid_lines.append(f"    {step_id}[\"{label}\"{status}]")

        # エッジ（矢印）を追加
        first_step = steps[0]['id'] if steps else None
        if first_step:
            mermaid_lines.append(f"    Start --> {first_step}")

        for step in steps:
            step_id = step['id']

            # ConditionalBranchTaskの特別な処理
            if step.get('module') == 'ConditionalBranchTask':
                on_true = step.get('on_true')
                on_false = step.get('on_false')
                if on_true:
                    mermaid_lines.append(f"    {step_id} -->|Yes: Repost| {on_true}")
                if on_false:
                    mermaid_lines.append(f"    {step_id} -->|No: New| {on_false}")
            else:
                # 成功時の次ステップ
                on_success = step.get('on_success')
                if on_success:
                    if on_success == 'end':
                        mermaid_lines.append(f"    {step_id} --> End([\"🎉 Complete\"])")
                    else:
                        mermaid_lines.append(f"    {step_id} -->|✅| {on_success}")

            # 失敗時の次ステップ (Conditional以外)
            if step.get('module') != 'ConditionalBranchTask':
                on_failure = step.get('on_failure')
                if on_failure and on_failure != 'end':
                     # 失敗矢印は handle_error に統一するなどのルールも可能
                    mermaid_lines.append(f"    {step_id} -.->|❌| {on_failure}")

        # スタイル定義
        mermaid_lines.extend([
            "",
            "    %% Style Definitions",
            "    classDef success fill:#90EE90,stroke:#006400,stroke-width:2px",
            "    classDef error fill:#FFB6C1,stroke:#8B0000,stroke-width:2px",
            "    classDef pending fill:#E0E0E0,stroke:#696969,stroke-width:1px",
            "    classDef decision fill:#FFD700,stroke:#FF8C00,stroke-width:2px",
            "",
            "    class branch_repost_or_new decision"
        ])

        return "\n".join(mermaid_lines)

    @staticmethod
    def print_to_console(
        workflow_path: str,
        execution_context: Optional[Dict[str, Any]] = None,
        title: str = "Workflow Visualization"
    ):
        """
        コンソールに Mermaid 図を出力（GitHub/VSCode で表示可能）

        Args:
            workflow_path: ワークフロー定義ファイルのパス
            execution_context: 実行後のコンテキスト
            title: 表示タイトル
        """
        mermaid = WorkflowVisualizer.generate_mermaid(workflow_path, execution_context)

        print("\n" + "="*70)
        print(f"📊 {title}")
        print("="*70)
        print("```mermaid")
        print(mermaid)
        print("```")
        print("="*70)
        print("💡 Tip: Copy the above Mermaid code and paste into:")
        print("   - https://mermaid.live/")
        print("   - VSCode (with Mermaid extension)")
        print("   - GitHub Markdown")
        print("="*70 + "\n")

    @staticmethod
    def save_to_file(
        workflow_path: str,
        output_path: str,
        execution_context: Optional[Dict[str, Any]] = None
    ):
        """
        Mermaid 図をファイルに保存

        Args:
            workflow_path: ワークフロー定義ファイルのパス
            output_path: 出力先ファイルパス（.md または .mmd）
            execution_context: 実行後のコンテキスト
        """
        mermaid = WorkflowVisualizer.generate_mermaid(workflow_path, execution_context)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Workflow Visualization\n\n")
            f.write("```mermaid\n")
            f.write(mermaid)
            f.write("\n```\n")

        print(f"✅ Mermaid diagram saved to: {output_path}")

    @staticmethod
    def get_execution_summary(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        実行結果のサマリーを取得

        Args:
            context: 実行後のコンテキスト

        Returns:
            サマリー情報（成功/失敗ステップ数など）
        """
        summary = {
            'total_variables': len([k for k in context.keys() if not k.startswith('initial_input')]),
            'has_error': 'last_error_message' in context,
            'error_message': context.get('last_error_message', None),
            'output_variables': [k for k in context.keys() if not k.startswith('initial_input') and k != 'last_error_message']
        }

        return summary


# CLI ツールとして使用可能
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python workflow_visualizer.py <workflow_path> [output_path]")
        sys.exit(1)

    workflow_path = sys.argv[1]

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
        WorkflowVisualizer.save_to_file(workflow_path, output_path)
    else:
        WorkflowVisualizer.print_to_console(workflow_path)
