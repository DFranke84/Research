"""List kept PDFs that contain scanned pages (image-only pages with no text layer)."""
import json, os, sys
import fitz
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
R = json.load(open(os.path.join(RESEARCH, "CATALOG.json"), encoding="utf-8"))
out = []
for r in R:
    if r["source_type"] != "pdf" or not r["original_file"]:
        continue
    p = os.path.join(RESEARCH, r["original_file"])
    try:
        d = fitz.open(p)
    except Exception as e:
        print("ERR", p, e); continue
    empty = [i for i, pg in enumerate(d) if len(pg.get_text().strip()) < 40 and pg.get_images()]
    if empty:
        out.append({"md": r["file"], "pdf": r["original_file"], "pages": len(d), "scanned": empty})
json.dump(out, open(os.path.join(RESEARCH, "_work", "scanned_pdfs.json"), "w"), indent=0)
for o in out:
    print(f'{len(o["scanned"]):4}/{o["pages"]:<4} {o["pdf"]}')
print(len(out), "pdfs,", sum(len(o["scanned"]) for o in out), "pages")
