#!/usr/bin/env python3
"""Create/refresh Drive share links for each dataset directory and cache them
in links.json ({"<platform>/<dataset>": "<drive url>"}).

Only datasets without a cached link are queried (rclone link changes the folder's
sharing to "anyone with the link"), so re-runs are cheap. Pass --force to refresh all.

Requires the rclone remote 'gdrive:' mounted at /home/wook/gdrive.
Usage:
  python3 gen_links.py           # link datasets missing from links.json
  python3 gen_links.py --force   # re-link everything
"""
import json
import subprocess
import sys
from pathlib import Path

SOURCE = Path("/home/wook/gdrive/library_data")
REMOTE = "gdrive:library_data"  # gdrive: root maps to /home/wook/gdrive
LINKS = Path(__file__).parent / "links.json"


def dataset_paths():
    for platform in sorted(p for p in SOURCE.iterdir() if p.is_dir()):
        for ds in sorted(p for p in platform.iterdir() if p.is_dir()):
            yield f"{platform.name}/{ds.name}"


def rclone_link(rel):
    remote_path = f"{REMOTE}/{rel}"
    out = subprocess.run(
        ["rclone", "link", remote_path],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return out.stdout.strip()


def main():
    force = "--force" in sys.argv
    links = json.loads(LINKS.read_text()) if LINKS.exists() else {}
    todo = [r for r in dataset_paths() if force or r not in links]
    print(f"링크 발급 대상: {len(todo)}개")
    for rel in todo:
        try:
            links[rel] = rclone_link(rel)
            print(f"  ✓ {rel}")
        except Exception as e:
            print(f"  ✗ {rel}: {e}")
    LINKS.write_text(json.dumps(links, ensure_ascii=False, indent=2))
    print(f"links.json: {len(links)}개 링크 저장")


if __name__ == "__main__":
    main()
