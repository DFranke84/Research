"""Give every recipe a rough "date added" (date_added + date_source in its front matter), as close as we can get to when
it was originally saved - not when it was put into the library:

  bookmarks      the date the link was bookmarked in Edge (live Bookmarks file), else the ADD_DATE in the old favorites
                 export; recipes added by link with 63_add_recipe.py and not bookmarked -> the day they were added
  email recipes  the date the email was received
  documents, Homesteading files, recipe files with an original beside them -> the original file's date
  Facebook saved recipes, the Cooking School -> no date (unknown; never invented)
The bookmark fetch log gets the dates too, and the bookmark folder pages show them. Rerunnable.

  _scripts\\.venv\\Scripts\\python _scripts\\66_add_dates.py [--dry-run]
"""
import collections, datetime, glob, html, importlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

m = importlib.import_module("63_add_recipe")
bm = m.bm
EDGE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data", "Default", "Bookmarks")
OLD_FAV = os.path.join(os.path.expanduser("~"), "Downloads", "favorites_5_26_23.html")
LIBRARY_BUILT = datetime.date(2026, 9, 28)   # file dates from this day on are copies made by the library, not originals
DRY = "--dry-run" in sys.argv


def edge_dates():
    out = {}
    try:
        b = json.load(open(EDGE, encoding="utf-8"))
    except Exception:
        return out
    def walk(n):
        if n.get("type") == "url" and n.get("date_added", "0") != "0":
            d = (datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=int(n["date_added"]))).date()
            k = m.norm(html.unescape(n["url"]))
            out[k] = min(out.get(k, d), d)
        for c in n.get("children", []):
            walk(c)
    for r in b.get("roots", {}).values():
        if isinstance(r, dict):
            walk(r)
    return out


def old_fav_dates():
    out = {}
    if os.path.exists(OLD_FAV):
        for u, ts in re.findall(r'HREF="([^"]+)"[^>]*ADD_DATE="(\d+)"', open(OLD_FAV, encoding="utf-8", errors="replace").read()):
            d = datetime.date.fromtimestamp(int(ts))
            k = m.norm(html.unescape(u))
            out[k] = min(out.get(k, d), d)
    return out


def file_date(path):
    try:
        d = datetime.date.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return None
    return d if d < LIBRARY_BUILT else None


FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def set_fm(path, date, source):
    txt = open(path, encoding="utf-8").read()
    mm = FM.match(txt)
    if not mm:
        return False
    body = [l for l in mm.group(1).split("\n") if not l.startswith(("date_added:", "date_source:"))]
    if date:
        body += [f'date_added: "{date}"', f'date_source: "{source}"']
    new = "---\n" + "\n".join(body) + "\n---\n" + txt[mm.end():]
    if new != txt and not DRY:
        open(path, "w", encoding="utf-8").write(new)
    return new != txt


def main():
    edge, old = edge_dates(), old_fav_dates()
    log = json.load(open(bm.LOG, encoding="utf-8"))
    by_md = {(e.get("folder"), e.get("md")): (u, e) for u, e in log.items() if e.get("md")}
    stats, changed = collections.Counter(), 0
    for f in glob.glob(os.path.join(RESEARCH, "recipes", "**", "*.md"), recursive=True):
        rel = os.path.relpath(f, RESEARCH).replace(os.sep, "/")
        if "/wardee-traditional-cooking-school" in "/" + rel:
            continue
        txt = open(f, encoding="utf-8").read(3000)
        if re.search(r'^source_type: "(collection|bookmark-collection|image-collection)"', txt, re.M):
            continue   # list pages
        g = lambda k: (re.search(rf'^{k}: "?([^"\n]*)"?$', txt, re.M) or [None, None])[1]
        date = source = None
        if g("received") and g("received") != "null":
            date, source = g("received")[:10], "email received"
        elif re.search(r"Recipe link in an email \((\d{4}-\d{2}-\d{2})\)", g("provenance") or ""):   # recipes linked from an email
            date, source = re.search(r"\((\d{4}-\d{2}-\d{2})\)", g("provenance"))[1], "email received"
        elif "/bookmarks/" in rel:
            folder = rel.split("/")[3]
            u, e = by_md.get((folder, os.path.basename(f)), (g("source_url"), {}))
            k = m.norm(html.unescape(u or ""))
            if k in edge:
                date, source = edge[k].isoformat(), "bookmarked in Edge"
            elif k in old:
                date, source = old[k].isoformat(), "bookmarked (favorites export)"
            elif e.get("added"):
                date, source = e["added"], "added by link"
            if e and date:
                e["date_added"], e["date_source"] = date, source
        elif "/facebook-saved/" in rel:
            pass   # the saved-items page had no dates
        else:
            orig = g("file")
            d = file_date(os.path.join(os.path.dirname(f), orig)) if orig and orig != "null" else None
            if d:
                date, source = d.isoformat(), "original file date"
        stats[(rel.split("/")[2] if rel.startswith("recipes/personal-recipe-collection/") else "recipes (files)", source or "unknown")] += 1
        changed += set_fm(f, date, source)
    for (sec, src), n in sorted(stats.items()):
        print(f"{n:5}  {sec:28} {src}")
    print(f"{changed} files {'would change' if DRY else 'updated'}")
    if not DRY:
        json.dump(log, open(bm.LOG, "w", encoding="utf-8"), indent=1)
        m.refresh_pages(log, {e.get("folder") for e in log.values() if e.get("folder")})
        import subprocess
        for script in ("20_catalog.py", "21_readme.py"):
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), script)], capture_output=True)


if __name__ == "__main__":
    main()
