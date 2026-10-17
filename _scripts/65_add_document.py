"""Add ONE document (PDF, Word, text, web page, e-book, slides...) to the library - the single-file version of
50_ingest_folder.py, with the same duplicate checks, relevance scoring, OCR and file layout.

  _scripts\\.venv\\Scripts\\python _scripts\\65_add_document.py "<file>" --check
      only look: prints the suggested category/title and whether it is already in the library
      (last line: RESULT {json} for the Library Manager app)
  _scripts\\.venv\\Scripts\\python _scripts\\65_add_document.py "<file>" [--category <folder>] [--title "<title>"] [--force]
      add it: the original is copied into the category folder next to a Markdown file with its full text,
      then the catalog and LIBRARY.md are refreshed.
      --force  add it even though it looks like a duplicate or not relevant;  --no-ocr  skip OCR of scanned pages
"""
import argparse, csv, datetime, hashlib, importlib, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from categories import CATEGORIES

ing = importlib.import_module("50_ingest_folder")


def analyse(path, ocr=True):
    """The same decision 50_ingest_folder's review makes, for one file."""
    ext = os.path.splitext(path)[1].lower()
    row = {"file": path, "decision": "", "category": "", "score": "", "title": "", "words": "", "reason": "", "matches": "", "sha256": ""}
    if ext not in ing.EXT:
        row.update(decision="unsupported", reason=f"file type {ext or '(none)'} is not handled")
        return row
    print("Checking the library for duplicates (the first check can take a few minutes)...", flush=True)
    idx = ing.load_index()
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    row["sha256"] = sha
    same = next((rel for rel, v in idx.items() if sha in v["sha"]), None)
    if same:
        row.update(decision="duplicate", reason="this exact file is already in the library", matches=same)
    print("Reading the document" + (" (scanned pages are OCR'd - this can take a while)" if ocr and ext == ".pdf" else "") + "...", flush=True)
    try:
        title, text, info = ing.extract(path, ocr)
    except Exception as e:
        row.update(decision="unreadable", reason=f"{type(e).__name__}: {e}"[:200])
        return row
    words = len(text.split())
    row.update(title=ing.guess_title(title, text, path), words=words)
    cat, score, second, nd = ing.relevance(text, row["title"])
    row.update(category=cat, score=score)
    if row["decision"]:
        return row
    if words < 80:
        row.update(decision="unreadable", reason="little or no text could be read from it"
                   + (" (scanned - try again with OCR on)" if info.get("scanned_pages_not_ocrd") else ""))
        return row
    fp = ing.fingerprint(text)
    hits = Counter(rel for rel, v in idx.items() for h in v["fp"] if h in fp) if fp else Counter()
    best = hits.most_common(1)
    if fp and best and best[0][1] / len(fp) >= 0.6:
        row.update(decision="near-duplicate", reason=f"{best[0][1] * 100 // len(fp)}% of its text is already in the library",
                   matches=best[0][0])
    elif score < 8 or nd < ing.MIN_DISTINCT:
        row.update(decision="not-relevant", reason=f"low relevance to the library topics (score {score}, best match {cat})")
    else:
        row.update(decision="add", reason=f"fits {cat} (also {second})" + (f"; OCR'd {info['ocr_pages']} pages" if info.get("ocr_pages") else ""))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--category")
    ap.add_argument("--title")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()
    path = os.path.abspath(a.file)
    if not os.path.isfile(path):
        sys.exit(f"file not found: {path}")
    if a.category and a.category not in CATEGORIES:
        sys.exit(f"unknown category {a.category!r}; use one of: {', '.join(CATEGORIES)}")
    row = analyse(path, not a.no_ocr)
    print(f"\n  {os.path.basename(path)}\n  title:    {row['title']}\n  category: {row['category']}  (score {row['score']})"
          f"\n  result:   {row['decision']} - {row['reason']}" + (f"\n  already:  {row['matches']}" if row["matches"] else ""), flush=True)
    if a.check:
        print("RESULT " + json.dumps(row, ensure_ascii=False))
        return
    if row["decision"] in ("unsupported", "unreadable"):
        sys.exit("Nothing added.")
    if row["decision"] != "add" and not a.force:
        sys.exit("Nothing added (it is a " + row["decision"] + "; tick 'add anyway' / use --force to add it regardless).")
    row.update(decision="add", category=a.category or row["category"], title=(a.title or row["title"]).strip())
    report = os.path.join(ing.W, "single_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv")
    with open(report, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader(); w.writerow(row)
    print("\nAdding to the library...", flush=True)
    ing.apply(report, not a.no_ocr)
    print("Done.")


if __name__ == "__main__":
    main()
