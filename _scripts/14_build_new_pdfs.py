"""Add the newly downloaded PDFs (_work/pdf_sources_new.tsv, files in _sources/pdf) to the library.

For each PDF: copy it into its category folder, write a Markdown sidecar (front-matter + native text),
and list any image-only pages in _work/scanned_pdfs_new.json so they can be OCR'd with
    31_ocr_pdfs.py --list scanned_pdfs_new.json
"""
import csv, hashlib, json, os, shutil, sys
import pymupdf
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, cat_dir, front_matter, SlugRegistry

W = os.path.join(RESEARCH, "_work")
SRC = os.path.join(RESEARCH, "_sources", "pdf")


def main():
    reg = SlugRegistry()
    rows = list(csv.DictReader(open(os.path.join(W, "pdf_sources_new.tsv"), encoding="utf-8"), delimiter="\t"))
    scanned, built = [], []
    for r in rows:
        src = os.path.join(SRC, r["filename"])
        data = open(src, "rb").read()
        sha = hashlib.sha256(data).hexdigest()
        slug = reg.claim(os.path.splitext(r["filename"])[0], "pdf:" + sha)
        cat = r["category"]
        dest = os.path.join(cat_dir(cat), slug + ".pdf")
        md = os.path.join(cat_dir(cat), slug + ".md")
        if not os.path.exists(dest):
            shutil.copy2(src, dest)
        doc = pymupdf.open(dest)
        parts, empty = [], []
        for i, pg in enumerate(doc):
            t = pg.get_text().strip()
            if len(t) < 40 and pg.get_images():
                empty.append(i)
            if t:
                parts.append(f"\n\n[Page {i + 1}]\n\n{t}")
        text = "".join(parts).strip()
        meta = {
            "title": r["title"], "category": cat, "source_type": "pdf", "file": slug + ".pdf",
            "publisher": r["publisher"], "source_url": r["url"], "license": r["license"],
            "pages": doc.page_count, "text_layer": bool(text), "sha256": sha,
            "provenance": "Downloaded " + TODAY + " from the publisher URL above (gap-filling acquisition)",
            "compiled": TODAY,
        }
        doc.close()
        body = [front_matter(meta), f"# {r['title']}\n",
                f"**Source:** {r['publisher']} - <{r['url']}>  ",
                f"**License:** {r['license']}  ",
                f"**Original file:** [{slug}.pdf]({slug}.pdf)\n",
                "## Full text (extracted from the original file)\n", text]
        open(md, "w", encoding="utf-8").write("\n".join(body) + "\n")
        if empty:
            scanned.append({"md": os.path.relpath(md, RESEARCH).replace("\\", "/"),
                            "pdf": os.path.relpath(dest, RESEARCH).replace("\\", "/"),
                            "pages": meta["pages"], "scanned": empty})
        built.append({"slug": slug, "category": cat, "pages": meta["pages"], "words": len(text.split()), "scanned_pages": len(empty)})
        print(f"{cat:28} {slug:70} {meta['pages']:4}p {len(text.split()):7}w  scanned:{len(empty)}", flush=True)
    reg.save()
    json.dump(scanned, open(os.path.join(W, "scanned_pdfs_new.json"), "w"), indent=0)
    json.dump(built, open(os.path.join(W, "built_new_pdfs.json"), "w"), indent=1)
    print("built", len(built), "| PDFs with scanned pages:", len(scanned), "| pages:", sum(len(s["scanned"]) for s in scanned))


main()
