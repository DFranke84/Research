"""Add one or more recipes to the personal recipe collection straight from their web addresses.

Each URL gets the same treatment as the browser bookmarks (58_fetch_bookmarks.py): only the recipe (title, photo,
ingredients, steps) as .md + a clean one-page PDF + any matching recipe video; video links (YouTube, Facebook, TikTok, ...)
are saved as the video. Dead pages fall back to the Internet Archive.
The recipe is then sorted into a bookmark folder:
  air-fryer     - air fryer recipes
  instant-pot   - Instant Pot / pressure cooker recipes
  food-recipes  - everything else
(override with --folder air-fryer|instant-pot|food-recipes). The folder's list page, the collection page and the
catalog are refreshed afterwards.

  _scripts\\.venv\\Scripts\\python _scripts\\63_add_recipe.py <url> [<url> ...] [--folder <folder>] [--force]
  --force   re-fetch / add a recipe even though it is already in the collection
Duplicates are checked before anything is added: the same address (tracking codes, www., http/https and trailing
slashes ignored) in the bookmark folders or anywhere else in the library, and - after fetching - the same recipe
name from the same site under a different address.
"""
import importlib, json, os, re, subprocess, sys
from urllib.parse import urlparse
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, slugify

bm = importlib.import_module("58_fetch_bookmarks")
FOLDERS = ("air-fryer", "instant-pot", "food-recipes")
AIR = re.compile(r"\bair[\s-]?fr(y|ied|ier|yer|ying)", re.I)
PRESSURE = re.compile(r"\binstant[\s-]?pot\b|\bpressure[\s-]?cook|\binstapot\b|\bninja foodi\b|\bmulti[\s-]?cooker\b", re.I)


def categorize(md_text):
    """Folder from what the recipe is cooked in: the title counts most, then the ingredients/steps."""
    title = (re.search(r"^# (.+)$", md_text, re.M) or [None, ""])[1]
    for text in (title, md_text):
        a, p = len(AIR.findall(text)), len(PRESSURE.findall(text))
        if a or p:
            return "air-fryer" if a >= p else "instant-pot"
    return "food-recipes"


TRACKING = re.compile(r"(fbclid|utm_[a-z]+|mibextid|igsh|gclid|ref|epik|crlt\.pid)=")


def norm(url):
    """One key per recipe address: no tracking codes, http/https, www., trailing slash, case or /2017/01/31/ date folders."""
    u = urlparse(url or "")
    q = "&".join(x for x in u.query.split("&") if x and not TRACKING.match(x))
    path = re.sub(r"^/\d{4}/\d{2}/\d{2}/", "/", u.path.rstrip("/").lower() + "/")
    return u.netloc.lower().removeprefix("www.") + path + ("?" + q if q else "")


def library_copy(url):
    """A file anywhere else in the library (email/Facebook recipes, other categories) saved from this address."""
    cat = os.path.join(RESEARCH, "CATALOG.json")
    if not os.path.exists(cat):
        return None
    key = norm(url)
    return next((r["file"] for r in json.load(open(cat, encoding="utf-8"))
                 if r.get("source_url") and "/bookmarks/" not in r["file"] and norm(r["source_url"]) == key), None)


def same_recipe(log, title, url):
    """Saved recipes with the same name: (same site -> the same recipe under another address, other sites -> just a namesake)."""
    t, site = (title or "").lower().strip(), urlparse(url).netloc.lower().removeprefix("www.")
    hits = [(u, e) for u, e in log.items() if e.get("status") == "ok" and (e.get("title") or "").lower().strip() == t and t]
    return ([h for h in hits if urlparse(h[0]).netloc.lower().removeprefix("www.") == site],
            [h for h in hits if urlparse(h[0]).netloc.lower().removeprefix("www.") != site])


def folder_name(fslug):
    """The browser folder name the list page was built under ("Food Recipes - Air Fryer")."""
    page = os.path.join(bm.OUT, fslug, fslug + ".md")
    m = re.search(r"^# Bookmarked recipes: (.+)$", open(page, encoding="utf-8").read(), re.M) if os.path.exists(page) else None
    return m.group(1).strip() if m else fslug.replace("-", " ").title()


