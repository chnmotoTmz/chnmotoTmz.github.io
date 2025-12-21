#!/usr/bin/env python3
import sys
from pathlib import Path
import json

# Ensure repository root is on PYTHONPATH for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.services.tasks.article_strategy_planner_task import ArticleStrategyPlannerTask


class DummyLLM:
    def __init__(self, response_text: str):
        self._resp = response_text

    def generate_text(self, prompt: str, **kwargs):
        # Return JSON text as the LLM would
        return self._resp


def test_generate_strategy_parses_json():
    dummy_response = json.dumps({
        "structure": [{"title": "Intro"}],
        "affiliate_strategy": {"links": []},
        "thumbnail_concept": "Test Thumb",
        "target_keywords": ["alpha"]
    }, ensure_ascii=False)

    task = ArticleStrategyPlannerTask({})
    # Inject dummy LLM
    task.llm_service = DummyLLM(dummy_response)

    strategy = task._generate_strategy({"concept": "x"}, ["text1", "text2"], [], [], {})

    assert isinstance(strategy, dict)
    assert strategy.get("structure") and strategy.get("thumbnail_concept") == "Test Thumb"


def test_generate_strategy_handles_non_json():
    # Non-JSON response should gracefully return an empty dict from parse
    task = ArticleStrategyPlannerTask({})
    task.llm_service = DummyLLM("This is not JSON")

    strategy = task._generate_strategy({"concept": "x"}, ["text1"], [], [], {})
    assert isinstance(strategy, dict)

