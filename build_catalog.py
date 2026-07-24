#!/usr/bin/env python3
"""Scan library_data (dataset = a directory under a platform) and emit a static
HTML catalog into this script's directory. One table row per dataset.

Download links come from links.json ({"<platform>/<dataset>": "<drive url>"}),
populated separately by gen_links.py. CSV row counts are cached in .scan_cache.json
keyed on (mtime, size) so unchanged big files aren't re-read every run.

Run: python3 build_catalog.py
"""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path("/home/wook/gdrive/library_data")
OUT = Path(__file__).parent
LINKS = OUT / "links.json"
CACHE = OUT / ".scan_cache.json"

_cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
_links = json.loads(LINKS.read_text()) if LINKS.exists() else {}


def read_head_text(path, n=65536):
    data = path.read_bytes()[:n]
    for enc in ("utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1", errors="replace")


def read_text_any(path):
    data = path.read_bytes()
    for enc in ("utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1", errors="replace")


def csv_header(path):
    line = read_head_text(path).splitlines()[:1]
    return next(csv.reader(line), None) if line else None


def count_rows(path):
    """Stream newline count (minus header). Avoids loading a huge file into memory."""
    n = 0
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            n += chunk.count(b"\n")
    return max(n - 1, 0)


def scan_csv(path):
    """Return (header, rows) with an (mtime,size)-keyed cache."""
    st = path.stat()
    key = str(path)
    cached = _cache.get(key)
    if cached and cached["mtime"] == st.st_mtime and cached["size"] == st.st_size:
        return cached["header"], cached["rows"]
    header = csv_header(path)
    rows = count_rows(path)
    _cache[key] = {"mtime": st.st_mtime, "size": st.st_size, "header": header, "rows": rows}
    return header, rows


def kosis_source(text):
    m = re.search(r"출처\s*:\s*(.+)", text)
    return m.group(1).strip() if m else None


def describe_dataset(platform, ds_dir):
    files = sorted(p for p in ds_dir.rglob("*") if p.is_file())
    rel = f"{platform}/{ds_dir.name}"
    entry = {
        "platform": platform,
        "dataset": ds_dir.name,
        "path": rel,
        "files": [],
        "size_kb": 0.0,
        "rows": 0,
        "modified": None,
        "source": None,
        "description": None,
        "has_desc_file": False,
        "preview": None,
        "download": _links.get(rel),
    }
    latest = 0.0
    for f in files:
        st = f.stat()
        latest = max(latest, st.st_mtime)
        ext = f.suffix.lower()
        fentry = {"name": f.name, "ext": ext, "size_kb": round(st.st_size / 1024, 1), "rows": None}
        entry["size_kb"] += st.st_size / 1024
        try:
            if ext == ".csv":
                header, rows = scan_csv(f)
                fentry["rows"] = rows
                fentry["schema"] = header
                entry["rows"] += rows
            elif ext == ".txt":
                text = read_text_any(f)
                entry["description"] = text
                entry["source"] = kosis_source(text)
                entry["has_desc_file"] = True
            elif ext in (".hwp", ".hwpx"):
                entry["has_desc_file"] = True
            elif ext == ".png" and not entry["preview"]:
                dest = OUT / "previews" / f.name
                dest.parent.mkdir(exist_ok=True)
                dest.write_bytes(f.read_bytes())
                entry["preview"] = f"previews/{f.name}"
        except Exception as e:  # ponytail: best-effort; one bad file shouldn't kill the scan
            fentry["error"] = str(e)
        entry["files"].append(fentry)
    entry["size_kb"] = round(entry["size_kb"], 1)
    entry["modified"] = datetime.fromtimestamp(latest, tz=timezone.utc).strftime("%Y-%m-%d") if latest else None
    return entry


def collect():
    datasets = []
    for platform_dir in sorted(p for p in SOURCE.iterdir() if p.is_dir()):
        for ds_dir in sorted(p for p in platform_dir.iterdir() if p.is_dir()):
            datasets.append(describe_dataset(platform_dir.name, ds_dir))
    return datasets


