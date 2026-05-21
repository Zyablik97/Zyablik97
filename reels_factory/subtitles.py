from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT_DIR
from .tts import WordTiming

VIDEO_SIZE = (1080, 1920)


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        ROOT_DIR / "assets" / "fonts" / "Inter-Black.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def _chunks(word_timings: Sequence[WordTiming]) -> list[tuple[str, float, float]]:
    chunks: list[tuple[str, float, float]] = []
    current: list[WordTiming] = []
    for item in word_timings:
        current.append(item)
        text = " ".join(w.word for w in current)
        hard_break = bool(re.search(r"[.!?…,:;]$", item.word))
        too_long = len(current) >= 2 or (current[-1].end - current[0].start) >= 1.0 or len(text) > 16
        if hard_break or too_long:
            chunks.append((text, current[0].start, current[-1].end))
            current = []
    if current:
        chunks.append((" ".join(w.word for w in current), current[0].start, current[-1].end))
    return chunks


def _caption_png(text: str, index: int, video_size: tuple[int, int]) -> Path:
    width, height = video_size
    image = Image.new("RGBA", (width, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    text = text.upper()
    stroke = 8
    font_size = 78
    while font_size >= 48:
        font = _font(font_size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=stroke, spacing=8, align="center")
        if bbox[2] - bbox[0] <= width - 80:
            break
        font_size -= 4
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (width - tw) / 2
    y = (300 - th) / 2 - 8
    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill="white",
        stroke_width=stroke,
        stroke_fill="black",
        spacing=8,
        align="center",
    )
    out_dir = Path("/tmp/reels_subtitles")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"caption_{index:04d}.png"
    image.save(path)
    return path


def render_caption_images(word_timings: Sequence[WordTiming], video_size: tuple[int, int] = VIDEO_SIZE) -> list[tuple[Path, float, float]]:
    return [(_caption_png(text, index, video_size), start, end) for index, (text, start, end) in enumerate(_chunks(word_timings))]


def build_caption_layer(word_timings: Sequence[WordTiming], video_size: tuple[int, int] = VIDEO_SIZE) -> list:
    from moviepy import ImageClip

    clips = []
    y = int(video_size[1] * 0.62)
    for png, start, end in render_caption_images(word_timings, video_size):
        duration = max(0.12, end - start)
        clip = ImageClip(str(png))
        if hasattr(clip, "with_start"):
            clip = clip.with_start(start).with_duration(duration).with_position(("center", y))
        else:
            clip = clip.set_start(start).set_duration(duration).set_position(("center", y))
        clips.append(clip)
    return clips
