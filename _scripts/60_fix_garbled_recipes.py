"""Re-render saved recipes whose text still shows mis-decoded characters ("â€“", "Â¼") - from the page cache, no downloads.

  _scripts\\.venv\\Scripts\\python _scripts\\60_fix_garbled_recipes.py
"""
import importlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import recipe_clean as rc

bm = importlib.import_module("58_fetch_bookmarks")
log = json.load(open(bm.LOG, encoding="utf-8"))
fixed = 0
for url, e in log.items():
    if e.get("status") != "ok" or e.get("type") != "page":
        continue
    d = os.path.join(bm.OUT, e["folder"])
    mdp = os.path.join(d, e["md"])
    if not os.path.isfile(mdp) or not rc.MOJIBAKE.search(open(mdp, encoding="utf-8").read()):
        continue
    slug = e["md"][:-3]
    r = bm.do_page(rc.clean(e.get("title") or slug), url, d, slug, {"category": "recipes", "collection": "personal-recipe-collection",
                                                                     "provenance": f"Browser bookmark, fetched {bm.TODAY}",
                                                                     "license": "Copyright of the original site - personal offline copy",
                                                                     "compiled": bm.TODAY})
    if r.get("status") == "ok":
        r["folder"] = e["folder"]; log[url] = r; fixed += 1
        print("  fixed", e["md"], flush=True)
json.dump(log, open(bm.LOG, "w", encoding="utf-8"), indent=1)
print(fixed, "recipes re-rendered")
