"""
RAG自動更新機能の全テスト実行スクリプト

このスクリプトは、RAG自動更新機能に関連する全てのテストを実行し、
レポートを生成します。
"""

import sys
import os
import pytest
from pathlib import Path

# プロジェクトのルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """全てのRAG関連テストを実行"""
    
    print("=" * 70)
    print("🧪 RAG自動更新機能 - テストスイート実行開始")
    print("=" * 70)
    print()
    
    # テストファイルのリスト
    test_files = [
        "tests/services/test_blog_rag_service.py",
        "tests/integration/test_rag_api.py",
        "tests/test_rag_auto_update_e2e.py",
    ]
    
    # 各テストファイルが存在するかチェック
    missing_files = []
    for test_file in test_files:
        if not (project_root / test_file).exists():
            missing_files.append(test_file)
    
    if missing_files:
        print("⚠️  以下のテストファイルが見つかりません:")
        for file in missing_files:
            print(f"  - {file}")
        print()
    
    # 実行するテストファイルを絞り込み
    existing_test_files = [f for f in test_files if (project_root / f).exists()]
    
    if not existing_test_files:
        print("❌ 実行可能なテストファイルがありません。")
        return 1
    
    print("📋 実行するテスト:")
    for test_file in existing_test_files:
        print(f"  ✓ {test_file}")
    print()
    
    # pytestのオプション
    pytest_args = [
        "-v",  # 詳細出力
        "--tb=short",  # トレースバックを短く
        "--color=yes",  # カラー出力
        "-ra",  # 全ての結果のサマリーを表示
    ] + existing_test_files
    
    # 環境変数を設定（テスト環境）
    os.environ['TESTING'] = 'true'
    os.environ['ENABLE_AUTO_RAG_UPDATE'] = 'true'
    
    # テスト実行
    print("=" * 70)
    print("🚀 テスト実行中...")
    print("=" * 70)
    print()
    
    result = pytest.main(pytest_args)
    
    print()
    print("=" * 70)
    if result == 0:
        print("✅ 全てのテストが成功しました！")
    else:
        print("❌ 一部のテストが失敗しました。")
    print("=" * 70)
    
    return result


def run_unit_tests_only():
    """単体テストのみを実行"""
    print("🧪 単体テストのみを実行...")
    
    pytest_args = [
        "-v",
        "tests/services/test_blog_rag_service.py",
    ]
    
    return pytest.main(pytest_args)


def run_integration_tests_only():
    """統合テストのみを実行"""
    print("🧪 統合テストのみを実行...")
    
    pytest_args = [
        "-v",
        "tests/integration/test_rag_api.py",
    ]
    
    return pytest.main(pytest_args)


def run_e2e_tests_only():
    """E2Eテストのみを実行"""
    print("🧪 E2Eテストのみを実行...")
    
    pytest_args = [
        "-v",
        "tests/test_rag_auto_update_e2e.py",
    ]
    
    return pytest.main(pytest_args)


def print_usage():
    """使用方法を表示"""
    print("使用方法:")
    print("  python run_rag_tests.py [option]")
    print()
    print("オプション:")
    print("  (なし)     - 全てのテストを実行")
    print("  --unit     - 単体テストのみ実行")
    print("  --int      - 統合テストのみ実行")
    print("  --e2e      - E2Eテストのみ実行")
    print("  --help     - このヘルプを表示")


if __name__ == "__main__":
    # コマンドライン引数の処理
    if len(sys.argv) > 1:
        option = sys.argv[1].lower()
        
        if option in ['--help', '-h']:
            print_usage()
            sys.exit(0)
        elif option == '--unit':
            sys.exit(run_unit_tests_only())
        elif option == '--int':
            sys.exit(run_integration_tests_only())
        elif option == '--e2e':
            sys.exit(run_e2e_tests_only())
        else:
            print(f"❌ 不明なオプション: {option}")
            print()
            print_usage()
            sys.exit(1)
    else:
        # 全テストを実行
        sys.exit(run_all_tests())
