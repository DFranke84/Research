"""Browse and read the E:\\Research library inside Library Manager.

Items come from CATALOG.json (one per source .md) plus things with no .md of their own: the recipe cards (images inside
recipe-cards.md), the recipe videos folder and the Traditional Cooking School lesson videos/audio. Thumbnails are made once
and cached in _work/thumbs: a photo saved with the item > a frame from its video > page 1 of its PDF > a coloured tile.

Views:
  BrowsePage    searchable card grid (Recipes, Documents & Books, Whole Library)
  CoursePage    the Traditional Cooking School laid out as its learning schedule: modules in order, each with its course
                materials, numbered lessons (all parts of a lesson together), extra/Q&A videos; Previous/Next in course order
  FavoritesPage starred items, grouped by section or category (stored in _work/favorites.json)
  Reader        an item's text (Markdown rendered with headings, lists, links, pictures) and, for PDFs, the pages
Course items appear ONLY in the Cooking School (and Favorites), never in the other views.
"""
import hashlib, json, os, re, subprocess, threading, time, webbrowser
from urllib.parse import unquote
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageOps, ImageTk
from lm_ui import *
import waypoints as wpt

THUMBS =os.path.join(RESEARCH, "_work", "thumbs")
os.makedirs(THUMBS, exist_ok=True)
FAV_FILE = os.path.join(RESEARCH, "_work", "favorites.json")
PROGRESS_FILE = os.path.join(RESEARCH, "_work", "course_progress.json")
SETTINGS_FILE = os.path.join(RESEARCH, "_work", "viewer_settings.json")
PAGE_SIZES = ["24", "48", "96", "200", "All"]
SORTS = ["Title A\u2013Z", "Newest added", "Oldest added"]   # date = when the item was originally saved (date_added)
LIBRARY_BUILT = "2026-09-28"   # file dates from this day on are library copies, not when the item was saved
TW, TH = 184, 120          # grid card picture
LW, LH = 130, 73           # lesson tile picture
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
VID_EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi")
AUD_EXT = (".mp3", ".m4a", ".wav", ".ogg")
INDEX_TYPES = {"collection", "bookmark-collection", "image-collection"}
TYPE_NAMES = {"local-profile": "Plant", "local-wildlife": "Wildlife", "local-reference": "Reference", "local-pest": "Pest / problem",
              "local-guide": "Kalispell guide", "local-map": "Map",
              "growing-guide": "Growing guide", "local-overview": "Overview", "repair-guide": "Repair guide", "q-and-a": "Q & A", "wikipedia-article": "Wikipedia", "web-page": "Web page",
              "wiki-article": "Wiki article", "species-profile": "Species profile", "pdf": "PDF document", "web-recipe": "Web recipe",
              "email-recipe": "Email recipe", "document": "Document", "wiki-book": "Book", "video": "Video",
              "facebook-post": "Facebook recipe", "course-module": "Module overview", "course": "Course", "recipe-card": "Recipe card",
              "audio": "Audio lesson", "lesson-video": "Lesson video", "zim-article": "Archive article"}
TYPE_ICON = {"video": "\u25b6", "pdf": "\U0001F4D5", "document": "\U0001F4C4", "wiki-book": "\U0001F4D6", "repair-guide": "\U0001F527",
             "q-and-a": "\U0001F4AC", "species-profile": "\U0001F33F", "web-recipe": "\U0001F372", "email-recipe": "\u2709",
             "facebook-post": "\U0001F372", "recipe-card": "\U0001F5C2", "course": "\U0001F393", "course-module": "\U0001F393",
             "audio": "\U0001F3A7", "lesson-video": "\u25b6"}
TILE = ["#3f6f5a", "#8a5a2b", "#4b6584", "#7a4e6d", "#5c6b2f", "#9b5f3a", "#2f6f73", "#6a5a8e", "#7d6b3c", "#4f7a3a"]
DOC_TYPES = {"pdf", "document", "wiki-book"}
PCOL = "recipes/personal-recipe-collection"
WARDEE = "recipes/wardee-traditional-cooking-school"
PLAYABLE = VID_EXT + AUD_EXT
COURSE_TAIL = re.compile(r"\s*[-\u2013]\s*Traditional Cooking School( by GNOWFGLINS)?( \(Wardee Harmon\))?\s*$", re.I)
STAR_ON, STAR_OFF = "\u2605", "\u2606"


def natural(s):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", (s or "").lower())]


def pretty_title(t):
    """'000-fundamentals-ebook-traditional-cooking-school-gnowfglins' -> 'Fundamentals eBook'."""
    if not t or " " in t.strip() or t.count("-") + t.count("_") < 2:
        return t
    t = re.sub(r"[-_]+", " ", t)
    t = re.sub(r"\b(traditional cooking school|by gnowfglins|gnowfglins)\b", "", t, flags=re.I)
    t = re.sub(r"^\d{2,3}\s+", "", t.strip())
    t = " ".join(w if w.isupper() else w.capitalize() for w in t.split()).replace("Ebook", "eBook")
    return re.sub(r"\s+", " ", t).strip() or t


def web_view_available():
    try:
        import tkinterweb  # noqa: F401  (installed by Setup; without it the Web page tab is simply not shown)
        return True
    except Exception:
        return False


def tname(t):
    return TYPE_NAMES.get(t, (t or "Item").replace("-", " ").capitalize())


def is_course(it):
    return it["path"].startswith(WARDEE)


def abspath(rel):
    return os.path.join(RESEARCH, rel.replace("/", os.sep)) if rel else ""


def open_path(p):
    try:
        os.startfile(p)
    except OSError as e:
        messagebox.showerror("Can't open", str(e))


def load_json(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def save_json(p, data):
    tmp = p + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, p)


# ======================================================================= the item list
def recipe_group(it):
    f = it.get("file") or it.get("path") or ""
    if it["type"] == "recipe-card":
        return "cards"
    if "/videos/" in f:
        return "videos"
    for key, g in (("/bookmarks/", "web"), ("/email-recipes/", "email"), ("/facebook-saved/", "facebook")):
        if key in f:
            return g
    return "course" if "wardee" in f else "books"


def file_date(rel):
    """An original file's date as YYYY-MM-DD, or "" when the file was made by the library (no real date known)."""
    try:
        d = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(abspath(rel))))
    except OSError:
        return ""
    return d if d < LIBRARY_BUILT else ""


def extra_items():
    """Things without a .md of their own: recipe cards, loose recipe videos, Cooking School lesson videos/audio."""
    out = []
    cards = os.path.join(COLL, "recipe-cards", "recipe-cards.md")
    if os.path.exists(cards):
        txt = open(cards, encoding="utf-8").read()
        for sec in re.split(r"^## ", txt, flags=re.M)[1:]:
            title = sec.split("\n", 1)[0].strip()
            img = re.search(r"!\[[^\]]*\]\(<?([^)>]+)>?\)", sec)
            if not img:
                continue
            body = re.search(r"```text\n(.*?)```", sec, re.S)
            body = body[1].strip() if body else ""
            rel = f"{PCOL}/recipe-cards/{unquote(img[1])}"
            out.append({"file": "", "path": rel, "title": title, "category": "recipes", "type": "recipe-card",
                        "publisher": "Recipe card", "original": rel, "source_url": "", "words": len(body.split()), "text": body,
                        "date": file_date(rel)})
    vids = os.path.join(COLL, "videos")
    if os.path.isdir(vids):
        for f in sorted(os.listdir(vids)):
            if f.lower().endswith(VID_EXT):
                rel = f"{PCOL}/videos/{f}"
                out.append({"file": "", "path": rel, "title": os.path.splitext(f)[0].replace("_", " "), "category": "recipes",
                            "type": "video", "publisher": "Personal recipe video", "original": rel, "source_url": "", "words": 0,
                            "date": file_date(rel)})
    wd = abspath(WARDEE)
    if os.path.isdir(wd):
        for mod in sorted(os.listdir(wd)):
            md = os.path.join(wd, mod)
            if not os.path.isdir(md):
                continue
            for f in sorted(os.listdir(md), key=natural):
                ext = os.path.splitext(f)[1].lower()
                if ext in PLAYABLE:
                    rel = f"{WARDEE}/{mod}/{f}"
                    out.append({"file": "", "path": rel, "title": os.path.splitext(f)[0].replace("_", " ").strip(), "category": "recipes",
                                "type": "audio" if ext in AUD_EXT else "lesson-video", "publisher": "Traditional Cooking School",
                                "original": rel, "source_url": "", "words": 0})
    return out


class Library:
    """CATALOG.json + extra items, loaded in the background; listeners are told when it is ready."""
    def __init__(self, root):
        self.root, self.items, self.by_path, self.ready, self.listeners = root, [], {}, False, []
        self.reload()

    def reload(self, retry=True):
        def guarded():
            try:
                work()
            except Exception:   # never leave the app on "Loading the library" for ever: log it and try once more
                import traceback
                traceback.print_exc()
                if retry:
                    self.root.after(2000, lambda: self.reload(retry=False))

        def work():
            rows = load_json(os.path.join(RESEARCH, "CATALOG.json"), [])
            items = []
            for r in rows:
                if r.get("source_type") in INDEX_TYPES:
                    continue
                items.append({"file": r["file"], "path": r["file"], "title": r.get("title") or os.path.basename(r["file"]),
                              "category": r.get("category"), "type": r.get("source_type") or "", "publisher": r.get("publisher") or "",
                              "original": r.get("original_file") or "", "source_url": r.get("source_url") or "",
                              "words": r.get("words") or 0, "images": r.get("images") or 0, "date": r.get("date_added") or "",
                              "ltype": r.get("group") or ""})   # Local Area plant type
            items += extra_items()
            mods = {it["path"].split("/")[2]: COURSE_TAIL.sub("", it["title"]) for it in items
                    if it["path"].startswith(WARDEE + "/") and it["type"] == "course-module"}
            for it in items:
                it["title"] = COURSE_TAIL.sub("", pretty_title(it["title"])) or it["title"]
                if it["path"].startswith(WARDEE + "/") and it["path"].count("/") >= 3:
                    it["module"] = mods.get(it["path"].split("/")[2], it["path"].split("/")[2])
                it["key"] = (it["title"] or "").lower()
                it["search"] = (it["title"] + " " + it["publisher"] + " " + os.path.basename(it["path"])).lower()
                if it["category"] == "recipes":
                    it["group"] = recipe_group(it)
            items.sort(key=lambda i: i["key"])
            # No per-file checks here: on a cold start (after a reboot or a big download) looking at ~19,000 files on a
            # spinning disk takes 1-2 minutes. "Recently added" uses the catalog's date_added instead.
            self.root.after(0, lambda: self._done(items))
        threading.Thread(target=guarded, daemon=True).start()

    def _done(self, items):
        self.items, self.ready = items, True
        self.by_path = {i["path"]: i for i in items}
        for f in self.listeners:
            f()

    def on_ready(self, f):
        self.listeners.append(f)
        if self.ready:
            f()


class Favorites:
    """Starred items (by library path), saved in _work/favorites.json; listeners are told about every change."""
    def __init__(self):
        self.d = load_json(FAV_FILE, {}).get("items", {})
        self.listeners = []

    def has(self, it):
        return it["path"] in self.d

    def toggle(self, it):
        if it["path"] in self.d:
            del self.d[it["path"]]
        else:
            self.d[it["path"]] = time.strftime("%Y-%m-%d %H:%M")
        save_json(FAV_FILE, {"items": self.d})
        for f in list(self.listeners):
            try:
                f()
            except tk.TclError:
                pass


class Notes:
    """Item notes: plain .txt files beside the items (see common.note_path). Listeners are told about every change."""
    def __init__(self):
        self.cache, self.listeners = {}, []

    def path(self, it):
        from common import note_path
        return note_path(abspath(it.get("file") or it["path"]), abspath(it.get("original")) or None)

    def has(self, it):
        if it["path"] not in self.cache:
            self.cache[it["path"]] = os.path.isfile(self.path(it))
        return self.cache[it["path"]]

    def read(self, it):
        try:
            return open(self.path(it), encoding="utf-8-sig", errors="replace").read()
        except OSError:
            return ""

    def save(self, it, text):
        with open(self.path(it), "w", encoding="utf-8", newline="\r\n") as fh:   # Notepad-friendly
            fh.write(text.rstrip() + "\n")
        self.cache[it["path"]] = True
        self.tell()

    def delete(self, it):
        import library_delete as ld
        p = self.path(it)
        left = ld.recycle([p]) if os.path.exists(p) else []
        self.cache[it["path"]] = os.path.isfile(p)
        self.tell()
        return not self.cache[it["path"]]

    def tell(self):
        for f in list(self.listeners):
            try:
                f()
            except tk.TclError:
                pass


# ======================================================================= fixing where an item shows up
RECIPE_TILES_FILE = os.path.join(RESEARCH, "_work", "recipe_tiles.json")
RECIPE_TILES = load_json(RECIPE_TILES_FILE, {})   # recipe path -> [tile names] chosen by the user (overrides the title guess)


def edit_recipe_tiles(page, it):
    """Tick the Recipes tiles a recipe belongs in (saved in _work/recipe_tiles.json)."""
    app = page.app
    rp = app.pages.get("recipes")
    if not isinstance(rp, TopicPage):
        return
    names = [t[0] for t in rp.topics if t[0] not in ("All Recipes", "Other Recipes")]
    now = {t[0] for t in rp.topics if t[0] in names and t[3](it)}
    win = tk.Toplevel(app); win.title("Recipe tiles"); win.configure(bg=C["card"]); win.transient(app)
    win.geometry(f"520x560+{app.winfo_rootx() + 220}+{app.winfo_rooty() + 80}")
    label(win, "Which Recipes tiles should this recipe be in?", 13, True).pack(fill="x", padx=20, pady=(16, 2))
    label(win, it["title"], 10, fg="dim", wraplength=470).pack(fill="x", padx=20)
    auto = it["path"] not in RECIPE_TILES
    label(win, "Currently: chosen automatically from the title" if auto else "Currently: your own choice", 9, fg="dim").pack(fill="x", padx=20, pady=(6, 6))
    box = tk.Frame(win, bg=C["card"]); box.pack(fill="both", expand=True, padx=20)
    vars_ = {}
    for k, n in enumerate(names):
        v = tk.BooleanVar(value=n in now); vars_[n] = v
        tk.Checkbutton(box, text=n, variable=v, bg=C["card"], font=(F, 10), anchor="w", activebackground=C["card"]).grid(
            row=k % 9, column=k // 9, sticky="w", padx=(0, 18))
    label(win, "No ticks = it goes in 'Other Recipes'. All Recipes always has it.", 9, fg="dim").pack(fill="x", padx=20, pady=(8, 0))
    row = tk.Frame(win, bg=C["card"]); row.pack(fill="x", padx=20, pady=14)

    def done(value):
        if value is None:
            RECIPE_TILES.pop(it["path"], None)
        else:
            RECIPE_TILES[it["path"]] = value
        save_json(RECIPE_TILES_FILE, RECIPE_TILES)
        win.destroy()
        if rp.topic is None:
            rp.paint_tiles()
        else:
            rp.set_topic(rp.topic) if not rp.reader.winfo_ismapped() else None
    Btn(row, "Save", lambda: done([n for n, v in vars_.items() if v.get()]), "primary", 10, 18, 6).pack(side="left")
    Btn(row, "Use automatic", lambda: done(None), "secondary", 10, 14, 6).pack(side="left", padx=8)
    Btn(row, "Cancel", win.destroy, "secondary", 10, 14, 6).pack(side="right")
    win.grab_set()


LOCAL_TYPES_FILE = os.path.join(RESEARCH, "_work", "local_area", "type_overrides.json")   # also read by 69 / 71 builders


def local_types():
    """Local Area types, in menu order (the '## ' groups of the plant list + the Field Guide groups)."""
    try:
        from local_area_specs import PLANT_TABLE, WILD_GROUPS
        return [l[3:].strip() for l in PLANT_TABLE.splitlines() if l.startswith("## ")] + WILD_GROUPS
    except Exception:
        return []


def set_local_type(app, it, new, refresh_catalog=True):
    """Change a Local Area page's type: its 'group' + 'Type:' line, the saved override, and the app's lists."""
    cur = it.get("ltype") or ""
    md = abspath(it["file"])
    try:
        t = open(md, encoding="utf-8").read()
        t = re.sub(r'^group:\s*"[^"\n]*"\s*$', f'group: "{new}"', t, count=1, flags=re.M)
        if cur:
            t = t.replace(f"Type: {cur}", f"Type: {new}", 1)
        open(md, "w", encoding="utf-8").write(t)
        ov = load_json(LOCAL_TYPES_FILE, {})
        ov[it["path"]] = new
        save_json(LOCAL_TYPES_FILE, ov)
    except Exception as e:
        messagebox.showerror("Change type", f"Could not change it:\n{e}"); return False
    for i in app.lib.items:
        if i["path"] == it["path"]:
            i["ltype"] = new
    app.lib._done(list(app.lib.items))   # every page refreshes

    def catalog():
        for script in ("20_catalog.py", "21_readme.py"):
            subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe"),
                            os.path.join(os.path.dirname(os.path.abspath(__file__)), script)], cwd=RESEARCH,
                           capture_output=True, creationflags=0x08000000)
    if refresh_catalog:
        threading.Thread(target=catalog, daemon=True).start()
    return True


