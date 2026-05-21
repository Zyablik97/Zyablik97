from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from reels_factory.pipeline import main


def _probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_pipeline_dry_run_generates_valid_reel(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    monkeypatch.setenv("PUBLISH", "0")
    monkeypatch.setenv("USE_LOCAL_VISUALS", "1")
    monkeypatch.setenv("USE_MUSIC", "0")
    video = main()
    assert video is not None
    assert video.exists()
    assert video.stat().st_size > 100_000

    meta = _probe(video)
    streams = meta["streams"]
    video_stream = next(s for s in streams if s["codec_type"] == "video")
    audio_stream = next(s for s in streams if s["codec_type"] == "audio")
    duration = float(meta["format"]["duration"])

    assert video_stream["width"] == 1080
    assert video_stream["height"] == 1920
    assert video_stream["codec_name"] == "h264"
    assert audio_stream["codec_name"] == "aac"
    assert 25 <= duration <= 50
