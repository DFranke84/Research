"""Copy every kept PDF (or HTML) into its category folder with a descriptive
filename, and write a same-named .md sidecar: YAML front-matter (title,
category, source, license, provenance) + the full extracted text.

Inputs: _work/pdf_unique.json, _work/pdf_decisions_*.txt, _work/pdf_title_overrides.txt
"""
import glob, json, os, re, shutil, sys
import pymupdf
from markdownify import markdownify
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, SlugRegistry

W = os.path.join(RESEARCH, "_work")
COPYRIGHT_RE = re.compile(r"(copyright\s*©|©\s*(19|20)\d\d|all rights reserved|copyright\s+(19|20)\d\d)", re.I)
GOV_RE = re.compile(r"\b(FM|TM|ATP|TC|DA PAM|AFH|MCRP|NAVPERS|NEETS|DTIC|CPG|EM-1)\b|Navy|Army|Department of|National Park|USDA|CDC|FEMA|Civil Defense", re.I)


def load_decisions():
    dec = {}
    for f in sorted(glob.glob(os.path.join(W, "pdf_decisions_*.txt"))):
        for l in open(f, encoding="utf-8"):
            if l.startswith("#") or not l.strip():
                continue
            p = l.strip().split("|")
            dec[p[0]] = p[1:]
    return dec


def load_titles():
    t = {}
    for l in open(os.path.join(W, "pdf_title_overrides.txt"), encoding="utf-8"):
        if l.startswith("#") or "|" not in l:
            continue
        k, v = l.rstrip("\n").split("|", 1)
        t[k] = v
    return t


def clean_title(u, overrides):
    if u["key"] in overrides:
        return overrides[u["key"]], None
    t = u["title"].split(" | FAQ")[0].strip()
    ident = None
    m = re.match(r"^(DTIC [A-Z0-9]+|ERIC E[DJ]\d+|CIA Reading Room [\w-]+):\s*(.+)$", t)
    if m:
        ident, t = m.group(1), m.group(2).rstrip(".")
    return t, ident


def publisher_for(title, ident, url):
    s = f"{title} {ident or ''}"
    if ident and ident.startswith("DTIC"):
        return "Defense Technical Information Center (DTIC)"
    if ident and ident.startswith("ERIC"):
        return "ERIC - US Department of Education (document as submitted by its originating agency)"
    if ident and ident.startswith("CIA"):
        return "CIA FOIA Electronic Reading Room"
    if re.match(r"^(FM|TM|ATP|TC|DA Pam|SH)\b", title, re.I):
        return "US Department of the Army"
    if re.search(r"NAVPERS|Navy Electricity|US Navy|U\.S\. Navy|Naval", s):
        return "US Navy"
    if s.startswith("MCRP"):
        return "US Marine Corps"
    if s.startswith("AFH"):
        return "US Air Force"
    if s.startswith("B-G"):
        return "Canadian Department of National Defence"
    if url:
        return re.sub(r"https?://(www\.)?([^/]+)/.*", r"\2", url)
    return None


def canonical_urls(ident, u):
    urls = [x for x in [u.get("source_url")] + u.get("alt_urls", []) if x]
    if ident:
        m = re.match(r"DTIC ([A-Z0-9]+)", ident)
        if m:
            urls.append(f"https://apps.dtic.mil/sti/citations/{m.group(1)}")
        m = re.match(r"ERIC (E[DJ]\d+)", ident)
        if m:
            urls.append(f"https://eric.ed.gov/?id={m.group(1)}")
    if u.get("ia_identifier"):
        urls.append(f"https://archive.org/details/{u['ia_identifier']}")
    return list(dict.fromkeys(urls))


def extract(path):
    if path.lower().endswith(".html"):
        html = open(path, encoding="utf-8", errors="replace").read()
        return markdownify(html, heading_style="ATX"), 0, True
    doc = pymupdf.open(path)
    parts = []
    for i, page in enumerate(doc):
        t = page.get_text().strip()
        if t:
            parts.append(f"\n\n[Page {i + 1}]\n\n{t}")
    text = "".join(parts).strip()
    return text, doc.page_count, len(text) > 200 * max(1, min(doc.page_count, 5)) / 5


def main():
    dec, overrides = load_decisions(), load_titles()
    reg = SlugRegistry()
    units = json.load(open(os.path.join(W, "pdf_unique.json"), encoding="utf-8"))
    built = []
    for u in units:
        d = dec.get(u["key"])
        if not d or d[0] in ("X", "CHECK"):
            continue
        category = CODES[d[0]]
        title, ident = clean_title(u, overrides)
        slug = reg.claim(d[1], "pdf:" + u["sha256"])
        src = next((p for p in u["paths"] if p.lower().endswith((".pdf", ".html"))), u["paths"][0])
        ext = os.path.splitext(src)[1].lower()
        dest_dir = cat_dir(category)
        dest_file = os.path.join(dest_dir, slug + ext)
        md_file = os.path.join(dest_dir, slug + ".md")
        if not os.path.exists(dest_file) or os.path.getsize(dest_file) != u["size"]:
            shutil.copy2(src, dest_file)
        text, pages, has_text = extract(src)
        head = text[:8000]
        urls = canonical_urls(ident, u)
        publisher = publisher_for(title, ident, u.get("source_url"))
        lic = u.get("license")
        license_note = None
        if COPYRIGHT_RE.search(head) and not GOV_RE.search(title + " " + (publisher or "")):
            license_note = (f"Copyright notice found in the document; the original library labelled it "
                            f"'{lic}', which appears inaccurate. Treat as all-rights-reserved (personal reference copy).")
            lic = "Copyrighted - all rights reserved by author/publisher"
        elif lic in (None, "mixed"):
            license_note = "License not recorded by the original library; verify before redistribution."
            lic = lic or "unknown"
        provenance = ("AIPortable library PDF " + ", ".join(sorted({os.path.relpath(p, r'E:\AIPortable') for p in u['paths']})))
        meta = {
            "title": title,
            "category": category,
            "source_type": "document" if ext == ".html" else "pdf",
            "file": slug + ext,
            "publisher": publisher,
            "document_id": ident,
            "source_url": urls[0] if urls else None,
            "additional_source_urls": urls[1:],
            "license": lic,
            "license_note": license_note,
            "pages": pages or None,
            "text_layer": bool(has_text),
            "sha256": u["sha256"],
            "original_library_ids": u.get("library_ids", []),
            "original_library_title": u["title"].split(" | FAQ")[0],
            "provenance": provenance,
            "notes": u.get("notes") or [],
            "compiled": TODAY,
        }
        body = [front_matter(meta), f"# {title}\n"]
        body.append(f"**Source:** {publisher or 'unknown publisher'}"
                    + (f" - <{urls[0]}>" if urls else " - no online source recorded (local copy from the original library)") + "  ")
        body.append(f"**License:** {lic}  ")
        body.append(f"**Original file:** [{slug + ext}]({slug + ext})\n")
        if has_text:
            body.append("## Full text (extracted from the original file)\n")
            body.append(text)
        else:
            body.append("## Full text\n")
            body.append("_This PDF is a scanned image with no text layer; OCR is required before its text can be indexed._"
                        + ("\n\n" + text if text else ""))
        open(md_file, "w", encoding="utf-8").write("\n".join(body) + "\n")
        built.append({"key": u["key"], "category": category, "slug": slug, "title": title, "has_text": has_text})
        print(category, slug, flush=True)
    reg.save()
    json.dump(built, open(os.path.join(W, "built_pdfs.json"), "w", encoding="utf-8"), indent=1)
    print("built", len(built))


main()