def edit_local_type(page, it):
    """Local Area: file a plant / animal page under another type (tile + button). No files move - the pages link to
    each other; the page's 'group' changes and the choice is saved so rebuilds keep it."""
    app = page.app
    types = local_types()
    cur = it.get("ltype") or ""
    win = tk.Toplevel(app); win.title("Change type"); win.configure(bg=C["card"]); win.transient(app)
    win.geometry(f"560x520+{app.winfo_rootx() + 200}+{app.winfo_rooty() + 80}")
    label(win, "File this page under another type", 13, True).pack(fill="x", padx=20, pady=(16, 2))
    label(win, it["title"], 10, fg="dim", wraplength=510).pack(fill="x", padx=20)
    label(win, f"Now: {cur or 'none'}", 9, fg="dim").pack(fill="x", padx=20, pady=(6, 8))
    var = tk.StringVar(value=cur)
    box = tk.Frame(win, bg=C["card"]); box.pack(fill="both", expand=True, padx=20)
    for k, ty in enumerate(types):
        tk.Radiobutton(box, text=ty, value=ty, variable=var, bg=C["card"], font=(F, 10), anchor="w",
                       activebackground=C["card"]).grid(row=k % 11, column=k // 11, sticky="w", padx=(0, 16))
    label(win, "The page stays where it is (other pages link to it) - only the tile and button it shows under change.",
          9, fg="dim", wraplength=510).pack(fill="x", padx=20, pady=(8, 0))
    row = tk.Frame(win, bg=C["card"]); row.pack(fill="x", padx=20, pady=14)

    def save():
        new = var.get()
        win.destroy()
        if new and new != cur:
            set_local_type(app, it, new)
    Btn(row, "Save", save, "primary", 10, 18, 6).pack(side="left")
    Btn(row, "Cancel", win.destroy, "secondary", 10, 14, 6).pack(side="right")
    win.grab_set()


def waypoint_dialog(app, title, wp=None, lat=None, lon=None):
    """Add / edit a waypoint: name, position (any common format) and notes.  Returns the waypoint (not yet saved) or None.
    Shows which map the position falls on as you type."""
    wp = dict(wp or {})
    win = tk.Toplevel(app); win.title(title); win.configure(bg=C["card"]); win.transient(app)
    win.geometry(f"560x440+{app.winfo_rootx() + 220}+{app.winfo_rooty() + 110}")
    label(win, title, 13, True).pack(fill="x", padx=20, pady=(16, 8))
    name = tk.StringVar(value=wp.get("name", ""))
    pos = tk.StringVar(value=wpt.fmt(wp["lat"], wp["lon"]) if "lat" in wp else wpt.fmt(lat, lon) if lat is not None else "")
    label(win, "Name", 10, True).pack(fill="x", padx=20)
    e = entry(win, name); e.pack(fill="x", padx=20, pady=(4, 10), ipady=5)
    label(win, "Position (latitude, longitude)", 10, True).pack(fill="x", padx=20)
    pr = tk.Frame(win, bg=C["card"]); pr.pack(fill="x", padx=20, pady=(4, 2))
    pe = entry(pr, pos); pe.pack(side="left", fill="x", expand=True, ipady=5)

    def paste():
        try:
            pos.set(win.clipboard_get().strip())
        except tk.TclError:
            pass
    Btn(pr, "Paste", paste, "secondary", 9, 12, 5).pack(side="left", padx=(8, 0))
    hint = label(win, "", 9, fg="dim", wraplength=510); hint.pack(fill="x", padx=20, pady=(2, 10))
    label(win, "Notes", 10, True).pack(fill="x", padx=20)
    nt = tk.Text(win, height=4, wrap="word", font=(F, 10), bg="#fbfaf7", fg=C["text"], relief="flat", highlightthickness=1,
                 highlightbackground=C["line"], highlightcolor=C["primary"], padx=8, pady=6)
    nt.pack(fill="both", expand=True, padx=20, pady=(4, 0)); nt.insert("1.0", wp.get("notes", ""))
    result = {}

    def check(*_):
        if not pos.get().strip():
            hint.config(text="e.g. 48.1958, -114.3129  or  48°11'45\"N 114°18'46\"W  -  or paste a Google Maps link", fg=C["dim"])
            return None
        try:
            la, lo = wpt.parse(pos.get())
        except ValueError as ex:
            hint.config(text=str(ex), fg=C["err_fg"])
            return None
        d, r = wpt.maps_at(la, lo)
        on = d or r
        hint.config(text=f"{wpt.fmt_dms(la, lo)}  →  " + (on["title"] if on else "not on any map in the library"),
                    fg=C["ok_fg"] if on else C["warn_fg"])
        return la, lo
    pos.trace_add("write", check); check()
    row = tk.Frame(win, bg=C["card"]); row.pack(fill="x", padx=20, pady=14)

    def ok():
        p = check()
        if not p:
            pe.focus_set(); return
        wp.update(name=name.get().strip() or "Waypoint", lat=round(p[0], 6), lon=round(p[1], 6), notes=nt.get("1.0", "end").strip())
        result["wp"] = wp if wp.get("id") else wpt.new(wp["name"], wp["lat"], wp["lon"], wp["notes"])
        win.destroy()
    Btn(row, "Save", ok, "primary", 10, 18, 6).pack(side="left")
    Btn(row, "Cancel", win.destroy, "secondary", 10, 14, 6).pack(side="right")
    e.bind("<Return>", lambda ev: ok())
    (pe if name.get() and not pos.get() else e).focus_set()
    win.grab_set(); win.wait_window()
    return result.get("wp")


def save_waypoint(wp):
    """Add a waypoint, or replace the one with the same id (keeping its place in the list)."""
    wps = wpt.load()
    k = next((k for k, w in enumerate(wps) if w.get("id") == wp["id"]), None)
    if k is None:
        wps.append(wp)
    else:
        wps[k] = wp
    wpt.save(wps)


def map_item(app, m):
    """The library item (map page) for a waypoints.index() map."""
    want = os.path.normcase(os.path.abspath(m["md"]))
    for it in app.lib.items:
        if it.get("file") and os.path.normcase(abspath(it["file"])) == want:
            return it
    return None


def open_waypoint(app, wp, which="detail"):
    """Open the map holding the waypoint, zoomed in on it.  which = 'detail' (1:24,000) or 'regional' (1:100,000);
    falls back to the other one when the point is only on one of them."""
    d, r = wpt.maps_at(wp["lat"], wp["lon"])
    m = (d or r) if which == "detail" else (r or d)
    it = map_item(app, m) if m and app.lib.ready else None
    if not it:
        messagebox.showinfo("Waypoint", "The library is still loading - try again in a moment." if m else
                            f"“{wp['name']}” ({wpt.fmt(wp['lat'], wp['lon'])}) isn't on any map in the library.", parent=app)
        return
    it["_wp"] = dict(wp)   # Reader.show picks this up: Pages tab, zoomed in, centred on the marker
    app.open_item(it)


def confirm_move(page, it):
    """Move an item to another category - same look as Change type / Recipe tiles: pick one, Save."""
    import library_move as lm
    lm._INCOMING.clear()   # check links afresh for each window
    app = page.app
    cur = (it.get("file") or "").split("/")[0]
    win = tk.Toplevel(app); win.title("Change category"); win.configure(bg=C["card"]); win.transient(app)
    win.geometry(f"640x660+{app.winfo_rootx() + 200}+{app.winfo_rooty() + 50}")
    label(win, "Which category does this belong in?", 13, True).pack(fill="x", padx=20, pady=(16, 2))
    label(win, it["title"], 10, fg="dim", wraplength=590).pack(fill="x", padx=20)
    label(win, f"Now: {nice(cur)}", 9, fg="dim").pack(fill="x", padx=20, pady=(6, 8))
    var = tk.StringVar(value=cur)
    box = tk.Frame(win, bg=C["card"]); box.pack(fill="both", expand=True, padx=20)
    cats = sorted((c for c in CATEGORIES if c != "local-area"), key=nice)   # Local Area is built from its plant list
    half = (len(cats) + 1) // 2
    for k, c in enumerate(cats):
        tk.Radiobutton(box, text=nice(c), value=c, variable=var, bg=C["card"], font=(F, 10), anchor="w",
                       activebackground=C["card"], command=lambda: show()).grid(row=k % half, column=k // half, sticky="w", padx=(0, 16))
    info = label(win, "", 9, fg="dim", wraplength=590); info.pack(fill="x", padx=20, pady=(10, 0))
    row = tk.Frame(win, bg=C["card"]); row.pack(fill="x", padx=20, pady=14)
    state = {"plan": None}
    Btn(row, "Save", lambda: go(), "primary", 10, 18, 6).pack(side="left")
    Btn(row, "Cancel", win.destroy, "secondary", 10, 14, 6).pack(side="right")

    def summary(p):
        files = p["move"] + p["copy"]
        pics = sum(len([x for x in os.listdir(f) if x.lower().endswith(IMG_EXT)]) for f in files if os.path.isdir(f))
        parts = ["the page"]
        if any(f.lower().endswith(".pdf") for f in files):
            parts.append("its PDF")
        if pics:
            parts.append(f"{pics} photo" + ("s" if pics != 1 else ""))
        if any(f.lower().endswith(".txt") for f in files):
            parts.append("your note")
        other = [f for f in files if os.path.isfile(f) and not f.lower().endswith((".md", ".pdf", ".txt"))]
        if other:
            parts.append(f"{len(other)} other file" + ("s" if len(other) != 1 else ""))
        return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]

    def show():
        new = var.get()
        if new == cur:
            info.config(text="Pick the category it belongs in, then Save. The page and everything that belongs to it "
                             "(its PDF, photos, your note) move there; Favorites follow it.", fg=C["dim"])
            state["plan"] = None
            return
        win.config(cursor="watch"); win.update_idletasks()
        p = lm.plan(it, new); state["plan"] = p
        win.config(cursor="")
        if p["problems"]:
            info.config(text="It can't be moved: " + "; ".join(p["problems"]), fg=C["err_fg"])
        else:
            info.config(text=f"Save moves {summary(p)} to {nice(new)}. Favorites follow it.", fg=C["text"])
    show()

    def go():
        p = state["plan"]
        if not p or p["problems"]:
            return
        win.destroy()
        page.close_reader()   # lets go of the open PDF / pictures first
        app.update()
        errs = lm.execute(p)
        if errs:
            messagebox.showerror("Change category", "\n".join(errs))
        new_path = p.get("new_path")
        if new_path:
            for i in app.lib.items:   # update the item in place; every page refreshes
                if i["path"] == it["path"]:
                    i["file"] = i["path"] = new_path
                    i["category"] = p["new_cat"]
                    i["original"] = re.sub(r"^[^/]+/", p["new_cat"] + "/", i.get("original") or "") if i.get("original") else ""
            app.favs.d = load_json(FAV_FILE, {}).get("items", {})
            app.lib._done(list(app.lib.items))
            for f in list(app.favs.listeners):
                try:
                    f()
                except tk.TclError:
                    pass

        def catalog():
            for script in ("20_catalog.py", "21_readme.py"):
                subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe"),
                                os.path.join(os.path.dirname(os.path.abspath(__file__)), script)], cwd=RESEARCH,
                               capture_output=True, creationflags=0x08000000)
        threading.Thread(target=catalog, daemon=True).start()
    win.grab_set()


# ======================================================================= deleting an item
def confirm_delete(page, it):
    """Show everything that deleting this item removes; only on "Move to Recycle Bin" is anything touched."""
    import library_delete as ld
    app = page.app
    try:
        plan = ld.plan(it)
    except Exception as e:
        messagebox.showerror("Can't delete", f"Could not work out what belongs to this item:\n{e}"); return
    win = tk.Toplevel(app); win.title("Delete from the library"); win.configure(bg=C["card"]); win.transient(app)
    win.geometry(f"720x520+{app.winfo_rootx() + 160}+{app.winfo_rooty() + 90}")
    tk.Label(win, text="\U0001F5D1  Delete this item?", font=(F, 14, "bold"), bg=C["card"], fg=C["err_fg"], anchor="w").pack(fill="x", padx=20, pady=(16, 2))
    tk.Label(win, text=it["title"], font=(F, 11, "bold"), bg=C["card"], fg=C["text"], anchor="w", justify="left",
             wraplength=670).pack(fill="x", padx=20)
    files = [f for f in plan["files"] if "_work" not in f]
    thumbs = len(plan["files"]) - len(files)
    tk.Label(win, text=f"These {len(files)} file(s) go to the Recycle Bin (you can restore them from there):", font=(F, 9),
             bg=C["card"], fg=C["dim"], anchor="w").pack(fill="x", padx=20, pady=(12, 4))
    box = tk.Frame(win, bg=C["card"], highlightthickness=1, highlightbackground=C["line"]); box.pack(fill="both", expand=True, padx=20)
    t = tk.Text(box, font=("Consolas", 9), bg="#fbfaf7", fg=C["text"], relief="flat", wrap="none", height=12, padx=8, pady=6)
    sb = ttk.Scrollbar(box, command=t.yview); t.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y"); t.pack(fill="both", expand=True)
    last = None
    for f in sorted(files, key=lambda f: (os.path.dirname(f), f)):
        d = os.path.dirname(ld.rel(f))
        if d != last:
            t.insert("end", ("\n" if last is not None else "") + f"In {d or RESEARCH}/\n"); last = d
        size = os.path.getsize(f) if os.path.isfile(f) else 0
        t.insert("end", ("   \U0001F4C1 " if os.path.isdir(f) else "   ") + os.path.basename(f)
                 + (f"   ({size / 1e6:.1f} MB)" if size > 1e6 else "")
                 + ("   \u2190 your note" if os.path.normcase(f) == os.path.normcase(app.notes.path(it)) else "") + "\n")
    if plan["edits"] or plan["notes"] or thumbs:
        t.insert("end", "\nAlso:\n")
        for d, _ in plan["edits"]:
            t.insert("end", "   - " + d + "\n")
        if thumbs:
            t.insert("end", f"   - remove {thumbs} cached thumbnail(s)\n")
        for n in plan["notes"]:
            t.insert("end", "   - " + n + "\n")
    t.config(state="disabled")
    row = tk.Frame(win, bg=C["card"]); row.pack(fill="x", padx=20, pady=14)

    def go():
        win.destroy()
        page.close_reader()   # lets go of the open PDF / pictures first, so Windows can move them
        app.update()
        errs = ld.execute(plan)
        app.notes.cache.pop(it["path"], None)
        app.favs.d = load_json(FAV_FILE, {}).get("items", {})
        items = [i for i in app.lib.items if i["path"] != it["path"]]
        app.lib._done(items)   # every page refreshes without the item
        for f in list(app.favs.listeners):
            try:
                f()
            except tk.TclError:
                pass
        def catalog():   # CATALOG.json / README in the background
            for script in ("20_catalog.py", "21_readme.py"):
                subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe"),
                                os.path.join(os.path.dirname(os.path.abspath(__file__)), script)], cwd=RESEARCH,
                               capture_output=True, creationflags=0x08000000)
        threading.Thread(target=catalog, daemon=True).start()
        if errs:
            messagebox.showwarning("Deleted, with problems", "The item was deleted, but:\n\n" + "\n".join(errs[:12]))
    Btn(row, "Cancel", win.destroy, "secondary", 10, 18, 6).pack(side="right")
    d = Btn(row, "\U0001F5D1  Move to Recycle Bin", go, "primary", 10, 18, 6)
    d.c_bg, d.c_hov = C["err_fg"], "#7d2219"; d.config(bg=C["err_fg"]); d.pack(side="right", padx=(0, 8))
    win.bind("<Escape>", lambda e: win.destroy())
    win.grab_set(); win.focus_set()


# ======================================================================= text helpers
FM = re.compile(r"\A---\n.*?\n---\n", re.S)


def read_md(it, limit=None):
    if not it.get("file"):
        return it.get("text", "")
    try:
        with open(abspath(it["file"]), encoding="utf-8", errors="replace") as fh:
            return fh.read(limit) if limit else fh.read()
    except OSError:
        return ""


SKIP = re.compile(r"^(#|!\[|\*\*[A-Z][\w ]{0,25}:\*\*|<|\||\[Page|```|---|>|Part of |\*Source|\[\!\[|Video:|\s*$)")
BOILER = ("extracted from", "recipe email,", "saved on facebook from", "video and audio links", "source:", "license:")


def plain(s):
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<(https?://[^>]+)>", r"\1", s)
    return re.sub(r"[*_`]+", "", s).strip()


def snippet(it, n=170):
    if it.get("zim"):
        return (it.get("desc") or "")[:n]
    key = f"_snip{n}"
    if key not in it:
        it[key] = _snippet(it, n)
    return it[key]


def _snippet(it, n):
    if it["type"] == "recipe-card":
        return " ".join(it.get("text", "").split())[:n] or "Recipe card photo"
    if not it.get("file"):
        if it.get("module"):
            return it["module"] + (" \u2022 audio lesson" if it["type"] == "audio" else " \u2022 lesson video")
        return "Recipe video - click to watch."
    body = FM.sub("", read_md(it, 60000), 1)
    if "\n## Wikipedia article" in body:   # field guides: photos + credits come first, the description after
        body = body.split("\n## Wikipedia article", 1)[1]
    out = []
    for line in body.splitlines():
        l = line.strip()
        if SKIP.match(l) or plain(l).lower().startswith(BOILER) or "rights reserved" in l or l.lower().startswith(
                ("**source", "**license", "**original", "**video", "**author", "**recipe pdf")):
            continue
        l = plain(re.sub(r"^([-*+]|\d+[.)])\s+", "", l))
        if len(l) < 3:
            continue
        out.append(l)
        if sum(len(x) for x in out) > n:
            break
    s = " \u00b7 ".join(out) if out and len(out[0]) < 60 else " ".join(out)
    return (s[:n].rsplit(" ", 1)[0] + "\u2026") if len(s) > n else s


# ======================================================================= an item's pictures
JUNK_CAP = re.compile(r"^[\w.-]+\.(jpe?g|png|gif|webp|svg|tiff?|bmp)$|^[A-Za-z0-9]{10,24}$", re.I)


def gallery_images(it):
    """Every picture that belongs to an item, in the order the page uses them: [(absolute path, caption)]."""
    if it.get("zim"):
        return list(it.get("gallery") or [])
    if it["type"] == "recipe-card":
        p = abspath(it.get("original"))
        return [(p, it["title"])] if os.path.exists(p) else []
    if not it.get("file"):
        return []
    md = abspath(it["file"]); base = md[:-3]
    out, seen = [], set()

    def add(p, cap=""):
        k = os.path.normcase(os.path.normpath(p))
        if k not in seen and os.path.exists(p) and p.lower().endswith(IMG_EXT):
            seen.add(k)
            cap = cap.strip()
            out.append((p, "" if JUNK_CAP.match(cap) else cap))
    for e in IMG_EXT:   # recipe photo saved beside the page
        add(base + e)
    for m in re.finditer(r"!\[([^\]]*)\]\(<?([^)>]+?)>?\)", FM.sub("", read_md(it), 1)):
        if not m[2].startswith("http"):
            add(os.path.normpath(os.path.join(os.path.dirname(md), unquote(m[2]))), m[1])
    d = base + "_images"
    if os.path.isdir(d):
        for f in sorted(os.listdir(d), key=natural):
            add(os.path.join(d, f))
    return out


def fit_image(path, w, h):
    im = Image.open(path); im.seek(0)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    if im.mode == "RGBA":   # transparent diagrams on white
        bg = Image.new("RGB", im.size, "#ffffff"); bg.paste(im, mask=im.split()[3]); im = bg
    im.thumbnail((w, h), Image.LANCZOS)
    return im


# ======================================================================= thumbnails
def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def thumb_sources(it):
    """Candidate pictures for an item, best first: ('image'|'video'|'pdf', absolute path)."""
    if it.get("zim"):
        return [("image", g[0]) for g in (it.get("gallery") or [])[:3]] + \
               ([("pdf", it["original"])] if (it.get("original") or "").lower().endswith(".pdf") else [])
    out = []
    orig = abspath(it.get("original"))
    if it["type"] == "recipe-card" and orig:
        return [("image", orig)]
    if it.get("file"):
        md = abspath(it["file"]); base = md[:-3]
        for e in IMG_EXT:
            if os.path.exists(base + e):
                out.append(("image", base + e)); break
        head = read_md(it, 80000)
        for m in re.finditer(r"!\[[^\]]*\]\(<?([^)>]+?)>?\)", FM.sub("", head, 1)):
            p = m[1]
            if not p.startswith("http") and p.lower().split("?")[0].endswith(IMG_EXT):
                p = os.path.normpath(os.path.join(os.path.dirname(md), unquote(p)))
                if os.path.exists(p):
                    out.append(("image", p)); break
        d = base + "_images"
        if os.path.isdir(d):
            fs = sorted(f for f in os.listdir(d) if f.lower().endswith(IMG_EXT))
            if fs:
                out.append(("image", os.path.join(d, fs[0])))
        if os.path.exists(base + "-video.mp4"):
            out.append(("video", base + "-video.mp4"))
    if orig.lower().endswith(VID_EXT):
        out.append(("video", orig))
    if orig.lower().endswith(".pdf"):
        out.append(("pdf", orig))
    elif it.get("file") and os.path.exists(abspath(it["file"])[:-3] + ".pdf"):
        out.append(("pdf", abspath(it["file"])[:-3] + ".pdf"))
    return out


def render_source(kind, path, w, h):
    """PIL image w x h, or None."""
    if kind == "image":
        im = Image.open(path)
        im.seek(0)
        im = ImageOps.exif_transpose(im).convert("RGB")
        if im.width < 40 or im.height < 40:   # icons / spacer gifs
            return None
        return ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.35))
    if kind == "pdf":
        import pymupdf
        doc = pymupdf.open(path)
        pg = doc[0]
        z = (w * 2) / max(pg.rect.width, 1)
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
        return ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.0))
    if kind == "video":
        exe = ffmpeg()
        if not exe:
            return None
        tmp = os.path.join(THUMBS, f"_frame{threading.get_ident()}.jpg")
        for ss in ("4", "1", "0"):
            r = subprocess.run([exe, "-y", "-loglevel", "error", "-ss", ss, "-i", path, "-frames:v", "1", "-vf", "scale=640:-2", tmp],
                               capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=60)
            if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp):
                break
        else:
            return None
        im = ImageOps.fit(Image.open(tmp).convert("RGB"), (w, h), Image.LANCZOS)
        os.remove(tmp)
        d = ImageDraw.Draw(im, "RGBA")   # play badge
        r = min(w, h) // 6; cx, cy = w // 2, h // 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(0, 0, 0, 140))
        d.polygon([(cx - r // 3, cy - r // 2), (cx - r // 3, cy + r // 2), (cx + r // 2, cy)], fill=(255, 255, 255, 230))
        return im
    return None


def make_picture(it, w, h):
    for kind, p in thumb_sources(it):
        try:
            im = render_source(kind, p, w, h)
            if im:
                return im
        except Exception:
            continue
    return None


class Thumbs:
    """One background worker makes thumbnails (cached as JPEG). Each view has its own queue, and the view that asked
    most recently is served first, so the page you are looking at fills in first and nothing is lost."""
    def __init__(self, root):
        self.root, self.queues, self.lock = root, {}, threading.Condition()
        threading.Thread(target=self.work, daemon=True).start()

    def cache(self, it, size):
        h = hashlib.md5((it["path"] + f"|{size[0]}x{size[1]}").encode()).hexdigest()
        return os.path.join(THUMBS, h + ".jpg"), os.path.join(THUMBS, h + ".none")

    def cached(self, it, size=(TW, TH)):
        jpg, none = self.cache(it, size)
        got = jpg if os.path.exists(jpg) else (none if os.path.exists(none) else None)
        if got and it.get("file"):   # page rebuilt since the picture was made (e.g. its photos changed) -> make it again
            try:
                if os.path.getmtime(abspath(it["file"])) > os.path.getmtime(got):
                    os.remove(got)
                    return None
            except OSError:
                pass
        return None if got is None else (jpg if got == jpg else "none")

    def request(self, batch, size, callback):
        self.request_pairs([(it, size) for it in batch], callback)

    def request_pairs(self, pairs, callback):
        """pairs: [(item, (w, h))]; callback(item, path_or_None) runs on the Tk thread. A new request from the same
        callback replaces its old one (e.g. a new page of results)."""
        with self.lock:
            self.queues.pop(callback, None)
            self.queues[callback] = list(pairs)
            self.lock.notify()

    def work(self):
        while True:
            with self.lock:
                while not any(self.queues.values()):
                    self.lock.wait()
                cb = next(c for c in reversed(list(self.queues)) if self.queues[c])
                it, size = self.queues[cb].pop(0)
            jpg, none = self.cache(it, size)
            if not (os.path.exists(jpg) or os.path.exists(none)):
                im = make_picture(it, *size)
                if im:
                    im.save(jpg, quality=86)
                else:
                    open(none, "w").close()
            res = jpg if os.path.exists(jpg) else None
            self.root.after(0, lambda it=it, res=res, cb=cb: cb(it, res))


def placeholder(parent, it, w, h, big=False):
    """Coloured tile with an icon, used until (or instead of) a picture."""
    col = TILE[int(hashlib.md5((it.get("module") or it.get("category") or "").encode()).hexdigest(), 16) % len(TILE)]
    f = tk.Frame(parent, bg=col, width=w, height=h)
    f.pack_propagate(False)
    tk.Label(f, text=TYPE_ICON.get(it["type"], "\U0001F4C3"), font=("Segoe UI Emoji", 30 if big else (22 if h > 100 else 16)),
             bg=col, fg="#ffffff").pack(expand=True)
    return f


# ======================================================================= scrolling container
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg, jump=False, hscroll=False):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.on_scroll)
        self.hscroll = hscroll
        if hscroll:   # content wider than the window (a zoomed-in PDF page) scrolls sideways too
            self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(xscrollcommand=self.hsb.set)
            self.hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True); self.sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: (self.fit_width(), self.canvas.configure(scrollregion=self.canvas.bbox("all"))))
        self.canvas.bind("<Configure>", lambda e: self.fit_width(e.width))
        self.canvas.on_wheel = self.wheel
        self.listeners, self.on_bottom, self.on_top, self.jumps, self.on_edge = [], None, None, None, None
        if jump:   # floating "Top" / "Bottom" buttons, shown only when the list is long enough to scroll
            self.jumps = tk.Frame(self, bg=bg)
            for text, cmd in (("\u25b2  Top", self.go_top), ("\u25bc  Bottom", self.go_bottom)):
                b = tk.Label(self.jumps, text=text, font=(F, 8, "bold"), bg=C["primary"], fg="#ffffff", padx=9, pady=3, cursor="hand2")
                b.pack(fill="x", pady=(0, 3))
                b.bind("<Button-1>", lambda e, c=cmd: c())
                b.bind("<Enter>", lambda e, b=b: b.config(bg=C["primary_hover"]))
                b.bind("<Leave>", lambda e, b=b: b.config(bg=C["primary"]))

    def fit_width(self, width=None):
        w = width or self.canvas.winfo_width()
        if self.hscroll:
            w = max(w, self.inner.winfo_reqwidth())
        self.canvas.itemconfigure(self.win, width=w)

    def on_scroll(self, a, b):
        self.sb.set(a, b)
        if self.jumps:
            if float(a) > 0.0 or float(b) < 1.0:
                self.jumps.place(in_=self.canvas, relx=1.0, rely=1.0, x=-10, y=-8, anchor="se")
                self.jumps.lift()
            else:
                self.jumps.place_forget()
        for f in self.listeners:
            f(float(a), float(b))

    def go_top(self):
        if self.on_top:
            self.on_top()
        self.canvas.yview_moveto(0)

    def go_bottom(self):
        if self.on_bottom:   # lists that build their cards bit by bit decide how to get there
            self.on_bottom()
        else:
            self.update_idletasks(); self.canvas.yview_moveto(1.0)

    def wheel(self, e):
        if self.hscroll and e.state & 0x1:   # Shift + wheel: sideways
            return self.canvas.xview_scroll(int(-e.delta / 120) * 3, "units")
        d = 1 if e.delta < 0 else -1
        top, bottom = self.canvas.yview() if self.inner.winfo_height() > self.canvas.winfo_height() else (0.0, 1.0)
        if self.on_edge and (d > 0 and bottom >= 0.999 or d < 0 and top <= 0.001):
            return self.on_edge(d)   # wheel past the end of a PDF page: on to the next / previous page
        if self.inner.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120) * 3, "units")

    def top(self):
        self.canvas.yview_moveto(0)

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.top()

    def position(self):
        return self.canvas.canvasy(0)

    def restore(self, px):
        self.update_idletasks()
        h = self.inner.winfo_height()
        if h > 0:
            self.canvas.yview_moveto(min(px / h, 1.0))