def refresh_pages(log, folders):
    for fslug in folders:
        links = [(None, e.get("title"), url, None) for url, e in log.items() if e.get("folder") == fslug]
        bm.folder_page(folder_name(fslug), fslug, links, log)
    # the collection page's "N of M saved offline" line for each folder
    coll = os.path.join(RESEARCH, "recipes", "personal-recipe-collection.md")
    txt = open(coll, encoding="utf-8").read()
    for fslug in folders:
        n_ok = sum(1 for e in log.values() if e.get("folder") == fslug and e.get("status") == "ok")
        n_all = sum(1 for e in log.values() if e.get("folder") == fslug)
        txt = re.sub(rf"(\(personal-recipe-collection/bookmarks/{fslug}/{fslug}\.md\)) - \d+ of \d+ saved offline",
                     rf"\1 - {n_ok} of {n_all} saved offline", txt)
    open(coll, "w", encoding="utf-8").write(txt)


def move(entry, src, dst):
    """Move a saved recipe's files (md, pdf, photo, video) into another folder."""
    slug = os.path.splitext(entry["md"])[0]
    for f in os.listdir(os.path.join(bm.OUT, src)):
        if f.startswith(slug + ".") or f.startswith(slug + "-video."):
            os.replace(os.path.join(bm.OUT, src, f), os.path.join(bm.OUT, dst, f))
    entry["folder"] = dst


