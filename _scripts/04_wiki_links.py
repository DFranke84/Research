"""Collect outgoing article links from the kept Wikipedia set and count, for
each target, how many kept articles link to it (in-degree). Output:
_work/wiki_link_candidates.json  [{target, indeg}] sorted desc."""
import collections, glob, json, os, re, sys
from urllib.parse import unquote
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(__file__))
from zimlib import zim

W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work")
R = json.load(open(os.path.join(W, "wiki_review.json"), encoding="utf-8"))
keep = {}
for f in sorted(glob.glob(os.path.join(W, "wiki_keep_*.txt"))):
    for tok in open(f).read().split():
        i, c = tok.split(":")
        keep[int(i)] = c
paths = [R[i]["path"] for i in keep]
z = zim()
indeg = collections.Counter()
for n, p in enumerate(paths):
    html = bytes(z.get_entry_by_path(p).get_item().content).decode("utf-8", "replace")
    body = BeautifulSoup(html, "lxml").find(id="mw-content-text")
    if body is None:
        continue
    for t in body.select(".navbox, .reflist, .references, .hatnote, .sidebar, .metadata"):
        t.decompose()
    seen = set()
    for a in body.find_all("a", href=True):
        h = a["href"]
        if h.startswith(("http", "#", "./_", "_")) or ":" in h.split("#")[0]:
            continue
        t = unquote(h.split("#")[0]).lstrip("./")
        if t and t not in seen:
            seen.add(t)
    for t in seen:
        indeg[t] += 1
    if n % 100 == 0:
        print(n, flush=True)
kept_paths = set(paths)
out = [{"target": t, "indeg": c} for t, c in indeg.most_common() if t not in kept_paths]
json.dump(out, open(os.path.join(W, "wiki_link_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("candidates", len(out), "indeg>=2", sum(1 for o in out if o["indeg"] >= 2), "indeg>=3", sum(1 for o in out if o["indeg"] >= 3))