# ======================================================================= shared card + reader handling
class ItemView(tk.Frame):
    """Base for pages that show item cards (with thumbnail and favourite star) and open them in a Reader."""
    show_log = False

    def init_view(self, app, title, subtitle):
        self.app, self.title, self.subtitle = app, title, subtitle
        self.slots, self.photos, self.stars, self.note_badges = {}, {}, {}, {}
        app.favs.listeners.append(self.paint_stars)
        app.notes.listeners.append(self.paint_notes)

    def reset_cards(self):
        self.slots, self.photos, self.stars, self.note_badges = {}, {}, {}, {}

    def make_card(self, parent, it, w=TW, h=TH, lines=True, title=None, meta=None):
        f = tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["line"], cursor="hand2")
        box = tk.Frame(f, bg=C["card"], width=w, height=h); box.pack(); box.pack_propagate(False)
        ph = placeholder(box, it, w, h); ph.pack(fill="both", expand=True)
        self.slots[it["path"]] = box
        txt = tk.Frame(f, bg=C["card"], width=w, height=112 if lines else (54 if h > 100 else 52)); txt.pack(fill="x")
        txt.pack_propagate(False)
        title = title or it["title"]
        if len(title) > (60 if lines else 48):
            title = title[:(58 if lines else 46)].rsplit(" ", 1)[0] + "\u2026"
        t = tk.Label(txt, text=title, font=(F, 9 if w > 160 else 8, "bold"), bg=C["card"], fg=C["text"], wraplength=w - 16,
                     justify="left", anchor="nw")
        t.pack(fill="x", padx=8, pady=(6, 0))
        if meta is None:
            meta = tname(it["type"]) + ("  \u2022  " + nice(it["category"]) if it.get("category") and it["category"] != "recipes" else "")
            if it.get("module") and lines:
                meta = tname(it["type"]) + "  \u2022  " + re.sub(r"^Module (\d+):.*", r"Module \1", it["module"])
            if getattr(self, "sort_v", None) is not None and self.sort_v.get() != SORTS[0]:
                meta = tname(it["type"]) + "  \u2022  " + (it.get("date") or "date unknown")
        m = tk.Label(txt, text=meta, font=(F, 8), bg=C["card"], fg=C["accent"], anchor="w")
        m.pack(fill="x", padx=8, pady=(1, 0))
        ws = [f, box, txt, t, m]
        if lines:
            s = tk.Label(txt, text=snippet(it, 110), font=(F, 8), bg=C["card"], fg=C["dim"], wraplength=w - 16, justify="left", anchor="nw")
            s.pack(fill="both", expand=True, padx=8, pady=(3, 6)); ws.append(s)
        for wd in ws + list(ph.winfo_children()) + [ph]:
            wd.bind("<Button-1>", lambda e: self.open_item(it))
            wd.bind("<Enter>", lambda e: f.config(highlightbackground=C["primary"]))
            wd.bind("<Leave>", lambda e: f.config(highlightbackground=C["line"]))
        npics = it.get("images") or (1 if it["type"] == "recipe-card" else 0)
        if npics > 1 and h > 100:
            badge = tk.Label(f, text=f"\U0001F4F7 {npics}", font=("Segoe UI Emoji", 8), bg="#24302a", fg="#ffffff", padx=5, pady=1)
            badge.place(in_=box, relx=0.0, rely=1.0, x=5, y=-5, anchor="sw")
            badge.bind("<Button-1>", lambda e: self.open_item(it, "Pictures"))
        star = tk.Label(f, font=("Segoe UI Symbol", 11 if h > 100 else 9), bg="#ffffff", cursor="hand2", padx=3, pady=0, bd=0)
        star.place(in_=box, relx=1.0, x=-5, y=5, anchor="ne")
        star.bind("<Button-1>", lambda e: (self.app.favs.toggle(it), "break")[1])
        self.stars.setdefault(it["path"], []).append((star, it))
        self.paint_star(star, it)
        nb = tk.Label(f, text="\U0001F4DD", font=("Segoe UI Emoji", 9 if h > 100 else 8), bg="#fff4cc", fg="#7a5a00",
                      padx=3, pady=0, bd=0, cursor="hand2")
        nb.bind("<Button-1>", lambda e: (self.open_item(it, "Note"), "break")[1])
        self.note_badges.setdefault(it["path"], []).append((nb, box, it))
        self.paint_note(nb, box, it)
        return f

    def paint_star(self, star, it):
        on = self.app.favs.has(it)
        star.config(text=STAR_ON if on else STAR_OFF, fg=C["accent"] if on else "#8a918c")

    def paint_note(self, nb, box, it):
        if self.app.notes.has(it):
            nb.place(in_=box, relx=1.0, rely=1.0, x=-5, y=-5, anchor="se"); nb.lift()
        else:
            nb.place_forget()

    def paint_notes(self):
        for lst in self.note_badges.values():
            for nb, box, it in lst:
                if nb.winfo_exists():
                    self.paint_note(nb, box, it)

    def paint_stars(self):
        for path, lst in self.stars.items():
            for star, it in lst:
                if star.winfo_exists():
                    self.paint_star(star, it)
        if self.reader.winfo_ismapped():
            self.reader.paint_fav()

    def load_thumbs(self, pairs):
        """pairs [(item, size)]: show cached pictures now, queue the rest."""
        todo = []
        for it, size in pairs:
            got = self.app.thumbs.cached(it, size)
            if got and got != "none":
                self.set_thumb(it, got)
            elif not got:
                todo.append((it, size))
        self.pending = todo
        if todo:
            self.app.thumbs.request_pairs(todo, self.set_thumb)

    def set_thumb(self, it, path):
        box = self.slots.get(it["path"])
        if not path or not box or not box.winfo_exists():
            return
        try:
            img = ImageTk.PhotoImage(Image.open(path))
        except Exception:
            return
        self.photos[it["path"]] = img
        for w in box.winfo_children():
            w.destroy()
        l = tk.Label(box, image=img, bg=C["card"], bd=0, cursor="hand2"); l.pack(fill="both", expand=True)
        l.bind("<Button-1>", lambda e: self.open_item(it))

    def requeue_thumbs(self):
        todo = [(i, s) for i, s in getattr(self, "pending", []) if self.app.thumbs.cached(i, s) is None]
        if todo:   # put this view's missing thumbnails first in line
            self.app.thumbs.request_pairs(todo, self.set_thumb)

    def open_item(self, it, tab=None):
        self.listview.pack_forget()
        self.reader.pack(fill="both", expand=True)
        self.reader.show(it, tab)

    def close_reader(self):
        self.reader.pack_forget(); self.reader.clear()
        self.listview.pack(fill="both", expand=True)

    def neighbors(self, it):
        return None

    def restart(self):
        """Menu click: back to the section's starting point (subclasses reset their filters too)."""
        if self.reader.winfo_manager():   # placed, even if this section isn't on screen right now
            self.close_reader()

    def jump(self, where):
        if self.reader.winfo_ismapped():   # reading: Top / Bottom of the page
            return self.reader.jump(where)
        sf = getattr(self, "scroll", None) or getattr(self, "body", None)
        if sf:
            (sf.go_top if where == "top" else sf.go_bottom)()

    def display_title(self, it):
        return it["title"]

    def on_show(self):
        self.requeue_thumbs()


def section_title(parent, text, count=None, bg="bg"):
    f = tk.Frame(parent, bg=C[bg]); f.pack(fill="x", pady=(16, 6))
    label(f, text, 12, True, bg=bg).pack(side="left")
    if count is not None:
        label(f, f"  {count}", 10, fg="dim", bg=bg).pack(side="left", pady=(3, 0))
    return f


