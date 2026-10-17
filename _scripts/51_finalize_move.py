"""After 50_ingest_folder.py --apply: turn the copy into a MOVE and document what stayed behind.

  _scripts\\.venv\\Scripts\\python _scripts\\51_finalize_move.py <review CSV> [--delete]

1. Collects the sha256 of every library file that came from the scanned folder (provenance line).
2. Originals whose bytes are identical to a library file (added now, or already there) are deleted
   when --delete is given (without it, the script only reports what it would delete).
3. Every file left in the folder is written to <folder>\\_NOT_MOVED_REASONS.csv with the reason it stayed.
"""
import argparse, csv, hashlib, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
from categories import CATEGORIES

MEDIA = {".mp4": "video", ".m4v": "video", ".mp3": "audio"}
WHY_EXT = {
    ".jpg": "Image (photo / scanned page / chart) - no text for the library; OCR or transcribe by hand if wanted",
    ".mobi": "Kindle e-book - same book is in this folder as EPUB/PDF (that copy was evaluated instead)",
    ".azw3": "Kindle e-book - same book is in this folder as EPUB/PDF (that copy was evaluated instead)",
    ".xls": "Old Excel spreadsheet - personal tracker/data table, not a text source",
    ".xlsx": "Excel spreadsheet - personal tracker/template, not a text source",
    ".ppt": "Old PowerPoint (binary) - not extractable; a .pptx version exists or it is a template",
    ".zip": "Archive - contents already present unpacked in this folder, or holds only a program (.exe)",
    ".rar": "Archive - contains only a Windows .exe e-book reader (not safe/useful to run)",
    ".opf": "Calibre metadata file for the e-book beside it",
    ".partial": "Incomplete (0-byte) browser download - safe to delete",
}
WHY_FILE = {   # exact-filename reasons (lower-case)
    "ews.zip": "Emergency War Surgery (2004) chapter PDFs - the complete book is already in the library "
               "(medical-first-aid/emergency-war-surgery-third-us-revision-2004.md)",
    "herbs&essentialoilssuperbundle2017.zip": "Zip of the Herbs & Essential Oils bundle - its unpacked PDFs were moved",
    "herbsessentialoilssuperbundle2017.zip": "Second copy of the Herbs & Essential Oils bundle zip (misfiled in Sourdough) - its PDFs were moved",
    "gestcalculator.zip": "Contains only a Windows program (goat gestation calculator .exe) - not a document",
    "my enchanted acres sonrise.docx": "Personal record (goat pedigree/sales page) - was added to the library by mistake and returned here",
    "cookies.doc": "Word 97 file too small/damaged for text extraction - open it in Word; it is a recipe",
}
WHY_DECISION = {
    "not-relevant": "Not relevant to the survival/self-reliance library",
    "unreadable": "Could not extract usable text",
    "near-duplicate": "Near-duplicate - same text already in the library (or another copy here was moved)",
    "duplicate": "Exact duplicate",
    "skip": "Reviewed and skipped",
    "later": "Deferred",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def library_shas():
    out = {}
    for c in CATEGORIES:
        d = os.path.join(RESEARCH, c)
        if not os.path.isdir(d):
            continue
        for root, _, fs in os.walk(d):   # includes course folders
            for f in fs:
                if f.endswith(".md"):
                    head = open(os.path.join(root, f), encoding="utf-8", errors="replace").read(4000).partition("\n---\n")[0]
                    for s in re.findall(r"^(?:sha256|sha256_before_ocr|original_sha256): \"?([0-9a-f]{64})", head, re.M):
                        out[s] = os.path.relpath(os.path.join(root, f), RESEARCH)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--delete", action="store_true")
    a = ap.parse_args()
    rows = {r["file"]: r for r in csv.DictReader(open(a.report, encoding="utf-8-sig"))}
    folder = os.path.commonpath(list(rows))
    if len(rows) == 1 or os.path.isfile(folder) or os.path.splitext(folder)[1]:
        folder = os.path.dirname(folder)
    lib = library_shas()
    moved, kept = 0, []
    for r in rows.values():
        p = r["file"]
        if not os.path.exists(p) or not r.get("sha256"):
            continue
        if r["sha256"] in lib and sha(p) == r["sha256"]:
            if a.delete:
                os.chmod(p, 0o666); os.remove(p)
            moved += 1
    print(("Deleted" if a.delete else "Would delete"), moved, "originals now in the library")
    for root, _, fs in os.walk(folder):
        for f in fs:
            p = os.path.join(root, f)
            if f == "_NOT_MOVED_REASONS.csv" or (a.delete is False and rows.get(p, {}).get("sha256") in lib):
                continue
            ext = os.path.splitext(f)[1].lower()
            r = rows.get(p, {})
            dec = (r.get("decision") or "").strip().lower()
            size = os.path.getsize(p)
            if dec == "unreadable" and ext == ".pdf" and size and size % 128000 == 0:
                why = (f"Incomplete/truncated download (cut off at exactly {size // 1000:,} KB, will not open) - re-download "
                       "if wanted; check the library first, it may already hold this title")
            elif f.lower() in WHY_FILE:
                why = WHY_FILE[f.lower()]
            elif r.get("note"):
                why = r["note"]
            elif ext in MEDIA:
                why = (f"{MEDIA[ext].title()} lesson/recording - relevant topic, but the library holds text only; "
                       "could be transcribed (e.g. Whisper) and added later")
            elif dec in WHY_DECISION:
                why = WHY_DECISION[dec] + (": " + r["reason"] if r.get("reason") else "")
            elif ext in WHY_EXT:
                why = WHY_EXT[ext]
            else:
                why = r.get("reason") or f"File type {ext or '(none)'} not handled"
            if r.get("matches"):
                why += f" [matches: {r['matches']}]"
            kept.append({"folder": os.path.relpath(root, folder), "file": f, "size_mb": round(os.path.getsize(p) / 1e6, 2),
                         "decision": dec or ("media" if ext in MEDIA else "unsupported"),
                         "suggested_category": r.get("category", ""), "title": r.get("title", ""), "reason": why})
    kept.sort(key=lambda k: (k["folder"].lower(), k["file"].lower()))
    out = os.path.join(folder, "_NOT_MOVED_REASONS.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(kept[0].keys()))
        w.writeheader(); w.writerows(kept)
    print(len(kept), "files left ->", out)
    print(Counter(k["decision"] for k in kept))


if __name__ == "__main__":
    main()