def main():
    args, forced, folder = sys.argv[1:], False, None
    if "--force" in args:
        args.remove("--force"); forced = True
    if "--folder" in args:
        i = args.index("--folder"); folder = args[i + 1]; del args[i:i + 2]
        if folder not in FOLDERS:
            sys.exit(f"--folder must be one of {', '.join(FOLDERS)}")
    urls = [a for a in args if a.startswith("http")]
    if not urls:
        sys.exit(__doc__)
    log = json.load(open(bm.LOG, encoding="utf-8")) if os.path.exists(bm.LOG) else {}
    touched = set()
    for url in urls:
        url = bm.unshorten(url.strip())
        u = urlparse(url)   # drop tracking codes, keep any real query parameters
        q = [p for p in u.query.split("&") if p and not re.match(r"(fbclid|utm_[a-z]+|mibextid|igsh|gclid)=", p)]
        url = u._replace(query="&".join(q), fragment="").geturl()
        # duplicate check 1: the same address (ignoring tracking codes etc.) already saved
        old_key = next((k for k, e in log.items() if norm(k) == norm(url) and e.get("status") == "ok"), None) \
            or next((k for k in log if norm(k) == norm(url)), None)
        old = log.get(old_key, {}) if old_key else {}
        elsewhere = library_copy(url)
        if elsewhere and not forced:
            print(f"already in the library: {elsewhere}  (use --force to add it here anyway)")
            continue
        if old.get("status") == "ok" and not forced:
            print(f"already in the collection: bookmarks/{old['folder']}/{old['md']}  (use --force to re-fetch)")
            if folder and folder != old["folder"]:   # asked for a different folder: just move it
                touched |= {old["folder"], folder}; move(old, old["folder"], folder)
                print(f"  moved to {folder}")
            continue
        # fetch into a staging folder first, so the recipe can be categorized from its own text
        stage = os.path.join(bm.OUT, "_incoming"); os.makedirs(stage, exist_ok=True)
        slug = os.path.splitext(old["md"])[0] if old.get("md") else (slugify(urlparse(url).path.strip("/").split("/")[-1] or urlparse(url).netloc)[:70] or "recipe")
        meta_base = {"category": "recipes", "collection": "personal-recipe-collection", "bookmark_folder": None,
                     "source_url": url, "provenance": f"Added by URL with 63_add_recipe.py, fetched {TODAY}",
                     "license": "Copyright of the original site/creator - personal offline copy, do not redistribute",
                     "compiled": TODAY, "date_added": TODAY, "date_source": "added by link"}
        print(f"fetching {url}", flush=True)
        try:
            rec = (bm.do_video if bm.VIDEO_SITES.search(urlparse(url).netloc) else bm.do_page)("", url, stage, slug, meta_base)
        except Exception as e:
            rec = {"status": "failed", "error": f"{type(e).__name__}: {e}"[:200]}
        if rec["status"] != "ok":
            print(f"  FAILED: {rec.get('error')}  - nothing added")
            for f in os.listdir(stage): os.remove(os.path.join(stage, f))
            continue
        text = open(os.path.join(stage, rec["md"]), encoding="utf-8").read()
        rec["title"] = rec.get("title") or (re.search(r"^# (.+)$", text, re.M) or [None, url])[1]
        # duplicate check 2: the same recipe from the same site saved under a different address
        same, namesakes = same_recipe({k: e for k, e in log.items() if k != old_key}, rec["title"], url)
        if same and not forced:
            e = same[0][1]
            print(f"  duplicate: \"{rec['title']}\" from this site is already saved as bookmarks/{e['folder']}/{e['md']}"
                  f"  - nothing added (use --force to add it anyway)")
            for f in os.listdir(stage): os.remove(os.path.join(stage, f))
            continue
        for _, e in namesakes:
            print(f"  note: you also have a different \"{e.get('title')}\" recipe from {urlparse(e.get('source_url') or '').netloc or 'another site'}"
                  f" (bookmarks/{e['folder']}/{e['md']})")
        dest = folder or categorize(text)
        name = folder_name(dest)
        # a nicer file name from the recipe title, never reusing a name another recipe in that folder owns
        if not old.get("md"):
            used = {os.path.splitext(e["md"])[0] for e in log.values() if e.get("folder") == dest and e.get("md")}
            new = slugify(rec.get("title") or slug)[:70] or slug
            while new in used or os.path.exists(os.path.join(bm.OUT, dest, new + ".md")): new += "-2"
            for f in os.listdir(stage):
                os.rename(os.path.join(stage, f), os.path.join(stage, new + f[len(slug):]))
            text = re.sub(rf"(?<![\w-]){re.escape(slug)}(?=(-video)?\.\w)", new, text)
            rec = {k: (v.replace(slug, new, 1) if isinstance(v, str) and v.startswith(slug) else v) for k, v in rec.items()}
            slug = new
        text = text.replace('bookmark_folder: null', f'bookmark_folder: "{name}"', 1)
        open(os.path.join(stage, rec["md"]), "w", encoding="utf-8").write(text)
        if old.get("folder") and old["folder"] != dest:   # re-fetch landing in a different folder: clear the old copy
            for f in os.listdir(os.path.join(bm.OUT, old["folder"])):
                if f == slug + ".txt":   # your note moves with the recipe
                    os.replace(os.path.join(bm.OUT, old["folder"], f), os.path.join(bm.OUT, dest, f))
                elif f.startswith(slug + ".") or f.startswith(slug + "-video."): os.remove(os.path.join(bm.OUT, old["folder"], f))
            touched.add(old["folder"])
        for f in os.listdir(stage):
            os.replace(os.path.join(stage, f), os.path.join(bm.OUT, dest, f))
        rec.update(folder=dest, added=TODAY, via="63_add_recipe", date_added=TODAY, date_source="added by link")
        if old_key and old_key != url:
            log.pop(old_key)   # replaced: keep one entry, under the clean address
        log[url] = rec; touched.add(dest)
        json.dump(log, open(bm.LOG, "w", encoding="utf-8"), indent=1)
        print(f"  added: {rec.get('title')}\n  folder: {dest}  ->  bookmarks/{dest}/{rec['md']}"
              + (f"  (+ PDF)" if rec.get("pdf") else "") + (f"  (+ video)" if rec.get("video") else ""))
    if touched:
        json.dump(log, open(bm.LOG, "w", encoding="utf-8"), indent=1)
        refresh_pages(log, touched)
        for script in ("20_catalog.py", "21_readme.py"):
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), script)], capture_output=True)
        print("list pages and catalog refreshed")


if __name__ == "__main__":
    main()
