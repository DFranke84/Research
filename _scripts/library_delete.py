"""Delete one library item and everything that belongs to it (used by Library Manager's "Delete" button).

plan(it)    -> what would go: the item's files (its .md, the PDF/photos/videos/original/attachments it links to or that
               share its name, its _images folder, cached thumbnails) and the bookkeeping that mentions it (lines on list
               pages, the bookmark fetch log, favorites, course progress). Files another item also uses are kept.
execute(p)  -> files go to the Windows Recycle Bin (restorable), the bookkeeping is updated; the caller then refreshes
               the catalog (20_catalog.py + 21_readme.py).
"""
import ctypes, glob, hashlib, json, os, re
from ctypes import wintypes
from urllib.parse import unquote

RESEARCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(RESEARCH, "_work")
THUMBS = os.path.join(WORK, "thumbs")
FAV_FILE = os.path.join(WORK, "favorites.json")
PROGRESS_FILE = os.path.join(WORK, "course_progress.json")
BM_LOG = os.path.join(RESEARCH, "recipes", "personal-recipe-collection", "bookmarks", "fetch_log.json")
COLL_PAGE = os.path.join(RESEARCH, "recipes", "personal-recipe-collection.md")
CARDS_PAGE = os.path.join(RESEARCH, "recipes", "personal-recipe-collection", "recipe-cards", "recipe-cards.md")
THUMB_SIZES = [(184, 120), (130, 73), (300, 190)]
LINK = re.compile(r"\]\(<?([^)>\s]+)>?\)")
FM_FILE = re.compile(r'^file:\s*"?([^"\n]+?)"?\s*$', re.M)
INDEX = re.compile(r'^source_type: "(collection|bookmark-collection|image-collection)"', re.M)


def ab(rel):
    return os.path.join(RESEARCH, rel.replace("/", os.sep)) if rel else ""


def rel(p):
    return os.path.relpath(p, RESEARCH).replace(os.sep, "/")


def _local_links(md_path, text):
    """Files in the item's own folder (or below) that its .md links to or names in `file:`."""
    d = os.path.dirname(md_path)
    out = []
    for target in LINK.findall(text) + FM_FILE.findall(text[:3000]):
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        p = os.path.normpath(os.path.join(d, unquote(target.split("#")[0])))
        if p.lower().endswith(".md") and os.path.normcase(p) != os.path.normcase(md_path):
            continue   # another library page it merely links to - a separate item, never part of this one
        if p.startswith(d + os.sep) and os.path.isfile(p):
            out.append(p)
    return out


def _used_elsewhere(path, own_md):
    """True when another .md in the same folder links to this file (shared picture/document)."""
    d, name = os.path.dirname(path), os.path.basename(path)
    keys = {name, name.replace(" ", "%20")}
    from urllib.parse import quote
    keys.add(quote(name))
    for md in glob.glob(os.path.join(d, "*.md")):
        if os.path.samefile(md, own_md) if os.path.exists(own_md) else md == own_md:
            continue
        try:
            t = open(md, encoding="utf-8").read()
        except Exception:
            continue
        if INDEX.search(t[:2000]):
            continue   # list pages are cleaned separately
        if any(k in t for k in keys):
            return True
    return False


def plan(it):
    """Everything that deleting this item would remove or change."""
    files, notes = [], []
    md = ab(it.get("file"))
    own = ab(it.get("path"))
    if md and os.path.isfile(md):
        text = open(md, encoding="utf-8").read()
        stem = md[:-3]
        cands = [md] + _local_links(md, text)
        d = os.path.dirname(md)
        base = os.path.basename(stem)
        for f in os.listdir(d):   # files named after the item: slug.pdf, slug.jpg, slug-video.mp4, slug.print.html ...
            if f.startswith(base + ".") or f.startswith(base + "-video."):
                cands.append(os.path.join(d, f))
        if os.path.isdir(stem + "_images"):
            cands.append(stem + "_images")
        orig = ab(it.get("original"))
        if orig and os.path.isfile(orig):
            cands.append(orig)
        for p in dict.fromkeys(os.path.normpath(c) for c in cands):
            if p != md and os.path.isfile(p) and _used_elsewhere(p, md):
                notes.append(f"kept (another item uses it): {rel(p)}")
            else:
                files.append(p)
    elif own and os.path.exists(own):   # a loose video / recipe card / lesson file with no .md of its own
        files.append(own)
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import note_path
    base_file = md if md and os.path.isfile(md) else own
    note = note_path(base_file, ab(it.get("original")) or None) if base_file else None
    if note and os.path.isfile(note) and os.path.normpath(note) not in [os.path.normpath(f) for f in files]:
        files.append(note)   # your note about the item goes with it
    for size in THUMB_SIZES:
        h = hashlib.md5((it["path"] + f"|{size[0]}x{size[1]}").encode()).hexdigest()
        for ext in (".jpg", ".none"):
            p = os.path.join(THUMBS, h + ext)
            if os.path.exists(p):
                files.append(p)
    dirs = [f for f in files if os.path.isdir(f)]
    files = [f for f in files if not any(f.startswith(d + os.sep) for d in dirs)]   # a folder going covers its contents
    edits = _bookkeeping(it, files)
    return {"item": it, "files": files, "edits": edits, "notes": notes}


