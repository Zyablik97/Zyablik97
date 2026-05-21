from __future__ import annotations

import time
from typing import Any

import requests

from .llm import ScriptData

GRAPH = "https://graph.facebook.com/v21.0"


def build_caption(script: ScriptData) -> str:
    first = script.hook or script.full_text.split(".")[0]
    tags = " ".join(f"#{kw.replace(' ', '')}" for kw in script.keywords[:5])
    return f"{first}\n\n{tags} #факты #интересное #удивительно #наука"


def publish_reel(video_url: str, caption: str, ig_user_id: str, access_token: str) -> dict[str, Any]:
    if not ig_user_id or not access_token:
        raise ValueError("IG_USER_ID and IG_ACCESS_TOKEN are required")
    create = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": access_token,
        },
        timeout=60,
    )
    create.raise_for_status()
    container_id = create.json()["id"]

    deadline = time.time() + 300
    status = "IN_PROGRESS"
    while time.time() < deadline:
        check = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        check.raise_for_status()
        status = check.json().get("status_code", status)
        if status == "FINISHED":
            break
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container failed: {status}")
        time.sleep(5)
    else:
        raise TimeoutError(f"Instagram container stuck in {status}")

    publish = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=60,
    )
    publish.raise_for_status()
    return {"container_id": container_id, "media_id": publish.json().get("id"), "status": status}