# ======================================================================= browse page
class BrowsePage(ItemView):
    """A searchable grid of item cards with thumbnails; clicking a card opens the reader."""

    def __init__(self, app, title, subtitle, base, chips=None, cat_filter=False, type_filter=False):
        super().__init__(app.content, bg=C["bg"])
        self.init_view(app, title, subtitle)
        self.base = base
        # chips: one row [(name, filter)], or several rows [[...], [...]] (e.g. Local Area: view + plant type)
        self.chipsets = (chips if isinstance(chips[0], list) else [chips]) if chips else []
        self.sel = [c[0][0] for c in self.chipsets]
        self.items, self.shown, self.page, self.cols, self.chunk = [], [], 0, 4, []
        self.cat_v, self.type_v, self.q = tk.StringVar(value="All categories"), tk.StringVar(value="All types"), tk.StringVar()

        self.listview = tk.Frame(self, bg=C["bg"]); self.listview.pack(fill="both", expand=True)
        bar0 = tk.Frame(self.listview, bg=C["bg"]); bar0.pack(fill="x", pady=(0, 8))
        bar = tk.Frame(bar0, bg=C["bg"]); bar.pack(side="right")   # packed first: keeps its width when the window narrows
        self.search_entry = search_box(bar0, self.q, self.debounce)
        if cat_filter:
            cb = ttk.Combobox(bar, textvariable=self.cat_v, values=["All categories"] + CAT_LIST, state="readonly", font=(F, 10), width=26)
            cb.pack(side="left", padx=(8, 0), ipady=3); cb.bind("<<ComboboxSelected>>", lambda ev: self.refilter())
        if type_filter:
            self.type_cb = ttk.Combobox(bar, textvariable=self.type_v, state="readonly", font=(F, 10), width=17)
            self.type_cb.pack(side="left", padx=(8, 0), ipady=3); self.type_cb.bind("<<ComboboxSelected>>", lambda ev: self.refilter())
        saved = load_json(SETTINGS_FILE, {}).get("sort", {}).get(title, SORTS[0])
        self.sort_v = tk.StringVar(value=saved if saved in SORTS else SORTS[0])
        label(bar, "Sort", 9, fg="dim", bg="bg").pack(side="left", padx=(10, 4))
        sc = ttk.Combobox(bar, textvariable=self.sort_v, values=SORTS, state="readonly", font=(F, 10), width=13)
        sc.pack(side="left", ipady=3); sc.bind("<<ComboboxSelected>>", lambda ev: self.set_sort())
        self.chipbox = tk.Frame(self.listview, bg=C["bg"]); self.chipbox.pack(fill="x")
        self.chip_w = chip_rows(self.chipbox, self.chipsets, self.sel, self.set_chip)
        self.count = label(self.listview, "Loading the library...", 9, fg="dim", bg="bg"); self.count.pack(fill="x")
        self.scroll = ScrollFrame(self.listview, C["bg"], jump=True); self.scroll.pack(fill="both", expand=True, pady=(6, 0))
        self.scroll.on_bottom = self.jump_bottom
        self.scroll.on_top = self.cancel_bottom
        self.grid = self.scroll.inner
        pager = Flow(self.listview, C["bg"], gap=4); pager.pack(fill="x", pady=(8, 0))   # wraps in a narrow window
        self.first_b = pager.add(Btn(pager, "\u00ab", lambda: self.goto(0), "secondary", 9, 10, 4))
        self.prev_b = pager.add(Btn(pager, "\u2039  Previous", lambda: self.goto(self.page - 1), "secondary", 9, 12, 4), gap=10)
        pf = tk.Frame(pager, bg=C["bg"])
        label(pf, "Page", 9, fg="dim", bg="bg").pack(side="left")
        self.page_v = tk.StringVar(value="1")
        pe = tk.Entry(pf, textvariable=self.page_v, width=4, justify="center", font=(F, 9), relief="flat", bg="#fbfaf7",
                      highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["primary"])
        pe.pack(side="left", padx=5, ipady=2)
        pe.bind("<Return>", lambda e: self.goto_typed())
        self.pages_l = label(pf, "of 1", 9, fg="dim", bg="bg"); self.pages_l.pack(side="left")
        pager.add(pf, gap=10)
        self.next_b = pager.add(Btn(pager, "Next  \u203a", lambda: self.goto(self.page + 1), "secondary", 9, 12, 4))
        self.last_b = pager.add(Btn(pager, "\u00bb", lambda: self.goto(10 ** 9), "secondary", 9, 10, 4), gap=18)
        self.size = "All"
        self.range_l = label(pager, "", 9, fg="dim", bg="bg"); pager.add(self.range_l, gap=14)
        sz = tk.Frame(pager, bg=C["bg"])
        label(sz, "Show", 9, fg="dim", bg="bg").pack(side="left", padx=(0, 6))
        self.size_w = {}
        for n in PAGE_SIZES:
            l = tk.Label(sz, text=n, font=(F, 9), padx=9, pady=3, cursor="hand2")
            l.pack(side="left", padx=(0, 3))
            l.bind("<Button-1>", lambda e, n=n: self.set_size(n))
            self.size_w[n] = l
        pager.add(sz)
        self.paint_sizes()
        self.scroll.canvas.bind("<Configure>", self.resized, add="+")
        self.scroll.listeners.append(lambda a, b: self.scrolled(b))
        self.gen, self.rendered, self.thumb_pairs, self._more, self.restore_to = 0, 0, [], False, None
        self.reader = Reader(self)
        self._after = None
        app.lib.on_ready(self.loaded)

    def set_sort(self):
        st = load_json(SETTINGS_FILE, {})
        st.setdefault("sort", {})[self.title] = self.sort_v.get()
        save_json(SETTINGS_FILE, st)
        self.refilter()

    def sort_items(self, items):
        """Title A-Z (the library order), or by date added - items with no known date always go last."""
        s = self.sort_v.get()
        if s == SORTS[0]:
            return items
        dated = sorted((i for i in items if i.get("date")), key=lambda i: (i["date"], i["key"]), reverse=(s == SORTS[1]))
        return dated + [i for i in items if not i.get("date")]

    def set_chip(self, n, k=0):
        self.sel[k] = n; paint_chips(self.chip_w, self.sel); self.refilter()

    def restart(self):
        super().restart()
        self.q.set("")
        self.cat_v.set("All categories"); self.type_v.set("All types")
        self.sel = [c[0][0] for c in self.chipsets]
        paint_chips(self.chip_w, self.sel)
        if self.size != "All":
            self.size = "All"; self.paint_sizes()
        if self.app.lib.ready:
            self.refilter()

    def set_category(self, cat):
        self.cat_v.set(nice(cat) if cat else "All categories"); self.q.set(""); self.close_reader(); self.refilter()

    def loaded(self):
        self.items = [i for i in self.app.lib.items if self.base(i)]
        if hasattr(self, "type_cb"):
            types = sorted({i["type"] for i in self.items if i["type"]}, key=tname)
            self.type_names = {tname(t): t for t in types}
            self.type_cb.config(values=["All types"] + list(self.type_names))
        self.refilter(keep=bool(self.shown))

    def debounce(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(250, self.refilter)

    def refilter(self, keep=False):
        q = self.q.get().lower().split()
        cat = CAT_NAMES.get(self.cat_v.get())
        typ = getattr(self, "type_names", {}).get(self.type_v.get())
        fs = [f for k, cs in enumerate(self.chipsets) if (f := dict(cs).get(self.sel[k]))]
        self.shown = self.sort_items([i for i in self.items if (not cat or i["category"] == cat) and (not typ or i["type"] == typ)
                                      and all(f(i) for f in fs) and all(w in i["search"] for w in q)])
        if keep:
            self.goto(self.page, restore=(self.scroll.position(), self.rendered))
        else:
            self.goto(0)

    # ------------------------------------------------------------ paging
    BATCH = 48   # cards built per step; "All" adds the next step as you scroll near the bottom

    def per_page(self):
        return None if self.size == "All" else int(self.size)

    def paint_sizes(self):
        for n, l in self.size_w.items():
            on = n == self.size
            l.config(bg=C["primary"] if on else C["sec"], fg="#ffffff" if on else C["text"], font=(F, 9, "bold" if on else "normal"))

    def set_size(self, n):
        first = self.page * (self.per_page() or 0)   # keep roughly the same items in view
        self.size = n
        self.paint_sizes()
        st = load_json(SETTINGS_FILE, {})
        st.setdefault("page_size", {})[self.title] = n
        save_json(SETTINGS_FILE, st)
        self.goto(first // self.per_page() if self.per_page() else 0)

    def goto_typed(self):
        try:
            self.goto(int(self.page_v.get()) - 1)
        except ValueError:
            self.page_v.set(str(self.page + 1))

    def resized(self, e):
        if e.width < 100 or not self.listview.winfo_ismapped():
            return
        cols = max(2, (e.width - 4) // (TW + 18))
        if cols != self.cols:
            self.cols = cols
            if self.shown:
                self.goto(self.page, restore=(self.scroll.position(), self.rendered))

    def goto(self, n, restore=None):
        self.restore_to = restore   # (scroll pixels, cards that were built) to return to once rebuilt
        pp = self.per_page()
        pages = 1 if pp is None else max(1, -(-len(self.shown) // pp))
        self.page = max(0, min(n, pages - 1))
        self.scroll.clear(); self.reset_cards()
        self.chunk = self.shown if pp is None else self.shown[self.page * pp:(self.page + 1) * pp]
        total = len(self.items)
        self.count.config(text=(f"{len(self.shown):,} of {total:,} items" if len(self.shown) != total else f"{total:,} items")
                          + (self.sort_note() if self.shown else "  -  nothing matches"))
        self.page_v.set(str(self.page + 1)); self.pages_l.config(text=f"of {pages:,}")
        on_first, on_last = self.page == 0, self.page >= pages - 1
        for b, on in ((self.first_b, not on_first), (self.prev_b, not on_first), (self.next_b, not on_last), (self.last_b, not on_last)):
            b.set_enabled(on)
        self.show_range()
        for k in range(self.cols):
            self.grid.columnconfigure(k, weight=1, uniform="g")
        self.gen += 1; self.rendered, self.thumb_pairs = 0, []
        self.render_more(self.gen)

    def show_range(self):
        pp = self.per_page()
        if not self.shown:
            self.range_l.config(text="")
        elif pp is None:
            self.range_l.config(text=f"Showing all {len(self.shown):,}" + ("  (more load as you scroll)" if len(self.shown) > self.BATCH else ""))
        else:
            a = self.page * pp
            self.range_l.config(text=f"Showing {a + 1:,}\u2013{a + len(self.chunk):,} of {len(self.shown):,}")

    def sort_note(self):
        s = self.sort_v.get()
        if s == SORTS[0]:
            return "  \u2022  sorted A-Z"
        undated = sum(1 for i in self.shown if not i.get("date"))
        return f"  \u2022  {'newest' if s == SORTS[1] else 'oldest'} first" + (f"  ({undated:,} with no known date at the end)" if undated else "")

    def render_more(self, gen):
        """Build the next batch of cards. Numbered pages keep going on their own (in steps, so the window stays
        responsive); "All" waits until you scroll near the bottom."""
        self._more = False
        if gen != self.gen:
            return
        a, b = self.rendered, min(len(self.chunk), self.rendered + self.BATCH)
        for k in range(a, b):
            self.make_card(self.grid, self.chunk[k]).grid(row=k // self.cols, column=k % self.cols, padx=6, pady=6, sticky="n")
        self.rendered = b
        new = [(it, (TW, TH)) for it in self.chunk[a:b]]
        for it, size in new:
            got = self.app.thumbs.cached(it, size)
            if got and got != "none":
                self.set_thumb(it, got)
        self.thumb_pairs += new
        # newest cards' pictures first, then earlier ones still waiting (the worker skips any already made)
        fresh = [(i, s) for i, s in new if self.app.thumbs.cached(i, s) is None]
        self.pending = fresh + ([] if a == 0 else list(getattr(self, "pending", [])))
        if self.pending:
            self.app.thumbs.request_pairs(self.pending, self.set_thumb)
        if self.restore_to:
            px, need = self.restore_to
            if b >= min(need, len(self.chunk)):
                self.restore_to = None
                self.scroll.restore(px)
                self.show_range()
            elif px >= 10 ** 9:
                self.range_l.config(text=f"Going to the bottom\u2026  {b:,} of {len(self.chunk):,}")
        if b < len(self.chunk) and (self.per_page() is not None or self.restore_to):
            self._more = True   # the chain below keeps building; don't let scrolling start a second one
            self.after(20, lambda: self.render_more(gen))

    BIG = 1200   # "Bottom" on Show: All builds at most this many more cards; beyond that it offers pages of 200

    def jump_bottom(self):
        left = len(self.chunk) - self.rendered
        if left <= 0:
            self.scroll.restore(10 ** 9); return
        if self.per_page() is None and left > self.BIG:
            if messagebox.askyesno("Go to the bottom", f"This list has {len(self.chunk):,} items - too many to show all at once.\n\n"
                                   "Switch to pages of 200 and open the last page?", parent=self):
                self.set_size("200"); self.goto(10 ** 9, restore=(10 ** 9, 200))
            return
        self.restore_to = (10 ** 9, len(self.chunk))   # build the rest, then land at the bottom
        if not self._more:
            self.render_more(self.gen)

    def cancel_bottom(self):
        if self.restore_to and self.restore_to[0] >= 10 ** 9:
            self.restore_to = None
            self.show_range()

    def jump_top(self):
        self.scroll.go_top()

    def scrolled(self, bottom):
        if self.per_page() is None and bottom > 0.85 and self.rendered < len(self.chunk) and not self._more:
            self._more = True
            self.after(30, lambda g=self.gen: self.render_more(g))

    def on_show(self):
        if not self.reader.winfo_ismapped():
            self.search_entry.focus_set()
        self.requeue_thumbs()


def search_box(parent, var, on_key, width=None):
    sf = tk.Frame(parent, bg="#fbfaf7", highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["primary"])
    sf.pack(side="left", fill="x", expand=True)
    tk.Label(sf, text="\U0001F50D", font=("Segoe UI Emoji", 10), bg="#fbfaf7", fg=C["dim"]).pack(side="left", padx=(8, 0))
    e = tk.Entry(sf, textvariable=var, font=(F, 11), relief="flat", bg="#fbfaf7", fg=C["text"], insertbackground=C["text"],
                 **({"width": width} if width else {}))
    e.pack(side="left", fill="x", expand=True, ipady=6, padx=6)
    e.bind("<KeyRelease>", lambda ev: on_key())
    return e


def chip_rows(box, chipsets, sel, on_pick):
    """Wrapping rows of filter chips; returns the widgets per set for paint_chips."""
    for w in box.winfo_children():
        w.destroy()
    out = []
    for k, chips in enumerate(chipsets):
        ws = {}
        row = Flow(box, C["bg"]); row.pack(fill="x", pady=(0, 6))   # wraps onto more lines in a narrow window
        for name, _ in chips:
            l = tk.Label(row, text=name, font=(F, 9), padx=11, pady=4, cursor="hand2")
            row.add(l)
            l.bind("<Button-1>", lambda ev, k=k, n=name: on_pick(n, k))
            ws[name] = l
        out.append(ws)
    paint_chips(out, sel)
    return out


def paint_chips(chip_w, sel):
    for k, ws in enumerate(chip_w):
        for n, l in ws.items():
            on = n == sel[k]
            l.config(bg=(C["primary"] if k == 0 else C["accent"]) if on else C["sec"], fg="#ffffff" if on else C["text"],
                     font=(F, 9, "bold" if on else "normal"))


# ======================================================================= the cooking school, in course order
LESSON = re.compile(r"^lesson\s*0*(\d+)([a-z])?(?![a-z])[\s\-\u2013\u2014:.]*(.*)$", re.I)
START = re.compile(r"^(getting started|defining|introduction|intro\b|welcome|orientation|start here)", re.I)
WEAK = {"how", "to", "how to", "more", "natural", "cooking", "the", "a", "about", "making", "corn", "portable"}


def tidy(s):
    s = re.sub(r"[\s\-\u2013\u2014&,:]+$", "", s.strip())
    return re.sub(r"\s*-?\d+$", "", s).strip()


def lesson_title(rests):
    """A lesson's name from its parts' names: their shared beginning ('No-Knead Sourdough Bread' from '... 1', '... 2'),
    or the shortest part name when the shared part is too thin ('How to', 'Corn')."""
    if len(rests) == 1:
        return tidy(rests[0]) or rests[0]
    p = os.path.commonprefix([r.lower() for r in rests])
    if any(len(r) > len(p) and r[len(p)].isalpha() for r in rests) and p and p[-1].isalpha():
        p = p[:p.rfind(" ") + 1] if " " in p else ""   # don't cut a word in half
    p = tidy(rests[0][:len(p)])
    if len(p.split()) >= 2 and p.lower() not in WEAK or (len(p) >= 6 and p.lower() not in WEAK):
        return p
    return tidy(min(rests, key=len)) or min(rests, key=len)


def build_course(items):
    """Modules in course order, each with materials, numbered lessons (parts grouped), extras - read from the module
    pages, which list everything in teaching order."""
    course = [i for i in items if is_course(i)]
    by_path = {i["path"]: i for i in course}
    dirs = sorted({i["path"].split("/")[2] for i in course if i["path"].count("/") >= 3}, key=natural)
    mods = []
    for d in dirs:
        page = by_path.get(f"{WARDEE}/{d}/{d}.md")
        title = page["title"] if page else d
        m = re.match(r"Module (\d+):\s*(.*)", title)
        mod = {"dir": d, "title": title, "num": m[1] if m else "", "short": m[2] if m else title, "page": page,
               "materials": [], "start": [], "lessons": [], "more": [], "audio": [], "qa": [], "other": []}
        placed, lessons = set(), {}
        text = read_md(page) if page else ""
        for sec in re.split(r"^## ", FM.sub("", text, 1), flags=re.M)[1:]:
            head = sec.split("\n", 1)[0].lower()
            for link in re.findall(r"^- \[[^\]]*\]\(([^)]+)\)", sec, re.M):
                it = by_path.get(f"{WARDEE}/{d}/{unquote(link)}")
                if not it or it["path"] in placed:
                    continue
                placed.add(it["path"])
                if head.startswith("ebooks"):
                    mod["materials"].append(it); continue
                if head.startswith("q&a"):
                    mod["qa"].append(it); continue
                if head.startswith("other"):
                    mod["other"].append(it); continue
                name = os.path.splitext(os.path.basename(it["path"]))[0]
                lm = LESSON.match(name)
                if START.match(name):
                    mod["start"].append(it)
                elif lm:
                    key = (int(lm[1]), (lm[2] or "").lower())
                    lessons.setdefault(key, []).append((it, lm[3].strip()))
                else:
                    mod["audio" if it["type"] == "audio" else "more"].append(it)
        for it in course:   # anything the page doesn't list
            if it["path"].startswith(f"{WARDEE}/{d}/") and it["path"] not in placed and it is not page:
                (mod["materials"] if it.get("file") else mod["other"]).append(it)
        for key in sorted(lessons):
            parts = sorted(lessons[key], key=lambda p: (p[0]["type"] == "audio", natural(p[1].replace(" ", ""))))
            rests = [r for _, r in parts]
            title = lesson_title(rests) or f"Lesson {key[0]}"
            caps = []
            for k, (it, r) in enumerate(parts):
                c = r[len(title):].strip(" -\u2013\u2014,&") if r.lower().startswith(title.lower()) else r
                if re.fullmatch(r"-?\d+", c or ""):
                    c = "Part " + c.lstrip("-")
                caps.append(c or ("Audio" if it["type"] == "audio" else ("Video" if len(parts) == 1 else f"Part {k + 1}")))
            mod["lessons"].append({"num": f"{key[0]}{key[1]}", "title": title, "parts": [p[0] for p in parts], "caps": caps})
        mods.append(mod)
    return mods


class TopicPage(BrowsePage):
    """A section that opens on a page of topic tiles; clicking a tile drills into a normal browse list for that topic,
    with buttons for the topic's own groups and '◀ All topics' to go back (Local Area).
    topics: [(name, icon, blurb, filter, [(sub-button name, filter), ...])] - a topic with exactly one page opens it."""
    COLS = 3

    def __init__(self, app, title, subtitle, base, topics, unit="page"):
        self.topics, self.topic, self.unit = topics, None, unit
        super().__init__(app, title, subtitle, base, [("All", None)])
        # bar above the list: back to the tiles + the topic's name
        self.topbar = tk.Frame(self.listview, bg=C["bg"])
        self.topbar.pack(fill="x", pady=(0, 8), before=self.listview.winfo_children()[0])
        Btn(self.topbar, "◀  All topics", self.show_topics, "secondary", 9, 12, 4).pack(side="left")
        self.topic_l = label(self.topbar, "", 13, True, bg="bg")
        self.topic_l.pack(side="left", padx=12)
        self.topic_btns = tk.Frame(self.topbar, bg=C["bg"]); self.topic_btns.pack(side="right")
        self.actions = {}   # topic name -> [(button text, command)], shown at the right of the topic bar
        self.hints = {}     # topic name -> a line of help under the topic bar (e.g. Maps: search by position)
        self.hint_l = label(self.listview, "", 9, fg="dim", bg="bg", wraplength=900)
        self.home = tk.Frame(self, bg=C["bg"])
        self.home_scroll = ScrollFrame(self.home, C["bg"])
        self.home_scroll.pack(fill="both", expand=True)
        self.tiles = {}
        self.show_topics()

    # ------------------------------------------------------------ the tiles
    def counts(self):
        return {t[0]: sum(1 for i in self.items if t[3](i)) for t in self.topics}

    def paint_tiles(self):
        box = self.home_scroll.inner
        for w in box.winfo_children():
            w.destroy()
        n = self.counts() if self.items else {}
        for c in range(self.COLS):
            box.grid_columnconfigure(c, weight=1, uniform="tile")
        for k, (name, icon, blurb, flt, subs) in enumerate(self.topics):
            t = tk.Frame(box, bg=C["card"], cursor="hand2", highlightthickness=1, highlightbackground=C["line"])
            t.grid(row=k // self.COLS, column=k % self.COLS, sticky="nsew", padx=6, pady=6)
            parts = [tk.Label(t, text=icon, font=("Segoe UI Emoji", 26), bg=C["card"]),
                     label(t, name, 13, True), label(t, blurb, 9, fg="dim", wraplength=250),
                     label(t, (f"{n.get(name, 0):,} {self.unit}" + ("s" if n.get(name, 0) != 1 else "")) if n else "loading...", 9, fg="primary")]
            parts[0].pack(anchor="w", padx=14, pady=(10, 0))
            for p in parts[1:]:
                p.pack(anchor="w", padx=14, pady=(2, 0), fill="x")
            parts[-1].pack_configure(pady=(4, 12))
            for w in [t] + parts:
                w.bind("<Button-1>", lambda e, k=k: self.open_topic(k))
                w.bind("<Enter>", lambda e, t=t: t.config(highlightbackground=C["primary"]))
                w.bind("<Leave>", lambda e, t=t: t.config(highlightbackground=C["line"]))

    def show_topics(self):
        if self.reader.winfo_manager():
            self.reader.pack_forget(); self.reader.clear()
        self.listview.pack_forget()
        self.topic = None
        self.paint_tiles()
        self.home.pack(fill="both", expand=True)
        self.home_scroll.top()

    def open_topic(self, k, keep_reader=False):
        name, icon, blurb, flt, subs = self.topics[k]
        if not keep_reader:
            pages = [i for i in self.items if flt(i)]
            if len(pages) == 1:   # e.g. Start Here: open the page itself, full size (tiles hidden)
                self.set_topic(k)
                self.home.pack_forget()
                return BrowsePage.open_item(self, pages[0])
        self.set_topic(k)
        self.home.pack_forget()
        if not keep_reader:
            self.listview.pack(fill="both", expand=True)

    def set_topic(self, k):
        name, icon, blurb, flt, subs = self.topics[k]
        self.topic = k
        subs = [(s, f) for s, f in subs if not self.items or any(flt(i) and f(i) for i in self.items)]   # hide empty buttons
        chips = [(f"All {name.lower()}" if subs else name, flt)] + [(s, (lambda i, f=f, flt=flt: flt(i) and f(i))) for s, f in subs]
        self.chipsets = [chips]
        self.sel = [chips[0][0]]
        self.chip_w = chip_rows(self.chipbox, self.chipsets, self.sel, self.set_chip)
        self.topic_l.config(text=f"{icon}  {name}")
        for w in self.topic_btns.winfo_children():
            w.destroy()
        for text, cmd in self.actions.get(name, []):
            Btn(self.topic_btns, text, cmd, "secondary", 9, 12, 4).pack(side="left", padx=(8, 0))
        if self.hints.get(name):
            self.hint_l.config(text=self.hints[name])
            self.hint_l.pack(fill="x", pady=(0, 8), after=self.topbar)
        else:
            self.hint_l.pack_forget()
        self.q.set("")
        if self.app.lib.ready:
            self.refilter()

    # ------------------------------------------------------------ BrowsePage hooks
    def loaded(self):
        super().loaded()
        if self.topic is None:
            self.paint_tiles()

    COORD_RE = re.compile(r"^[\s\d.,;:°º'\"’′”″NSEWnsew+-]+$")

    def coord_query(self):
        """The search box holds a position (48.19, -114.31 / 48°11'45"N 114°18'46"W / a Google Maps link)? -> (lat, lon)."""
        q = self.q.get().strip()
        if not re.search(r"\d", q) or not (self.COORD_RE.match(q) or ("http" in q and "@" in q)):
            return None
        try:
            return wpt.parse(q)
        except ValueError:
            return None

    def refilter(self, keep=False):
        self.coord_hit = None
        if self.topic is None:   # tiles showing: nothing to list
            self.shown = []
            return
        p = self.coord_query()
        if p and any(i["type"] == "local-map" for i in self.items):
            # a position typed into the search (any Local Area topic): the map(s) it is on, detailed first; opening one
            # zooms to the spot.  The topic's own buttons narrow it (Detailed / Regional) when they leave something.
            fs = [f for k, cs in enumerate(self.chipsets) if (f := dict(cs).get(self.sel[k]))]
            d, r = wpt.maps_at(*p)
            by_file = {os.path.normcase(abspath(i["file"])): i for i in self.items if i.get("file") and i["type"] == "local-map"}
            maps = [by_file[w] for w in (os.path.normcase(m["md"]) for m in (d, r) if m) if w in by_file]
            narrowed = [i for i in maps if all(f(i) for f in fs)]
            self.shown = narrowed or maps
            self.coord_hit = p
            self.goto(0)
            n = len(self.shown)
            self.count.config(text=f"\U0001F4CD  {wpt.fmt(*p)} is on {n} map{'s' if n != 1 else ''} - open one to zoom in on the spot"
                              if n else f"\U0001F4CD  {wpt.fmt(*p)} is not on any map in the library")
            return
        super().refilter(keep)

    def open_item(self, it, tab=None):
        """From elsewhere in the app (search, favorites, links): open it inside its topic, so Back lands in that list."""
        if getattr(self, "coord_hit", None) and it in self.shown and it["type"] == "local-map" and not it.get("_wp"):
            it["_wp"] = {"name": "Searched position", "lat": self.coord_hit[0], "lon": self.coord_hit[1]}
        if self.topic is None or not self.topics[self.topic][3](it):
            n = self.counts()   # the most specific tile that has it (not 'All ...', which has everything)
            hits = [k for k, t in enumerate(self.topics) if t[3](it)]
            k = min(hits, key=lambda k: n.get(self.topics[k][0], 0)) if hits else None
            if k is not None:
                self.set_topic(k)
        self.home.pack_forget()
        super().open_item(it, tab)

    def close_reader(self):
        if self.topic is not None and len([i for i in self.items if self.topics[self.topic][3](i)]) == 1:
            return self.show_topics()   # a one-page topic: Back goes straight to the tiles
        super().close_reader()

    def restart(self):
        super().restart()
        self.show_topics()

    def set_category(self, cat):
        """Home page category shortcut: open the topic that holds the category and pick its own button."""
        if self.reader.winfo_manager():
            self.reader.pack_forget(); self.reader.clear()
        mine = [i for i in self.items if i["category"] == cat]
        n = self.counts()
        hits = [k for k, t in enumerate(self.topics) if mine and all(t[3](i) for i in mine)]
        if not hits:
            return self.show_topics()
        k = min(hits, key=lambda k: n.get(self.topics[k][0], 0))
        self.set_topic(k)
        for name, f in self.chipsets[0][1:]:
            if all(f(i) for i in mine) and all(i["category"] == cat for i in self.items if f(i)):
                self.sel[0] = name; paint_chips(self.chip_w, self.sel); self.refilter()
                break
        self.home.pack_forget()
        self.listview.pack(fill="both", expand=True)

    def jump(self, where):
        if self.topic is None:
            return (self.home_scroll.go_top if where == "top" else self.home_scroll.go_bottom)()
        super().jump(where)


class CoursePage(ItemView):
    def __init__(self, app):
        super().__init__(app.content, bg=C["bg"])
        self.init_view(app, "Traditional Cooking School",
                       "Wardee Harmon's eCourse, in its learning order: work through the modules top to bottom, lesson by lesson.")
        self.mods, self.cur, self.seq, self.cols = [], None, [], 4
        self.progress = load_json(PROGRESS_FILE, {})
        self.listview = tk.Frame(self, bg=C["bg"]); self.listview.pack(fill="both", expand=True)
        left = card(self.listview, width=262); left.pack(side="left", fill="y"); left.pack_propagate(False)
        sb = tk.Frame(left, bg=C["card"]); sb.pack(fill="x", padx=12, pady=(12, 6))
        self.q = tk.StringVar()
        self._after = None
        self.search_entry = search_box(sb, self.q, self.debounce, width=10)
        self.cont = tk.Frame(left, bg=C["card"]); self.cont.pack(fill="x", padx=12)
        self.outline = ScrollFrame(left, C["card"]); self.outline.pack(fill="both", expand=True, pady=(4, 8))
        right = tk.Frame(self.listview, bg=C["bg"]); right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.body = ScrollFrame(right, C["bg"], jump=True); self.body.pack(fill="both", expand=True)
        self.body.canvas.bind("<Configure>", self.resized, add="+")
        self.reader = Reader(self)
        app.lib.on_ready(self.loaded)

    # ------------------------------------------------------------ data
    def loaded(self):
        self.mods = build_course(self.app.lib.items)
        self.seq, self.where_is, self.disp = [], {}, {}
        for m in self.mods:
            for it in m["materials"]:
                self.add_seq(it, m, "Course materials")
            for it in m["start"]:
                self.add_seq(it, m, "Start here")
            for ls in m["lessons"]:
                n = len(ls["parts"])
                for k, it in enumerate(ls["parts"]):
                    self.add_seq(it, m, f"Lesson {ls['num']} \u00b7 {ls['title']}" + (f"  (part {k + 1} of {n})" if n > 1 else ""))
                    self.disp[it["path"]] = ls["title"] + (f" \u2014 {ls['caps'][k]}" if n > 1 or ls["caps"][k] == "Audio" else "")
            for key, name in (("more", "More videos"), ("audio", "Audio"), ("qa", "Q&A and bonus videos"), ("other", "Other files")):
                for it in m[key]:
                    self.add_seq(it, m, name)
        px = self.body.position() if self.cur else 0
        self.build_outline()
        cur = next((m for m in self.mods if self.cur and m["dir"] == self.cur["dir"]), None)
        self.select(cur or (self.mods[0] if self.mods else None))
        if cur and px:
            self.after_idle(lambda: self.body.restore(px))

    def restart(self):
        super().restart()
        self.q.set("")
        if self.mods:
            self.select(self.mods[0])
        self.body.top()

    def add_seq(self, it, m, ctx):
        self.where_is[it["path"]] = (len(self.seq), m, ctx)
        self.seq.append(it)

    def neighbors(self, it):
        if it["path"] not in self.where_is:
            return None
        i, m, ctx = self.where_is[it["path"]]
        prev = self.seq[i - 1] if i > 0 else None
        nxt = self.seq[i + 1] if i + 1 < len(self.seq) else None
        return prev, nxt, f"{('Module ' + m['num'] + ' \u00b7 ') if m['num'] else ''}{m['short']}  \u203a  {ctx}"

    def display_title(self, it):
        return self.disp.get(it["path"], it["title"])

    def viewed(self, it):
        if it["path"] in self.where_is:
            self.progress["last"] = it["path"]
            save_json(PROGRESS_FILE, self.progress)
            self.show_continue()

    # ------------------------------------------------------------ outline (left)
    def build_outline(self):
        o = self.outline.inner
        for w in o.winfo_children():
            w.destroy()
        self.rows = {}
        label(o, "MODULES", 8, True, fg="dim").pack(anchor="w", padx=14, pady=(6, 4))
        extras_started = False
        for m in self.mods:
            if not m["num"] and not extras_started:
                extras_started = True
                label(o, "EXTRAS", 8, True, fg="dim").pack(anchor="w", padx=14, pady=(12, 4))
            r = tk.Frame(o, bg=C["card"], cursor="hand2"); r.pack(fill="x")
            badge = tk.Label(r, text=m["num"] or "\u2022", font=(F, 9, "bold"), width=3, bg=C["sec"], fg=C["text"], pady=2)
            badge.pack(side="left", padx=(12, 8), pady=5)
            n = len(m["lessons"])
            t = tk.Label(r, text=m["short"], font=(F, 10), bg=C["card"], fg=C["text"], anchor="w", justify="left", wraplength=150)
            t.pack(side="left", fill="x", expand=True)
            c = tk.Label(r, text=f"{n}" if n else f"{len(m['materials'])}", font=(F, 8), bg=C["card"], fg=C["dim"], padx=10)
            c.pack(side="right")
            for w in (r, badge, t, c):
                w.bind("<Button-1>", lambda e, m=m: (self.q.set(""), self.select(m)))
            self.rows[m["dir"]] = (r, badge, t, c)
        label(o, "Numbers on the right = lessons\n(or eBooks for the extras).", 8, fg="dim").pack(anchor="w", padx=14, pady=(12, 4))
        self.show_continue()

    def show_continue(self):
        for w in self.cont.winfo_children():
            w.destroy()
        it = self.app.lib.by_path.get(self.progress.get("last", ""))
        if it and it["path"] in self.where_is:
            f = tk.Frame(self.cont, bg=C["ok_bg"], cursor="hand2"); f.pack(fill="x", pady=(2, 4))
            a = tk.Label(f, text="\u25b6  Continue where you left off", font=(F, 9, "bold"), bg=C["ok_bg"], fg=C["ok_fg"], anchor="w")
            a.pack(fill="x", padx=10, pady=(6, 0))
            b = tk.Label(f, text=self.display_title(it)[:70], font=(F, 8), bg=C["ok_bg"], fg=C["ok_fg"], anchor="w", wraplength=220, justify="left")
            b.pack(fill="x", padx=10, pady=(0, 6))
            for w in (f, a, b):
                w.bind("<Button-1>", lambda e, it=it: self.open_item(it))

    def paint_outline(self):
        for d, (r, badge, t, c) in self.rows.items():
            on = self.cur is not None and d == self.cur["dir"] and not self.q.get().strip()
            bg = C["ok_bg"] if on else C["card"]
            for w in (r, t, c):
                w.config(bg=bg)
            t.config(font=(F, 10, "bold" if on else "normal"), fg=C["ok_fg"] if on else C["text"])
            badge.config(bg=C["primary"] if on else C["sec"], fg="#ffffff" if on else C["text"])

    # ------------------------------------------------------------ module view (right)
    def resized(self, e):
        if e.width < 100 or not self.listview.winfo_ismapped():
            return
        cols = max(2, (e.width - 108) // (LW + 12))
        if cols != self.cols:
            self.cols = cols
            if self.cur:
                px = self.body.position()
                self.render()
                self.after_idle(lambda: self.body.restore(px))

    def select(self, m):
        self.cur = m
        self.render()

    def debounce(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(300, self.render)

    def render(self):
        self.paint_outline()
        self.body.clear(); self.reset_cards()
        q = self.q.get().lower().split()
        pairs = self.render_search(q) if q else (self.render_module(self.cur) if self.cur else [])
        self.load_thumbs(pairs)

    def render_module(self, m):
        inner, pairs = self.body.inner, []
        hd = card(inner); hd.pack(fill="x")
        hi = tk.Frame(hd, bg=C["card"]); hi.pack(fill="x", padx=18, pady=14)
        if m["num"]:
            label(hi, f"MODULE {m['num']}", 8, True, fg="accent").pack(anchor="w")
        label(hi, m["short"], 17, True).pack(anchor="w")
        nv = sum(1 for ls in m["lessons"] for p in ls["parts"] if p["type"] != "audio") + len(m["more"]) + len(m["qa"]) + len(m["start"])
        na = sum(1 for ls in m["lessons"] for p in ls["parts"] if p["type"] == "audio") + len(m["audio"])
        bits = [f"{len(m['lessons'])} lessons" if m["lessons"] else "", f"{nv} videos" if nv else "", f"{na} audio" if na else "",
                f"{len(m['materials'])} eBooks & handouts" if m["materials"] else ""]
        label(hi, "  \u2022  ".join(b for b in bits if b), 9, fg="dim").pack(anchor="w", pady=(2, 0))
        if m["lessons"]:
            first = (m["materials"] or m["start"] or m["lessons"][0]["parts"])[0]
            row = tk.Frame(hi, bg=C["card"]); row.pack(anchor="w", pady=(10, 0))
            Btn(row, "\u25b6  Start this module", lambda: self.open_item(first), "primary", 9, 14, 5).pack(side="left")
            if m["page"]:
                Btn(row, "Module page", lambda: self.open_item(m["page"]), "secondary", 9, 14, 5).pack(side="left", padx=(8, 0))
        if m["materials"]:
            section_title(inner, "Course materials", len(m["materials"]))
            g = tk.Frame(inner, bg=C["bg"]); g.pack(fill="x")
            cols = max(2, (self.body.canvas.winfo_width() - 10) // (TW + 14))
            for k, it in enumerate(m["materials"]):
                self.make_card(g, it, lines=False).grid(row=k // cols, column=k % cols, padx=(0, 10), pady=(0, 10), sticky="nw")
                pairs.append((it, (TW, TH)))
        if m["start"]:
            section_title(inner, "Start here", len(m["start"]))
            pairs += self.tile_grid(inner, m["start"])
        if m["lessons"]:
            section_title(inner, "Lessons", len(m["lessons"]))
            for ls in m["lessons"]:
                pairs += self.lesson_row(inner, ls)
        for key, name in (("more", "More videos"), ("audio", "Audio"), ("qa", "Q&A and bonus videos"), ("other", "Other files")):
            if m[key]:
                section_title(inner, name, len(m[key]))
                pairs += self.tile_grid(inner, m[key])
        tk.Frame(inner, bg=C["bg"], height=20).pack()
        return pairs

    def lesson_row(self, parent, ls):
        row = card(parent); row.pack(fill="x", pady=(0, 8))
        lft = tk.Frame(row, bg=C["card"], width=92); lft.pack(side="left", fill="y"); lft.pack_propagate(False)
        label(lft, "LESSON", 7, True, fg="dim").pack(pady=(14, 0))
        tk.Label(lft, text=ls["num"], font=(F, 20, "bold"), bg=C["card"], fg=C["primary"]).pack()
        rt = tk.Frame(row, bg=C["card"]); rt.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=(10, 4))
        label(rt, ls["title"], 11, True).pack(anchor="w")
        nv = sum(1 for p in ls["parts"] if p["type"] != "audio"); na = len(ls["parts"]) - nv
        label(rt, "  \u2022  ".join(x for x in (f"{nv} video" + ("s" if nv != 1 else "") if nv else "",
                                                f"{na} audio" if na else "") if x), 8, fg="dim").pack(anchor="w")
        return self.tile_grid(rt, ls["parts"], ls["caps"], bg="card")

    def tile_grid(self, parent, items, caps=None, bg="bg"):
        g = tk.Frame(parent, bg=C[bg]); g.pack(fill="x", pady=(6, 6))
        cols = self.cols if bg == "card" else max(2, (self.body.canvas.winfo_width() - 10) // (LW + 10))
        for k, it in enumerate(items):
            cap = caps[k] if caps else it["title"]
            meta = tname(it["type"]) if it["type"] not in ("lesson-video",) else "Video"
            self.make_card(g, it, LW, LH, lines=False, title=cap, meta=meta).grid(row=k // cols, column=k % cols, padx=(0, 8),
                                                                                   pady=(0, 8), sticky="nw")
        return [(it, (LW, LH)) for it in items]

    def render_search(self, q):
        inner, pairs = self.body.inner, []
        hits = [(m, it) for m in self.mods for it in self.seq if self.where_is[it["path"]][1] is m and all(w in it["search"] for w in q)]
        section_title(inner, "Search results", len(hits))
        if not hits:
            label(inner, "Nothing in the course matches that.", 10, fg="dim", bg="bg").pack(anchor="w")
        for m in self.mods:
            its = [it for mm, it in hits if mm is m]
            if its:
                label(inner, (f"Module {m['num']}: " if m["num"] else "") + m["short"], 10, True, fg="primary", bg="bg").pack(anchor="w", pady=(10, 0))
                pairs += self.tile_grid(inner, its[:60])
        return pairs

    def close_reader(self):
        it = self.reader.it
        super().close_reader()
        if it and it["path"] in self.where_is and self.where_is[it["path"]][1] is not self.cur and not self.q.get().strip():
            self.select(self.where_is[it["path"]][1])   # Next/Previous moved into another module
        if it:
            self.after_idle(lambda: self.reveal(it))

    def reveal(self, it):
        """Back from the reader: if you moved on with Next/Previous, scroll so the lesson you were on is in view."""
        box = self.slots.get(it["path"])
        try:
            if not box or not box.winfo_exists():
                return
            self.update_idletasks()
            y = box.winfo_rooty() - self.body.inner.winfo_rooty()
        except tk.TclError:   # the module was redrawn meanwhile
            return
        top, h = self.body.position(), self.body.canvas.winfo_height()
        if y < top or y + box.winfo_height() > top + h:
            self.body.restore(max(0, y - 120))

    def on_show(self):
        self.requeue_thumbs()


# ======================================================================= favourites
class FavoritesPage(ItemView):
    MODES = [("By section", None), ("By category", None), ("Newest first", None)]

    def __init__(self, app):
        super().__init__(app.content, bg=C["bg"])
        self.init_view(app, "Favorites", "Everything you've starred, grouped. Click \u2606 on any card (or in the reader) to add it here.")
        self.listview = tk.Frame(self, bg=C["bg"]); self.listview.pack(fill="both", expand=True)
        self.sel = ["By section"]
        cb = tk.Frame(self.listview, bg=C["bg"]); cb.pack(fill="x")
        self.chip_w = chip_rows(cb, [self.MODES], self.sel, self.set_mode)
        self.body = ScrollFrame(self.listview, C["bg"], jump=True); self.body.pack(fill="both", expand=True, pady=(4, 0))
        self.reader = Reader(self)
        self.dirty = True
        app.favs.listeners.append(self.changed)
        app.lib.on_ready(lambda: self.render(keep=True))

    def restart(self):
        super().restart()
        self.render()
        self.body.top()

    def set_mode(self, n, k=0):
        self.sel[0] = n; paint_chips(self.chip_w, self.sel); self.render()

    def changed(self):
        if self.winfo_ismapped() and not self.reader.winfo_ismapped():
            self.render(keep=True)
        else:
            self.dirty = True

    def group_of(self, it):
        mode = self.sel[0]
        if mode == "By category":
            return ("Cooking School", "") if is_course(it) else (nice(it["category"]) if it.get("category") else "Other", "")
        if is_course(it):
            return "Cooking School", (f"Module {re.match(r'Module (\d+)', it['module'])[1]} \u00b7 " if re.match(r"Module \d+", it.get("module") or "") else "") + re.sub(r"^Module \d+:\s*", "", it.get("module") or "")
        if it["category"] == "recipes":
            return "Recipes", {"web": "Web recipes", "email": "Email recipes", "facebook": "Facebook", "cards": "Recipe cards",
                               "videos": "Recipe videos", "books": "Cookbooks & documents"}.get(it.get("group"), "")
        if it["type"] in DOC_TYPES:
            return "Documents & Books", nice(it["category"])
        return "Library", nice(it["category"])

    def render(self, keep=False):
        self.dirty = False
        px = self.body.position() if keep else 0
        self.body.clear(); self.reset_cards()
        if px:
            self.after_idle(lambda: self.body.restore(px))
        favs = self.app.favs.d
        items = [self.app.lib.by_path[p] for p in favs if p in self.app.lib.by_path]
        inner, pairs = self.body.inner, []
        if not items:
            e = card(inner); e.pack(fill="x", pady=20)
            label(e, "\u2606  No favorites yet", 14, True).pack(anchor="w", padx=22, pady=(20, 4))
            label(e, "Click the star on any recipe, document or lesson to add it here. Click it again to remove it.", 10,
                  fg="dim").pack(anchor="w", padx=22, pady=(0, 20))
            return
        cols = max(2, (self.body.canvas.winfo_width() - 4) // (TW + 18))
        if self.sel[0] == "Newest first":
            groups = [(("Newest first", ""), sorted(items, key=lambda i: favs[i["path"]], reverse=True))]
        else:
            gm = {}
            for it in items:
                gm.setdefault(self.group_of(it), []).append(it)
            order = {"Recipes": 0, "Cooking School": 1, "Documents & Books": 2}
            groups = sorted(gm.items(), key=lambda kv: (order.get(kv[0][0], 3), kv[0][0], natural(kv[0][1])))
        last = None
        for (main, sub), its in groups:
            if main != last:
                section_title(inner, main, sum(len(v) for (m2, _), v in groups if m2 == main)); last = main
            if sub:
                label(inner, sub, 10, True, fg="primary", bg="bg").pack(anchor="w", pady=(4, 2))
            g = tk.Frame(inner, bg=C["bg"]); g.pack(fill="x")
            its = sorted(its, key=lambda i: i["key"]) if self.sel[0] != "Newest first" else its
            for k, it in enumerate(its):
                self.make_card(g, it).grid(row=k // cols, column=k % cols, padx=(0, 10), pady=(0, 10), sticky="nw")
                pairs.append((it, (TW, TH)))
        tk.Frame(inner, bg=C["bg"], height=20).pack()
        self.load_thumbs(pairs)

    def close_reader(self):
        super().close_reader()
        if self.dirty:
            self.render(keep=True)

    def on_show(self):
        if self.dirty and not self.reader.winfo_ismapped():
            self.render(keep=True)
        self.requeue_thumbs()


# ======================================================================= reader
class Reader(tk.Frame):
    MAXCH = 250000
    ZOOMS = [0.5, 0.67, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]
    MAP_ZOOMS = ZOOMS + [5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0]   # topo maps hold detail far past 400%
    TEXT_SIZES = {"base": 10, "h1": 15, "h2": 12, "h3": 10, "b": 10, "mono": 9, "dim": 9}
    INSTANCES = []

    def __init__(self, page):
        super().__init__(page, bg=C["bg"])
        self.page, self.it, self.imgs, self.doc = page, None, [], None
        top = tk.Frame(self, bg=C["bg"]); top.pack(fill="x", pady=(0, 8))
        Btn(top, "\u2190  Back", page.close_reader, "secondary", 9, 12, 4).pack(side="left")
        self.nav = tk.Frame(top, bg=C["bg"]); self.nav.pack(side="right")
        self.where = label(top, "", 9, fg="dim", bg="bg"); self.where.pack(side="left", padx=12, fill="x", expand=True)

        head = self.head = card(self); head.pack(fill="x")
        self.pic = tk.Frame(head, bg=C["card"], width=300, height=190); self.pic.pack(side="left", padx=14, pady=14); self.pic.pack_propagate(False)
        info = tk.Frame(head, bg=C["card"]); info.pack(side="left", fill="both", expand=True, pady=14, padx=(0, 16))
        self.h = tk.Label(info, font=(F, 15, "bold"), bg=C["card"], fg=C["text"], justify="left", anchor="w", wraplength=560)
        self.h.pack(fill="x")
        self.meta = tk.Frame(info, bg=C["card"]); self.meta.pack(fill="x", pady=(6, 0))
        self.desc = tk.Label(info, font=(F, 9), bg=C["card"], fg=C["dim"], justify="left", anchor="w", wraplength=560)
        self.desc.pack(fill="x", pady=(8, 0))
        self.btns = Flow(info, C["card"], gap=8); self.btns.pack(side="bottom", fill="x", anchor="w", pady=(10, 0))   # wraps
        info.bind("<Configure>", lambda e: (self.h.config(wraplength=e.width - 8), self.desc.config(wraplength=e.width - 8)))

        tabs = self.tabs = tk.Frame(self, bg=C["bg"]); tabs.pack(fill="x", pady=(10, 0))
        self.tab_w = {}
        for n in ("Read", "Web page", "Pictures", "Pages", "Note"):
            l = tk.Label(tabs, text=n, font=(F, 10), padx=16, pady=5, cursor="hand2")
            l.bind("<Button-1>", lambda e, n=n: self.set_tab(n))
            self.tab_w[n] = l
        self.pnav = tk.Frame(tabs, bg=C["bg"])
        Btn(self.pnav, "\u25c0", lambda: self.pdf_go(self.pno - 1), "secondary", 9, 10, 3).pack(side="left")
        self.pl = label(self.pnav, "", 9, fg="dim", bg="bg"); self.pl.pack(side="left", padx=8)
        Btn(self.pnav, "\u25b6", lambda: self.pdf_go(self.pno + 1), "secondary", 9, 10, 3).pack(side="left")
        # maps (georeferenced topo PDFs): position under the mouse, waypoint markers, click to drop a waypoint
        self.mapbar = tk.Frame(tabs, bg=C["bg"])
        self.addwp_b = Btn(self.mapbar, "\U0001F4CD  Add waypoint", self.toggle_add_wp, "secondary", 9, 12, 3)
        self.addwp_b.pack(side="left")
        self.meas_b = Btn(self.mapbar, "📏  Measure", self.toggle_measure, "secondary", 9, 12, 3)
        self.meas_b.pack(side="left", padx=(6, 0))
        self.ml = label(self.mapbar, "", 9, fg="dim", bg="bg"); self.ml.config(width=24); self.ml.pack(side="left", padx=(8, 0))
        self.geo, self.wp_focus, self.adding_wp, self.wp_marks, self.pdf_z = None, None, False, [], 1.0
        self.measuring, self.mpts, self._base = False, [], None   # 📏 Measure: points (lat, lon); the picture before the line
        self.mstrip = tk.Frame(self, bg="#fce4ec", highlightthickness=1, highlightbackground="#c2185b")
        self.mtotal = tk.Label(self.mstrip, font=(F, 10, "bold"), bg="#fce4ec", fg="#880e4f", anchor="w")
        self.mtotal.pack(side="left", padx=12, pady=6)
        Btn(self.mstrip, "Done", lambda: self.toggle_measure(False), "primary", 9, 12, 3).pack(side="right", padx=(4, 10), pady=4)
        Btn(self.mstrip, "Clear", self.measure_clear, "secondary", 9, 12, 3).pack(side="right", padx=4, pady=4)
        Btn(self.mstrip, "↶  Undo last point", self.measure_undo, "secondary", 9, 12, 3).pack(side="right", padx=4, pady=4)
        self.wp_menu = tk.Menu(self, tearoff=0)
        # zoom: text (Read), the PDF page (Pages) or the picture being viewed; Ctrl + / Ctrl - / Ctrl 0 and Ctrl + wheel too
        self.zbar = tk.Frame(tabs, bg=C["bg"])
        Btn(self.zbar, "\u2212", lambda: self.zoom(-1), "secondary", 10, 10, 2).pack(side="left")
        self.zl = label(self.zbar, "100%", 9, fg="dim", bg="bg"); self.zl.config(width=6); self.zl.pack(side="left", padx=4)
        Btn(self.zbar, "+", lambda: self.zoom(1), "secondary", 10, 10, 2).pack(side="left")
        Btn(self.zbar, "Fit", lambda: self.zoom(0), "ghost", 9, 8, 2).pack(side="left", padx=(4, 0))
        self.zhelp_b = Btn(self.zbar, "?", lambda: self.zoom_tip.toggle(self.zhelp_b), "ghost", 9, 8, 2)
        self.zhelp_b.pack(side="left", padx=(2, 0))
        self.zoom_tip = Tip(list(self.zbar.winfo_children()), self.zoom_help)
        self.tz = float(load_json(SETTINGS_FILE, {}).get("reader_zoom", 1.0))   # text zoom is remembered
        self.pz = self.iz = 1.0                                                   # PDF / picture zoom start at 'fit'
        Reader.INSTANCES.append(self)
        if len(Reader.INSTANCES) == 1:
            for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
                self.bind_all(seq, lambda e: Reader.active_zoom(1))
            for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
                self.bind_all(seq, lambda e: Reader.active_zoom(-1))
            self.bind_all("<Control-0>", lambda e: Reader.active_zoom(0))
            self.bind_all("<Control-MouseWheel>", lambda e: Reader.active_zoom(1 if e.delta > 0 else -1))

        body = tk.Frame(self, bg=C["card"], highlightthickness=1, highlightbackground=C["line"]); body.pack(fill="both", expand=True)
        self.bodyf = body
        self.sticky = tk.Frame(self, bg=C["card"], highlightthickness=1, highlightbackground=C["line"])   # fixed strip (sort choices)
        self.text = tk.Text(body, wrap="word", font=(F, 10), bg=C["card"], fg=C["text"], relief="flat", padx=28, pady=18,
                            spacing1=2, spacing3=4, cursor="arrow", insertwidth=0)
        self.tsb = ttk.Scrollbar(body, command=self.text.yview); self.text.configure(yscrollcommand=self.text_scrolled)
        self._more_busy = False
        self.tjumps = tk.Frame(body, bg=C["card"])   # floating Top / Bottom, like the lists
        for text, where in (("▲  Top", "top"), ("▼  Bottom", "bottom")):
            jb = tk.Label(self.tjumps, text=text, font=(F, 8, "bold"), bg=C["primary"], fg="#ffffff", padx=9, pady=3, cursor="hand2")
            jb.pack(fill="x", pady=(0, 3))
            jb.bind("<Button-1>", lambda e, w=where: self.jump(w))
            jb.bind("<Enter>", lambda e, b=jb: b.config(bg=C["primary_hover"]))
            jb.bind("<Leave>", lambda e, b=jb: b.config(bg=C["primary"]))
        self.pdfv = ScrollFrame(body, C["sec"], hscroll=True)
        self.pdfv.on_edge = self.pdf_edge
        self.pdf_l = tk.Label(self.pdfv.inner, bg=C["sec"], bd=0, padx=0, pady=0, highlightthickness=0); self.pdf_l.pack(pady=12)
        self.pdf_l.bind("<Motion>", self.map_motion)
        self.pdf_l.bind("<Leave>", lambda e: self.geo and self.ml.config(text=""))
        self.pdf_l.bind("<ButtonPress-1>", self.map_press)
        self.pdf_l.bind("<B1-Motion>", self.map_drag)
        self.pdf_l.bind("<ButtonRelease-1>", self.map_release)
        self.pdf_l.bind("<Button-3>", self.map_menu)
        # deep map zoom: the visible piece, laid over the page-sized pdf_l (see render_window)
        self.tile = tk.Label(self.pdf_l, bg=C["sec"], bd=0, padx=0, pady=0, highlightthickness=0)
        for seq, fn in (("<Motion>", self.map_motion), ("<ButtonPress-1>", self.map_press), ("<B1-Motion>", self.map_drag),
                        ("<ButtonRelease-1>", self.map_release), ("<Button-3>", self.map_menu)):
            self.tile.bind(seq, fn)
        self.blank = tk.PhotoImage(width=1, height=1)
        self.win_rect, self._win_job = None, None
        self.pdfv.listeners.append(self.map_scrolled)
        self.pdfv.canvas.configure(xscrollcommand=lambda a, b: (self.pdfv.hsb.set(a, b), self.map_scrolled()))
        self.galv = ScrollFrame(body, C["card"])
        self.imv = tk.Frame(body, bg="#1c211f")
        bar = tk.Frame(self.imv, bg="#1c211f"); bar.pack(fill="x", padx=10, pady=8)
        Btn(bar, "\u2190  All pictures", lambda: self.set_tab("Pictures"), "secondary", 9, 12, 4).pack(side="left")
        Btn(bar, "Open full size", lambda: open_path(self.gallery[self.gi][0]), "secondary", 9, 12, 4).pack(side="right")
        nx = tk.Frame(bar, bg="#1c211f"); nx.pack(side="top")
        Btn(nx, "\u2039", lambda: self.show_image(self.gi - 1), "secondary", 11, 12, 2).pack(side="left")
        self.gl = tk.Label(nx, font=(F, 9), bg="#1c211f", fg="#cfd8d3", padx=12); self.gl.pack(side="left")
        Btn(nx, "\u203a", lambda: self.show_image(self.gi + 1), "secondary", 11, 12, 2).pack(side="left")
        self.cap = tk.Label(self.imv, font=(F, 9), bg="#1c211f", fg="#cfd8d3", wraplength=700, justify="center")
        self.cap.pack(side="bottom", fill="x", pady=(4, 10))
        self.big = tk.Canvas(self.imv, bg="#1c211f", highlightthickness=0, cursor="hand2"); self.big.pack(fill="both", expand=True)
        self.big.bind("<ButtonPress-1>", self.img_press)
        self.big.bind("<B1-Motion>", self.img_drag)
        self.big.bind("<ButtonRelease-1>", self.img_release)
        self.big.on_wheel = lambda e: self.zoom(1 if e.delta > 0 else -1)   # in the picture viewer the wheel zooms
        self.big.bind("<Configure>", lambda e: self.imv.winfo_ismapped() and self.draw_image())
        self._full = None
        self.gallery, self.gi, self.ggen, self.keys_on = [], 0, 0, False
        self.webv, self.web_url, self.cur_tab = None, None, "Read"   # the in-app web page view is made on first use
        self.webbox = tk.Frame(body, bg=C["card"])
        self.notev = tk.Frame(body, bg=C["card"])
        nbar = tk.Frame(self.notev, bg=C["card"]); nbar.pack(fill="x", padx=18, pady=(12, 6))
        Btn(nbar, "Save note", self.save_note, "primary", 9, 14, 5).pack(side="left")
        self.ndel = Btn(nbar, "\U0001F5D1  Delete note", self.delete_note, "secondary", 9, 14, 5); self.ndel.pack(side="left", padx=(8, 0))
        self.ndel.c_fg = C["err_fg"]; self.ndel.config(fg=C["err_fg"])
        Btn(nbar, "Open in Notepad", self.notepad, "ghost", 9, 10, 5).pack(side="left", padx=(8, 0))
        self.nstat = label(nbar, "", 9, fg="dim"); self.nstat.pack(side="left", padx=14)
        nbox = tk.Frame(self.notev, bg=C["card"], highlightthickness=1, highlightbackground=C["line"]); nbox.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        self.note = tk.Text(nbox, wrap="word", font=(F, 11), bg="#fffdf5", fg=C["text"], relief="flat", padx=14, pady=10, undo=True,
                            insertbackground=C["text"])
        nsb = ttk.Scrollbar(nbox, command=self.note.yview); self.note.configure(yscrollcommand=nsb.set)
        nsb.pack(side="right", fill="y"); self.note.pack(fill="both", expand=True)
        self.note.bind("<Control-s>", lambda e: (self.save_note(), "break")[1])
        self.note_open = False
        t = self.text
        t.tag_configure("h1", font=(F, 15, "bold"), spacing1=12, spacing3=6, foreground=C["primary"])
        t.tag_configure("h2", font=(F, 12, "bold"), spacing1=14, spacing3=4, foreground=C["primary"])
        t.tag_configure("h3", font=(F, 10, "bold"), spacing1=10, spacing3=2)
        t.tag_configure("b", font=(F, 10, "bold"))
        t.tag_configure("li", lmargin1=14, lmargin2=30)
        t.tag_configure("mono", font=("Consolas", 9), background="#f6f4ef", lmargin1=10, lmargin2=10)
        t.tag_configure("link", foreground="#2b6cb0", underline=True)
        t.tag_configure("dim", foreground=C["dim"], font=(F, 9))
        t.bind("<Control-MouseWheel>", lambda e: (self.zoom(1 if e.delta > 0 else -1), "break")[1])   # zoom, not scroll
        self.apply_text_zoom()
        t.tag_bind("link", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.config(cursor="arrow"))
        self.links, self.fav_b = {}, None

    def clear(self):
        self.autosave()
        self.imgs, self.gimgs = [], []
        self.ggen += 1
        self.keys(False)
        if self.doc:
            self.doc.close(); self.doc = None

    # ------------------------------------------------------------ header
    def show(self, it, tab=None):
        self.clear()
        self.it = it
        self.pz = self.iz = 1.0
        for w in self.meta.winfo_children() + self.btns.winfo_children() + self.pic.winfo_children() + self.nav.winfo_children():
            w.destroy()
        if hasattr(self.page, "viewed"):
            self.page.viewed(it)
        nb = self.page.neighbors(it)
        if nb:   # course order: Previous / Next (a page may rename them, or hide one with None)
            prev, nxt, ctx = nb[:3]
            labels = nb[3] if len(nb) > 3 else ("\u2039  Previous", "Next  \u203a")
            self.where.config(text=ctx)
            if labels[0]:
                p = Btn(self.nav, labels[0], (lambda: self.show(prev)) if prev else (lambda: None), "secondary", 9, 12, 4)
                p.pack(side="left"); p.set_enabled(bool(prev))
            if labels[1]:
                n = Btn(self.nav, labels[1], (lambda: self.show(nxt)) if nxt else (lambda: None), "primary", 9, 14, 4)
                n.pack(side="left", padx=(8, 0)); n.set_enabled(bool(nxt))
        else:
            self.where.config(text=f"{self.page.title}  \u203a  {it['title'][:80]}")
        self.h.config(text=self.page.display_title(it))
        chips = [(it.get("module") or (nice(it["category"]) if it.get("category") else ""), C["ok_bg"], C["ok_fg"]),
                 (tname(it["type"]), C["warn_bg"], C["warn_fg"]),
                 (it["publisher"][:40] if it.get("publisher") and not it.get("module") else "", C["sec"], C["text"]),
                 (f"{it['words']:,} words" if it.get("words") else "", C["sec"], C["dim"])]
        for txt, bg, fg in chips:
            if txt:
                tk.Label(self.meta, text=txt, font=(F, 8, "bold"), bg=bg, fg=fg, padx=8, pady=2).pack(side="left", padx=(0, 6))
        self.note_chip = tk.Label(self.meta, text="\U0001F4DD  Note", font=("Segoe UI Emoji", 8, "bold"), bg="#fff4cc", fg="#7a5a00",
                                  padx=8, pady=2, cursor="hand2")
        self.note_chip.bind("<Button-1>", lambda e: self.set_tab("Note"))
        self.paint_note_marks()
        self.desc.config(text=snippet(it, 240))
        orig = abspath(it.get("original"))
        md = abspath(it.get("file"))
        pdf = orig if orig.lower().endswith(".pdf") else (md[:-3] + ".pdf" if md and os.path.exists(md[:-3] + ".pdf") else "")
        aud = orig if orig.lower().endswith(AUD_EXT) else ""
        vid = orig if orig.lower().endswith(VID_EXT) else (md[:-3] + "-video.mp4" if md and os.path.exists(md[:-3] + "-video.mp4") else "")
        first = True

        def b(text, cmd):
            nonlocal first
            w = Btn(self.btns, text, cmd, "primary" if first else "secondary", 9, 14, 6)
            self.btns.add(w)
            first = False
            return w
        if vid:
            b("\u25b6  Play video", lambda: open_path(vid))
        if aud:
            b("\u25b6  Play audio", lambda: open_path(aud))
        if pdf:
            b("Open PDF", lambda: open_path(pdf))
        if orig and orig not in (pdf, vid, aud) and os.path.exists(orig):
            ext = os.path.splitext(orig)[1].upper().lstrip(".")
            b(f"Open original ({ext})" if it["type"] != "recipe-card" else "Open picture", lambda: open_path(orig))
        if it.get("source_url", "").startswith("http"):
            b("Open web page", lambda: webbrowser.open(it["source_url"]))
        if it.get("zim"):   # read-only archive page: no library actions
            b("\U0001F310  Open in browser", lambda: self.page.open_in_browser(self.it))
            self.fav_b = None
        else:
            b("Show in folder", lambda: show_in_folder(md or orig))
            self.fav_b = b("", lambda: self.page.app.favs.toggle(self.it))
            self.paint_fav()
            f_ = it.get("file") or ""
            if it["category"] == "recipes" and not is_course(it):
                b("Recipe tiles\u2026", lambda: edit_recipe_tiles(self.page, self.it))
            if f_.count("/") == 1 and not f_.startswith(("local-area/", "recipes/personal-recipe-collection")):
                b("Change category\u2026", lambda: confirm_move(self.page, self.it))
            if it["category"] == "local-area" and it.get("ltype") and it["type"] in ("local-profile", "local-wildlife", "species-profile",
                                                                                       "wikipedia-article"):   # plant / animal pages only
                b("Change type\u2026", lambda: edit_local_type(self.page, self.it))
            dl = Btn(self.btns, "\U0001F5D1  Delete\u2026", lambda: confirm_delete(self.page, self.it), "secondary", 9, 14, 6)
            dl.c_fg = C["err_fg"]; dl.config(fg=C["err_fg"]); self.btns.add(dl)
        ph = placeholder(self.pic, it, 300, 190, big=True); ph.pack(fill="both", expand=True)
        self.after(10, self.load_pic)
        self.pdf_path = pdf
        self.wp_focus = it.pop("_wp", None)   # opened from a waypoint: zoom in on it
        self.adding_wp = False
        self.measuring, self.mpts, self._base = False, [], None
        self.mstrip.pack_forget()
        self.geo = wpt.georef_for_pdf(pdf) if pdf and os.sep + "maps" + os.sep in os.path.normpath(pdf) \
            and "local-area" in pdf else None
        if self.geo and self.wp_focus:
            tab, self.pz = "Pages", 3.0
        if (it.get("file") or "").endswith("/north-america-map.md") and hasattr(self.page.app, "open_na_map"):
            b("\U0001F30E  Open the North America map", lambda: self.page.app.open_na_map())
        if self.geo:
            if self.wp_focus:
                b("Same spot on the " + ("detailed map" if "regional" in pdf else "regional map"),
                  lambda: open_waypoint(self.page.app, self.wp_focus, "detail" if "regional" in self.pdf_path else "regional"))
            if getattr(self.page.app, "na_map_available", lambda: False)():
                b("\U0001F30E  North America map", self.open_na_here)
            b("\U0001F4CD  My waypoints", lambda: self.page.app.show_waypoints())
        self.gallery = gallery_images(it)
        for l in self.tab_w.values():
            l.pack_forget()
        self.tab_w["Pictures"].config(text=f"Pictures ({len(self.gallery)})")
        # pages the app builds itself (bookshelf, document lists) have no web version worth showing: the archive's own
        # front page for them is a JavaScript app the in-app view can't run
        web = bool(it.get("zim")) and not it.get("original") and not it.get("synthetic") and web_view_available()
        shown = ["Read"] + (["Web page"] if web else []) + (["Pictures"] if self.gallery else []) + (["Pages"] if pdf else []) \
            + ([] if it.get("zim") else ["Note"])
        self.web_url = None
        for n in shown:
            self.tab_w[n].pack(side="left", padx=(0, 4))
        if tab not in shown and it.get("zim") and getattr(self.page, "pref_tab", None) in shown:
            tab = self.page.pref_tab   # archive articles: the tab last chosen (Read or Web page)
        if tab not in shown:
            tab = ("Pages" if pdf and (it["type"] in DOC_TYPES or it.get("words", 0) < 400) else
                   "Pictures" if self.gallery and it["type"] in ("species-profile", "recipe-card") else "Read")
        self.set_tab(tab)
        self.paint_sticky(it)

    def paint_sticky(self, it):
        """A fixed 'Sort:' strip above the reading area for pages that can be re-ordered; it never scrolls away."""
        for w in self.sticky.winfo_children():
            w.destroy()
        bar = it.get("sortbar") if it else None
        if not bar:
            self.sticky.pack_forget()
            return
        row = tk.Frame(self.sticky, bg=C["card"]); row.pack(fill="x", padx=22, pady=6)
        tk.Label(row, text="Sort:", font=(F, 9, "bold"), bg=C["card"], fg=C["dim"]).pack(side="left", padx=(0, 8))
        for k, (label, url) in enumerate(bar):
            if k:
                tk.Label(row, text="\u00b7", font=(F, 9), bg=C["card"], fg=C["dim"]).pack(side="left", padx=4)
            if url is None:   # the current order
                tk.Label(row, text=label, font=(F, 9, "bold"), bg=C["ok_bg"], fg=C["ok_fg"], padx=8, pady=1).pack(side="left")
            else:
                l = tk.Label(row, text=label, font=(F, 9, "underline"), bg=C["card"], fg="#2b6cb0", cursor="hand2", padx=4)
                l.pack(side="left")
                l.bind("<Button-1>", lambda e, u=url: self.page.open_link(u))
        self.sticky.pack(fill="x", before=self.bodyf, pady=(0, 0))

    def paint_fav(self):
        if self.fav_b and self.fav_b.winfo_exists() and self.it:
            on = self.page.app.favs.has(self.it)
            self.fav_b.config(text=f"{STAR_ON}  Favorite" if on else f"{STAR_OFF}  Add to favorites",
                              fg=C["accent"] if on else C["text"])
            self.fav_b.c_fg = C["accent"] if on else C["text"]

    def load_pic(self):
        it = self.it
        im = make_picture(it, 300, 190) if it else None
        if im and it is self.it:
            img = ImageTk.PhotoImage(im); img._pic = True; self.imgs.append(img)
            for w in self.pic.winfo_children():
                w.destroy()
            tk.Label(self.pic, image=img, bg=C["card"], bd=0).pack(fill="both", expand=True)

    def set_tab(self, n):
        if self.note_open and n != "Note":
            self.autosave()
        self.note_open = n == "Note"
        self.cur_tab = n
        if self.it and self.it.get("zim") and not self.it.get("synthetic") and n in ("Read", "Web page") and hasattr(self.page, "pref_tab"):
            self.page.pref_tab = n   # archive articles open on the tab last chosen
        for k, l in self.tab_w.items():
            on = k == n
            l.config(bg=C["card"] if on else C["bg"], fg=C["primary"] if on else C["dim"], font=(F, 10, "bold" if on else "normal"))
        self.text.pack_forget(); self.tsb.pack_forget(); self.pdfv.pack_forget(); self.pnav.pack_forget()
        self.galv.pack_forget(); self.imv.pack_forget(); self.keys(False); self.notev.pack_forget(); self.webbox.pack_forget()
        self.zbar.pack_forget(); self.mapbar.pack_forget()
        if n in ("Read", "Pages"):
            self.zbar.pack(side="right", padx=(10, 0))
            self.paint_zoom()
        if not self.head.winfo_ismapped():
            self.head.pack(fill="x", before=self.tabs)
        if n == "Pictures":
            self.galv.pack(fill="both", expand=True)
            self.after(30, self.render_gallery)
            return
        if n == "Web page":
            self.webbox.pack(fill="both", expand=True)
            self.show_web()
            return
        if n == "Note":
            self.load_note()
            self.notev.pack(fill="both", expand=True)
            self.note.focus_set()
            return
        if n == "Pages":
            self.pdfv.pack(fill="both", expand=True)
            self.pnav.pack(side="right", before=self.zbar)
            if self.geo:
                self.mapbar.pack(side="right", padx=(0, 14), before=self.pnav)
                self.paint_add_wp()
            if not self.doc:
                import pymupdf
                try:
                    self.doc = pymupdf.open(self.pdf_path)
                except Exception:
                    return self.set_tab("Read")
                self.pno = 0
            self.after(30, lambda: self.pdf_go(self.pno))
        else:
            self.tsb.pack(side="right", fill="y"); self.text.pack(side="left", fill="both", expand=True)
            self.render_text()

    # ------------------------------------------------------------ long lists that load more as you scroll (bookshelf)
    def text_scrolled(self, first, last):
        self.tsb.set(first, last)
        if float(first) > 0.0 or float(last) < 1.0:
            self.tjumps.place(in_=self.text, relx=1.0, rely=1.0, x=-10, y=-8, anchor="se"); self.tjumps.lift()
        else:
            self.tjumps.place_forget()
        it = self.it
        if float(last) >= 0.97 and it and it.get("more") and not it.get("more_done") and not self._more_busy:
            self._more_busy = True
            self.after(30, self.load_more)

    def load_more(self):
        it = self.it
        try:
            chunk = it["more"]() if it and it.get("more") else ""
            if not chunk:
                it["more_done"] = True
                return
            it["text"] += "\n" + chunk   # kept, so Back shows everything already loaded
            if it["_shown"] and it.get("more") and "That's all" in chunk:
                it["more_done"] = True
            t = self.text
            t.config(state="normal")
            self.md(chunk)
            t.config(state="disabled")
        finally:
            self._more_busy = False

    def jump(self, where):
        """Top / Bottom of the page being read (Bottom first loads the rest of a list that loads as you scroll)."""
        t = self.text
        if where == "top":
            return t.yview_moveto(0)
        it = self.it
        if it and it.get("more") and not it.get("more_done"):
            rest = []
            while True:
                chunk = it["more"]()
                if not chunk:
                    break
                rest.append(chunk)
            it["more_done"] = True
            if rest:
                chunk = "\n".join(rest)
                it["text"] += "\n" + chunk
                t.config(state="normal"); self.md(chunk); t.config(state="disabled")
        t.update_idletasks()
        t.yview_moveto(1.0)

    # ------------------------------------------------------------ web page (archive articles)
    def show_web(self):
        if self.webv is None:
            from tkinterweb import HtmlFrame
            self.webv = HtmlFrame(self.webbox, messages_enabled=False, on_link_click=self.web_link)
            self.webv.pack(fill="both", expand=True)
            self.webv.on_wheel = self.web_wheel   # the app's wheel handler finds this (normal speed: ~100 px per notch)
        url = self.page.server.url(*self.it["zim"])
        if url != self.web_url:
            self.web_url = url
            self.webv.load_website(url)

    def web_wheel(self, e):
        h = getattr(self.webv, "html", None) or self.webv
        try:
            first, last = h.yview()
            if last - first >= 1:
                return
            doc = max(h.winfo_height() / (last - first), 1)
            h.yview_moveto(max(0.0, min(1.0, first - (e.delta / 120) * 90 / doc)))
        except Exception:
            pass

    def web_link(self, url):
        """A click inside the web page: same page (#section) -> scroll there; another archive page -> open it in the
        reader (keeps Previous article); a real web address -> the normal browser."""
        base = self.page.server.url("", "").rsplit("/", 2)[0] + "/"
        if not url.startswith(base):
            return webbrowser.open(url)
        key, _, path = unquote(url[len(base):]).partition("/")
        path, _, frag = path.partition("#")
        if self.it and self.it.get("zim") == (key, path):
            return self.webv.load_url(url)
        self.page.open_entry(key, path)

    # ------------------------------------------------------------ note (a .txt beside the item)
    def paint_note_marks(self):
        has = bool(self.it) and self.page.app.notes.has(self.it)
        self.tab_w["Note"].config(text="\U0001F4DD  Note" if has else "+ Add note")
        if hasattr(self, "note_chip") and self.note_chip.winfo_exists():
            if has:
                self.note_chip.pack(side="left", padx=(0, 6))
            else:
                self.note_chip.pack_forget()
        self.ndel.set_enabled(has)

    def load_note(self):
        notes = self.page.app.notes
        self.note.delete("1.0", "end")
        if notes.has(self.it):
            self.note.insert("1.0", notes.read(self.it).rstrip("\n"))
            self.nstat.config(text=os.path.basename(notes.path(self.it)))
        else:
            self.nstat.config(text="Type a note, then Save (it is also saved when you leave this tab).")
        self.note.edit_modified(False); self.note.edit_reset()
        self.paint_note_marks()

    def save_note(self, quiet=False):
        if not self.it:
            return
        notes = self.page.app.notes
        text = self.note.get("1.0", "end").strip()
        if not text:
            if notes.has(self.it) and not quiet:
                return self.delete_note()
            return
        notes.save(self.it, text)
        self.note.edit_modified(False)
        self.nstat.config(text=f"Saved {time.strftime('%H:%M')}  \u2022  {os.path.basename(notes.path(self.it))}")
        self.paint_note_marks()

    def autosave(self):
        """Leaving the note (another tab, Back, Previous/Next, closing the app) keeps what was typed."""
        if getattr(self, "note", None) is not None and self.it and self.note.edit_modified():
            if self.note.get("1.0", "end").strip():
                self.save_note(quiet=True)
            self.note.edit_modified(False)

    def delete_note(self):
        notes = self.page.app.notes
        if not (self.it and notes.has(self.it)):
            return
        if not messagebox.askyesno("Delete note", "Delete the note for this item?\n\nIt goes to the Recycle Bin.", parent=self):
            return
        if notes.delete(self.it):
            self.note.delete("1.0", "end"); self.note.edit_modified(False)
            self.nstat.config(text="Note deleted (it is in the Recycle Bin).")
        self.paint_note_marks()

    def notepad(self):
        self.autosave()
        notes = self.page.app.notes
        if not notes.has(self.it):
            if not self.note.get("1.0", "end").strip():
                return self.nstat.config(text="Type something first - Notepad opens the saved note.")
            self.save_note()
        subprocess.Popen(["notepad.exe", notes.path(self.it)])
        self.nstat.config(text="Opened in Notepad - come back to this tab to see your changes.")

    # ------------------------------------------------------------ pictures
    def render_gallery(self):
        self.galv.clear()
        self.ggen += 1; gen = self.ggen
        self.gimgs = []
        g = self.galv.inner
        gw, gh = 176, 132
        cols = max(2, (self.galv.canvas.winfo_width() - 24) // (gw + 14))
        label(g, f"{len(self.gallery)} picture" + ("s" if len(self.gallery) != 1 else "") + " - click one to see it large",
              9, fg="dim").grid(row=0, column=0, columnspan=cols, sticky="w", padx=14, pady=(12, 6))
        slots = []
        for k, (p, cap) in enumerate(self.gallery):
            f = tk.Frame(g, bg=C["card"], cursor="hand2", highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=1 + k // cols, column=k % cols, padx=(14 if k % cols == 0 else 0, 14), pady=(0, 14), sticky="n")
            box = tk.Frame(f, bg="#eceae3", width=gw, height=gh); box.pack(); box.pack_propagate(False)
            c = tk.Label(f, text=(cap[:70] + ("\u2026" if len(cap) > 70 else "")) if cap else f"Picture {k + 1}",
                         font=(F, 8), bg=C["card"], fg=C["dim"] if cap else "#a0a69f", wraplength=gw - 8, justify="left",
                         anchor="nw", height=2)
            c.pack(fill="x", padx=4, pady=(3, 4))
            for w in (f, box, c):
                w.bind("<Button-1>", lambda e, k=k: self.show_image(k))
                w.bind("<Enter>", lambda e, f=f: f.config(highlightbackground=C["primary"]))
                w.bind("<Leave>", lambda e, f=f: f.config(highlightbackground=C["line"]))
            slots.append(box)

        def work():   # small previews made off the main thread, shown as they are ready
            for k, (p, _) in enumerate(self.gallery):
                if gen != self.ggen:
                    return
                try:
                    im = fit_image(p, gw, gh)
                except Exception:
                    continue
                self.after(0, lambda k=k, im=im: self.put_thumb(gen, k, slots[k], im))
        threading.Thread(target=work, daemon=True).start()

    def put_thumb(self, gen, k, box, im):
        if gen != self.ggen or not box.winfo_exists():
            return
        img = ImageTk.PhotoImage(im); self.gimgs.append(img)
        l = tk.Label(box, image=img, bg="#eceae3", bd=0, cursor="hand2"); l.pack(expand=True)
        l.bind("<Button-1>", lambda e: self.show_image(k))

    def show_image(self, k):
        if not self.gallery:
            return
        self.gi = k % len(self.gallery)
        if not self.imv.winfo_ismapped():
            self.galv.pack_forget(); self.head.pack_forget()
            self.imv.pack(fill="both", expand=True)
            self.keys(True)
            self.update_idletasks()
        p, cap = self.gallery[self.gi]
        self.iz = 1.0
        try:
            self._full = fit_image(p, 6000, 6000)   # the picture itself (very large ones capped at 6000 px)
        except Exception:
            self._full = None
        if not self.zbar.winfo_ismapped():
            self.zbar.pack(side="right", padx=(10, 0))
        self.draw_image()
        self.gl.config(text=f"{self.gi + 1} of {len(self.gallery)}")
        self.cap.config(text=cap or f"Picture {self.gi + 1}")

    def draw_image(self):
        c = self.big
        c.delete("all")
        cw, ch = max(c.winfo_width(), 400), max(c.winfo_height(), 300)
        im = self._full
        if im is None:
            c.create_text(cw // 2, ch // 2, text="This picture can't be shown - use Open full size.", fill="#cfd8d3", font=(F, 10))
            self.bigimg = None
            self.paint_zoom()
            return
        fit = min((cw - 20) / im.width, (ch - 20) / im.height, 1.0)   # fit the window, never enlarged at 'Fit'
        sc = min(fit * self.iz, 4.0)
        w, h = max(1, int(im.width * sc)), max(1, int(im.height * sc))
        self.bigimg = ImageTk.PhotoImage(im.resize((w, h), Image.LANCZOS) if (w, h) != im.size else im)
        x, y = max(cw, w) // 2, max(ch, h) // 2
        c.create_image(x, y, image=self.bigimg)
        c.configure(scrollregion=(0, 0, max(cw, w), max(ch, h)))
        c.xview_moveto((1 - cw / max(cw, w)) / 2 if w > cw else 0)   # start in the middle of a zoomed picture
        c.yview_moveto((1 - ch / max(ch, h)) / 2 if h > ch else 0)
        c.config(cursor="fleur" if (w > cw or h > ch) else "hand2")
        self.paint_zoom()

    def img_press(self, e):
        self._moved = False
        self.big.scan_mark(e.x, e.y)

    def img_drag(self, e):
        if self.iz > 1.0:
            self._moved = True
            self.big.scan_dragto(e.x, e.y, gain=1)

    def img_release(self, e):
        if not getattr(self, "_moved", False) and self.iz <= 1.0:   # a plain click at 'Fit' goes to the next picture
            self.show_image(self.gi + 1)

    # ------------------------------------------------------------ zoom
    @staticmethod
    def active_zoom(step):
        for r in Reader.INSTANCES:
            if r.winfo_ismapped():
                r.zoom(step)
                return "break"

    def zoom_target(self):
        if self.imv.winfo_ismapped():
            return "image"
        if self.cur_tab == "Pages" and (self.pdfv.winfo_ismapped() or self.doc):   # (just opened: not drawn on screen yet)
            return "pdf"
        if self.cur_tab == "Read" and self.text.winfo_ismapped():
            return "text"
        return None

    def zoom_help(self):
        """The '?' / hover note on the zoom buttons: every way to zoom and move, for what is showing."""
        t = self.zoom_target()
        if t == "text":
            return ("Text size\n"
                    "  \u2212  /  +  /  Fit  -  smaller, bigger, back to normal\n"
                    "  Ctrl + mouse wheel  -  smaller / bigger\n"
                    "  Ctrl +   Ctrl \u2212   Ctrl 0  -  bigger, smaller, normal\n"
                    "The size is remembered for every page.")
        if t != "pdf":
            return ""
        common = ("  \u2212  /  +  /  Fit  -  zoom out, in, whole page width\n"
                  "  Ctrl + mouse wheel  -  zoom in / out\n"
                  "  Ctrl +   Ctrl \u2212   (number-pad + \u2212 too)  -  zoom in / out\n"
                  "  Ctrl 0  -  back to Fit\n"
                  "  Mouse wheel  -  scroll up / down\n"
                  "  Shift + mouse wheel  -  scroll sideways\n"
                  "  Click and drag  -  move around a zoomed-in page")
        if not self.geo:
            return "Zooming the page\n" + common
        return ("Zooming the map  (zooming keeps the middle of the view in place, up to 2000%)\n" + common +
                "\n\nOn the map\n"
                "  \U0001F4CD Add waypoint, then click  -  save a spot (or right-click a spot)\n"
                "  \U0001F4CF Measure, then click points  -  straight-line distances and the total\n"
                "  Click a red pin  -  edit that waypoint\n"
                "  \U0001F30E North America map  -  the same spot on the road map")

    def step(self, z, d):
        if d == 0:
            return 1.0
        zs = Reader.MAP_ZOOMS if self.geo and self.zoom_target() == "pdf" else Reader.ZOOMS
        k = min(range(len(zs)), key=lambda i: abs(zs[i] - z))
        return zs[max(0, min(len(zs) - 1, k + d))]

    def zoom(self, d):
        t = self.zoom_target()
        if t == "text":
            self.tz = self.step(self.tz, d)
            self.apply_text_zoom()
            st = load_json(SETTINGS_FILE, {}); st["reader_zoom"] = self.tz; save_json(SETTINGS_FILE, st)
        elif t == "pdf":
            self.pz = max(1.0 if d == 0 else 0.5, self.step(self.pz, d))
            self.pdf_go(self.pno, keep=True)
        elif t == "image":
            self.iz = max(1.0, self.step(self.iz, d))
            self.draw_image()
        self.paint_zoom()

    def paint_zoom(self):
        t = self.zoom_target()
        z = {"text": self.tz, "pdf": self.pz, "image": self.iz}.get(t, 1.0)
        self.zl.config(text="Fit" if t in ("pdf", "image") and z == 1.0 else f"{round(z * 100)}%")

    def apply_text_zoom(self):
        z, t = self.tz, self.text
        sz = {k: max(6, round(v * z)) for k, v in Reader.TEXT_SIZES.items()}
        t.configure(font=(F, sz["base"]))
        t.tag_configure("h1", font=(F, sz["h1"], "bold")); t.tag_configure("h2", font=(F, sz["h2"], "bold"))
        t.tag_configure("h3", font=(F, sz["h3"], "bold")); t.tag_configure("b", font=(F, sz["b"], "bold"))
        t.tag_configure("mono", font=("Consolas", sz["mono"])); t.tag_configure("dim", font=(F, sz["dim"]))

    def keys(self, on):
        top = self.winfo_toplevel()
        if on and not self.keys_on:
            top.bind("<Left>", lambda e: self.imv.winfo_ismapped() and self.show_image(self.gi - 1))
            top.bind("<Right>", lambda e: self.imv.winfo_ismapped() and self.show_image(self.gi + 1))
            top.bind("<Escape>", lambda e: self.imv.winfo_ismapped() and self.set_tab("Pictures"))
        elif not on and self.keys_on:
            for k in ("<Left>", "<Right>", "<Escape>"):
                top.unbind(k)
        self.keys_on = on

    # ------------------------------------------------------------ pdf pages
    def pdf_edge(self, d):
        """Mouse wheel at the bottom (top) of a PDF page turns to the next (previous) page - not on maps, which pan.
        A short pause after each turn, so one fast flick of the wheel doesn't skip several pages."""
        if not self.doc or self.geo or self.cur_tab != "Pages" or not 0 <= self.pno + d < self.doc.page_count:
            return
        now = time.monotonic()
        if now < getattr(self, "_edge_until", 0):
            return
        self._edge_until = now + 0.45
        self.pdf_go(self.pno + d)
        if d < 0:   # going back up: land at the bottom of the previous page, as if scrolling through one long document
            self.update_idletasks(); self.pdfv.canvas.yview_moveto(1.0)

    def pdf_go(self, n, keep=False):
        if not self.doc:
            return
        import pymupdf
        self.pno = max(0, min(n, self.doc.page_count - 1))
        pg = self.doc[self.pno]
        w = max(self.pdfv.canvas.winfo_width() - 40, 500)
        z = min(w / pg.rect.width, 2.5) * self.pz   # fit to the window width, times the zoom
        # maps go much deeper (the imagery has ~1 m detail); Tk can't show a widget over ~32,000 px
        z = min(z, 30000 / max(pg.rect.width, pg.rect.height)) if self.geo else min(z, 8.0)
        centre = self.view_centre() if self.geo and keep else None   # maps keep the same spot in view when zooming
        self.pdf_z = z
        self.tile.place_forget()
        self.win_rect = None
        if self.geo and pg.rect.width * pg.rect.height * z * z > self.FULL_PIXELS:
            # too big to draw whole: an empty label the size of the page, with just the part on screen drawn on top of it
            self.pdf_l.config(image=self.blank, width=round(pg.rect.width * z), height=round(pg.rect.height * z))
            self.win_rect = ()   # nothing drawn yet: drawn once the view has been placed (map_scrolled below)
        else:
            pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if self.geo and self.pno == 0:
                self.draw_waypoints(im, z)
                self._base = (im, (0, 0), self.pdf_l)
                im = self.with_measure(im, z, (0, 0))
            img = ImageTk.PhotoImage(im)
            self.imgs = [i for i in self.imgs if getattr(i, "_pic", False)] + [img]
            self.pdf_l.config(image=img, width=0, height=0)
        self.pl.config(text=f"Page {self.pno + 1} of {self.doc.page_count}")
        if self.geo and self.wp_focus and not keep:
            x, y = self.geo.forward(self.wp_focus["lat"], self.wp_focus["lon"])
            self.after_idle(lambda: self.centre_on(x, y))
        elif centre:
            self.after_idle(lambda: self.centre_on(*centre))
        elif self.geo and not keep and (m := wpt.map_for_pdf(self.pdf_path)):
            # a map opens on the middle of the sheet (not the title strip at the top), so zooming in goes to the map's centre
            mx, my = self.geo.forward((m["s"] + m["n"]) / 2, (m["w"] + m["e"]) / 2)
            self.after_idle(lambda: self.centre_on(mx, my))
        elif not keep:
            self.pdfv.top()
            self.pdfv.canvas.xview_moveto(0)
        if self.win_rect is not None:
            self.after_idle(self.map_scrolled)
        self.after_idle(self.paint_zoom)   # e.g. a waypoint opens the map at 300%

    # ------------------------------------------------------------ maps: deep zoom draws only the part on screen
    FULL_PIXELS = 30e6   # above this a map is drawn in pieces (a whole 1:24,000 sheet at 1600% would be ~1 GB)

    def map_scrolled(self, *_):
        """After scrolling / dragging a deeply zoomed map: draw the newly visible part (once things settle)."""
        if self.geo and self.win_rect is not None:
            if getattr(self, "_win_job", None):
                self.after_cancel(self._win_job)
            self._win_job = self.after(120, lambda: self.render_window(only_if_needed=True))

    def render_window(self, only_if_needed=False):
        import pymupdf
        self._win_job = None
        if not self.doc or not self.geo or self.cur_tab != "Pages":
            return
        c, z = self.pdfv.canvas, self.pdf_z
        lx, ly = self.pdf_l.winfo_x(), self.pdf_l.winfo_y()
        vx0, vy0 = c.canvasx(0) - lx, c.canvasy(0) - ly
        vw, vh = c.winfo_width(), c.winfo_height()
        W, H = self.pdf_l.winfo_reqwidth(), self.pdf_l.winfo_reqheight()
        vx0, vy0, vx1, vy1 = max(0, vx0), max(0, vy0), min(W, vx0 + vw), min(H, vy0 + vh)
        r = self.win_rect
        if only_if_needed and r and r[0] <= vx0 and r[1] <= vy0 and r[2] >= vx1 and r[3] >= vy1:
            return   # still inside what was drawn
        mx, my = vw * 0.5, vh * 0.5   # draw a margin around the view so small scrolls need no redraw
        x0, y0 = int(max(0, vx0 - mx)), int(max(0, vy0 - my))
        x1, y1 = int(min(W, vx1 + mx)), int(min(H, vy1 + my))
        if x1 <= x0 or y1 <= y0:
            return
        pg = self.doc[self.pno]
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=pymupdf.Rect(x0 / z, y0 / z, x1 / z, y1 / z), alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        if self.pno == 0:
            self.draw_waypoints(im, z, (x0, y0))
            self._base = (im, (x0, y0), self.tile)
            im = self.with_measure(im, z, (x0, y0))
        img = ImageTk.PhotoImage(im)
        self.imgs = [i for i in self.imgs if getattr(i, "_pic", False)] + [img]
        self.tile.config(image=img)
        self.tile.place(x=x0, y=y0)
        self.win_rect = (x0, y0, x0 + pix.width, y0 + pix.height)

    def open_na_here(self):
        """The North America road map at the same spot: the waypoint / searched position this map was opened for,
        else the middle of what is on screen, else the middle of the sheet."""
        f, name = self.wp_focus, None
        if f:
            lat, lon, name = f["lat"], f["lon"], f.get("name")
        else:
            sheet = re.sub(r" - USGS .*", "", self.it["title"])
            m = wpt.map_for_pdf(self.pdf_path)
            c = self.view_centre() if self.cur_tab == "Pages" and self.doc and self.pno == 0 else None
            p = self.geo.inverse(*c) if c else None
            if p and (not m or (m["s"] <= p[0] <= m["n"] and m["w"] <= p[1] <= m["e"])):
                (lat, lon), name = p, f"Centre of the view on {sheet}"
            elif m:
                lat, lon, name = (m["s"] + m["n"]) / 2, (m["w"] + m["e"]) / 2, f"{sheet} (centre of the sheet)"
            else:
                return self.page.app.open_na_map()
        self.page.app.open_na_map(lat, lon, name)

    # ------------------------------------------------------------ maps: 📏 Measure (straight-line legs and the total)
    def toggle_measure(self, on=None):
        self.measuring = (not self.measuring) if on is None else on
        if self.measuring:
            self.adding_wp = False; self.paint_add_wp()
        self.meas_b.config(text="📏  Measuring…" if self.measuring else "📏  Measure")
        self.meas_b.c_bg = "#c2185b" if self.measuring else C["sec"]; self.meas_b.c_fg = "#ffffff" if self.measuring else C["text"]
        self.meas_b.config(bg=self.meas_b.c_bg, fg=self.meas_b.c_fg)
        self.paint_measure()

    def measure_undo(self):
        if self.mpts:
            self.mpts.pop(); self.measure_changed()

    def measure_clear(self):
        if self.mpts:
            self.mpts = []; self.measure_changed()

    def measure_changed(self):
        """Redraw the line on the picture already on screen (no new render of the map)."""
        if self._base:
            base, off, widget = self._base
            img = ImageTk.PhotoImage(self.with_measure(base, self.pdf_z, off))
            self.imgs = [i for i in self.imgs if getattr(i, "_pic", False)] + [img]
            widget.config(image=img)
        self.paint_measure()

    def paint_measure(self):
        pts = self.mpts
        if not self.measuring and not pts:
            self.mstrip.pack_forget(); return
        legs = [wpt.distance_km(pts[k - 1], pts[k]) for k in range(1, len(pts))]
        self.mtotal.config(text=("📏  Click points on the map to measure straight-line distances." if len(pts) < 2 else
                                 f"📏  Total {wpt.dist_text(sum(legs))}  ·  {len(legs)} leg{'s' if len(legs) != 1 else ''}"
                                 + (f"  ·  last leg {wpt.dist_text(legs[-1])}" if len(legs) > 1 else "")))
        if not self.mstrip.winfo_manager():
            self.mstrip.pack(fill="x", before=self.bodyf, pady=(0, 4))

    def with_measure(self, im, z, offset):
        """A copy of the picture with the measuring line, points and each leg's distance (or the picture itself if none)."""
        if not self.mpts or not self.geo:
            return im
        from PIL import ImageFont
        im = im.copy()
        d = ImageDraw.Draw(im)
        try:
            font = ImageFont.truetype("segoeuib.ttf", max(12, round(13 * min(z, 1.6))))
        except OSError:
            font = ImageFont.load_default()
        xy = [(x * z - offset[0], y * z - offset[1]) for x, y in (self.geo.forward(*p) for p in self.mpts)]
        col = (194, 24, 91)
        if len(xy) > 1:
            d.line(xy, fill=(255, 255, 255), width=7, joint="curve")
            d.line(xy, fill=col, width=4, joint="curve")
        for k, (x, y) in enumerate(xy):
            d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 255, 255), outline=col, width=3)
        for k in range(1, len(xy)):
            (x0, y0), (x1, y1) = xy[k - 1], xy[k]
            d.text(((x0 + x1) / 2, (y0 + y1) / 2 - 12), wpt.dist_text(wpt.distance_km(self.mpts[k - 1], self.mpts[k])), font=font,
                   fill=(136, 14, 79), anchor="mm", stroke_width=3, stroke_fill=(255, 255, 255))
        return im

    def _pos(self, e):
        """Mouse position in pixels of the whole (zoomed) page, whichever piece of it the event came from."""
        return e.x_root - self.pdf_l.winfo_rootx(), e.y_root - self.pdf_l.winfo_rooty()

    # ------------------------------------------------------------ maps: waypoints on georeferenced topo PDFs
    def draw_waypoints(self, im, z, offset=(0, 0)):
        """Red pins + names for every saved waypoint on this map; the one it was opened for is larger.
        offset = where this picture sits on the whole zoomed page (deep zoom draws only a piece)."""
        from PIL import ImageFont
        d = ImageDraw.Draw(im)
        try:
            font = ImageFont.truetype("segoeuib.ttf", max(11, round(13 * min(z, 1.6))))
        except OSError:
            font = ImageFont.load_default()
        self.wp_marks = []
        focus = (self.wp_focus or {}).get("id")
        for wp in wpt.load():
            x, y = self.geo.forward(wp["lat"], wp["lon"])
            if not (0 <= x <= self.geo.width and 0 <= y <= self.geo.height):
                continue
            px, py = x * z - offset[0], y * z - offset[1]
            if not (-300 <= px <= im.width + 300 and -60 <= py <= im.height + 60):
                self.wp_marks.append((px + offset[0], py + offset[1], wp))
                continue
            r = 11 if wp.get("id") == focus else 8
            if wp.get("id") == focus:
                d.ellipse((px - 26, py - 26, px + 26, py + 26), outline=(214, 40, 40), width=3)
            d.ellipse((px - r, py - r, px + r, py + r), fill=(214, 40, 40), outline=(255, 255, 255), width=3)
            d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 255, 255))
            d.text((px + r + 6, py), wp["name"], font=font, fill=(150, 20, 20), anchor="lm", stroke_width=3, stroke_fill=(255, 255, 255))
            self.wp_marks.append((px + offset[0], py + offset[1], wp))
        f = self.wp_focus
        if f and not f.get("id"):   # a searched position (not a saved waypoint): blue target
            x, y = self.geo.forward(f["lat"], f["lon"])
            px, py = x * z - offset[0], y * z - offset[1]
            blue = (26, 115, 232)
            d.ellipse((px - 26, py - 26, px + 26, py + 26), outline=blue, width=3)
            d.line((px - 34, py, px - 10, py), fill=blue, width=3); d.line((px + 10, py, px + 34, py), fill=blue, width=3)
            d.line((px, py - 34, px, py - 10), fill=blue, width=3); d.line((px, py + 10, px, py + 34), fill=blue, width=3)
            d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=blue, outline=(255, 255, 255), width=2)
            d.text((px + 32, py - 30), f"{f['name']}  {wpt.fmt(f['lat'], f['lon'])}", font=font, fill=(11, 79, 174), anchor="lm",
                   stroke_width=3, stroke_fill=(255, 255, 255))

    def centre_on(self, x, y):
        """Scroll the page so PDF point (x, y) is in the middle of the window."""
        c = self.pdfv.canvas
        self.pdfv.fit_width(); c.update_idletasks()
        bb = c.bbox("all")
        if not bb:
            return
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        ix, iy = self.pdf_l.winfo_x() + x * self.pdf_z, self.pdf_l.winfo_y() + y * self.pdf_z
        c.xview_moveto(max(0.0, (ix - c.winfo_width() / 2) / tw))
        c.yview_moveto(max(0.0, (iy - c.winfo_height() / 2) / th))

    def view_centre(self):
        """PDF point at the middle of the window now."""
        c = self.pdfv.canvas
        bb = c.bbox("all")
        if not bb or not self.pdf_z:
            return None
        cx = c.canvasx(c.winfo_width() / 2) - self.pdf_l.winfo_x()
        cy = c.canvasy(c.winfo_height() / 2) - self.pdf_l.winfo_y()
        # the whole page fits across (or down): use the middle of the map itself - not the empty space around the page,
        # nor the page's middle (regional sheets have their legend down one side)
        w, h = self.pdf_l.winfo_reqwidth(), self.pdf_l.winfo_reqheight()
        m = wpt.map_for_pdf(self.pdf_path) if self.geo else None
        mx, my = (v * self.pdf_z for v in self.geo.forward((m["s"] + m["n"]) / 2, (m["w"] + m["e"]) / 2)) if m else (w / 2, h / 2)
        if w <= c.winfo_width():
            cx = mx
        if h <= c.winfo_height():
            cy = my
        return cx / self.pdf_z, cy / self.pdf_z

    def map_point(self, e):
        """(lat, lon) under the mouse, or None off the map."""
        if not self.geo or self.pno != 0:
            return None
        ex, ey = self._pos(e)
        lat, lon = self.geo.inverse(ex / self.pdf_z, ey / self.pdf_z)
        m = wpt.map_for_pdf(self.pdf_path)
        if m and not (m["s"] - 0.002 <= lat <= m["n"] + 0.002 and m["w"] - 0.002 <= lon <= m["e"] + 0.002):
            return None   # in the page margin, outside the map itself
        return lat, lon

    def mark_at(self, e):
        ex, ey = self._pos(e)
        for px, py, wp in self.wp_marks:
            if abs(ex - px) <= 12 and abs(ey - py) <= 12:
                return wp
        return None

    def map_motion(self, e):
        if not self.geo:
            return
        p = self.map_point(e)
        wp = self.mark_at(e)
        self.ml.config(text=wp["name"][:30] if wp else wpt.fmt(*p) if p else "")
        cur = "crosshair" if self.adding_wp and p else "hand2" if wp else "fleur" if self.pz > 1 else ""
        self.pdf_l.config(cursor=cur); self.tile.config(cursor=cur)

    def map_press(self, e):
        self._drag = (e.x_root, e.y_root, False)
        self.pdfv.canvas.scan_mark(e.x_root, e.y_root)

    def map_drag(self, e):   # drag to move around a zoomed-in map
        if getattr(self, "_drag", None):
            x0, y0, _ = self._drag
            if abs(e.x_root - x0) + abs(e.y_root - y0) > 4:
                self._drag = (x0, y0, True)
                self.pdfv.canvas.scan_dragto(e.x_root, e.y_root, gain=1)

    def map_release(self, e):
        moved = getattr(self, "_drag", (0, 0, False))[2]
        self._drag = None
        if moved or not self.geo:
            return
        if self.measuring:
            p = self.map_point(e)
            if p:
                self.mpts.append(p); self.measure_changed()
            return
        wp = self.mark_at(e)
        if wp and not self.adding_wp:
            return self.edit_wp(wp)
        if self.adding_wp:
            p = self.map_point(e)
            if p:
                self.add_wp(*p)

    def map_menu(self, e):
        p = self.map_point(e)
        if not p:
            return
        m = self.wp_menu
        m.delete(0, "end")
        wp = self.mark_at(e)
        if wp:
            m.add_command(label=f"Edit “{wp['name'][:30]}”…", command=lambda: self.edit_wp(wp))
            m.add_separator()
        m.add_command(label=f"Add a waypoint here  ({wpt.fmt(*p)})", command=lambda: self.add_wp(*p))
        m.add_command(label="Copy position", command=lambda: (self.clipboard_clear(), self.clipboard_append(wpt.fmt(*p))))
        m.tk_popup(e.x_root, e.y_root)

    def toggle_add_wp(self):
        self.adding_wp = not self.adding_wp
        self.paint_add_wp()

    def paint_add_wp(self):
        on = self.adding_wp
        self.addwp_b.config(text="✖  Cancel adding" if on else "\U0001F4CD  Add waypoint")
        self.ml.config(text="Click the spot on the map" if on else "")

    def add_wp(self, lat, lon):
        self.adding_wp = False; self.paint_add_wp()
        wp = waypoint_dialog(self.page.app, "Add a waypoint", lat=lat, lon=lon)
        if wp:
            save_waypoint(wp)
            self.redraw_map()
            self.page.app.waypoints_changed()

    def edit_wp(self, wp):
        new = waypoint_dialog(self.page.app, "Edit waypoint", wp)
        if new:
            save_waypoint(new)
            self.redraw_map()
            self.page.app.waypoints_changed()

    def redraw_map(self):
        if self.doc and self.cur_tab == "Pages":
            self.pdf_go(self.pno, keep=True)

    # ------------------------------------------------------------ markdown
    def render_text(self):
        t, it = self.text, self.it
        t.config(state="normal"); t.delete("1.0", "end"); self.links = {}
        if it["type"] == "recipe-card":
            self.inline_image(abspath(it["original"]), 640)
            t.insert("end", "\n\nText read from the card (check the picture for exact amounts):\n", "dim")
            t.insert("end", it.get("text") or "(no text could be read)", "mono")
        elif it.get("zim"):
            self.md(it.get("text") or "")
        elif not it.get("file"):
            what = "audio lesson" if it["type"] == "audio" else "video"
            where = f" from {it['module']}" if it.get("module") else ""
            t.insert("end", f"This is a {what}{where}. Use \u201cPlay\u201d above to {'listen to' if it['type'] == 'audio' else 'watch'} it."
                     + ("\nUse Next \u203a at the top to go on to the next part of the course." if it.get("module") else ""), "dim")
        else:
            self.md(read_md(it))
        t.config(state="disabled")
        t.yview_moveto(it.pop("_ypos", 0) if it.get("zim") else 0)   # archive pages: back where you left them

    def md(self, src):
        t = self.text
        base = self.it.get("base") or os.path.dirname(abspath(self.it["file"]))
        body = FM.sub("", src, 1)
        limit = 3_000_000 if self.it.get("zim") else self.MAXCH   # archive books are read whole (a novel renders in ~1 s)
        cut = len(body) > limit
        body = body[:limit]
        title_skipped, fence, nimg = False, False, 0
        self.md_base, self.nimg = base, 0
        for line in body.splitlines():
            if line.startswith("```"):
                fence = not fence; continue
            if fence:
                t.insert("end", line + "\n", "mono"); continue
            s = line.strip()
            if not title_skipped and s.startswith("# "):
                title_skipped = True; continue
            m = re.match(r"^(#{1,6})\s+(.*)", s)
            if m:
                t.insert("end", plain(m[2]) + "\n", "h" + str(min(len(m[1]), 3))); continue
            im = re.fullmatch(r"!\[([^\]]*)\]\(<?([^)>]+?)>?\)", s)
            if im:
                p = im[2]
                if not p.startswith("http") and self.nimg < 40:
                    self.nimg += 1
                    self.inline_image(os.path.normpath(os.path.join(base, unquote(p))), 560)
                    t.insert("end", "\n")
                continue
            if re.fullmatch(r"-{3,}|\*{3,}", s):
                t.insert("end", "\u2500" * 40 + "\n", "dim"); continue
            if s.startswith("|"):
                if re.fullmatch(r"\|[\s:|-]+\|?", s):
                    continue
                t.insert("end", "   ".join(c.strip() for c in s.strip("|").split("|")) + "\n", "mono"); continue
            lm = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)", line)
            if lm:
                bullet = "\u2022" if lm[1] in "-*+" else lm[1]
                self.inline(f"{bullet}  " + lm[2], ("li",)); t.insert("end", "\n", "li"); continue
            if s.startswith(">"):
                self.inline(s.lstrip("> "), ("dim",)); t.insert("end", "\n"); continue
            if len(s) > 2 and s[0] == s[-1] and s[0] in "*_" and s[1] not in "*_":   # *caption / credit line*
                self.inline(s[1:-1], ("dim",)); t.insert("end", "\n"); continue
            self.inline(s, ()); t.insert("end", "\n")
        if cut:
            t.insert("end", "\n\u2026 (very long - the rest is in the full file: use Show in folder)\n", "dim")

    INL = re.compile(r"(\*\*[^*]+\*\*|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\)|<https?://[^>]+>)")

    def inline(self, s, tags):
        t = self.text
        for part in self.INL.split(s):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                t.insert("end", part[2:-2], tags + ("b",))
            elif part.startswith("!["):
                m = re.match(r"!\[[^\]]*\]\(<?([^)>]+?)>?\)", part)
                if m and not m[1].startswith("http") and getattr(self, "nimg", 99) < 40:
                    self.nimg += 1
                    t.insert("end", "\n")
                    self.inline_image(os.path.normpath(os.path.join(self.md_base, unquote(m[1]))), 360)
            elif part.startswith("[") and "](" in part:
                txt, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part).groups()
                self.link(txt, url, tags)
            elif part.startswith("<http"):
                self.link(part[1:-1], part[1:-1], tags)
            else:
                t.insert("end", re.sub(r"(?<!\w)[*_](\S[^*_]*?)[*_](?!\w)", r"\1", part), tags)

    def link(self, txt, url, tags):
        tag = f"link{len(self.links)}"
        url = re.sub(r'\s+"[^"]*"\s*$', "", url.strip())   # [text](address "hover title") -> address
        if url.startswith("zim://"):   # another page of the same offline archive
            self.links[tag] = url
            self.text.insert("end", txt, tags + ("link", tag))
            self.text.tag_bind(tag, "<Button-1>", lambda e, u=url: self.page.open_link(u))
            return
        target = url if url.startswith(("http", "mailto:")) else os.path.normpath(
            os.path.join(os.path.dirname(abspath(self.it["file"])), unquote(url)))
        self.links[tag] = target
        self.text.insert("end", txt, tags + ("link", tag))
        self.text.tag_bind(tag, "<Button-1>", lambda e, u=target: webbrowser.open(u) if u.startswith(("http", "mailto:")) else self.open_local(u))

    def open_local(self, p):
        rel = os.path.relpath(p, RESEARCH).replace("\\", "/")
        it = self.page.app.lib.by_path.get(rel)
        if it and (it.get("file") or it.get("module")):   # another library item: show it here
            return self.show(it)
        if os.path.exists(p):
            open_path(p)

    def inline_image(self, p, maxw):
        try:
            im = Image.open(p); im.seek(0)
            im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width < 40:
                return
            if im.width > maxw:
                im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
            img = ImageTk.PhotoImage(im); img._pic = True
            self.imgs.append(img)
            self.text.image_create("end", image=img, padx=4, pady=6)
        except Exception:
            pass
