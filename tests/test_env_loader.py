import os
from pathlib import Path
import tempfile
import sys
# ensure repo root is on sys.path for imports in test environment
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_loader import _read_dotenv, load


def test_read_dotenv_parses_key_value(tmp_path):
    f = tmp_path / ".env.develop"
    f.write_text("IMGUR_ACCESS_TOKEN=mytoken\n# comment\nANOTHER=1")
    data = _read_dotenv(f)
    assert data.get('IMGUR_ACCESS_TOKEN') == 'mytoken'
    assert data.get('ANOTHER') == '1'


def test_load_prefers_env_develop(tmp_path, monkeypatch):
    # Create a fake repo root by placing a .env.develop in cwd (env_loader uses its own file path)
    # We'll monkeypatch Path.glob to simulate files in repo root
    repo_root = Path(__file__).resolve().parents[1]

    # Create a temporary .env.develop in the real repo root for this test
    dev_file = repo_root / '.env.develop'
    try:
        dev_file.write_text('IMGUR_ACCESS_TOKEN=devtoken')
        # Ensure env var is unset
        monkeypatch.delenv('IMGUR_ACCESS_TOKEN', raising=False)
        load()
        assert os.getenv('IMGUR_ACCESS_TOKEN') == 'devtoken'
    finally:
        try:
            dev_file.unlink()
        except Exception:
            pass
