import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import logging
from src.services.tasks.article_reviewer_task import ArticleReviewer


def test_article_reviewer_handles_none_blog(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)

    # Patch _get_review_feedback to avoid external calls
    def fake_get_review_feedback(self, prompt):
        return "【結論】基準をクリア"

    monkeypatch.setattr(ArticleReviewer, '_get_review_feedback', fake_get_review_feedback)

    reviewer = ArticleReviewer(config={})

    inputs = {
        'title': 'Test Title',
        'content': 'This is the article content.',
        'blog': None  # Simulate upstream sending None
    }

    result = reviewer.execute(inputs)

    assert isinstance(result, dict)
    # Should not raise and should produce a review_feedback
    assert 'review_feedback' in result
    # Should log a warning about missing blog
    assert any('blog' in rec.getMessage() and 'None' in rec.getMessage() or 'empty blog' in rec.getMessage() for rec in caplog.records)
