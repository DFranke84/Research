"""Write LIBRARY.md - a summary of what is in THIS library (counts per category and per source) - from
CATALOG.json. Run after 20_catalog.py; Library Manager does both after every add, move or delete.

LIBRARY.md describes your own library, so it stays out of git; README.md is the hand-written guide."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY
from categories import CATEGORIES

cf = os.path.join(RESEARCH, "CATALOG.json")
R = json.load(open(cf, encoding="utf-8")) if os.path.exists(cf) else []
cc = collections.Counter(r["category"] for r in R)
pub = collections.Counter((r.get("publisher") or "Unknown").split(" - ")[0].split(" (")[0] for r in R)
imgs = sum(r.get("images") or 0 for r in R)
words = sum(r.get("words") or 0 for r in R)
n_pdf = sum(1 for r in R if r.get("source_type") == "pdf")
nice = lambda c: c.replace("-", " ").title().replace("Cbrn", "CBRN")

cat_rows = "\n".join(f"| {nice(c)} | {cc[c]:,} | {d} |" for c, d in sorted(CATEGORIES.items(), key=lambda x: nice(x[0])))
src_rows = "\n".join(f"| {p} | {n:,} |" for p, n in pub.most_common(25))
more = len(pub) - 25

text = f"""# This library

Written automatically from `CATALOG.json` on {TODAY} - it changes whenever you add, move or delete something.
How to set up and use the library: [README.md](README.md) and [README - Library Manager.md](README%20-%20Library%20Manager.md).

- **{len(R):,} items** (about {words / 1e6:.1f} million words)
- **{n_pdf:,} PDFs** kept as the original file, each with a searchable text copy beside it
- **{imgs:,} pictures** stored beside their pages

`CATALOG.csv` (opens in Excel) and `CATALOG.json` list every item: title, category, source, web address, license,
original file, pictures and words.

## Categories

| Category | Items | Covers |
|---|---:|---|
{cat_rows}

## Where the items come from

| Source | Items |
|---|---:|
{src_rows}
""" + (f"| *{more} more sources* | |\n" if more > 0 else "") + """
## Licenses

Every page records its license in its front matter (the `license:` line at the top of the `.md` file). Most free
sources are CC BY-SA (Wikipedia, Wikibooks, Appropedia, energypedia, Stack Exchange) or public domain (US government
works); iFixit is CC BY-NC-SA (non-commercial). Pages saved from other websites and your own documents are for
personal offline use - check the source before sharing them.
"""
open(os.path.join(RESEARCH, "LIBRARY.md"), "w", encoding="utf-8").write(text)
print("LIBRARY.md written:", len(R), "items")
