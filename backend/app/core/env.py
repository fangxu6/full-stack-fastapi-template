import os
from pathlib import Path


def get_env_file() -> Path:
    configured_path = os.environ.get("APP_ENV_FILE")
    if configured_path:
        return Path(configured_path)
    return Path(__file__).resolve().parents[3] / ".env"
