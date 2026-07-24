#!/usr/bin/env python3
"""Reorganize flat platform dirs into per-dataset subdirectories on the Drive mount.
Each CSV + its companion (txt/png) moves into a folder named after the CSV.
혁신플랫폼 is already nested and is left untouched.

Dry-run by default (prints the plan). Pass --apply to actually move files.
Usage:
  python3 migrate_structure.py            # dry-run
  python3 migrate_structure.py --apply    # execute moves
"""
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

SOURCE = Path("/home/wook/gdrive/library_data")
FLAT_PLATFORMS = ["강원통계정보", "공공데이터포털"]  # 혁신플랫폼은 이미 데이터셋 폴더 구조


def norm(stem):
    """Match csv↔companion despite space/underscore differences."""
    return re.sub(r"[ _]+", "", stem)


def plan_platform(platform_dir):
    """Return list of (dataset_name, [files_to_move]) and a list of orphan files."""
    files = [p for p in platform_dir.iterdir() if p.is_file()]
    csvs = [p for p in files if p.suffix.lower() == ".csv"]
    companions = [p for p in files if p.suffix.lower() in (".txt", ".png")]

    used = set()
    datasets = []
    for csv in sorted(csvs):
        ds = csv.stem
        members = [csv]
        for comp in companions:
            if comp not in used and norm(comp.stem) == norm(csv.stem):
                members.append(comp)
                used.add(comp)
        datasets.append((ds, members))

    orphans = [p for p in companions if p not in used]
    return datasets, orphans


def main():
    apply = "--apply" in sys.argv
    for platform in FLAT_PLATFORMS:
        pdir = SOURCE / platform
        if not pdir.exists():
            print(f"[skip] {platform} 없음")
            continue
        datasets, orphans = plan_platform(pdir)
        print(f"\n=== {platform}: 데이터셋 {len(datasets)}개 ===")
        for ds, members in datasets:
            comp = ", ".join(m.suffix for m in members if m.suffix != ".csv") or "설명파일 없음"
            print(f"  {ds}/  ({comp})")
            if apply:
                target = pdir / ds
                target.mkdir(exist_ok=True)
                for m in members:
                    dest = target / m.name
                    if m.resolve() != dest.resolve():
                        shutil.move(str(m), str(dest))
        if orphans:
            print(f"  [주의] 짝 없는 파일 {len(orphans)}개 (이동 안 함):")
            for o in orphans:
                print(f"      {o.name}")
    print("\n" + ("✅ 이동 완료" if apply else "ℹ️  dry-run (실제 이동하려면 --apply)"))


if __name__ == "__main__":
    main()
