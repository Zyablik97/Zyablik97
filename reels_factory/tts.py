from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .utils import ensure_dir, ffprobe_duration, log


@dataclass(frozen=True)
class WordTiming:
    word: str
    start: float
    end: float


@dataclass(frozen=True)
class TTSResult:
    audio_path: Path
    word_timings: list[WordTiming]
    duration_sec: float


def _clean_word(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def _edge_stream(text: str, voice: str, output_dir: Path) -> TTSResult:
    import edge_tts

    audio_path = output_dir / "voice.mp3"
    vtt_path = output_dir / "voice.vtt"
    communicate = edge_tts.Communicate(text, voice=voice, rate="+5%", boundary="WordBoundary")
    timings: list[WordTiming] = []
    with audio_path.open("wb") as audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = float(chunk["offset"]) / 10_000_000
                end = start + float(chunk["duration"]) / 10_000_000
                word = _clean_word(str(chunk.get("text", "")))
                if word:
                    timings.append(WordTiming(word=word, start=start, end=end))
    _write_vtt(vtt_path, timings)
    duration = max(ffprobe_duration(audio_path), timings[-1].end if timings else 0.0)
    return TTSResult(audio_path=audio_path, word_timings=timings, duration_sec=duration)


def _write_vtt(path: Path, timings: list[WordTiming]) -> None:
    def fmt(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, rest = divmod(ms, 3_600_000)
        m, rest = divmod(rest, 60_000)
        s, ms = divmod(rest, 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    lines = ["WEBVTT", ""]
    for item in timings:
        lines.extend([f"{fmt(item.start)} --> {fmt(item.end)}", item.word, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _fallback_audio(text: str, output_dir: Path) -> TTSResult:
    words = re.findall(r"[\wА-Яа-яЁё-]+", text, flags=re.UNICODE)
    duration = min(45.0, max(30.0, len(words) * 0.42))
    audio_path = output_dir / "voice.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            f"{duration:.3f}",
            "-c:a",
            "libmp3lame",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
    )
    per_word = duration / max(1, len(words))
    timings = [WordTiming(word=w, start=i * per_word, end=(i + 1) * per_word) for i, w in enumerate(words)]
    _write_vtt(output_dir / "voice.vtt", timings)
    return TTSResult(audio_path=audio_path, word_timings=timings, duration_sec=duration)


def synthesize(text: str, voice: str = "ru-RU-DmitryNeural", output_dir: Path | None = None) -> TTSResult:
    output_dir = ensure_dir(output_dir or Path("/tmp/reels_tts"))
    try:
        return asyncio.run(_edge_stream(text, voice, output_dir))
    except Exception as exc:
        log.warning("Edge-TTS failed, using silent fallback audio for testability: %s", exc)
        return _fallback_audio(text, output_dir)
