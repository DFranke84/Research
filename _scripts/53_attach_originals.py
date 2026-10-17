"""Attach original PDFs to library entries that only had extracted text (e.g. AIPortable/Kiwix exports), so every
.md can be opened next to its PDF in a viewer. Also swaps the mislabelled Foxfire 2/3 entries.

  _scripts\\.venv\\Scripts\\python _scripts\\53_attach_originals.py [--apply]

For each (source PDF -> library .md): copies the PDF to <category>/<slug>.pdf, adds `file:` and `original_sha256:`
to the front matter plus an "Original file" link, then (with --apply) deletes the source after verifying the copy.
"""
import argparse, hashlib, json, os, re, shutil, sys, zipfile, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

H = r"E:\Homesteading"
ATTACH = [   # (source file, library .md relative to E:\Research)
    (H + r"\Medical -Survival\AM Final 2.pdf", r"medical-first-aid\survival-and-austere-medicine-an-introduction-2nd-edition.md"),
    (H + r"\Medical -Survival\Eliot Wigginton - The Foxfire Book - Volume 01 (pdf).pdf", r"tools-crafts-skills\the-foxfire-book-volume-1.md"),
    (H + r"\Medical -Survival\Eliot Wigginton - The Foxfire Book - Volume 02 (pdf).pdf", r"tools-crafts-skills\foxfire-2.md"),  # after swap
    (H + r"\Medical -Survival\Eliot Wigginton - The Foxfire Book - Volume 03 (pdf).pdf", r"tools-crafts-skills\foxfire-3.md"),  # after swap
    (H + r"\Medical -Survival\Good\Midwives_A Book For.pdf", r"medical-conditions\a-book-for-midwives-care-for-pregnancy-birth-and-womens-health.md"),
    (H + r"\Medical -Survival\Good\Where There Is No Doctor_2011_full.pdf", r"medical-first-aid\where-there-is-no-doctor-2011.md"),
    (H + r"\Medical -Survival\How_To_Make_Soap-Potash_2008.pdf", r"sanitation-hygiene\soapmaking-practical-action.md"),
    (H + r"\Medical -Survival\Preservation_of_Fish_and_Meat_2004.pdf", r"food-storage-preservation\agrodok-12-preservation-of-fish-and-meat.md"),
    (H + r"\Medical -Survival\EWS.ZIP", r"medical-first-aid\emergency-war-surgery-third-us-revision-2004.md"),   # chapters merged
]
EWS_ORDER = (["TableOfContents"] + [f"Chp{i}" for i in range(1, 35)] + ["Appendix1", "Appendix2", "Appendix3", "Envoi", "Index"])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def merge_ews(zpath, out):
    import pymupdf
    z = zipfile.ZipFile(zpath)
    names = {n: n for n in z.namelist() if n.lower().endswith(".pdf")}
    doc = pymupdf.open()
    toc = []
    for key in EWS_ORDER:
        n = next((n for n in names if re.match(re.escape(key) + r"(?![0-9])", n)), None)
        if not n:
            continue
        part = pymupdf.open(stream=z.read(n), filetype="pdf")
        toc.append([1, os.path.splitext(n)[0], doc.page_count + 1])
        doc.insert_pdf(part)
    doc.set_toc(toc)
    doc.save(out, garbage=3, deflate=True)
    return doc.page_count, len(toc)


def swap_foxfire(apply):
    """Library foxfire-2.md holds Foxfire 3's text and vice versa: swap the files' names, titles and slug owners."""
    d = os.path.join(RESEARCH, "tools-crafts-skills")
    a, b = os.path.join(d, "foxfire-2.md"), os.path.join(d, "foxfire-3.md")
    ta, tb = open(a, encoding="utf-8").read(), open(b, encoding="utf-8").read()
    if "banjo" not in ta.lower()[:10**7] or ta.lower().count("banjo") < tb.lower().count("banjo"):
        print("Foxfire already swapped (foxfire-2.md does not hold the banjo/dulcimer volume)"); return
    print("swap: foxfire-2.md <-> foxfire-3.md (text of Foxfire 3 was titled Foxfire 2)")
    if not apply:
        return
    fix = lambda t, frm, to: t.replace(f'title: "Foxfire {frm}"', f'title: "Foxfire {to}"').replace(f"# Foxfire {frm}\n", f"# Foxfire {to}\n", 1)
    open(a, "w", encoding="utf-8").write(fix(tb, 3, 2))
    open(b, "w", encoding="utf-8").write(fix(ta, 2, 3))
    rp = os.path.join(RESEARCH, "_work", "slug_registry.json")
    reg = json.load(open(rp, encoding="utf-8"))
    reg["foxfire-2"], reg["foxfire-3"] = reg.get("foxfire-3"), reg.get("foxfire-2")
    json.dump(reg, open(rp, "w", encoding="utf-8"), indent=0, ensure_ascii=False)


def attach(src, md_rel, apply):
    md = os.path.join(RESEARCH, md_rel)
    txt = open(md, encoding="utf-8").read()
    head, sep, body = txt.partition("\n---\n")
    if re.search(r'^file: "', head, re.M):
        print("  already has an original file:", md_rel); return
    slug = os.path.splitext(os.path.basename(md))[0]
    dst = os.path.join(os.path.dirname(md), slug + ".pdf")
    print(f"  {os.path.basename(src)}  ->  {os.path.relpath(dst, RESEARCH)}")
    if not apply:
        return
    if src.lower().endswith(".zip"):
        pages, parts = merge_ews(src, dst)
        print(f"    merged {parts} chapter PDFs, {pages} pages")
        s = sha(dst)
    else:
        s = sha(src)
        shutil.copy2(src, dst)
        if sha(dst) != s:
            raise RuntimeError("copy verification failed: " + dst)
    os.chmod(dst, 0o666)
    head = head.replace("\ncategory:", f'\nfile: "{slug}.pdf"\noriginal_sha256: "{s}"\ncategory:', 1)
    body = re.sub(r"^(# .*\n)", lambda m: m.group(1) + f"\n**Original file:** [{slug}.pdf]({slug}.pdf)  \n", body, count=1, flags=re.M)
    open(md, "w", encoding="utf-8").write(head + sep + body)
    os.chmod(src, 0o666); os.remove(src)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    apply = ap.parse_args().apply
    swap_foxfire(apply)
    for src, md in ATTACH:
        if os.path.exists(src):
            attach(src, md, apply)
        else:
            print("  missing source:", src)
