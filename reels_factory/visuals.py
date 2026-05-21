from __future__ import annotations

import math
import os
import random
import subprocess
from pathlib import Path
from urllib.parse import quote_plus

import requests
from PIL import Image, ImageDraw, ImageFilter

from .config import ROOT_DIR
from .utils import cleanup_dir, ensure_dir, log, retry

VISUAL_DIR = Path("/tmp/reels_visuals")
PREP_DIR = Path("/tmp/reels_visuals_prepared")


@retry(attempts=3, delay=1)
def _download(url: str, path: Path, headers: dict[str, str] | None = None) -> Path:
    with requests.get(url, headers=headers, timeout=45, stream=True) as response:
        response.raise_for_status()
        with path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    file.write(chunk)
    return path


def _pexels_videos(keyword: str, target_dir: Path, start_index: int) -> list[Path]:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return []
    url = "https://api.pexels.com/videos/search"
    params = {"query": keyword, "per_page": 5, "orientation": "portrait", "size": "medium"}
    response = requests.get(url, params=params, headers={"Authorization": key}, timeout=30)
    response.raise_for_status()
    paths: list[Path] = []
    for video in response.json().get("videos", []):
        if float(video.get("duration") or 0) < 3:
            continue
        files = sorted(video.get("video_files", []), key=lambda f: abs((f.get("width") or 1080) - 1080))
        if not files:
            continue
        link = files[0].get("link")
        if not link:
            continue
        path = target_dir / f"pexels_{start_index + len(paths)}.mp4"
        try:
            paths.append(_download(link, path))
        except Exception as exc:
            log.warning("Pexels video download failed: %s", exc)
        if len(paths) >= 2:
            break
    return paths


def _pollinations_image(keyword: str, target_dir: Path, index: int) -> Path | None:
    prompt = quote_plus(f"vertical cinematic realistic stock footage frame about {keyword}, amazing fact, no text")
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true&model=flux&seed={random.randint(1, 999999)}"
    path = target_dir / f"pollinations_{index}.jpg"
    try:
        response = requests.get(url, timeout=12)
        response.raise_for_status()
        path.write_bytes(response.content)
        return path
    except Exception as exc:
        log.warning("Pollinations fallback failed: %s", exc)
        return None


def _local_image(keyword: str, target_dir: Path, index: int) -> Path:
    path = target_dir / f"local_{index}.jpg"
    img = Image.new("RGB", (1080, 1920), (10, 16, 30))
    top = Image.new("RGB", (1080, 1920), (25 + index * 17 % 100, 25, 80 + index * 23 % 140))
    mask = Image.linear_gradient("L").resize((1080, 1920))
    img = Image.composite(top, img, mask).filter(ImageFilter.GaussianBlur(0.3))
    draw = ImageDraw.Draw(img)
    for _ in range(180):
        x = random.randint(0, 1079)
        y = random.randint(0, 1919)
        r = random.randint(1, 4)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255))
    img.save(path, quality=92)
    return path


def _prepare_visual(path: Path, index: int, clip_duration: float) -> Path:
    ensure_dir(PREP_DIR)
    output = PREP_DIR / f"clip_{index:03d}.mp4"
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1,fps=30,format=yuv420p"
    )
    image_vf = (
        "scale=1188:2112:force_original_aspect_ratio=increase,"
        f"zoompan=z='min(zoom+0.0015,1.05)':d={max(1, int(clip_duration * 30))}:s=1080x1920:fps=30,"
        "setsar=1,format=yuv420p"
    )
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(path),
            "-t",
            f"{clip_duration:.3f}",
            "-vf",
            image_vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(output),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(path),
            "-t",
            f"{clip_duration:.3f}",
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(output),
        ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output


def fetch_visuals(keywords: list[str], duration_sec: float) -> list[Path]:
    cleanup_dir(VISUAL_DIR)
    cleanup_dir(PREP_DIR)
    raw_paths: list[Path] = []
    target_count = max(8, math.ceil(duration_sec / 4.5))
    keywords = keywords or ["science", "nature", "space"]

    if os.getenv("USE_LOCAL_VISUALS", "0") != "1":
        for keyword in keywords:
            if len(raw_paths) >= target_count:
                break
            try:
                raw_paths.extend(_pexels_videos(keyword, VISUAL_DIR, len(raw_paths)))
            except Exception as exc:
                log.warning("Pexels search failed for %s: %s", keyword, exc)

    index = 0
    pollinations_failed = False
    while len(raw_paths) < target_count:
        keyword = keywords[index % len(keywords)]
        use_local = os.getenv("USE_LOCAL_VISUALS", "0") == "1" or pollinations_failed
        image = None if use_local else _pollinations_image(keyword, VISUAL_DIR, index)
        if image is None and not use_local:
            pollinations_failed = True
        raw_paths.append(image or _local_image(keyword, VISUAL_DIR, index))
        index += 1

    clip_duration = max(3.0, min(5.0, duration_sec / len(raw_paths)))
    prepared = [_prepare_visual(path, i, clip_duration) for i, path in enumerate(raw_paths)]
    log.info("Prepared %s visuals covering %.1fs", len(prepared), len(prepared) * clip_duration)
    return prepared
