from __future__ import annotations

import json
import logging
import random
import shutil
import subprocess
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

from .config import ROOT_DIR

T = TypeVar("T")


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("reels_factory")


log = setup_logging()


def retry(attempts: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            wait = delay
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    if attempt == attempts:
                        break
                    log.warning("%s failed (%s/%s): %s", func.__name__, attempt, attempts, exc)
                    time.sleep(wait)
                    wait *= backoff
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(result.stdout.strip())


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    log.debug("run: %s", " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def cleanup_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def pick_random_file(directory: Path, patterns: tuple[str, ...]) -> Path | None:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(directory.glob(pattern))
    return random.choice(files) if files else None


def asset_path(*parts: str) -> Path:
    return ROOT_DIR.joinpath(*parts)