HTML_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>library_data catalog</title>
<style>
:root{--bg:#f6f7fb;--card:#fff;--ink:#1d2433;--muted:#6b7280;--line:#e6e8ef;--accent:#3b5bdb}
*{box-sizing:border-box}
body{font-family:"Pretendard",system-ui,-apple-system,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
.wrap{max-width:76rem;margin:0 auto;padding:2.5rem 2rem 4rem}
header h1{font-size:1.5rem;margin:0 0 .2rem}
header p{color:var(--muted);margin:0 0 1rem;font-size:.9rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));gap:.8rem;margin-bottom:1.8rem}
.stat{background:var(--card);border:1px solid var(--line);border-radius:.7rem;padding:.9rem 1.1rem;box-shadow:0 1px 2px rgba(20,20,40,.03)}
.stat .n{font-size:1.4rem;font-weight:700;color:var(--accent)}
.stat .l{font-size:.78rem;color:var(--muted);margin-top:.1rem}
input#q{padding:.6rem .9rem;width:100%;max-width:24rem;margin-bottom:1.2rem;border:1px solid var(--line);border-radius:.6rem;font-size:.9rem;outline:none;transition:border-color .15s}
input#q:focus{border-color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:.8rem;overflow:hidden;box-shadow:0 1px 3px rgba(20,20,40,.04)}
table{border-collapse:collapse;width:100%;font-size:.82rem}
th,td{padding:.55rem .8rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
th{background:#fafbfd;cursor:pointer;position:sticky;top:0;font-weight:600;color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.03em;user-select:none}
th:hover{color:var(--accent)}
tbody tr:hover{background:#f8f9ff}
tbody tr:last-child td{border-bottom:none}
.badge{display:inline-block;padding:.15rem .55rem;border-radius:1rem;font-size:.72rem;font-weight:600;white-space:nowrap}
.ds{color:var(--ink);font-weight:600}
.num{font-variant-numeric:tabular-nums;color:var(--muted)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(20rem,1fr));gap:1rem;margin-bottom:1.8rem}
.chart{background:var(--card);border:1px solid var(--line);border-radius:.8rem;padding:1.1rem 1.3rem;box-shadow:0 1px 3px rgba(20,20,40,.04)}
.chart h3{margin:0 0 .8rem;font-size:.82rem;color:var(--muted);font-weight:600}
.bar-row{display:grid;grid-template-columns:8rem 1fr 3rem;align-items:center;gap:.6rem;margin-bottom:.45rem;font-size:.78rem}
.bar-track{background:var(--bg);border-radius:.3rem;height:.6rem;overflow:hidden}
.bar-fill{height:100%;border-radius:.3rem}
details>summary{cursor:pointer;color:var(--accent)}
details[open]>summary{margin-bottom:.4rem}
details pre{white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,monospace;font-size:.72rem;color:var(--ink);background:var(--bg);border-radius:.5rem;padding:.6rem .8rem;margin:0}
.filelist{list-style:none;margin:.3rem 0 0;padding:0;font-size:.75rem}
.filelist li{padding:.15rem 0;color:var(--muted)}
.dl{display:inline-block;padding:.25rem .6rem;border-radius:.4rem;background:var(--accent);color:#fff;text-decoration:none;font-size:.75rem;font-weight:600}
.dl.off{background:var(--line);color:var(--muted);pointer-events:none}
.mut{color:var(--muted)}
</style>
<div class="wrap">
<header>
  <h1>library_data 수집 현황</h1>
  <p id="meta"></p>
  <nav style="font-size:.85rem"><a href="airgap-llm-guide.html" style="color:var(--accent);text-decoration:none">폐쇄망 LLM 인프라 구축 가이드 &rarr;</a></nav>
</header>
<div class="stats" id="stats"></div>
<div class="charts">
  <div class="chart"><h3>플랫폼별 데이터셋 수</h3><div id="chart-count"></div></div>
  <div class="chart"><h3>플랫폼별 데이터 행수</h3><div id="chart-rows"></div></div>
</div>
<input id="q" placeholder="필터 (플랫폼 / 데이터셋 / 파일명 검색)">
<div class="card">
<table id="t">
<thead><tr>
<th data-k="platform">플랫폼</th><th data-k="dataset">데이터셋</th><th>구성</th><th data-k="rows">행수</th>
<th data-k="size_kb">크기</th><th data-k="modified">수정일</th><th data-k="source">출처 / 설명</th><th>다운로드</th>
</tr></thead>
<tbody></tbody>
</table>
</div>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ["#3b5bdb","#0f9d58","#e8590c","#9c36b5","#1098ad","#e03131"];
const colorOf = (() => {
  const seen = new Map();
  return name => { if (!seen.has(name)) seen.set(name, PALETTE[seen.size % PALETTE.length]); return seen.get(name); };
})();
const escapeHtml = s => (s ?? "").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const fmtSize = kb => kb >= 1024 ? (kb/1024).toFixed(1)+" MB" : kb.toFixed(0)+" KB";

const tbody = document.querySelector("#t tbody");
const platforms = [...new Set(DATA.map(r => r.platform))];
const totalRows = DATA.reduce((s,r)=>s+(r.rows||0),0);
const totalSize = DATA.reduce((s,r)=>s+(r.size_kb||0),0);

document.querySelector("#meta").textContent =
  `총 ${DATA.length}개 데이터셋 · 생성일 ${new Date().toISOString().slice(0,10)}`;
document.querySelector("#stats").innerHTML = [
  ["데이터셋", DATA.length],
  ["플랫폼", platforms.length],
  ["총 데이터 행수", totalRows.toLocaleString()],
  ["총 용량", fmtSize(totalSize)],
].map(([l,n]) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");

function barChart(el, pairs) {
  const max = Math.max(...pairs.map(([,v])=>v), 1);
  el.innerHTML = pairs.map(([label,v]) => `<div class="bar-row">
    <span>${label}</span>
    <div class="bar-track"><div class="bar-fill" style="width:${v/max*100}%;background:${colorOf(label)}"></div></div>
    <span class="num">${v.toLocaleString()}</span>
  </div>`).join("");
}
barChart(document.querySelector("#chart-count"), platforms.map(p=>[p, DATA.filter(r=>r.platform===p).length]));
barChart(document.querySelector("#chart-rows"), platforms.map(p=>[p, DATA.filter(r=>r.platform===p).reduce((s,r)=>s+(r.rows||0),0)]));

function composition(r) {
  const byExt = {};
  r.files.forEach(f => { byExt[f.ext] = (byExt[f.ext]||0)+1; });
  const summary = Object.entries(byExt).map(([e,n]) => `${e||"?"}×${n}`).join(" · ");
  const list = r.files.map(f => `<li>${escapeHtml(f.name)}${f.rows!=null?` <span class="num">(${f.rows.toLocaleString()}행)</span>`:""}</li>`).join("");
  return `<details><summary>파일 ${r.files.length}개 · ${summary}</summary><ul class="filelist">${list}</ul></details>`;
}

function sourceCell(r) {
  if (r.description) return `<details><summary>${escapeHtml(r.source || "설명 보기")}</summary><pre>${escapeHtml(r.description)}</pre></details>`;
  if (r.has_desc_file) return `<span class="mut">설명서 포함 (hwp)</span>`;
  return `<span class="mut">—</span>`;
}

function render(rows) {
  tbody.innerHTML = rows.map(r => {
    const c = colorOf(r.platform);
    const dsName = `<span class="ds">${escapeHtml(r.dataset)}</span>` +
      (r.preview ? ` <a href="${r.preview}" target="_blank" title="미리보기">🖼️</a>` : "");
    const dl = r.download
      ? `<a class="dl" href="${r.download}" target="_blank">⬇ 다운로드</a>`
      : `<span class="dl off">준비 중</span>`;
    return `<tr>
    <td><span class="badge" style="background:${c}1a;color:${c}">${r.platform}</span></td>
    <td>${dsName}</td>
    <td>${composition(r)}</td>
    <td class="num">${(r.rows||0).toLocaleString()}</td>
    <td class="num">${fmtSize(r.size_kb||0)}</td>
    <td class="num">${r.modified ?? ""}</td>
    <td>${sourceCell(r)}</td>
    <td>${dl}</td>
  </tr>`;
  }).join("");
}
render(DATA);

document.querySelector("#q").addEventListener("input", e => {
  const needle = e.target.value.toLowerCase();
  render(DATA.filter(r => JSON.stringify(r).toLowerCase().includes(needle)));
});
let sortDir = 1;
document.querySelectorAll("th[data-k]").forEach(th => th.addEventListener("click", () => {
  const k = th.dataset.k;
  const sorted = [...DATA].sort((a,b) => (a[k] ?? "") > (b[k] ?? "") ? sortDir : -sortDir);
  sortDir *= -1;
  render(sorted);
}));
</script>
"""


def build():
    datasets = collect()
    CACHE.write_text(json.dumps(_cache, ensure_ascii=False))
    (OUT / "catalog.json").write_text(json.dumps(datasets, ensure_ascii=False, indent=2))
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(datasets, ensure_ascii=False))
    (OUT / "index.html").write_text(html)
    return datasets


def demo():
    datasets = build()
    assert len(datasets) > 0, "expected at least one dataset"
    assert any(d["rows"] for d in datasets), "expected at least one dataset with rows"
    assert all("/" in d["path"] for d in datasets), "dataset path must be platform/dataset"
    print(f"OK: {len(datasets)} datasets cataloged, index.html written.")


if __name__ == "__main__":
    demo()
