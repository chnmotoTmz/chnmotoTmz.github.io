import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services.framework.task_runner import TaskRunner


def test_workflow_skips_publishing_when_draft_skipped(tmp_path):
    # Minimal workflow: save_draft -> post_to_hatena -> end
    workflow = {
        "workflow_name": "Integration: Draft Skip",
        "description": "Ensure that when draft save is skipped, Hatena publish is skipped gracefully.",
        "steps": [
            {
                "id": "save_draft",
                "module": "DraftPersister",
                "inputs": {
                    "blog": "${blog_data}",
                    "user": "${user_data}",
                    "title": "${final_title:Test Title}",
                    "content": "${final_content:Test body}",
                    "message_ids": "${original_message_ids}"
                },
                "outputs": {"post_id": "draft_post_id"},
                "on_success": "post_to_hatena",
                "on_failure": "handle_error"
            },
            {
                "id": "post_to_hatena",
                "module": "HatenaPublisher",
                "inputs": {
                    "blog": "${blog_data}",
                    "post_id": "${draft_post_id}",
                    "article_concept": "${article_concept}"
                },
                "outputs": {"hatena_entry": "hatena_entry"},
                "on_success": "end",
                "on_failure": "handle_error"
            }
        ],
        "variables": {
            "blog_data": None,
            "user_data": None,
            "original_message_ids": None,
            "draft_post_id": None,
            "hatena_entry": None
        }
    }

    wf_file = tmp_path / "integration_draft_skip.json"
    wf_file.write_text(json.dumps(workflow), encoding="utf-8")

    runner = TaskRunner(str(wf_file), enable_visualization=False)

    context = runner.run(initial_inputs={})

    # DraftPersister should set draft_post_id to None explicitly
    assert 'draft_post_id' in context
    assert context['draft_post_id'] is None

    # HatenaPublisher should have been invoked (but skipped) and produced hatena_entry = None
    assert 'hatena_entry' in context
    assert context['hatena_entry'] is None
