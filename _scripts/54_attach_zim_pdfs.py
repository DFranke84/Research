"""Attach the original PDFs from the zimgit Kiwix archives (_sources/zim/zimgit-*.zim) to library entries that were
exported from AIPortable as text only ("offline Kiwix ZIM 'Field Guide' collection").

Each entry records `original_library_title: "Food Preparation (10) (Field Guide)"`; the archives hold
`files/Food Preparation (10).pdf`. The same collection appears in several archives with possibly different numbering,
so every candidate PDF is verified by text overlap (shared 8-word shingles) before it is attached.

  _scripts\\.venv\\Scripts\\python _scripts\\54_attach_zim_pdfs.py [--apply]
"""
import argparse, glob, hashlib, importlib, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import pymupdf
from libzim.reader import Archive
from common import RESEARCH
from categories import CATEGORIES

ing = importlib.import_module("50_ingest_folder")
MIN_OVERLAP = 0.5


def zim_pdfs():
    out = []
    for p in sorted(glob.glob(os.path.join(RESEARCH, "_sources", "zim", "zimgit-*.zim"))):
        z = Archive(p)
        for i in range(z.all_entry_count):
            e = z._get_entry_by_id(i)
            if not e.is_redirect and e.path.lower().endswith(".pdf"):
                out.append((os.path.basename(p), e.path, z))
    return out


def pdf_text(data):
    doc = pymupdf.open(stream=data, filetype="pdf")
    return "\n".join(pg.get_text() for pg in doc)


def main():
    apply = argparse.ArgumentParser().parse_known_args()[0] and "--apply" in sys.argv
    pdfs = zim_pdfs()
    by_coll = {}
    for zname, path, z in pdfs:
        coll = re.sub(r"^files/| \(\d+\)\.pdf$", "", path)
        by_coll.setdefault(coll, []).append((zname, path, z))
    cache = {}
    done = missing = 0
    for c in CATEGORIES:
        d = os.path.join(RESEARCH, c)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".md"):
                continue
            md = os.path.join(d, f)
            txt = open(md, encoding="utf-8").read()
            head, sep, body = txt.partition("\n---\n")
            if re.search(r'^file: "', head, re.M) or "offline Kiwix ZIM" not in head:
                continue
            lt = re.search(r'^original_library_title: "(.*) \((\d+)\) \(Field Guide\)"$', head, re.M)
            if not lt:
                continue
            coll, num = lt.group(1), lt.group(2)
            fp = ing.fingerprint(body)
            if not fp:
                continue
            # exact-name candidates first, then the rest of the collection
            cands = sorted(by_coll.get(coll, []), key=lambda x: x[1] != f"files/{coll} ({num}).pdf")
            best = None
            for zname, path, z in cands:
                key = (zname, path)
                if key not in cache:
                    data = bytes(z.get_entry_by_path(path).get_item().content)
                    try:
                        cache[key] = (data, ing.fingerprint(pdf_text(data)))
                    except Exception:
                        cache[key] = (data, set())
                ov = len(fp & cache[key][1]) / len(fp)
                if not best or ov > best[0]:
                    best = (ov, zname, path)
                if ov >= 0.8:
                    break
            if not best or best[0] < MIN_OVERLAP:
                missing += 1
                print(f"  NO MATCH  {c}/{f}  ({coll} ({num}); best {best[0]:.0%} {best[2] if best else ''})" if best else f"  NO PDF    {c}/{f}")
                continue
            ov, zname, path = best
            slug = f[:-3]
            print(f"  {ov:4.0%}  {c}/{f}  <-  {zname}:{path}")
            done += 1
            if not apply:
                continue
            data = cache[(zname, path)][0]
            dst = os.path.join(d, slug + ".pdf")
            open(dst, "wb").write(data)
            s = hashlib.sha256(data).hexdigest()
            head = head.replace("\ncategory:", f'\nfile: "{slug}.pdf"\noriginal_sha256: "{s}"\ncategory:', 1)
            head = head.replace("Exact ZIM file not recorded.", f"Original PDF recovered from {zname} ({path}).")
            body = re.sub(r"^(# .*\n)", lambda m: m.group(1) + f"\n**Original file:** [{slug}.pdf]({slug}.pdf)  \n", body, count=1, flags=re.M)
            open(md, "w", encoding="utf-8").write(head + sep + body)
    print(f"{done} PDFs {'attached' if apply else 'would be attached'}, {missing} entries without a verified PDF")


if __name__ == "__main__":
    main()
