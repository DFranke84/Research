"""Remove Field Guide pages whose species already has a Local Area page (user rule 2026-10-11: a species in Local Area
must NOT also be in the Field Guides).

  72_remove_field_guide_twins.py --check     list what would go
  72_remove_field_guide_twins.py             remove them (Recycle Bin, via library_delete), log to _work/removed_duplicates.txt

Match = the same plain species name on both pages (two words, case-insensitive); subspecies, varieties, cultivars
('Malus domestica Honeycrisp') and complexes never match. Afterwards rebuild the Local Area pages that linked to them (71 / 69) and run 20_catalog + 21_readme.
"""
import glob, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
import library_delete as LD

SCI = re.compile(r'^scientific_name: "(.*)"', re.M)


def species(sci):
    """'genus species' for a plain species name; '' for subspecies, varieties, cultivars, hybrids and complexes."""
    w = (sci or "").split()
    return " ".join(w).lower() if len(w) == 2 and w[0][:1].isupper() and re.fullmatch(r"[a-z-]+", w[1]) else ""


def local_species():
    out = {}
    for f in glob.glob(os.path.join(RESEARCH, "local-area", "**", "*.md"), recursive=True):
        m = SCI.search(open(f, encoding="utf-8").read(3000))
        if m and species(m.group(1)):
            out.setdefault(species(m.group(1)), f)
    return out


def twins():
    loc = local_species()
    res = []
    for f in sorted(glob.glob(os.path.join(RESEARCH, "field-guide-*", "*.md"))):
        m = SCI.search(open(f, encoding="utf-8").read(3000))
        if m and species(m.group(1)) in loc:
            res.append((f, loc[species(m.group(1))]))
    return res


def main():
    check = "--check" in sys.argv
    found = twins()
    log = []
    for f, lf in found:
        r = LD.rel(f)
        print(("would remove " if check else "removing ") + r + "   (in Local Area: " + LD.rel(lf) + ")", flush=True)
        if check:
            continue
        errs = LD.execute(LD.plan({"file": r, "path": r}))
        for e in errs:
            print("  !", e)
        log.append(f"{r.replace('/', os.sep)}\tsame species is in Local Area ({LD.rel(lf)})")
    print(len(found), "field guide pages" + (" would go" if check else " removed"))
    if log:
        with open(os.path.join(RESEARCH, "_work", "removed_duplicates.txt"), "a", encoding="utf-8") as fh:
            fh.write("\n".join(log) + "\n")
        for s in ("20_catalog.py", "21_readme.py"):
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), s)])


if __name__ == "__main__":
    main()
