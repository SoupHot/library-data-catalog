#!/usr/bin/env bash
# 크론용 자동 갱신: 링크 발급 → 빌드 → 변경 있으면 커밋·push.
# cron은 최소 환경이라 PATH·gh 인증 경로를 여기서 고정한다.
set -euo pipefail

export PATH="/home/wook/anaconda3/envs/tour/bin:/usr/bin:/bin"
cd /home/wook/library-data-catalog

LOG=/home/wook/library-data-catalog/update.log
exec >> "$LOG" 2>&1
echo "===== $(date '+%F %T') ====="

# 가드: rclone 마운트가 살아있는지 (죽었으면 빈 카탈로그를 push하지 않도록 중단)
if [ ! -d "/home/wook/gdrive/library_data/강원통계정보" ]; then
  echo "SKIP: gdrive 마운트 없음"
  exit 0
fi

python3 gen_links.py
python3 build_catalog.py

# 배포 대상 파일에 변경이 있을 때만 커밋·push
if [ -n "$(git status --porcelain index.html catalog.json links.json previews)" ]; then
  git add index.html catalog.json links.json previews
  git commit -m "Auto-update catalog $(date '+%F')"
  git push origin master
  echo "pushed"
else
  echo "변경 없음"
fi
