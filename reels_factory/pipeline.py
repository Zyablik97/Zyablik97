from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .config import ROOT_DIR, load_config
from .editor import compose
from .llm import generate_script
from .publisher import build_caption, publish_reel
from .tts import synthesize
from .uploader import upload_to_github_release
from .utils import log, pick_random_file
from .visuals import fetch_visuals


def _pick_music(cfg) -> Path | None:
    if cfg.music_path:
        return cfg.music_path
    return pick_random_file(ROOT_DIR / "assets" / "music", ("*.mp3", "*.m4a", "*.wav", "*.aac"))


def main() -> Path | None:
    cfg = load_config()
    with tempfile.TemporaryDirectory(prefix="reels_factory_") as tmp:
        tmp_dir = Path(tmp)
        script = generate_script()
        log.info("Script topic: %s", script.topic)
        tts = synthesize(script.full_text, voice=cfg.voice, output_dir=tmp_dir / "tts")
        log.info("TTS duration: %.2fs, words: %s", tts.duration_sec, len(tts.word_timings))
        visuals = fetch_visuals(script.keywords, tts.duration_sec)
        music = _pick_music(cfg) if cfg.use_music else None
        video = compose(tts.audio_path, visuals, tts.word_timings, music)
        if cfg.publish:
            url = upload_to_github_release(video, cfg.repo, os.getenv("GITHUB_TOKEN", ""))
            result = publish_reel(url, build_caption(script), cfg.ig_user_id or "", cfg.ig_access_token or "")
            log.info("Published %s", result)
        else:
            log.info("Dry run, video at %s", video)
        return video


if __name__ == "__main__":
    main()
