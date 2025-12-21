#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Logger with File Output
Logs both to console and file for persistent viewing
"""
import sys
import logging
import io
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Create logs directory if it doesn't exist
logs_dir = project_root / 'logs'
logs_dir.mkdir(exist_ok=True)

# Create timestamped log file
log_filename = logs_dir / f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging with both console and file handlers
log_format = '%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s'
date_format = '%H:%M:%S'

# Console handler
# Wrap stdout in a UTF-8 text wrapper on Windows so emojis and other
# non-cp932 characters don't cause logging to fail with UnicodeEncodeError.
try:
    # Use a TextIOWrapper around stdout.buffer with utf-8 encoding and
    # replace errors to ensure logging never raises for characters the
    # terminal doesn't support.
    console_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    # Fallback: if we can't wrap stdout (e.g., in some test harnesses),
    # fall back to sys.stdout as-is.
    console_stream = sys.stdout

console_handler = logging.StreamHandler(console_stream)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

# File handler
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S'))

# Root logger configuration
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

# Set specific loggers to DEBUG
for logger_name in [
    'src.services.gemini_service',
    'src.services.content_enhancer_service',
    'src.services.tasks.style_memory_builder_task',
    'src.services.tasks.rag_similar_articles_fetcher',
    'src.services.workflow_processing_service',
]:
    logging.getLogger(logger_name).setLevel(logging.DEBUG)

# Import and start the app
from src.app_factory import create_app
from env_loader import load as load_env

def main():
    """Start the Flask app with DEBUG logging to console and file"""
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*100)
    print("   Hatena Blog Suite - Logger with File Output")
    print("="*100)
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Log Level: DEBUG (console + file)")
    print(f"   Log File: {log_filename}")
    print(f"   Working Dir: {Path.cwd()}")
    print("="*100 + "\n")
    
    logger.info("="*100)
    logger.info("Application startup with DEBUG logging")
    logger.info("="*100)
    
    # Load environment
    load_env()
    
    # Create Flask app
    app = create_app()
    
    # Get settings from environment
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
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
        logger.info("="*100)
        logger.info("Application stopped by user")
        logger.info("="*100)
        print("\n\n" + "="*100)
        print("   Application stopped")
        print(f"   Logs saved to: {log_filename}")
        print("="*100 + "\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
