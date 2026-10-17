"""Scan every source .md in E:\\Research, validate its front-matter, and write
CATALOG.csv + CATALOG.json (one row per source file) and category counts.
Also reports files missing a source (source_url / sources / provenance)."""
import csv, glob, json, os, sys, collections
import yaml
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
from categories import CATEGORIES

rows, problems = [], []
for cat in CATEGORIES:
    for f in sorted(glob.glob(os.path.join(RESEARCH, cat, "**", "*.md"), recursive=True)):   # incl. course folders
        txt = open(f, encoding="utf-8").read()
        try:
            fm = yaml.safe_load(txt.split("---\n", 2)[1])
        except Exception as e:
            problems.append((f, "bad front-matter: %s" % e)); continue
        src = fm.get("source_url") or (fm.get("sources") or [{}])[0].get("url") or fm.get("provenance")
        if not src:
            problems.append((f, "no source"))
        if fm.get("category") != cat:
            problems.append((f, "category mismatch %s" % fm.get("category")))
        img_dir = f[:-3] + "_images"
        rows.append({
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
        })
with open(os.path.join(RESEARCH, "CATALOG.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
json.dump(rows, open(os.path.join(RESEARCH, "CATALOG.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
cc = collections.Counter(r["category"] for r in rows)
st = collections.Counter(r["source_type"] for r in rows)
print("files", len(rows)); print(cc.most_common()); print(st.most_common())
print("problems", len(problems)); [print(" ", p) for p in problems[:30]]
json.dump({"by_category": cc, "by_type": st, "total": len(rows), "problems": problems},
          open(os.path.join(RESEARCH, "_work", "catalog_stats.json"), "w"), indent=1)
