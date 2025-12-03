import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

log = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _normalize_env_value(value: str) -> str:
    if not value:
        return value
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_env(env_path: str | Path = ".env") -> None:
    env_path = Path(env_path)
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


def read_bool(key: str, default: bool = False) -> bool:
    raw_value = get_env_value(key)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    log.warning("Expected boolean for %s but received '%s'; using %s", key, raw_value, default)
    return default


def read_int(key: str, default: int | None = None) -> int | None:
    raw_value = get_env_value(key)
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except ValueError:
        log.warning("Expected integer for %s but received '%s'; using %s", key, raw_value, default)
        return default


def read_float(key: str, default: float | None = None) -> float | None:
    raw_value = get_env_value(key)
    if raw_value is None or raw_value == "":
        return default
    try:
        return float(raw_value)
    except ValueError:
        log.warning("Expected float for %s but received '%s'; using %s", key, raw_value, default)
        return default


def read_path(key: str, default: str | Path) -> Path:
    raw_value = get_env_value(key)
    target = raw_value if raw_value not in (None, "") else default
    return Path(target).expanduser()
