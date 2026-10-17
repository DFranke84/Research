"""Inventory every PDF across the AIPortable source folders (read-only).

Hashes each file (sha256), pulls page count + first ~600 chars of text, and
joins it to the library.db metadata (title/source_url/license) where possible.
Output: E:/Research/_work/pdf_inventory.json
"""
import hashlib, json, os, sqlite3, sys
import pymupdf

ROOT = r"E:\AIPortable"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "pdf_inventory.json")
DIRS = {
    "library-pdfs": r"data\library\pdfs",
    "archive-org": r"tempDocsInstalled\archive-org",
    "team-archive": r"tempDocsInstalled\team-archive",
    "local-pdf": r"tempDocsInstalled\local-pdf",
    "unattributed": r"tempDocsInstalled\unattributed",
    "defense-field-manuals": r"tempDocs\defense-field-manuals",
    "animal-tracks": r"tempDocs\animal-tracks",
}

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prev = {}
    if os.path.exists(OUT):
        for r in json.load(open(OUT, encoding="utf-8")):
            prev[(r["path"], r["size"])] = r
    db = sqlite3.connect(f"file:{ROOT}\\data\\library.db?mode=ro", uri=True)
    by_pdf = {r[0]: r for r in db.execute(
        "select pdf_filename,id,title,source,source_url,license,category from library_docs where pdf_filename is not null")}
    rows = []
    for label, rel in DIRS.items():
        d = os.path.join(ROOT, rel)
        for dp, _, fns in os.walk(d):
            for fn in fns:
                p = os.path.join(dp, fn)
                if not fn.lower().endswith((".pdf", ".html")):
                    continue
                size = os.path.getsize(p)
                if (p, size) in prev:
                    rows.append(prev[(p, size)]); continue
                r = {"folder": label, "path": p, "file": fn, "size": size, "sha256": sha(p)}
                if fn.lower().endswith(".pdf"):
                    try:
                        doc = pymupdf.open(p)
                        r["pages"] = doc.page_count
                        txt = ""
                        for i in range(min(doc.page_count, 6)):
                            txt += doc[i].get_text()
                            if len(txt) > 1500: break
                        r["head"] = " ".join(txt.split())[:700]
                        r["has_text"] = len(txt.strip()) > 100
                        md = doc.metadata or {}
                        r["pdf_title"] = md.get("title") or ""
                    except Exception as e:
                        r["error"] = str(e)
                m = by_pdf.get(fn)
                if m:
                    r.update(db_id=m[1], db_title=m[2], db_source=m[3], source_url=m[4], license=m[5], db_category=m[6])
                rows.append(r)
                if len(rows) % 50 == 0:
                    print(len(rows), flush=True)
                    json.dump(rows, open(OUT, "w", encoding="utf-8"), indent=1)
    json.dump(rows, open(OUT, "w", encoding="utf-8"), indent=1)
    print("done", len(rows))

main()
