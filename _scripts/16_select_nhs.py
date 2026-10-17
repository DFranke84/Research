"""Select NHS medicine documents: one document per medicine that has its full set of sub-pages
(about / who can take / how to take / side effects / pregnancy / interactions / common questions).
Hub-only medicines (contents page but no sub-pages in this snapshot) are skipped - MedlinePlus covers them."""
import json, os, re, sys
from collections import defaultdict
from libzim.reader import Archive
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

z = Archive(os.path.join(RESEARCH, "_sources", "zim", "nhs.uk_en_medicines_2026-09b.zim"))
paths = []
for i in range(z.entry_count):
    e = z._get_entry_by_id(i)
    if not e.is_redirect and e.get_item().mimetype.startswith("text/html") and e.path.startswith("www.nhs.uk/medicines/"):
        paths.append(e.path)
pset = set(paths)
children = defaultdict(list)
for p in paths:
    parent = p.rstrip("/").rsplit("/", 1)[0] + "/"
    children[parent].append(p)
ORDER = ["about", "who-can", "how-and-when", "side-effects", "pregnancy", "taking", "common-questions"]


def rank(p):
    leaf = p.rstrip("/").rsplit("/", 1)[-1]
    return next((i for i, k in enumerate(ORDER) if leaf.startswith(k)), 99)


docs = []
for parent, kids in children.items():
    leaves = [k.rstrip("/").rsplit("/", 1)[-1] for k in kids]
    if not any(l.startswith(("about-", "side-effects")) for l in leaves) or parent not in pset:
        continue
    title = re.sub(r"-Brand names?:.*$", "", z.get_entry_by_path(parent).title.split(":")[0]).strip()
    title = re.sub(r"\s+-\s+NHS$", "", title)
    leaf = parent.rstrip("/").rsplit("/", 1)[-1]
    if re.search(r"-for-|-to-", leaf):          # e.g. amitriptyline-for-pain vs -for-depression
        title = leaf.replace("-", " ").capitalize()
    docs.append({"key": parent, "title": f"{title} (NHS medicine guide)", "slug": "nhs " + parent.rstrip("/").rsplit("/", 1)[-1],
                 "category": "medicine-pharmacology", "paths": sorted(kids, key=rank),
                 "source_url": "https://" + parent})
docs.sort(key=lambda d: d["key"])
json.dump(docs, open(os.path.join(RESEARCH, "_work", "zimsel_nhs.json"), "w", encoding="utf-8"), indent=0)
print(len(docs), "medicines;", sum(len(d["paths"]) for d in docs), "pages")
print([d["title"] for d in docs[:12]])
