import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.framework.task_runner import TaskRunner
import pytest

WORKFLOW_PATH = "src/workflows/article_generation_v2.json"


def test_missing_context_variable_returns_none():
    runner = TaskRunner(workflow_path=WORKFLOW_PATH)
    runner.context = {}  # Ensure no variables present
    resolved = runner._resolve_inputs({'post_id': '${draft_post_id}'})
    assert 'post_id' in resolved
    assert resolved['post_id'] is None


def test_initial_input_missing_raises():
    runner = TaskRunner(workflow_path=WORKFLOW_PATH)
    runner.context = {'initial_input': {}}
    with pytest.raises(ValueError):
        runner._resolve_inputs({'post_id': '${initial_input.missing_key}'})
