#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point with DEBUG logging to file and console.
Run the Flask app or execute a specific workflow via CLI arguments.
"""
import sys
import logging
import os
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Create logs directory
logs_dir = project_root / 'logs'
logs_dir.mkdir(exist_ok=True)

# Create separate log files for different components
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
debug_log_file = logs_dir / f"debug_{log_timestamp}.log"
prompt_log_file = logs_dir / f"prompts_{log_timestamp}.log"

# Configure logging handlers
log_format = '%(asctime)s | %(levelname)-8s | %(name)-50s | %(message)s'

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)  # Show INFO and above on console
console_handler.setFormatter(logging.Formatter(log_format, datefmt='%H:%M:%S'))

# Full debug log file handler
debug_handler = logging.FileHandler(debug_log_file, encoding='utf-8')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S'))

# Prompt-only log file handler (filters for prompt markers)
class PromptFilter(logging.Filter):
    def filter(self, record):
        return '【' in record.getMessage()

prompt_handler = logging.FileHandler(prompt_log_file, encoding='utf-8')
prompt_handler.setLevel(logging.DEBUG)
prompt_handler.setFormatter(logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S'))
prompt_handler.addFilter(PromptFilter())

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
root_logger.addHandler(debug_handler)
root_logger.addHandler(prompt_handler)

# Set DEBUG level for key loggers
for logger_name in [
    'src.services.gemini_service',
    'src.services.content_enhancer_service',
    'src.services.tasks.style_memory_builder_task',
    'src.services.tasks.rag_similar_articles_fetcher',
    'src.services.unified_llm_service',
    'src.services.tasks.web_summary_fetcher_task',
    'src.services.thumbnail_generator_service', # Added for thumbnail debugging
]:
    logging.getLogger(logger_name).setLevel(logging.DEBUG)


# Register modules manually if needed
try:
    from src.services.framework.service_registry import service_registry
    from src.services.tasks.rag_similar_articles_fetcher import RagSimilarArticlesFetcher
    service_registry.register_module("RagSimilarArticlesFetcher", RagSimilarArticlesFetcher)
except Exception as e:
    print(f"[ERROR] RagSimilarArticlesFetcher registration failed: {e}")

# Import dependencies
from env_loader import load as load_env
from src.app_factory import create_app

def run_workflow(workflow_name: str, topic: str):
    """Executes a specific workflow by name/path."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting workflow execution mode: {workflow_name}")
    
    # Initialize Flask app context for DB access
    app = create_app()
    with app.app_context():
        from src.services.framework.task_runner import TaskRunner
        from src.database import User, Blog, db

        # Resolve workflow path
        workflow_path = workflow_name
        if not os.path.exists(workflow_path):
            # Try looking in standard directories
            candidates = [
                project_root / 'src' / 'workflows' / workflow_name,
                project_root / 'src' / 'workflows' / f"{workflow_name}.json",
                project_root / 'src' / 'apps' / workflow_name / 'workflow.json'
            ]
            for candidate in candidates:
                if candidate.exists():
                    workflow_path = str(candidate)
                    break

        if not os.path.exists(workflow_path):
            logger.error(f"Workflow file not found: {workflow_name}")
            return

        logger.info(f"Using workflow definition: {workflow_path}")

        # Prepare inputs
        # Fetch first available user and blog for simplicity
        user = User.query.first()
        blog = Blog.query.first()

        if not user or not blog:
            logger.error("No User or Blog found in database. Please initialize the database first.")
            return

        # Simple to_dict helper
        def to_dict(obj):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

        user_data = to_dict(user)
        blog_data = to_dict(blog)

        # Initial inputs for SimpleHatenaPipeline
        initial_inputs = {
            "user_id": user.id,
            "line_user_id": user.line_user_id,
            "message_ids": [], # Dummy
            "user": user_data,
            "blog": blog_data,
            "texts": [topic],
            "article_concept": {
                "theme": "General",
                "genre": "General",
                "keywords": ["Test", "Sample"]
            },
            "channel_id": "cli_execution"
        }

        try:
            task_runner = TaskRunner(workflow_path=workflow_path)
            result = task_runner.run(initial_inputs=initial_inputs)
            logger.info("Workflow execution completed successfully.")
            logger.info(f"Result keys: {list(result.keys())}")
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")

def main():
    """Main entry point."""
    load_env()
    load_dotenv('.env.production')
    from src.blog_config import BlogConfig
    BlogConfig.load_config()
    
    parser = argparse.ArgumentParser(description="Hatena Blog Suite Application")
    parser.add_argument('--flow', type=str, help='Name or path of the workflow to execute (e.g. simple_hatena_flow)')
    parser.add_argument('--topic', type=str, default='Python programming tips', help='Topic for the article generation (used with --flow)')

    args, unknown = parser.parse_known_args()

    # Setup basic logging
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*100)
    print("   Hatena Blog Suite - Application Server / CLI")
    print("="*100)
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Debug Log: {debug_log_file}")
    
    if args.flow:
        # Run in workflow mode
        run_workflow(args.flow, args.topic)
    else:
        # Run as server (original behavior)
        # Get Gemini API configuration for display
        gemini_keys = os.getenv('GEMINI_API_KEYS', '')
        gemini_key_count = len(gemini_keys.split(',')) if gemini_keys else 0
        gemini_single_key = os.getenv('GEMINI_API_KEY', 'Not set')

        print(f"   Prompts Log: {prompt_log_file}")
        print("-" * 100)
        print("   API Configuration:")
        print(f"   - Gemini API Keys: {gemini_key_count} keys configured")
        print(f"   - Primary Key: {gemini_single_key[:20]}..." if len(gemini_single_key) > 20 else f"   - Primary Key: {gemini_single_key}")
        print("="*100 + "\n")

        logger.info("Application starting in SERVER mode")

        app = create_app()
        port = int(os.getenv('PORT', 8000))
        host = os.getenv('HOST', '0.0.0.0')
        debug = os.getenv('FLASK_ENV', 'production') == 'development'

        try:
            app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=False
            )
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
            sys.exit(0)

if __name__ == '__main__':
    main()