def _bookkeeping(it, files):
    """[(description, function)] for the list pages / logs / favorites that mention the item."""
    edits = []
    targets = {os.path.normcase(os.path.normpath(f)) for f in files}
    # list pages anywhere in the item's category: drop list lines that link to a deleted file
    cat_dir = ab(it["path"].split("/")[0])
    for page in glob.glob(os.path.join(cat_dir, "**", "*.md"), recursive=True):
        if os.path.normcase(os.path.normpath(page)) in targets:
            continue
        try:
            t = open(page, encoding="utf-8").read()
        except Exception:
            continue
        hit = [l for l in t.split("\n") if re.match(r"^\s*([-*]|\d+\.)\s", l) and any(
            os.path.normcase(os.path.normpath(os.path.join(os.path.dirname(page), unquote(x.split("#")[0])))) in targets
            for x in LINK.findall(l) if not x.startswith(("http", "#", "mailto")))]
        if hit:
            edits.append((f"remove {len(hit)} line(s) from list page {rel(page)}", lambda page=page, hit=hit: _drop_lines(page, hit)))
    if it.get("type") == "recipe-card" and os.path.exists(CARDS_PAGE):
        edits.append(("remove the card from recipe-cards.md", lambda: _drop_card(os.path.basename(ab(it["path"])))))
    if os.path.exists(BM_LOG) and "/bookmarks/" in it["path"]:
        folder, md = it["path"].split("/")[3], os.path.basename(it["path"])
        log = json.load(open(BM_LOG, encoding="utf-8"))
        urls = [u for u, e in log.items() if e.get("folder") == folder and e.get("md") == md]
        if urls:
            edits.append(("remove it from the bookmark download log", lambda: _drop_log(urls)))
    favs = json.load(open(FAV_FILE, encoding="utf-8")).get("items", {}) if os.path.exists(FAV_FILE) else {}
    if it["path"] in favs:
        edits.append(("remove it from Favorites", lambda: _drop_key(FAV_FILE, it["path"], "items")))
    prog = json.load(open(PROGRESS_FILE, encoding="utf-8")) if os.path.exists(PROGRESS_FILE) else {}
    if isinstance(prog, dict) and it["path"] in prog:
        edits.append(("remove its Cooking School progress", lambda: _drop_key(PROGRESS_FILE, it["path"])))
    return edits


def _drop_lines(page, lines):
    t = open(page, encoding="utf-8").read().split("\n")
    drop, keep, head = set(lines), [], None
    for l in t:
        if re.match(r"^#{2,3} .*\(\d+\)\s*$", l):
            head = len(keep)
        if l in drop:
            if head is not None:   # "## Saved offline (352)" -> 351: the section heading right above the line
                keep[head] = re.sub(r"\((\d+)\)\s*$", lambda m: f"({max(0, int(m.group(1)) - 1)})", keep[head])
            continue
        keep.append(l)
    s = "\n".join(keep)
    n = len(lines)
    for k in ("saved", "recipes"):   # list-page front matter counts
        s = re.sub(rf"^({k}: )(\d+)$", lambda m: f"{m.group(1)}{max(0, int(m.group(2)) - n)}", s, count=1, flags=re.M)
    open(page, "w", encoding="utf-8").write(s)


def _drop_card(img_name):
    t = open(CARDS_PAGE, encoding="utf-8").read()
    parts = re.split(r"(?=^## )", t, flags=re.M)
    from urllib.parse import quote
    keep = [p for p in parts if not (p.startswith("## ") and (img_name in unquote(p) or quote(img_name) in p))]
    open(CARDS_PAGE, "w", encoding="utf-8").write("".join(keep))


def _drop_log(urls):
    log = json.load(open(BM_LOG, encoding="utf-8"))
    for u in urls:
        log.pop(u, None)
    json.dump(log, open(BM_LOG, "w", encoding="utf-8"), indent=1)


def _drop_key(path, key, inner=None):
    d = json.load(open(path, encoding="utf-8"))
    (d[inner] if inner else d).pop(key, None)
    tmp = path + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------- Recycle Bin
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", ctypes.c_uint), ("pFrom", ctypes.c_wchar_p), ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p)]


def recycle(paths):
    """Send files/folders to the Recycle Bin (FO_DELETE + FOF_ALLOWUNDO). Returns the paths that are still there."""
    import time
    left = []
    for p in (os.path.abspath(x) for x in paths if os.path.exists(x)):
        for attempt in range(3):   # one at a time, so a file that is briefly in use does not stop the others
            op = SHFILEOPSTRUCTW(None, 3, p + "\0\0", None, 0x0040 | 0x0010 | 0x0004 | 0x0400, False, None, None)
            ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if not os.path.exists(p):
                break
            time.sleep(0.4)
        else:
            left.append(p)
    return left


def execute(p):
    """Do it: bookkeeping first (it needs the files to still exist to find them), then the files to the Recycle Bin."""
    errors = []
    for desc, f in p["edits"]:
        try:
            f()
        except Exception as e:
            errors.append(f"{desc}: {e}")
    left = recycle(p["files"])
    errors += [f"could not remove {rel(x)}" for x in left]
    folders = {e.split("/")[3] for e in [p["item"]["path"]] if "/bookmarks/" in e}
    if folders:   # rebuild the bookmark folder page from the (updated) log so its counts stay right
        try:
            import importlib, sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            m = importlib.import_module("63_add_recipe")
            m.refresh_pages(json.load(open(BM_LOG, encoding="utf-8")), folders)
        except Exception as e:
            errors.append(f"bookmark page refresh: {e}")
    return errors
