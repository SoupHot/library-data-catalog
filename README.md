# library-data-catalog

강원도 데이터 현황 카탈로그. 정적 페이지(`index.html` 단독 동작)로 GitHub Pages 배포:
https://souphot.github.io/library-data-catalog/

## 데이터 구조 (소스: `~/gdrive/library_data`, rclone 마운트)

```
library_data/
  <플랫폼>/
    <데이터셋>/          ← 디렉토리 하나 = 데이터셋 하나
      xxx.csv
      xxx.txt / xxx.png / xxx.hwp   (설명·미리보기, 있으면)
```

새 데이터는 이 구조에 맞춰 데이터셋 폴더째로 올린다. 다운로드는 Drive 폴더
공유 링크로 제공하며, 방문자가 받을 때 Drive가 폴더를 자동으로 zip으로 묶어준다.

## 갱신 파이프라인

```
python3 gen_links.py       # 새 데이터셋의 Drive 공유 링크 발급 → links.json
python3 build_catalog.py   # 소스 스캔 → catalog.json + index.html 생성
git add -A && git commit && git push   # Pages 배포
```

- `build_catalog.py` — 데이터셋 단위로 스캔, CSV 행수는 `.scan_cache.json`에
  (mtime,size)로 캐시해 큰 파일을 매번 다시 읽지 않는다.
- `gen_links.py` — `rclone link`로 데이터셋 폴더 공유 링크 발급(캐시된 건 건너뜀).
- `migrate_structure.py` — 평평한 파일을 데이터셋 폴더로 옮긴 일회성 이관 스크립트.
- `previews/` — 카탈로그에 보여줄 미리보기 png(빌드가 복사).

원본 데이터 파일은 repo에 두지 않는다(Drive에만). repo엔 페이지·메타데이터만.
