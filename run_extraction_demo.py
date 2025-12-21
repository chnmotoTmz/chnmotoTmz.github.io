import os
import sys
import logging
import yaml

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath("."))

from src.framework.task_runner import TaskRunner

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s')

def main():
    # ワークフローファイルのパス
    workflow_path = "src/workflows/paragraph_extraction.json"
    
    # ブログ設定の読み込み
    with open("blogs.yml", "r", encoding="utf-8") as f:
        blogs_config = yaml.safe_load(f)
    
    # ターゲットブログ
    blog_key = "it_engineer_philosophy" 
    blog_info = blogs_config['blogs'][blog_key]
    
    # 入力パラメータ
    initial_input = {
        "blog": blog_info,
        "search_keywords": ["Python", "AI", "エンジニア"],
        "max_articles": 5,
        "output_file": "extracted_paragraphs.md"
    }
    
    # 実行
    runner = TaskRunner(workflow_path)
    
    print(f"--- 実行開始: {blog_info['blog_name']} ---")
    try:
        runner.run(initial_input)
        print("--- 実行完了 ---")
    except Exception as e:
        print(f"--- エラー発生: {e} ---")

if __name__ == "__main__":
    main()
