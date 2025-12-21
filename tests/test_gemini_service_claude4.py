import pytest
import os
from types import SimpleNamespace

# Ensure imports work in test runner

def test_claude4_preferred_for_image_analysis(monkeypatch):
    called = {}

    class DummyClaude4:
        def __init__(self):
            self.model = 'dummy-4'
        def generate_content(self, prompt, max_tokens=None, temperature=None):
            called['used'] = 'claude4'
            return 'image description from claude4'

    class DummyClaude:
        def __init__(self):
            pass
        def generate_text(self, prompt, max_tokens=None, temperature=None):
            called['used'] = 'claude'
            return 'legacy description'

    monkeypatch.setattr('src.services.gemini_service.Claude4Service', DummyClaude4)
    monkeypatch.setattr('src.services.gemini_service.ClaudeService', DummyClaude)

    from src.services.gemini_service import GeminiService
    svc = GeminiService()
    res = svc.analyze_image_from_path('/tmp/x.png', prompt='describe')
    assert res == 'image description from claude4'
    assert called['used'] == 'claude4'


def test_claude4_failure_falls_back_to_legacy(monkeypatch):
    called = {}

    class DummyClaude4:
        def __init__(self):
            self.model = 'dummy-4'
        def generate_content(self, prompt, max_tokens=None, temperature=None):
            raise RuntimeError('fail')

    class DummyClaude:
        def __init__(self):
            pass
        def generate_text(self, prompt, max_tokens=None, temperature=None):
            called['used'] = 'claude'
            return 'legacy description'

    monkeypatch.setattr('src.services.gemini_service.Claude4Service', DummyClaude4)
    monkeypatch.setattr('src.services.gemini_service.ClaudeService', DummyClaude)

    from src.services.gemini_service import GeminiService
    svc = GeminiService()
    res = svc.analyze_image_from_path('/tmp/x.png', prompt='describe')
    assert res == 'legacy description'
    assert called['used'] == 'claude'
