#!/usr/bin/env python3
"""Scan the library_data gdrive folder and emit a static HTML catalog
(counts, schema, last-modified) into this script's own directory.
Run after adding/changing source files: python3 build_catalog.py
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path("/home/wook/gdrive/library_data")
OUT = Path(__file__).parent


def read_text_any(path, max_bytes=None):
    data = path.read_bytes() if max_bytes is None else path.read_bytes()[:max_bytes]
    for enc in ("utf-8", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1")


def csv_schema(path):
    text = read_text_any(path)
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return None, 0
    header = rows[0]
    return header, max(len(rows) - 1, 0)


def kosis_source(txt_path):
    """Pull the '출처' line out of a KOSIS metadata .txt sidecar, if present."""
    text = read_text_any(txt_path)
    m = re.search(r"출처\s*:\s*(.+)", text)
    return m.group(1).strip() if m else None


def xlsx_schema(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    return [f"{ws.title} {ws.dimensions}" for ws in wb.worksheets], None


def describe(path):
    stat = path.stat()
    rel_parts = path.relative_to(SOURCE).parts
    entry = {
        "category": rel_parts[0] if len(rel_parts) > 1 else "(루트)",
        "path": str(path.relative_to(SOURCE)),
        "ext": path.suffix.lower(),
        "size_kb": round(stat.st_size / 1024, 1),
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d"),
        "rows": None,
        "schema": None,
        "source": None,
    }
    try:
        if entry["ext"] == ".csv":
            header, rows = csv_schema(path)
            entry["schema"] = header
            entry["rows"] = rows
            sidecar = path.with_suffix(".txt")
            if sidecar.exists():
                entry["source"] = kosis_source(sidecar)
        elif entry["ext"] == ".xlsx":
            sheets, _ = xlsx_schema(path)
            entry["schema"] = sheets
    except Exception as e:  # ponytail: best-effort scan, one bad file shouldn't kill the catalog
        entry["source"] = f"(parse error: {e})"
    return entry


HTML_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>library_data catalog</title>
<style>
:root{--bg:#f6f7fb;--card:#fff;--ink:#1d2433;--muted:#6b7280;--line:#e6e8ef;--accent:#3b5bdb}
*{box-sizing:border-box}
body{font-family:"Pretendard",system-ui,-apple-system,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
.wrap{max-width:72rem;margin:0 auto;padding:2.5rem 2rem 4rem}
header h1{font-size:1.5rem;margin:0 0 .2rem}
header p{color:var(--muted);margin:0 0 1.8rem;font-size:.9rem}
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
.schema{max-width:26rem;color:var(--muted);font-family:ui-monospace,monospace;font-size:.72rem}
.path{color:var(--ink)}
.num{font-variant-numeric:tabular-nums;color:var(--muted)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(20rem,1fr));gap:1rem;margin-bottom:1.8rem}
.chart{background:var(--card);border:1px solid var(--line);border-radius:.8rem;padding:1.1rem 1.3rem;box-shadow:0 1px 3px rgba(20,20,40,.04)}
.chart h3{margin:0 0 .8rem;font-size:.82rem;color:var(--muted);font-weight:600}
.bar-row{display:grid;grid-template-columns:7rem 1fr 3rem;align-items:center;gap:.6rem;margin-bottom:.45rem;font-size:.78rem}
.bar-track{background:var(--bg);border-radius:.3rem;height:.6rem;overflow:hidden}
.bar-fill{height:100%;border-radius:.3rem}
</style>
<div class="wrap">
<header>
  <h1>library_data 수집 현황</h1>
  <p id="meta"></p>
</header>
<div class="stats" id="stats"></div>
<div class="charts">
  <div class="chart"><h3>카테고리별 파일 수</h3><div id="chart-count"></div></div>
  <div class="chart"><h3>카테고리별 데이터 행수</h3><div id="chart-rows"></div></div>
  <div class="chart"><h3>파일 형식 분포</h3><div id="chart-ext"></div></div>
</div>
<input id="q" placeholder="필터 (카테고리 / 파일명 / 스키마 검색)">
<div class="card">
<table id="t">
<thead><tr>
<th data-k="category">카테고리</th><th data-k="path">파일</th><th data-k="rows">행수</th>
<th data-k="size_kb">크기(KB)</th><th data-k="modified">수정일</th><th data-k="source">출처/일자</th><th>스키마</th>
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
  return name => {
    if (!seen.has(name)) seen.set(name, PALETTE[seen.size % PALETTE.length]);
    return seen.get(name);
  };
})();

const tbody = document.querySelector("#t tbody");
document.querySelector("#meta").textContent =
  `총 ${DATA.length}개 파일 · 생성일 ${new Date().toISOString().slice(0,10)}`;

const cats = [...new Set(DATA.map(r => r.category))];
const totalRows = DATA.reduce((s, r) => s + (r.rows || 0), 0);
document.querySelector("#stats").innerHTML = [
  ["파일 수", DATA.length],
  ["카테고리", cats.length],
  ["총 데이터 행수", totalRows.toLocaleString()],
  ["CSV/XLSX", DATA.filter(r => [".csv",".xlsx"].includes(r.ext)).length],
].map(([l, n]) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");

function barChart(el, pairs, colorFor) {
  const max = Math.max(...pairs.map(([, v]) => v), 1);
  el.innerHTML = pairs.map(([label, v]) => `<div class="bar-row">
    <span>${label}</span>
    <div class="bar-track"><div class="bar-fill" style="width:${v / max * 100}%;background:${colorFor(label)}"></div></div>
    <span class="num">${v.toLocaleString()}</span>
  </div>`).join("");
}

const countByCat = cats.map(c => [c, DATA.filter(r => r.category === c).length]);
const rowsByCat = cats.map(c => [c, DATA.filter(r => r.category === c).reduce((s, r) => s + (r.rows || 0), 0)]);
const extCounts = {};
DATA.forEach(r => { const k = r.ext || "(없음)"; extCounts[k] = (extCounts[k] || 0) + 1; });
const extPairs = Object.entries(extCounts).sort((a, b) => b[1] - a[1]);

barChart(document.querySelector("#chart-count"), countByCat, colorOf);
barChart(document.querySelector("#chart-rows"), rowsByCat.filter(([, v]) => v > 0), colorOf);
barChart(document.querySelector("#chart-ext"), extPairs, () => "var(--accent)");

function render(rows) {
  tbody.innerHTML = rows.map(r => {
    const c = colorOf(r.category);
    return `<tr>
    <td><span class="badge" style="background:${c}1a;color:${c}">${r.category}</span></td>
    <td class="path">${r.path}</td>
    <td class="num">${r.rows ?? ""}</td>
    <td class="num">${r.size_kb}</td>
    <td class="num">${r.modified}</td>
    <td>${r.source ?? ""}</td>
    <td class="schema">${r.schema ? (Array.isArray(r.schema) ? r.schema.join(", ") : r.schema) : ""}</td>
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
  const sorted = [...DATA].sort((a, b) => (a[k] ?? "") > (b[k] ?? "") ? sortDir : -sortDir);
  sortDir *= -1;
  render(sorted);
}));
</script>
"""


def build():
    files = [p for p in SOURCE.rglob("*") if p.is_file()]
    catalog = sorted((describe(p) for p in files), key=lambda e: (e["category"], e["path"]))
    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(catalog, ensure_ascii=False))
    (OUT / "index.html").write_text(html)
    return catalog


def demo():
    catalog = build()
    assert len(catalog) > 0, "expected at least one file in the catalog"
    csv_entries = [e for e in catalog if e["ext"] == ".csv"]
    assert any(e["rows"] for e in csv_entries), "expected at least one CSV with row count"
    print(f"OK: {len(catalog)} files cataloged, index.html written.")


if __name__ == "__main__":
    demo()
