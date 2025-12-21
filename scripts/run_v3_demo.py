import os
import sys
from pathlib import Path
# ensure project root is on sys.path for script execution
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.services.thumbnail_generator_service import ThumbnailGeneratorService
from src.services.framework.task_runner import TaskRunner

# Load environment variables
import env_loader
env_loader.load()

runner = TaskRunner('src/workflows/article_generation_v3.json', enable_visualization=True)
ctx = runner.run({'title':'Demo: Image flow','content':'Body for the minimal thumbnail flow','line_user_id':'testuser','channel_id':'testchan'})
print('\nDemo completed. Context hatena_entry:')
print(ctx.get('hatena_entry'))

