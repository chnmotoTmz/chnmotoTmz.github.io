import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import logging
import pytest
from src.services.tasks.hatena_publisher_task import HatenaPublisherTask


def test_hatena_publisher_skips_none_post_id(caplog):
    caplog.set_level(logging.WARNING)
    task = HatenaPublisherTask(config={})

    inputs = {
        'blog': {'id': 1},
        'post_id': None
    }

    result = task.execute(inputs)
    assert result == {'hatena_entry': None}
    assert any('missing' in rec.getMessage() or 'skipping publish' in rec.getMessage() for rec in caplog.records)
