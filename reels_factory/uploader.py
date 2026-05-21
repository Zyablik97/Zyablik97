from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import requests


def _run(cmd: list[str], env: dict[str, str] | None = None) -> str:
    return subprocess.run(cmd, check=True, text=True, capture_output=True, env=env).stdout.strip()


def upload_to_github_release(video_path: Path, repo: str, token: str) -> str:
    if not repo:
        raise ValueError("GITHUB_REPOSITORY is required for release upload")
    if not token:
        raise ValueError("GITHUB_TOKEN is required for release upload")
    tag = f"reels-{int(time.time())}"
    env = {**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token}
    try:
        _run(["gh", "release", "create", tag, "--repo", repo, "--title", tag, "--notes", "auto"], env=env)
        _run(["gh", "release", "upload", tag, str(video_path), "--repo", repo, "--clobber"], env=env)
        data = _run(["gh", "release", "view", tag, "--repo", repo, "--json", "assets", "--jq", ".assets[0].url"], env=env)
        return data
    except Exception:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        release = requests.post(
            f"https://api.github.com/repos/{repo}/releases",
            headers=headers,
            json={"tag_name": tag, "name": tag, "body": "auto"},
            timeout=30,
        )
        release.raise_for_status()
        upload_url = release.json()["upload_url"].split("{")[0]
        with video_path.open("rb") as file:
            asset = requests.post(
                upload_url,
                headers={**headers, "Content-Type": "video/mp4"},
                params={"name": video_path.name},
                data=file,
                timeout=300,
            )
        asset.raise_for_status()
        return asset.json()["browser_download_url"]
