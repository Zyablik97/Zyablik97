from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

SUBTOPICS = [
    "космос",
    "история",
    "природа",
    "наука",
    "тело человека",
    "технологии",
    "животные",
    "океан",
    "мозг",
    "физика",
]


@dataclass(frozen=True)
class Config:
    niche: str
    voice: str
    repo: str
    pexels_api_key: str | None
    gemini_api_key: str | None
    groq_api_key: str | None
    github_token: str | None
    ig_user_id: str | None
    ig_access_token: str | None
    publish: bool
    use_mock_llm: bool
    use_music: bool
    music_path: Path | None
    width: int = 1080
    height: int = 1920
    fps: int = 30
    min_duration: int = 30
    max_duration: int = 45


def _get_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT_DIR / ".env")
    except Exception:
        pass

    music_path = os.getenv("MUSIC_PATH")
    return Config(
        niche=os.getenv("NICHE", "удивительные факты"),
        voice=os.getenv("TTS_VOICE", "ru-RU-DmitryNeural"),
        repo=os.getenv("GITHUB_REPOSITORY", ""),
        pexels_api_key=os.getenv("PEXELS_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        github_token=os.getenv("GITHUB_TOKEN"),
        ig_user_id=os.getenv("IG_USER_ID"),
        ig_access_token=os.getenv("IG_ACCESS_TOKEN"),
        publish=_get_bool("PUBLISH"),
        use_mock_llm=_get_bool("USE_MOCK_LLM"),
        use_music=_get_bool("USE_MUSIC", "1"),
        music_path=Path(music_path).expanduser() if music_path else None,
    )
