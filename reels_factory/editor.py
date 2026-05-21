from __future__ import annotations

import itertools
import subprocess
import time
from pathlib import Path

from .config import ROOT_DIR
from .subtitles import render_caption_images
from .tts import WordTiming
from .utils import ensure_dir, ffprobe_duration, log


def _fit_duration(paths: list[Path], duration: float) -> list[Path]:
    if not paths:
        raise ValueError("visual_paths is empty")
    selected: list[Path] = []
    total = 0.0
    for path in itertools.cycle(paths):
        selected.append(path)
        try:
            total += ffprobe_duration(path)
        except Exception:
            total += 4.0
        if total >= duration:
            return selected
    return selected


def _concat_visuals(paths: list[Path], target_duration: float, work_dir: Path) -> Path:
    list_file = work_dir / "visuals.txt"
    list_file.write_text("".join(f"file '{path.resolve()}'\n" for path in paths), encoding="utf-8")
    output = work_dir / "base.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-t",
            f"{target_duration:.3f}",
            "-vf",
            "fps=30,format=yuv420p",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output


def _normalize_audio(input_path: Path, target_duration: float, work_dir: Path) -> Path:
    output = work_dir / "voice_final.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-f",
            "lavfi",
            "-t",
            f"{target_duration:.3f}",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex",
            f"[0:a][1:a]amix=inputs=2:duration=longest,atrim=0:{target_duration:.3f},asetpts=PTS-STARTPTS[a]",
            "-map",
            "[a]",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output


def _mix_music(voice_path: Path, music_path: Path, target_duration: float, work_dir: Path) -> Path:
    output = work_dir / "mixed_audio.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path),
            "-filter_complex",
            f"[1:a]volume=0.126,atrim=0:{target_duration:.3f}[m];[0:a][m]amix=inputs=2:duration=first[a]",
            "-map",
            "[a]",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output


def _overlay_subtitles(base_video: Path, audio_path: Path, word_timings: list[WordTiming], output: Path, target_duration: float) -> None:
    captions = render_caption_images(word_timings, (1080, 1920))
    cmd = ["ffmpeg", "-y", "-i", str(base_video), "-i", str(audio_path)]
    for path, _, _ in captions:
        cmd.extend(["-i", str(path)])

    if captions:
        current = "[0:v]"
        chains: list[str] = []
        for index, (_, start, end) in enumerate(captions):
            out = f"[v{index}]"
            safe_start = max(0.0, start)
            safe_end = min(target_duration, max(end, start + 0.12))
            chains.append(
                f"{current}[{index + 2}:v]overlay=x=(main_w-overlay_w)/2:y=1190:"
                f"enable='between(t,{safe_start:.3f},{safe_end:.3f})'{out}"
            )
            current = out
        filter_complex = ";".join(chains)
        map_video = current
        cmd.extend(["-filter_complex", filter_complex, "-map", map_video])
    else:
        cmd.extend(["-map", "0:v"])

    cmd.extend(
        [
            "-map",
            "1:a",
            "-t",
            f"{target_duration:.3f}",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True)


def compose(audio_path: Path, visual_paths: list[Path], word_timings: list[WordTiming], music_path: Path | None = None) -> Path:
    work_dir = ensure_dir(Path("/tmp/reels_edit"))
    out_dir = ensure_dir(ROOT_DIR / "out")
    raw_audio_duration = ffprobe_duration(audio_path)
    target_duration = min(45.0, max(30.0, raw_audio_duration))
    final_audio = _normalize_audio(audio_path, target_duration, work_dir)
    if music_path and music_path.exists():
        try:
            final_audio = _mix_music(final_audio, music_path, target_duration, work_dir)
        except Exception as exc:
            log.warning("Music mix failed, continuing without music: %s", exc)

    selected = _fit_duration(visual_paths, target_duration)
    base_video = _concat_visuals(selected, target_duration, work_dir)
    output = out_dir / f"reel_{int(time.time())}.mp4"
    _overlay_subtitles(base_video, final_audio, word_timings, output, target_duration)
    log.info("Rendered %s", output)
    return output
