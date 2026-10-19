"""Scan every source .md in E:\\Research, validate its front-matter, and write
CATALOG.csv + CATALOG.json (one row per source file) and category counts.
Also reports files missing a source (source_url / sources / provenance).

Only new or changed files are read: each file's row is remembered in _work/catalog_cache.json with the file's
size and last-changed time (and its _images folder's), so adding one recipe doesn't re-read the whole library.
  --full   ignore the remembered rows and read every file again"""
import csv, glob, json, os, sys, collections
import yaml
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
from categories import CATEGORIES

CACHE = os.path.join(RESEARCH, "_work", "catalog_cache.json")
VERSION = 1   # bump when the row layout below changes, so old remembered rows are not reused
cache = {}
if "--full" not in sys.argv and os.path.exists(CACHE):
    try:
        c = json.load(open(CACHE, encoding="utf-8"))
        cache = c["files"] if c.get("version") == VERSION else {}
    except Exception:
        cache = {}   # damaged or half-written: read everything once


def read(f, cat, img_dir):
    """(row or None, [problems]) from one .md file."""
    problems = []
    txt = open(f, encoding="utf-8").read()
    try:
        fm = yaml.safe_load(txt.split("---\n", 2)[1])
    except Exception as e:
        return None, [(f, "bad front-matter: %s" % e)]
    src = fm.get("source_url") or (fm.get("sources") or [{}])[0].get("url") or fm.get("provenance")
    if not src:
        problems.append((f, "no source"))
    if fm.get("category") != cat:
        problems.append((f, "category mismatch %s" % fm.get("category")))
    return {
        "file": os.path.relpath(f, RESEARCH).replace("\\", "/"),
        "title": fm.get("title"),
        "category": cat,
        "source_type": fm.get("source_type"),
        "publisher": fm.get("publisher") or ", ".join(s.get("name", "") for s in fm.get("sources", []) or []),
        "source_url": fm.get("source_url") or "",
        "license": fm.get("license"),
        "original_file": os.path.relpath(os.path.join(os.path.dirname(f), fm["file"]), RESEARCH).replace("\\", "/") if fm.get("file") else "",
        "images": len(glob.glob(os.path.join(img_dir, "*"))) if os.path.isdir(img_dir) else 0,
        "words": len(txt.split()),
        "date_added": str(fm.get("date_added") or ""),
        "group": fm.get("group") or "",   # local-area plant type (Fruit trees - Apples, Roses, ...)
    }, problems


rows, problems, new_cache, n_read = [], [], {}, 0
for cat in CATEGORIES:
    for f in sorted(glob.glob(os.path.join(RESEARCH, cat, "**", "*.md"), recursive=True)):   # incl. course folders
        st = os.stat(f)
        img_dir = f[:-3] + "_images"
        img_m = os.stat(img_dir).st_mtime_ns if os.path.isdir(img_dir) else 0
        key = [st.st_mtime_ns, st.st_size, img_m, cat]
        rel = os.path.relpath(f, RESEARCH)
        hit = cache.get(rel)
        if hit and hit["key"] == key:
            row, probs = hit["row"], [tuple(p) for p in hit["problems"]]
        else:
            row, probs = read(f, cat, img_dir); n_read += 1
        new_cache[rel] = {"key": key, "row": row, "problems": probs}
        problems += probs
        if row:
            rows.append(row)
with open(os.path.join(RESEARCH, "CATALOG.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
json.dump(rows, open(os.path.join(RESEARCH, "CATALOG.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
tmp = CACHE + ".tmp"   # write then swap, so an interrupted run never leaves a broken cache
json.dump({"version": VERSION, "files": new_cache}, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, default=str)
os.replace(tmp, CACHE)
cc = collections.Counter(r["category"] for r in rows)
st = collections.Counter(r["source_type"] for r in rows)
print("files", len(rows), "(read %d new or changed)" % n_read); print(cc.most_common()); print(st.most_common())
print("problems", len(problems)); [print(" ", p) for p in problems[:30]]
json.dump({"by_category": cc, "by_type": st, "total": len(rows), "problems": problems},
          open(os.path.join(RESEARCH, "_work", "catalog_stats.json"), "w"), indent=1)
