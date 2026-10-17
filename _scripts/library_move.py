"""Move one library item to another category (Library Manager's "Change category..." button).

plan(it, new_cat) -> what would move (the item's .md and the files that belong to it - original PDF, photos, its
                     _images folder, your note), what is copied (files another item also uses), and why it cannot move
                     (items inside collections and courses, items other pages link to, a name already taken).
execute(p)        -> moves the files, sets 'category:' in the page, fixes its links to things that stay behind, moves its
                     Favorites entry and drops its cached thumbnails; the caller then refreshes the catalog
                     (20_catalog.py + 21_readme.py).
"""
import glob, json, os, re, shutil, sys
from urllib.parse import unquote, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library_delete as ld
from categories import CATEGORIES

RESEARCH, ab, rel, LINK = ld.RESEARCH, ld.ab, ld.rel, ld.LINK
# folders that are collections/courses of their own: their pages are listed and linked by index pages
LOCKED = ("recipes/personal-recipe-collection/", "recipes/wardee-traditional-cooking-school/", "local-area/")


_INCOMING = {}   # md path -> pages linking to it (reading a big category folder is slow; asked once per window)


def _incoming(md):
    """Other pages (anywhere in the item's category) that link to this page."""
    if md in _INCOMING:
        return _INCOMING[md]
    _INCOMING[md] = _incoming_scan(md)
    return _INCOMING[md]


def _incoming_scan(md):
    cat_dir = os.path.dirname(md)
    name = os.path.basename(md)
    keys = {name, quote(name), name.replace(" ", "%20")}
    hits = []
    for page in glob.glob(os.path.join(cat_dir, "**", "*.md"), recursive=True):
        if os.path.normcase(page) == os.path.normcase(md):
            continue
        try:
            t = open(page, encoding="utf-8").read()
        except Exception:
            continue
        if not any(k in t for k in keys):
            continue
        for x in LINK.findall(t):
            if x.startswith(("http", "#", "mailto")):
                continue
            p = os.path.normpath(os.path.join(os.path.dirname(page), unquote(x.split("#")[0])))
            if os.path.normcase(p) == os.path.normcase(md):
                hits.append(page); break
    return hits


def plan(it, new_cat):
    p = {"item": it, "new_cat": new_cat, "move": [], "copy": [], "thumbs": [], "problems": []}
    path = it.get("file") or ""
    md = ab(path)
    old_cat = path.split("/")[0] if path else ""
    if new_cat not in CATEGORIES:
        p["problems"].append(f"unknown category {new_cat!r}")
    if new_cat == old_cat:
        p["problems"].append("it is already in that category")
    if not path or not os.path.isfile(md):
        p["problems"].append("this item has no page of its own (it is part of a collection) - it cannot be moved")
        return p
    if path.startswith(LOCKED) or path.count("/") != 1:
        p["problems"].append("it belongs to a collection (recipe collection, Cooking School, Local Area or a course folder); "
                             "moving it would break that collection's lists - it cannot be moved")
        return p
    inc = _incoming(md)
    if inc:
        p["problems"].append("other pages link to it, and moving it would break those links: "
                             + ", ".join(rel(x) for x in inc[:5]) + (" ..." if len(inc) > 5 else ""))
    d = ld.plan(it)   # the same 'what belongs to this item' rules as Delete
    shared = {os.path.normcase(os.path.normpath(ab(n.split(": ", 1)[1]))) for n in d["notes"] if n.startswith("kept")}
    p["move"] = [f for f in d["files"] if "_work" not in f]
    p["thumbs"] = [f for f in d["files"] if "_work" in f]
    p["copy"] = [ab(n.split(": ", 1)[1]) for n in d["notes"] if n.startswith("kept")]
    dest = ab(new_cat)
    for f in p["move"] + p["copy"]:
        to = os.path.join(dest, os.path.relpath(f, os.path.dirname(md)))
        if os.path.exists(to):
            p["problems"].append(f"{new_cat}/ already has {os.path.relpath(to, dest)}")
    p["dest"] = dest
    return p


def _fix_page(md_new, md_old, new_cat, moved_names):
    """category: field + links to files that did not move (they stay in the old folder)."""
    t = open(md_new, encoding="utf-8").read()
    t = re.sub(r'^category:\s*"?[^"\n]*"?\s*$', f'category: "{new_cat}"', t, count=1, flags=re.M)
    old_dir, new_dir = os.path.dirname(md_old), os.path.dirname(md_new)

    def fix(m):
        x = m.group(1)
        if x.startswith(("http", "#", "mailto")):
            return m.group(0)
        target = unquote(x.split("#")[0])
        first = target.replace("\\", "/").split("/")[0]
        if first in moved_names:   # its own files: they moved along, the link still works
            return m.group(0)
        old_abs = os.path.normpath(os.path.join(old_dir, target))
        new_rel = os.path.relpath(old_abs, new_dir).replace(os.sep, "/")
        return m.group(0).replace(x, quote(new_rel, safe="/:#().-_~"))
    t = LINK.sub(fix, t)
    open(md_new, "w", encoding="utf-8").write(t)


def execute(p):
    """Returns a list of problems (empty = done)."""
    if p["problems"]:
        return p["problems"]
    _INCOMING.clear()   # links change once things move
    it = p["item"]
    md_old = ab(it["file"])
    src_dir, dest = os.path.dirname(md_old), p["dest"]
    errs = []
    moved_names = set()
    for f in p["move"]:
        to = os.path.join(dest, os.path.relpath(f, src_dir))
        os.makedirs(os.path.dirname(to), exist_ok=True)
        try:
            shutil.move(f, to)
            moved_names.add(os.path.relpath(f, src_dir).replace(os.sep, "/").split("/")[0])
        except Exception as e:
            errs.append(f"could not move {rel(f)}: {e}")
    for f in p["copy"]:
        to = os.path.join(dest, os.path.relpath(f, src_dir))
        os.makedirs(os.path.dirname(to), exist_ok=True)
        try:
            (shutil.copytree if os.path.isdir(f) else shutil.copy2)(f, to)
            moved_names.add(os.path.relpath(f, src_dir).replace(os.sep, "/").split("/")[0])
        except Exception as e:
            errs.append(f"could not copy {rel(f)}: {e}")
    md_new = os.path.join(dest, os.path.basename(md_old))
    if os.path.exists(md_new):
        _fix_page(md_new, md_old, p["new_cat"], moved_names)
    for f in p["thumbs"]:
        try:
            os.remove(f)
        except OSError:
            pass
    new_path = rel(md_new)
    if os.path.exists(ld.FAV_FILE):   # the favorite follows the item
        d = json.load(open(ld.FAV_FILE, encoding="utf-8"))
        items = d.get("items", {})
        if it["path"] in items:
            items[new_path] = items.pop(it["path"])
            tmp = ld.FAV_FILE + ".tmp"
            json.dump(d, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            os.replace(tmp, ld.FAV_FILE)
    p["new_path"] = new_path
    return errs
