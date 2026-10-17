"""Add PDFs from their web addresses: a direct link to a .pdf, or an archive.org item page
(https://archive.org/details/<id> - the item's PDF is found automatically).

Each PDF is downloaded, checked against the library (same file or same text = skipped), read (scanned pages are
OCR'd) and added like 'Add a Document', but credited to its web address. Links already in the library are skipped.

Usage:
  69_add_pdf_link.py --file list.txt               lines: URL|CODE[|title][|publisher]   (CODE from common.CODES)
  69_add_pdf_link.py --category CODE URL [URL ...]
"""
import csv, datetime, importlib, json, os, re, sys, time
from urllib.parse import quote, urlparse
import requests
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, slugify

doc = importlib.import_module("65_add_document")
ing = doc.ing
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ResearchLibrary/1.0 (personal offline archive)"}
GOV = re.compile(r"\.(gov|mil)$", re.I)


def pdf_url(url):
    """The downloadable PDF behind a link (archive.org item pages -> the item's PDF file)."""
    m = re.match(r"https?://(www\.)?archive\.org/details/([^/?#]+)", url)
    if not m:
        return url
    meta = requests.get(f"https://archive.org/metadata/{m.group(2)}", headers=H, timeout=60).json()
    pdfs = [f for f in meta.get("files", []) if f.get("name", "").lower().endswith(".pdf")]
    if not pdfs:
        return None
    best = max(pdfs, key=lambda f: (f.get("source") == "original", int(f.get("size") or 0)))
    return f"https://archive.org/download/{m.group(2)}/{quote(best['name'])}"


def download(url, dest):
    for attempt in range(3):
        try:
            with requests.get(url, headers=H, timeout=120, stream=True) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            with open(dest, "rb") as f:
                return f.read(5) == b"%PDF-"
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
    return False


def add_pdfs(items, ocr=True):
    """items: dicts with url, category (folder) and optional title, publisher, license. Returns how many were added."""
    cf = os.path.join(RESEARCH, "CATALOG.json")
    have = {r.get("source_url") for r in json.load(open(cf, encoding="utf-8"))} if os.path.exists(cf) else set()
    stage = os.path.join(ing.W, "pdf_downloads")
    os.makedirs(stage, exist_ok=True)
    rows = []
    for it in items:
        url = it["url"]
        if url in have:
            print(f"already in library: {url}")
            continue
        try:
            src = pdf_url(url)
        except Exception as e:
            src = None
        if not src:
            print(f"no PDF found at: {url}")
            continue
        path = os.path.join(stage, (slugify(it.get("title") or urlparse(src).path.rsplit("/", 1)[-1]) or "document")[:90] + ".pdf")
        print(f"downloading {url}", flush=True)
        if not download(src, path):
            print(f"  could not download a PDF from {src}")
            continue
        row = doc.analyse(path, ocr)
        if row["decision"] in ("duplicate", "near-duplicate", "unreadable", "unsupported"):
            print(f"  skipped: {row['decision']} - {row['reason']}")
            os.remove(path)
            continue
        host = urlparse(url).netloc.lower().removeprefix("www.")
        row.update(decision="add", category=it["category"], title=(it.get("title") or row["title"]).strip(),
                   source_url=url, publisher=it.get("publisher") or host,
                   license=it.get("license") or ("Government publication - check the source page for terms" if GOV.search(host) else
                                                 "See the source page - personal offline copy"))
        rows.append(row)
        have.add(url)
    if not rows:
        print("Nothing to add.")
        return 0
    report = os.path.join(ing.W, "pdf_links_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv")
    with open(report, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nAdding {len(rows)} PDF(s) to the library...", flush=True)
    ing.apply(report, ocr)
    for r in rows:   # the library keeps its own copy
        if os.path.exists(r["file"]):
            os.remove(r["file"])
    return len(rows)


def main():
    args = sys.argv[1:]
    items = []
    if "--file" in args:
        for line in open(args[args.index("--file") + 1], encoding="utf-8"):
            if line.strip() and not line.startswith("#"):
                p = line.strip().split("|") + ["", ""]
                items.append({"url": p[0], "category": CODES[p[1]], "title": p[2], "publisher": p[3]})
    elif "--category" in args:
        i = args.index("--category")
        items = [{"url": u, "category": CODES[args[i + 1]]} for a, u in enumerate(args) if a not in (i, i + 1)]
    else:
        sys.exit(__doc__)
    add_pdfs(items)


if __name__ == "__main__":
    main()
