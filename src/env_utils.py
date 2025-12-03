import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _normalize_env_value(value: str) -> str:
    if not value:
        return value
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_env() -> None:
    env_path = Path(".env")
    if load_dotenv:
        load_dotenv(env_path)
        return

    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _normalize_env_value(value.strip()))


def get_env_value(key: str, env_path: Path | None = None) -> str | None:
    value = os.getenv(key)
    if value:
        return _normalize_env_value(value)

    env_path = env_path or Path(".env")
    if not env_path.exists():
        return None

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        current_key, current_value = line.split("=", 1)
        if current_key.strip() == key:
            return _normalize_env_value(current_value.strip())

    return None
