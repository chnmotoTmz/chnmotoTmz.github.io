#!/usr/bin/env python3
import sys
from pathlib import Path
import json

# Ensure repository root is on PYTHONPATH for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services.gemini_service import GeminiService


def test_generate_adapter_parses_json(monkeypatch):
    svc = GeminiService()

    def fake_generate_text(prompt, **kwargs):
        return json.dumps({"ok": True, "a": 1}, ensure_ascii=False)

    monkeypatch.setattr(svc, "generate_text", fake_generate_text)

    res = svc.generate("prompt", context_text="CTX", web_context="WEB", video_context="VID", blog_name="B")
    assert isinstance(res, dict)
    assert res.get("ok") is True


def test_generate_adapter_returns_raw_when_not_json(monkeypatch):
    svc = GeminiService()

    def fake_generate_text(prompt, **kwargs):
        return "plain text response"

    monkeypatch.setattr(svc, "generate_text", fake_generate_text)

    res = svc.generate("prompt")
    assert isinstance(res, dict)
    assert res.get("raw") == "plain text response"
