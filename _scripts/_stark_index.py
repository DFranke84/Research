"""Stark Bro's product index -> _work/local_area/stark_products.json {path: name}."""
import json, os, re, sys, html
sys.path.insert(0, os.path.dirname(__file__))
import local_area as L
home = L.fetch(L.STARK + "/")
cats = sorted(set(re.findall(r'href="/products/([a-z0-9-]+/[a-z0-9-]+)"', home)))
out = {}
for c in cats:
    for page in range(1, 15):
        h = L.fetch(f"{L.STARK}/products/{c}" + (f"?page={page}" if page > 1 else ""))
        found = re.findall(r'href="/products/(' + re.escape(c) + r'/[a-z0-9-]+)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{3,80})<', h)
        new = 0
        for p, name in found:
            if p not in out:
                out[p] = html.unescape(name).strip(); new += 1
        if not new:
            break
    print(c, len(out), flush=True)
json.dump(out, open(os.path.join(L.W, "stark_products.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
