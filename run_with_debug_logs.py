#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Logger Viewer
Real-time log output with DEBUG level
"""
import sys
import logging
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set all loggers to DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s',
    datefmt='%H:%M:%S',
    encoding='utf-8'
)

# Set specific loggers to DEBUG
for logger_name in [
    'src.services.gemini_service',
    'src.services.content_enhancer_service',
    'src.services.tasks.style_memory_builder_task',
    'src.services.tasks.rag_similar_articles_fetcher',
]:
    logging.getLogger(logger_name).setLevel(logging.DEBUG)

# Import and start the app
from src.app_factory import create_app
from env_loader import load as load_env

def main():
    """Start the Flask app with DEBUG logging"""
    print("\n" + "="*100)
    print("   Hatena Blog Suite - Logger Viewer (DEBUG Level)")
    print("="*100)
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Log Level: DEBUG")
    print(f"   Working Dir: {Path.cwd()}")
    print("="*100 + "\n")
    
    # Load environment
    load_env()
    
    # Create Flask app
    app = create_app()
    
    # Get settings from environment
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Flask application on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Visit: http://{host}:{port}")
    
    # Run the app
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n" + "="*100)
        print("   Application stopped by user")
        print("="*100 + "\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
