import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import logging
from src.services.tasks.draft_persister_task import DraftPersisterTask


def test_draft_persister_skips_missing_inputs(caplog):
    caplog.set_level(logging.WARNING)
    task = DraftPersisterTask(config={})

    # Missing blog/user/title/content/message_ids should be handled gracefully
    inputs = {}
    result = task.execute(inputs)

    assert result == {"post_id": None}
    assert any('missing required inputs' in rec.getMessage() for rec in caplog.records)
