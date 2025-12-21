import os
from pathlib import Path
from dotenv import load_dotenv

def load_env_for_llm_api_server():
    env_path = Path(__file__).parent.parent / ".env.production"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print(f"[WARN] .env.production not found at {env_path}")

# LLM APIサーバ起動時に呼び出す
load_env_for_llm_api_server()
