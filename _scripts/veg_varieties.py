"""Variety tables from University of Idaho BUL 863 ('Short-Season, High-Altitude Gardening: Choosing and Growing Adapted
Vegetable Varieties') -> {crop table title: [(variety, days or relative maturity, notes)]}.

The PDF's text comes out one cell per line: a header block (VARIETY / DAYS TO HARVEST or RELATIVE MATURITY / NOTES), then
rows of  name / days / notes (notes may wrap).  A row starts where the NEXT line is a days value (or the name line ends with
one).  Used by 69_build_local_area.py for the vegetable pages' 'Varieties for a short season' lists.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

DOC = os.path.join(RESEARCH, "local-area", "references", "uidaho-bul863-short-season-varieties.md")
DAYS = re.compile(r"^(\d{2,3}(\s*[-–]\s*\d{2,3})?|Early|Medium|Late|Mid|Very early|Medium early|Medium late|Early-medium|Medium-late|Midseason)$", re.I)
NAME_DAYS = re.compile(r"^(.*[A-Za-z)])\s+(\d{2,3}(?:\s*[-–]\s*\d{2,3})?)$")
SUB = re.compile(r"^(Leaf|Head \(Iceberg\)|Head|Butterhead|Romaine|Cos|Hardneck|Softneck|Shelled|Edible Pod|Snow|Snap|Slicers|Picklers|"
                 r"Sweet|Hot|Bush|Pole|Wax|Summer|Winter|Summer Squash|Winter Squash|Muskmelon|Muskmelons|Watermelon|Watermelons|"
                 r"Cantaloupe|Russet|Fingerling|Cherry|Paste|Slicing|Specialty|Zucchini|Yellow|Scallop)$")
HEADER = {"DAYS TO", "VARIETY", "HARVEST", "NOTES", "RELATIVE", "MATURITY", "DAYS TO HARVEST", "RELATIVE MATURITY"}
JUNK = re.compile(r"^(\[Page \d+\]|\d+\s+SHORT-SEASON, HIGH-ALTITUDE GARDENING|CHOOSING AND GROWING ADAPTED VEGETABLE VARIETIES\s+\d+)$")


def tables(path=DOC):
    lines = [l.strip() for l in open(path, encoding="utf-8").read().split("## Full text", 1)[-1].splitlines()]
    lines = [l for l in lines if l and not JUNK.match(l)]
    out, i = {}, 0
    while i < len(lines):
        if lines[i] in ("DAYS TO", "RELATIVE") and i >= 1:
            title = lines[i - 1]
            j = i
            while j < len(lines) and lines[j] in HEADER:
                j += 1
            rows, cur, sub = [], None, ""
            while j < len(lines):
                l, nxt = lines[j], (lines[j + 1] if j + 1 < len(lines) else "")
                nxt2 = lines[j + 2] if j + 2 < len(lines) else ""
                if SUB.match(l) and not DAYS.match(nxt) and (DAYS.match(nxt2) or NAME_DAYS.match(nxt)):
                    sub = l; j += 1; continue   # a sub-type line ('Leaf', 'Butterhead', 'Bush') above its rows
                if l.startswith("Romaine "):   # the 'Romaine' sub-type label runs into the name in the PDF
                    sub, l = "Romaine", l[len("Romaine "):]
                m = NAME_DAYS.match(l)
                if DAYS.match(nxt) and not DAYS.match(l) and len(l) < 45:
                    cur = [l, nxt, f"{sub}: " if sub else ""]; rows.append(cur); j += 2; continue
                if m and not DAYS.match(nxt) and len(l) < 60 and (cur is None or cur[2].rstrip(": ") != sub):
                    cur = [m.group(1), m.group(2), f"{sub}: " if sub else ""]; rows.append(cur); j += 1; continue
                if cur is not None and len(l) < 60 and not l.endswith(".") and "—" not in l and l not in HEADER:
                    cur[2] = (cur[2] + " " + l).strip(); j += 1; continue
                break
            if rows:
                fix = lambda x: re.sub(r"\s+[A-Z][A-Z -]{8,}$", "", x.replace("jalape�o", "jalapeño").replace("�", "'").replace("’", "'")).strip()
                out[title] = [tuple(fix(c) for c in r) for r in rows]
            i = j
        else:
            i += 1
    return out


if __name__ == "__main__":
    for t, rows in tables().items():
        print(f"== {t} ({len(rows)})")
        for r in rows:
            print("   ", " | ".join(r))
