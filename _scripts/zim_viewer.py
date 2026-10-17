"""Offline Archives - a read-only viewer for the Kiwix .zim archives in _sources\\zim, inside Library Manager.

Nothing is imported into the library and nothing is written into the Research folder: an article is converted to
Markdown in memory and shown in the normal Reader; its pictures go to a temporary folder in Windows' TEMP (removed
when the app closes). "Open in browser" serves the archive's original pages from a small web server on this PC only
(127.0.0.1), the way Kiwix does.

  ZimShelf   the archives (title, icon, size, counts), title suggestions, full-text search, article conversion
  ZimServer  the local web server for "Open in browser"
  ZimPage    the "Offline Archives" section: archive cards, search across one or all archives, article reader
"""
import ast, atexit, glob, hashlib, html as _html, importlib, io, os, posixpath, queue, re, shutil, tempfile, threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from lm_ui import *
import library_viewer as lv

ZIM_DIR = os.path.join(RESEARCH, "_sources", "zim")
TMP = os.path.join(tempfile.gettempdir(), "LibraryManager-zim")   # outside the library; cleared at start and exit
shutil.rmtree(TMP, ignore_errors=True)
atexit.register(lambda: shutil.rmtree(TMP, ignore_errors=True))

# content area / junk to strip, per archive (same rules the library builders use, by file name prefix)
JUNK = ["style", "script", "link", "sup.reference", ".reference", ".mw-editsection", ".reflist", ".references", ".navbox",
        ".vertical-navbox", ".sidebar", ".metadata", ".ambox", ".noprint", ".mw-empty-elt", ".shortdescription",
        ".sistersitebox", ".portalbox", ".toc", "#toc", ".mbox-small", ".side-box", ".navbox-styles", ".authority-control",
        ".mw-authority-control", ".catlinks", "span.mw-cite-backlink", "nav", "footer", "#footer", "header", "form",
        ".js-post-menu", ".bottom-notice", "#sidebar", ".nhsuk-breadcrumb", ".nhsuk-related-nav", ".app-page-feedback",
        "#mplus-share", ".page-info", "#breadcrumbs", "#comments", ".comments", "#banner", ".banner-content"]
ROOTS = [("wikipedia", "#mw-content-text"), ("wikibooks", "#mw-content-text"), ("wikem", "#mw-content-text"),
         ("appropedia", "#mw-content-text"), ("energypedia", "#mw-content-text"), ("ifixit", "#mainBody, #main"),
         ("medlineplus", "#mplus-content, #d-article, article, main"), ("nhs", "main"),
         ("stackexchange", "#mainbar, main, #content")]
DROP_SECTIONS = {"references", "notes", "footnotes", "citations", "sources", "bibliography", "external links",
                 "notes and references", "references and notes", "works cited", "explanatory notes", "cited sources",
                 "general references", "general and cited references"}
ICON_RE = re.compile(r"(Symbol_|Commons-logo|Wiki[a-z]+-logo|Edit-clear|Question_book|Ambox|Padlock|OOjs_UI|Speakerlink|"
                     r"Sound-icon|Nuvola|Crystal_Clear|Portal-puzzle|Increase2|Decrease|Steady2|Red_Pencil|Lock-|"
                     r"Semi-protection|Disambig|Emblem-|gravatar|avatar)", re.I)
EXT = {"image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/svg+xml": ".svg"}


# translated copies of a page live at '<page>/<language code>' (WikEM, Appropedia); Wikipedia/Wikibooks use '/' for real sub-pages
LANG_CODES = {"ar", "bn", "cs", "da", "de", "el", "es", "fa", "fi", "fr", "ha", "he", "hi", "hu", "id", "ig", "it", "ja", "ko", "ms",
              "nl", "no", "pl", "pt", "pt-br", "ro", "ru", "sv", "sw", "th", "tl", "tr", "uk", "ur", "vi", "yo", "zh", "zh-hans", "zh-hant"}


def is_translation(key, path):
    if "wikipedia" in key or "wikibooks" in key or "/" not in path:
        return False
    return path.rstrip("/").rsplit("/", 1)[-1].lower() in LANG_CODES


def plain_text(s):
    """Lower case without accents, for matching names: 'Emily Bront\u00eb' -> 'emily bronte'."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


SHELF_SORTS = [("popular", "Most popular"), ("az", "Title A\u2013Z"), ("za", "Title Z\u2013A"), ("author", "Author A\u2013Z"),
               ("author-za", "Author Z\u2013A")]
AUTHOR_SORTS = SHELF_SORTS[:3]


def title_key(t):
    """Library-catalogue order: no leading quotes/punctuation, no leading The / A / An."""
    t = re.sub(r"^[^\w]+", "", plain_text(t))
    t = re.sub(r"^(the|a|an)\s+", "", t)
    return re.sub(r"^[^\w]+", "", t)   # "The 'Blackwood' Group" -> "blackwood' group'


def surname_key(name):
    """'G. A. (George Alfred) Henty' -> 'henty g a'; 'Charles Dickens' -> 'dickens charles'."""
    n = re.sub(r"\(.*?\)", " ", plain_text(name))
    n = re.sub(r"[^\w\s]", " ", re.sub(r",.*$", "", n)).split()   # stray brackets/dots in the data don't sort first
    return " ".join(n[-1:] + n[:-1]) if n else ""


def sort_bar(key, path, current, sorts):
    """The sort choices for the reader's fixed strip: [(label, link or None for the current order)]."""
    return [(label, None if code == current else f"zim://{quote(key)}/{quote(path + '?sort=' + code, safe='/')}")
            for code, label in sorts]


def resolve_path(a, here, target):
    """An href relative to the page -> the archive path that exists ('dir/' links keep their slash), or None."""
    zp = unquote(posixpath.normpath(posixpath.join(here, target)))
    cands = ([zp + "/", zp] if target.endswith("/") else [zp, zp + "/"]) + [zp.rstrip("/") + "/index.html"]
    return next((c for c in cands if a.has_entry_by_path(c)), None)


# ---------------------------------------------------------------- archives you mostly reach by searching
SE_EXAMPLES = {"diy": ["gfci keeps tripping", "leaking faucet", "drywall anchor", "water heater pilot"],
               "gardening": ["tomato leaves turning yellow", "compost", "aphids", "raised bed soil"],
               "mechanics": ["car won't start", "check engine light", "brake squeal", "battery drain"],
               "cooking": ["buttermilk substitute", "cast iron rust", "bread not rising", "freeze cooked rice"],
               "bicycles": ["chain skipping", "flat tire", "brake adjustment", "derailleur"],
               "outdoors": ["waterproof boots", "bear safety", "purify water hiking", "hypothermia"],
               "woodworking": ["wood glue clamp time", "finish for cutting board", "warped board"],
               "pets": ["dog won't eat", "cat vomiting", "chicken", "fleas"],
               "ham": ["antenna swr", "license exam", "emergency communication", "dipole"],
               "homebrew": ["stuck fermentation", "sanitize", "bottle carbonation", "mead"],
               "sustainability": ["compost smell", "rainwater", "solar panel", "reduce energy"],
               "crafts": ["resin bubbles", "glue for fabric", "candle making"],
               "lifehacks": ["remove sticker residue", "unclog drain", "keep food fresh"]}
GUIDES = [
    ("wikem", {"what": "WikEM is an emergency-medicine reference written by doctors: about 100,000 short notes, one per "
                       "condition, symptom, drug or procedure. It has no browsable index offline - you reach notes by searching.",
               "how": "Type a condition or symptom, e.g. a diagnosis (anaphylaxis) or what you see (shortness of breath).",
               "examples": ["anaphylaxis", "chest pain", "hypothermia", "snake bite", "burns", "seizure", "dehydration"],
               "tips": ["Each note runs Background - Clinical Features - Differential Diagnosis - Evaluation - Management - Disposition.",
                        "Many topics have a separate children's note marked (peds) with child doses.",
                        "Links inside a note jump to related notes; '\u2039 Previous article' takes you back.",
                        "Written for trained clinicians - a reference, not a substitute for professional care."]}),
    ("wikipedia", {"what": "The whole English Wikipedia with pictures - 21.7 million articles. The front page only links a few "
                           "topics, so searching is the way in.",
                   "how": "Type what you want to know about. Titles finds articles by name; 'Pages mentioning' searches the text.",
                   "examples": ["water purification", "solar cooker", "first aid", "edible plants", "food preservation", "ham radio"],
                   "tips": ["Use the Web page tab to see infoboxes and tables laid out as on the website.",
                            "Links inside an article open the next one; '\u2039 Previous article' goes back."]}),
    ("stackexchange", {"what": "Questions and answers from the {site} community. The front page only lists recent questions - "
                               "search for your problem to find the answers.",
                       "how": "Describe the problem in a few words, the way you would ask it.",
                       "examples": [],
                       "tips": ["Answers show their votes; the accepted answer is marked \u2713.",
                                "Try different wording if the first search misses - e.g. the part's name, or the symptom."]}),
    ("gutenberg", {"what": "Free public-domain books from Project Gutenberg - whole books you can read here, with their "
                           "original illustrations.",
                   "how": "Type a book title (e.g. Pride and Prejudice) or an author's name (e.g. Dickens) - matching "
                          "authors are listed first; click one to see all their books.",
                   "examples": [],
                   "tips": ["The whole book opens on the Read tab; the Web page tab shows it as typeset by Gutenberg.",
                            "Long books take a second or two to open.",
                            "Browse the bookshelf below for the most popular books, with their authors."]}),
    ("medlineplus", {"what": "MedlinePlus (US National Library of Medicine): health topics, a medical encyclopedia, drugs and "
                             "supplements, and medical tests, in plain language.",
                     "how": "Search for a condition, a medicine or a test. The front page links its main sections too.",
                     "examples": ["high blood pressure", "ibuprofen", "burns", "diabetes", "antibiotics", "food poisoning"],
                     "tips": ["Drug pages cover uses, dosing, side effects and precautions.",
                              "Use 'Open front page' below for the encyclopedia and other sections."]}),
]


def guide_for(key, title=""):
    for prefix, g in GUIDES:
        if prefix in key:
            g = dict(g)
            if prefix == "stackexchange":
                site = key.split(".", 1)[0]
                g["what"] = g["what"].format(site=title or site)
                g["examples"] = SE_EXAMPLES.get(site, [])
            return g
    return None


def human_size(n):
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit in ("bytes", "KB") else f"{n:,.1f} {unit}"
        n /= 1024


# ======================================================================= the archives
class ZimShelf:
    """All .zim archives in _sources\\zim. Every libzim call goes through one worker thread (run_async)."""
    def __init__(self, root):
        self.root, self.archives, self.info, self.jobs = root, {}, [], queue.Queue()
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        while True:
            fn, cb, err = self.jobs.get()
            try:
                res = fn()
            except Exception as e:
                if err:
                    self.root.after(0, lambda e=e, err=err: err(e))
                continue
            if cb:
                self.root.after(0, lambda r=res, cb=cb: cb(r))

    def run_async(self, fn, cb=None, err=None):
        self.jobs.put((fn, cb, err))

    def archive(self, key):
        if key not in self.archives:
            from libzim.reader import Archive
            self.archives[key] = Archive(os.path.join(ZIM_DIR, key + ".zim"))
        return self.archives[key]

    def scan(self):
        """Archive cards: [{key, title, desc, count, size, icon (PNG bytes), main}]."""
        out = []
        for f in sorted(glob.glob(os.path.join(ZIM_DIR, "*.zim"))):
            key = os.path.splitext(os.path.basename(f))[0]
            try:
                a = self.archive(key)
            except Exception:
                continue
            meta = lambda k: a.get_metadata(k).decode("utf-8", "replace") if k in a.metadata_keys else ""
            try:
                icon = bytes(a.get_illustration_item(48).content) if a.has_illustration(48) else b""
            except Exception:
                icon = b""
            title = meta("Title") or key
            if key.startswith("gutenberg") and meta("Description"):
                title = "Gutenberg \u2013 " + meta("Description")[:1].upper() + meta("Description")[1:]
            out.append({"key": key, "title": title, "desc": meta("Description"), "count": a.article_count,
                        "size": os.path.getsize(f), "icon": icon, "main": a.main_entry.get_item().path if a.has_main_entry else "",
                        "source": meta("Source"), "date": meta("Date")})
        out.sort(key=lambda r: (not r["key"].startswith("wikipedia"), r["title"].lower()))
        self.info = out
        return out

    def gutenberg_books(self, key):
        """Books of a Gutenberg archive, most popular first: [{title, author, path}] (path = the book's own page)."""
        cache = getattr(self, "_gb", {})
        self._gb = cache
        if key not in cache:
            import json
            a = self.archive(key)
            out = []
            if a.has_entry_by_path("full_by_popularity.js"):
                js = bytes(a.get_entry_by_path("full_by_popularity.js").get_item().content).decode("utf-8", "replace")
                try:
                    rows = json.loads(js[js.index("["):js.rindex("]") + 1])
                except ValueError:
                    rows = []
                for row in rows:
                    title, author, bid = row[0], row[1], row[3]
                    p = f"{title}.{bid}"
                    if a.has_entry_by_path(p):
                        out.append({"title": title, "author": author, "path": p})
            cache[key] = out
        return cache[key]

    def gutenberg_authors(self, key):
        """[{name, id, books}] for a Gutenberg archive (books = how many of theirs it holds)."""
        cache = getattr(self, "_ga", {})
        self._ga = cache
        if key not in cache:
            import json
            a = self.archive(key)
            out = []
            if a.has_entry_by_path("authors.js"):
                js = bytes(a.get_entry_by_path("authors.js").get_item().content).decode("utf-8", "replace")
                try:
                    rows = json.loads(js[js.index("["):js.rindex("]") + 1])
                except ValueError:
                    rows = []
                counts = {}
                for b in self.gutenberg_books(key):
                    counts[b["author"]] = counts.get(b["author"], 0) + 1
                for name, aid in rows:
                    if name not in ("Various", "Anonymous", "Unknown"):
                        out.append({"name": name, "id": str(aid), "books": counts.get(name, 0), "plain": plain_text(name)})
            cache[key] = out
        return cache[key]

    def find_authors(self, key, q, n=8):
        words = plain_text(q).split()
        if not words:
            return []
        hits = [au for au in self.gutenberg_authors(key) if all(w in au["plain"] for w in words)]
        hits.sort(key=lambda au: (not any(au["plain"].split()[-1:] == [w] for w in words), -au["books"]))   # surname matches first
        return hits[:n]

    def paged_list(self, key, path, title, intro, desc, rows, first, step, bar=None):
        """A reader page listing `rows` (Markdown lines): the first `first` now, `step` more each time you scroll near the
        bottom, ending with "That's all N books." (Reader: 'more' callback; loaded parts are kept for Back)."""
        end = f"\n*That's all {len(rows):,} book{'s' if len(rows) != 1 else ''}.*\n"
        md = f"# {title}\n\n{intro}\n\n" + "\n".join(rows[:first]) + (end if len(rows) <= first else "")
        it = {"file": "", "path": f"zim/{key}/{path}", "title": title, "category": None, "type": "zim-article",
              "publisher": self.title_of(key), "original": "", "source_url": "", "words": len(md.split()), "zim": (key, path),
              "base": TMP, "gallery": [], "text": md, "synthetic": True, "desc": desc, "_shown": min(first, len(rows)),
              "sortbar": bar or []}

        def more():
            a = it["_shown"]
            if a >= len(rows):
                return ""
            chunk = rows[a:a + step]
            it["_shown"] = a + len(chunk)
            return "\n".join(chunk) + (end if it["_shown"] >= len(rows) else "")
        it["more"] = more
        if it["_shown"] >= len(rows):
            it["more_done"] = True
        return it

    def author_page(self, key, aid, first=100, step=100, sort="popular"):
        """All of an author's books, most popular first - more are added as you scroll."""
        import json
        a = self.archive(key)
        au = next((x for x in self.gutenberg_authors(key) if x["id"] == aid), {"name": "Author", "id": aid})
        books = []
        f = f"auth_{aid}_by_popularity.js"
        if a.has_entry_by_path(f):
            js = bytes(a.get_entry_by_path(f).get_item().content).decode("utf-8", "replace")
            try:
                for row in json.loads(js[js.index("["):js.rindex("]") + 1]):
                    p = f"{row[0]}.{row[3]}"
                    if a.has_entry_by_path(p):
                        books.append((row[0], p))
            except ValueError:
                pass
        n = len(books)
        if sort in ("az", "za"):
            books.sort(key=lambda b: title_key(b[0]), reverse=(sort == "za"))
        rows = [f"\U0001F4D6  [{t}](zim://{quote(key)}/{quote(p, safe='/')})\n" for t, p in books]
        order = dict(AUTHOR_SORTS).get(sort, "Most popular"); order = order[:1].lower() + order[1:]
        intro = f"{n:,} book{'s' if n != 1 else ''} in {self.title_of(key)}, {order}" + \
                (" - more are added as you scroll down." if n > first else ".")
        return self.paged_list(key, f"author:{aid}", au["name"], intro, f"{n:,} book{'s' if n != 1 else ''} by {au['name']} in this archive.",
                               rows, first, step, sort_bar(key, f"author:{aid}", sort, AUTHOR_SORTS) if n > 1 else "")

    def bookshelf(self, key, first=1000, step=500, sort="popular"):
        """All books in the chosen order - more are added as you scroll."""
        books = list(self.gutenberg_books(key))   # most popular first
        rank = {b["path"]: i for i, b in enumerate(books)}
        if sort in ("az", "za"):
            books.sort(key=lambda b: title_key(b["title"]), reverse=(sort == "za"))
        elif sort in ("author", "author-za"):   # by surname; each author's books together, most popular first
            books.sort(key=lambda b: surname_key(b["author"]), reverse=(sort == "author-za"))
            groups, out = {}, []
            for b in books:
                groups.setdefault(surname_key(b["author"]) + "|" + b["author"], []).append(b)
            for k in groups:
                out += sorted(groups[k], key=lambda b: rank[b["path"]])
            books = out
        if sort in ("author", "author-za"):
            rows = [f"\U0001F464 *{b['author']}*  \u2014  \U0001F4D6  [{b['title']}](zim://{quote(key)}/{quote(b['path'], safe='/')})\n" for b in books]
        else:
            rows = [f"\U0001F4D6  [{b['title']}](zim://{quote(key)}/{quote(b['path'], safe='/')})  \u2014  *{b['author']}*\n" for b in books]
        order = dict(SHELF_SORTS).get(sort, "Most popular")
        intro = (f"{len(books):,} books ({(order[:1].lower() + order[1:])}) - more are added as you scroll down. Search above to find any of "
                 "them by title or author.")
        return self.paged_list(key, "Home", self.title_of(key), intro, f"A library of {len(books):,} public-domain books.",
                               rows, first, step, sort_bar(key, "Home", sort, SHELF_SORTS))

    def documents(self, key):
        """zimgit-style archives (a document library app): their list of documents from database.js, else None.
        [{title, desc, author, path}] where path is the PDF/file inside the archive."""
        a = self.archive(key)
        if not a.has_entry_by_path("database.js"):
            return None
        js = bytes(a.get_entry_by_path("database.js").get_item().content).decode("utf-8", "replace")
        try:
            rows = ast.literal_eval(js[js.index("["):js.rindex("]") + 1])
        except Exception:
            return None
        out = []
        for r in rows:
            for fp in r.get("fp") or []:
                out.append({"title": r.get("ti") or fp, "desc": r.get("dsc") or "", "author": r.get("aut") or "", "path": "files/" + fp})
        return out

    def title_of(self, key):
        return next((r["title"] for r in self.info if r["key"] == key), key)

    # ------------------------------------------------------------ search
    def suggest(self, key, q, n=8):
        from libzim.suggestion import SuggestionSearcher
        a = self.archive(key)
        if not a.has_title_index:
            return []
        out = []
        for p in SuggestionSearcher(a).suggest(q).getResults(0, n * 6):
            if is_translation(key, p):
                continue
            try:
                out.append((a.get_entry_by_path(p).title, p))
            except KeyError:
                pass
            if len(out) >= n:
                break
        return out

    def fulltext(self, key, q, n=10):
        from libzim.search import Query, Searcher
        a = self.archive(key)
        if not a.has_fulltext_index:
            return 0, []
        s = Searcher(a).search(Query().set_query(q))
        out = []
        for p in s.getResults(0, n * 6):
            if is_translation(key, p):
                continue
            try:
                out.append((a.get_entry_by_path(p).title, p))
            except KeyError:
                pass
            if len(out) >= n:
                break
        return s.getEstimatedMatches(), out

    # ------------------------------------------------------------ raw items (web server)
    def item(self, key, path):
        """(final path, mimetype, bytes) following redirects; KeyError if missing."""
        a = self.archive(key)
        e = a.get_entry_by_path(path)
        hops = 0
        while e.is_redirect and hops < 8:
            e = e.get_redirect_entry(); hops += 1
        it = e.get_item()
        return e.path, it.mimetype, bytes(it.content)

    def tidy_stackexchange(self, soup, body):
        """Question/answer pages: stats as one line, votes and accepted answer shown plainly, user cards = name + date."""
        stats = next((d for d in body.find_all("div") if d.find("span", string=re.compile(r"^\s*Asked\s*$"))
                      and d.find(string=re.compile("Viewed"))), None)
        if stats is not None:
            txt = " ".join(stats.get_text(" ", strip=True).split())
            asked = re.search(r"Asked\s+(.+?)\s+(?:at\s+\d|Active|Modified|Viewed)", txt)
            viewed = re.search(r"Viewed\s+([\d,]+)\s+times", txt)
            line = soup.new_tag("p")
            em = soup.new_tag("em")
            em.string = " \u00b7 ".join(x for x in (f"Asked {asked.group(1)}" if asked else "",
                                                     f"Viewed {viewed.group(1)} times" if viewed else "") if x)
            line.append(em)
            stats.replace_with(line)
        for v in body.select(".js-vote-count"):
            n = v.get_text(strip=True)
            post = v.find_parent(class_=re.compile(r"\banswer\b"))
            accepted = post is not None and ("accepted-answer" in (post.get("class") or []) or post.select_one(".js-accepted-answer-indicator:not(.d-none)"))
            p = soup.new_tag("p")
            b = soup.new_tag("strong"); b.string = f"Votes: {n}" + ("   \u2713 Accepted answer" if accepted else "")
            p.append(b)
            v.replace_with(p)
        for card in body.select(".s-user-card, .user-info"):
            name = card.select_one(".s-user-card--link, .user-details a, .user-details")
            when = card.select_one("time, .s-user-card--time, .user-action-time")
            p = soup.new_tag("p")
            em = soup.new_tag("em")
            em.string = "\u2014 " + ", ".join(x for x in ((name.get_text(" ", strip=True) if name else ""),
                                                          (when.get_text(" ", strip=True) if when else "")) if x)
            p.append(em)
            card.replace_with(p)
        for t in body.select(".js-vote-up-btn, .js-vote-down-btn, .js-bookmark-btn, .js-post-issue, .s-award-bling, .js-voting-container button"):
            t.decompose()

    def document_list(self, key, docs):
        """The front page of a document-library archive, as a readable list of its documents."""
        name = self.title_of(key)
        lines = [f"# {name}", "", f"{len(docs)} documents - click one to read it.", ""]
        for d in docs:
            lines += [f"\U0001F4C4  [{d['title']}](zim://{quote(key)}/{quote(d['path'], safe='/')})", ""]
            if d["desc"]:
                lines += [d["desc"], ""]
            if d["author"] and d["author"].lower() != "various":
                lines += [f"*{d['author']}*", ""]
        md = "\n".join(lines)
        return {"file": "", "path": f"zim/{key}/home", "title": name, "category": None, "type": "zim-article",
                "publisher": name, "original": "", "source_url": "", "words": len(md.split()), "zim": (key, "home"),
                "base": TMP, "gallery": [], "text": md, "synthetic": True, "desc": f"A library of {len(docs)} documents (PDFs)."}

    # ------------------------------------------------------------ an article for the Reader
    def article(self, key, path):
        """A Reader item for one entry: HTML -> Markdown (links between articles kept), pictures in TMP."""
        from bs4 import BeautifulSoup
        from markdownify import markdownify
        a = self.archive(key)
        if key.startswith("gutenberg"):
            base, _, query = path.partition("?")
            sort = query.split("sort=", 1)[1] if "sort=" in query else "popular"
            if base.startswith("author:"):
                return self.author_page(key, base.split(":", 1)[1], sort=sort)
            if base in ("Home", "index", "") or (a.has_main_entry and base == a.main_entry.get_item().path):
                return self.bookshelf(key, sort=sort)
            m = re.match(r"^(.*)_cover\.(\d+)$", path)   # title search finds the cover page: open the book itself
            if m and a.has_entry_by_path(f"{m.group(1)}.{m.group(2)}"):
                path = f"{m.group(1)}.{m.group(2)}"
        e = a.get_entry_by_path(path)
        hops = 0
        while e.is_redirect and hops < 8:
            e = e.get_redirect_entry(); hops += 1
        path, title = e.path, e.title or e.path
        docs = self.documents(key)
        if docs is not None:
            if path == (a.main_entry.get_item().path if a.has_main_entry else "") or path in ("home", "home.html"):
                return self.document_list(key, docs)
            title = next((d["title"] for d in docs if d["path"] == path), title)
        item = e.get_item()
        out = os.path.join(TMP, re.sub(r"[^\w.-]+", "_", key), hashlib.md5(path.encode()).hexdigest()[:16])
        os.makedirs(out, exist_ok=True)
        it = {"file": "", "path": f"zim/{key}/{path}", "title": title, "category": None, "type": "zim-article",
              "publisher": self.title_of(key), "original": "", "source_url": "", "words": 0, "zim": (key, path),
              "base": out, "gallery": [], "text": "", "desc": ""}
        if not item.mimetype.startswith("text/html"):   # a PDF, picture, ... stored in the archive: show it as itself
            ext = os.path.splitext(path)[1] or {"application/pdf": ".pdf"}.get(item.mimetype, EXT.get(item.mimetype, ".bin"))
            f = os.path.join(out, "file" + ext)
            open(f, "wb").write(bytes(item.content))
            it["original"] = f
            if item.mimetype.startswith("image/"):
                it["gallery"] = [(f, title)]
            it["text"] = f"*{title}* is a {item.mimetype.split('/')[-1].upper()} file inside the archive - use the buttons above to view it."
            it["desc"] = f"{item.mimetype} file, {human_size(item.size)}"
            return it
        soup = BeautifulSoup(bytes(item.content).decode("utf-8", "replace"), "lxml")
        body = None
        for prefix, sel in ROOTS:
            if prefix in key:
                body = soup.select_one(sel); break
        body = body or soup.find(id="mw-content-text") or soup.body or soup
        for sel in JUNK:
            for t in body.select(sel):
                t.decompose()
        for t in body.select('[style*="display:none"], [style*="display: none"]'):   # hidden counters / duplicates
            t.decompose()
        for h1 in body.find_all("h1"):   # a title linking to its own page
            for x in h1.find_all("a"):
                x.unwrap()
        if "stackexchange" in key:
            self.tidy_stackexchange(soup, body)
        for h in body.find_all(["h2", "h3"]):
            if h.get_text(" ", strip=True).lower() in DROP_SECTIONS:
                sec = h.find_parent("section")
                (sec if sec is not None else h).decompose()
        here = posixpath.dirname(path)
        # pictures -> files in TMP, marked for the Markdown
        pics = []
        for img in body.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            try:
                w = int(img.get("width") or 0)
            except ValueError:
                w = 0
            name = unquote(src.rsplit("/", 1)[-1])
            if not src or src.startswith(("data:", "http")) or ICON_RE.search(name) or (w and w < 50) or len(pics) >= 60:
                img.replace_with(""); continue
            zp = unquote(posixpath.normpath(posixpath.join(here, src.split("?")[0])))
            try:
                pe = a.get_entry_by_path(zp)
                while pe.is_redirect:
                    pe = pe.get_redirect_entry()
                pi = pe.get_item()
            except KeyError:
                img.replace_with(""); continue
            fn = os.path.join(out, f"{len(pics) + 1:02d}{EXT.get(pi.mimetype, os.path.splitext(name)[1] or '.img')}")
            open(fn, "wb").write(bytes(pi.content))
            cap = ""
            fig = img.find_parent("figure")
            if fig is not None and fig.find("figcaption"):
                cap = fig.find("figcaption").get_text(" ", strip=True)
            cap = re.sub(r"\s+", " ", cap or img.get("alt") or "").strip()[:200]
            if re.fullmatch(r"[\w.-]+\.(jpe?g|png|gif|webp|svg)", cap, re.I):
                cap = ""
            pics.append((fn, cap))
            marker = soup.new_tag("p"); marker.string = f"@@IMG{len(pics) - 1}@@"
            (fig if fig is not None and len(fig.find_all("img")) == 1 else img).replace_with(marker)
        for fc in body.find_all("figcaption"):
            fc.decompose()
        # links: to another entry of this archive -> zim://key/path (opens in the reader); web links kept; others plain text
        for link in body.find_all("a"):
            href = (link.get("href") or "").strip()
            if href.startswith(("http://", "https://")):
                link.attrs.pop("title", None)
                continue
            target = href.split("#", 1)[0]
            if not target:
                link.unwrap(); continue
            zp = resolve_path(a, here, target)
            if zp and not is_translation(key, zp):
                link["href"] = "zim://" + quote(key) + "/" + quote(zp, safe="/")
                link.attrs.pop("title", None)   # keep the Markdown link to just [text](address)
            else:
                link.unwrap()
        # infoboxes -> "key: value" lines
        for ib in body.find_all("table", class_=re.compile("infobox")):
            rows = []
            for tr in ib.find_all("tr"):
                cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in tr.find_all(["th", "td"]) if c.find_parent("tr") is tr]
                cells = [c for c in cells if c]
                if len(cells) >= 2:
                    rows.append(f"- **{cells[0].rstrip(':')}:** {' '.join(cells[1:])}")
                elif cells:
                    rows.append(f"\n**{cells[0]}**")
            new = soup.new_tag("div"); new.string = "@@IB@@" + "\n".join(rows) + "@@IBEND@@"
            ib.replace_with(new)
        md = markdownify(str(body), heading_style="ATX", bullets="-")
        md = re.sub(r"@@IB@@(.*?)@@IBEND@@", lambda m: "\n\n" + m.group(1).replace("\\*", "*").replace("\\_", "_") + "\n\n", md, flags=re.S)
        for i, (fn, cap) in enumerate(pics):
            md = md.replace(f"@@IMG{i}@@", f"![{cap.replace('[', '(').replace(']', ')')}]({fn})")
        md = re.sub(r"\[\s*\d+\s*\]", "", md)
        md = re.split(r"This (?:page|article) is issued from ", md)[0]
        md = re.sub(r"\n[ \t]+\n", "\n\n", md)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        if not md.lstrip().startswith("# "):
            md = f"# {title}\n\n" + md
        it.update(text=md, gallery=pics, words=len(md.split()))
        first = next((plain for plain in (lv.plain(l) for l in md.splitlines()[1:])
                      if len(plain) > 60 and not plain.startswith(("#", "!", "|", "-"))), "")
        it["desc"] = first[:300]
        return it


# ======================================================================= "Open in browser"
class ZimServer:
    """Serves /<archive>/<path> from the archives on 127.0.0.1 only (a mini kiwix-serve), started on first use."""
    def __init__(self, shelf):
        self.shelf, self.port = shelf, None

    def url(self, key, path):
        if self.port is None:
            shelf = self.shelf

            class H(BaseHTTPRequestHandler):
                def log_message(self, *a):
                    pass

                def do_GET(self):
                    parts = unquote(urlparse(self.path).path).lstrip("/").split("/", 1)
                    key, p = parts[0], (parts[1] if len(parts) > 1 else "")
                    try:
                        a = shelf.archive(key)
                        if not p and a.has_main_entry:
                            p = a.main_entry.get_item().path
                        final, mime, data = shelf.item(key, p)
                        if final != p:   # redirect inside the archive: let the browser follow it
                            self.send_response(302); self.send_header("Location", "/" + quote(key) + "/" + quote(final, safe="/"))
                            self.end_headers(); return
                    except Exception:
                        self.send_response(404); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers()
                        self.wfile.write(b"Not in this archive"); return
                    self.send_response(200)
                    self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") and "charset" not in mime else ""))
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
            srv.daemon_threads = True
            self.port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self.port}/{quote(key)}/{quote(path, safe='/')}"


# ======================================================================= the page
class ZimPage(lv.ItemView):
    """Offline Archives: archive cards when nothing is searched; title and full-text results otherwise."""

    def __init__(self, app):
        super().__init__(app.content, bg=C["bg"])
        self.init_view(app, "Offline Archives",
                       "Read the Kiwix archives directly - Wikipedia, iFixit, Stack Exchange, MedlinePlus and more.")
        self.shelf = ZimShelf(self)
        self.server = ZimServer(self.shelf)
        self.icons, self.history, self.cur, self.gen, self._after = {}, [], None, 0, None
        self.pref_tab = "Read"   # Read or Web page - whichever was used last
        self.listview = tk.Frame(self, bg=C["bg"]); self.listview.pack(fill="both", expand=True)
        bar = tk.Frame(self.listview, bg=C["bg"]); bar.pack(fill="x", pady=(0, 8))
        self.q = tk.StringVar()
        self.search_entry = lv.search_box(bar, self.q, self.debounce)
        self.search_entry.bind("<Return>", lambda e: self.search())
        self.scope = tk.StringVar(value="All archives")
        self.scope_cb = ttk.Combobox(bar, textvariable=self.scope, state="readonly", font=(F, 10), width=30, values=["All archives"])
        self.scope_cb.pack(side="left", padx=(8, 0), ipady=3)
        self.scope_cb.bind("<<ComboboxSelected>>", lambda e: self.search() if self.q.get().strip() else self.scope_chosen())
        self.status = label(self.listview, "Opening the archives...", 9, fg="dim", bg="bg"); self.status.pack(fill="x")
        self.body = lv.ScrollFrame(self.listview, C["bg"], jump=True); self.body.pack(fill="both", expand=True, pady=(6, 0))
        self.reader = lv.Reader(self)
        self.shelf.run_async(self.shelf.scan, self.scanned, lambda e: self.status.config(text=f"Could not open the archives: {e}"))

    # ------------------------------------------------------------ archive cards
    def scanned(self, info):
        self.scope_cb.config(values=["All archives"] + [r["title"] for r in info])
        self.show_archives()

    def scope_chosen(self):
        key = self.key_of(self.scope.get())
        r = next((x for x in self.shelf.info if x["key"] == key), None)
        if r and guide_for(key, r["title"]):
            return self.show_guide(r)
        self.show_archives()

    def key_of(self, title):
        return next((r["key"] for r in self.shelf.info if r["title"] == title), None)

    def icon(self, r):
        if r["key"] not in self.icons:
            try:
                im = Image.open(io.BytesIO(r["icon"])).convert("RGBA").resize((40, 40), Image.LANCZOS)
                bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
                self.icons[r["key"]] = ImageTk.PhotoImage(bg.convert("RGB"))
            except Exception:
                self.icons[r["key"]] = None
        return self.icons[r["key"]]

    def show_archives(self):
        self.gen += 1
        self.body.clear()
        info = self.shelf.info
        sel = self.key_of(self.scope.get())
        shown = [r for r in info if not sel or r["key"] == sel]
        total = sum(r["count"] for r in info)
        self.status.config(text=f"{len(info)} archives  •  {total:,} articles  •  "
                                f"{human_size(sum(r['size'] for r in info))}  -  search above, or open an archive's front page")
        g = tk.Frame(self.body.inner, bg=C["bg"]); g.pack(fill="x")
        cols = 2
        for k, r in enumerate(shown):
            f = card(g, cursor="hand2")
            f.grid(row=k // cols, column=k % cols, sticky="nsew", padx=(0, 10) if k % cols == 0 else (0, 0), pady=(0, 10))
            ic = self.icon(r)
            il = tk.Label(f, image=ic, bg=C["card"]) if ic else tk.Label(f, text="\U0001F4DA", font=("Segoe UI Emoji", 20), bg=C["card"])
            il.pack(side="left", padx=(14, 10), pady=12, anchor="n")
            box = tk.Frame(f, bg=C["card"]); box.pack(side="left", fill="both", expand=True, pady=10, padx=(0, 12))
            t = label(box, r["title"], 11, True); t.pack(anchor="w")
            d = label(box, (r["desc"] or "")[:110], 8, fg="dim", wraplength=330); d.pack(anchor="w")
            what = f"{r['count']:,} articles" if r["count"] > 1 else "document collection"
            mrow = tk.Frame(box, bg=C["card"]); mrow.pack(anchor="w", pady=(2, 0))
            m = label(mrow, f"{what}  •  {human_size(r['size'])}", 8, fg="accent"); m.pack(side="left")
            if guide_for(r["key"]):
                tag = tk.Label(mrow, text="\U0001F50D Search-first", font=("Segoe UI Emoji", 7, "bold"), bg=C["info_bg"], fg=C["info_fg"], padx=5)
                tag.pack(side="left", padx=(8, 0)); tag.bind("<Button-1>", lambda e, r=r: self.open_archive(r))
            for w in (f, il, box, t, d, m):
                w.bind("<Button-1>", lambda e, r=r: self.open_archive(r))
                w.bind("<Enter>", lambda e, f=f: f.config(highlightbackground=C["primary"]))
                w.bind("<Leave>", lambda e, f=f: f.config(highlightbackground=C["line"]))
        for c in range(cols):
            g.columnconfigure(c, weight=1, uniform="z")

    def open_archive(self, r):
        self.scope.set(r["title"])
        if guide_for(r["key"], r["title"]):
            self.q.set("")
            return self.show_guide(r)
        if r["main"]:
            self.open_entry(r["key"], r["main"], fresh=True)
        else:
            self.show_archives()

    def show_guide(self, r):
        """How to use a search-first archive: what it is, how to search, example searches, tips."""
        g = guide_for(r["key"], r["title"])
        self.gen += 1
        self.body.clear()
        self.status.config(text=f"{r['title']}  \u2022  {r['count']:,} articles  -  type in the search box above")
        f = card(self.body.inner); f.pack(fill="x")
        top = tk.Frame(f, bg=C["card"]); top.pack(fill="x", padx=18, pady=(16, 6))
        ic = self.icon(r)
        if ic:
            tk.Label(top, image=ic, bg=C["card"]).pack(side="left", padx=(0, 12))
        hb = tk.Frame(top, bg=C["card"]); hb.pack(side="left", fill="x", expand=True)
        label(hb, r["title"], 15, True).pack(anchor="w")
        tk.Label(hb, text="\U0001F50D  Search-first archive", font=("Segoe UI Emoji", 8, "bold"), bg=C["info_bg"], fg=C["info_fg"],
                 padx=6, pady=1).pack(anchor="w", pady=(3, 0))
        inner = tk.Frame(f, bg=C["card"]); inner.pack(fill="x", padx=18, pady=(4, 16))
        label(inner, g["what"], 10, wraplength=760).pack(anchor="w", pady=(4, 10))
        label(inner, "How to use it", 11, True).pack(anchor="w")
        label(inner, g["how"] + "  Results show matching titles first, then pages that mention your words.", 10,
              wraplength=760).pack(anchor="w", pady=(2, 10))
        if r["key"].startswith("gutenberg"):   # the most popular books, one click each
            g["examples"] = [(b["title"] if len(b["title"]) <= 40 else b["title"][:38].rsplit(" ", 1)[0] + "\u2026", b["path"])
                             for b in self.shelf.gutenberg_books(r["key"])[:10]]
        if g["examples"]:
            label(inner, "Most popular books:" if r["key"].startswith("gutenberg") else "Try one of these:", 10, True).pack(anchor="w")
            row = tk.Frame(inner, bg=C["card"]); row.pack(anchor="w", pady=(4, 10))
            used = 0
            for ex in g["examples"]:
                ex, book = (ex if isinstance(ex, tuple) else (ex, None))
                if used > 80:
                    row = tk.Frame(inner, bg=C["card"]); row.pack(anchor="w", pady=(0, 6)); used = 0
                chip = tk.Label(row, text=ex, font=(F, 9), bg=C["sec"], fg=C["text"], padx=10, pady=4, cursor="hand2")
                chip.pack(side="left", padx=(0, 6)); used += len(ex) + 4
                if book:   # a book: open it
                    chip.bind("<Button-1>", lambda e, b=book: self.open_entry(r["key"], b, fresh=True))
                else:      # a search
                    chip.bind("<Button-1>", lambda e, ex=ex: (self.q.set(ex), self.search()))
                chip.bind("<Enter>", lambda e, c=chip: c.config(bg=C["primary"], fg="#ffffff"))
                chip.bind("<Leave>", lambda e, c=chip: c.config(bg=C["sec"], fg=C["text"]))
        if g["tips"]:
            label(inner, "Tips", 11, True).pack(anchor="w", pady=(4, 0))
            for t in g["tips"]:
                label(inner, "\u2022  " + t, 9, fg="dim", wraplength=760).pack(anchor="w", pady=1)
        if r["key"].startswith("gutenberg"):
            Btn(inner, "\U0001F4DA  Browse the bookshelf", lambda: self.open_entry(r["key"], "Home", fresh=True), "primary", 9, 14, 5).pack(anchor="w", pady=(12, 0))
        elif r["main"]:
            Btn(inner, "Open front page anyway", lambda: self.open_entry(r["key"], r["main"], fresh=True), "ghost", 9, 8, 4).pack(anchor="w", pady=(12, 0))
        self.search_entry.focus_set()

    # ------------------------------------------------------------ search
    def debounce(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(450, self.search)

    def search(self):
        q = self.q.get().strip()
        if not q:
            return self.scope_chosen()
        self.gen += 1; gen = self.gen
        sel = self.key_of(self.scope.get())
        keys = [sel] if sel else [r["key"] for r in self.shelf.info]
        where = self.scope.get() if sel else "all archives"
        self.status.config(text=f"Searching {where} for “{q}”…")
        self.body.clear()
        self.authors_box = tk.Frame(self.body.inner, bg=C["bg"]); self.authors_box.pack(fill="x")
        self.titles_box = tk.Frame(self.body.inner, bg=C["bg"]); self.titles_box.pack(fill="x")
        self.text_box = tk.Frame(self.body.inner, bg=C["bg"]); self.text_box.pack(fill="x")
        self.found = {"titles": 0, "text": 0, "done": 0, "of": len(keys)}
        lv.section_title(self.titles_box, "Titles")
        lv.section_title(self.text_box, f"Pages mentioning “{q}”")

        def work():   # titles first (quick), then the full-text index, archive by archive
            res = []
            for k in keys:
                try:
                    res.append((k, self.shelf.suggest(k, q, 10 if sel else 4)))
                except Exception:
                    pass
            return res

        def text_work():
            res = []
            for k in keys:
                try:
                    n, hits = self.shelf.fulltext(k, q, 25 if sel else 5)
                    if hits:
                        res.append((k, n, hits))
                except Exception:
                    pass
            return res
        gut = [k for k in keys if k.startswith("gutenberg")]
        if gut:
            self.shelf.run_async(lambda: [(k, self.shelf.find_authors(k, q, 8 if sel else 4)) for k in gut],
                                 lambda res: self.show_authors(gen, res))
        self.shelf.run_async(work, lambda res: self.show_titles(gen, res))
        self.shelf.run_async(text_work, lambda res: self.show_text(gen, q, res))

    def result_row(self, parent, key, title, path, show_archive=True):
        f = tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["line"], cursor="hand2")
        f.pack(fill="x", pady=(0, 4))
        t = label(f, title, 10, True); t.pack(anchor="w", padx=12, pady=(6, 0))
        m = label(f, (self.shelf.title_of(key) + "  •  " if show_archive else "") + path[:110], 8, fg="dim")
        m.pack(anchor="w", padx=12, pady=(0, 6))
        for w in (f, t, m):
            w.bind("<Button-1>", lambda e: self.open_entry(key, path, fresh=True))
            w.bind("<Enter>", lambda e: f.config(highlightbackground=C["primary"]))
            w.bind("<Leave>", lambda e: f.config(highlightbackground=C["line"]))

    def show_authors(self, gen, res):
        if gen != self.gen or not any(hits for _, hits in res):
            return
        sel = self.key_of(self.scope.get())
        lv.section_title(self.authors_box, "Authors")
        for k, hits in res:
            for au in hits:
                f = tk.Frame(self.authors_box, bg=C["card"], highlightthickness=1, highlightbackground=C["line"], cursor="hand2")
                f.pack(fill="x", pady=(0, 4))
                t = label(f, "\U0001F464  " + au["name"], 10, True); t.pack(anchor="w", padx=12, pady=(6, 0))
                m = label(f, f"{au['books']} book{'s' if au['books'] != 1 else ''}" + ("" if sel else f"  \u2022  {self.shelf.title_of(k)}"), 8, fg="dim")
                m.pack(anchor="w", padx=12, pady=(0, 6))
                for w in (f, t, m):
                    w.bind("<Button-1>", lambda e, k=k, aid=au["id"]: self.open_entry(k, f"author:{aid}", fresh=True))
                    w.bind("<Enter>", lambda e, f=f: f.config(highlightbackground=C["primary"]))
                    w.bind("<Leave>", lambda e, f=f: f.config(highlightbackground=C["line"]))

    def show_titles(self, gen, res):
        if gen != self.gen:
            return
        sel = self.key_of(self.scope.get())
        n = 0
        for k, hits in res:
            for title, path in hits:
                self.result_row(self.titles_box, k, title, path, show_archive=not sel); n += 1
        if not n:
            label(self.titles_box, "No titles match.", 9, fg="dim", bg="bg").pack(anchor="w")
        self.found["titles"] = n
        self.status.config(text=f"{n} title match{'es' if n != 1 else ''}  •  searching the text…")

    def show_text(self, gen, q, res):
        if gen != self.gen:
            return
        sel = self.key_of(self.scope.get())
        total = 0
        for k, n, hits in res:
            total += n
            if not sel:
                label(self.text_box, f"{self.shelf.title_of(k)}  —  about {n:,} pages", 9, True, fg="primary", bg="bg").pack(anchor="w", pady=(8, 2))
            for title, path in hits:
                self.result_row(self.text_box, k, title, path, show_archive=False)
        if not res:
            label(self.text_box, "No pages mention that.", 9, fg="dim", bg="bg").pack(anchor="w")
        self.status.config(text=f"{self.found['titles']} title match{'es' if self.found['titles'] != 1 else ''}  •  "
                                f"about {total:,} pages mention “{q}”" + ("" if sel else "  (top results from each archive)"))

    # ------------------------------------------------------------ reading
    def open_entry(self, key, path, fresh=False):
        if fresh:
            self.history, self.cur = [], None
        if not self.reader.winfo_manager():   # leaving the list: remember its status line for coming back
            self._list_status = self.status.cget("text")
        self.status.config(text="Opening…")
        self.app.status.config(text="Opening the article…")

        def done(it):
            self.app.status.config(text="Ready")
            self.open_item(it, self.pref_tab if self.pref_tab != "Read" else None)

        def fail(e):
            self.app.status.config(text="Ready")
            messagebox.showerror("Can't open", f"This page could not be opened:\n{e}", parent=self)
        self.shelf.run_async(lambda: self.shelf.article(key, path), done, fail)

    def open_link(self, url):
        """zim://<archive>/<path> links inside an article."""
        rest = url[len("zim://"):]
        key, _, path = rest.partition("/")
        path = unquote(path)
        if "?sort=" in path:   # a different order of the same list: replace it, start at the top
            self._replace_next = True
        self.open_entry(unquote(key), path)

    def open_in_browser(self, it):
        key, path = it["zim"]
        webbrowser.open(self.server.url(key, path))

    def viewed(self, it):   # remember the article chain for "Previous article"
        if getattr(self, "_replace_next", False):   # re-sorted list: same place in the chain
            self._replace_next = False
            self.cur = it
            return
        if self.history and it is self.history[-1]:
            self.history.pop()
        elif self.cur is not None and self.cur is not it:
            if self.reader.cur_tab == "Read":   # where you were in it, for coming back
                self.cur["_ypos"] = self.reader.text.yview()[0]
            self.history.append(self.cur)
        self.cur = it

    def neighbors(self, it):
        prev = self.history[-1] if self.history else None
        return prev, None, f"{it['publisher']}  ›  {it['title'][:90]}", ("‹  Previous article", None)

    def close_reader(self):
        """Back: one step back along the pages you followed (e.g. a book -> the bookshelf, at the place you were);
        with nowhere to go back to, leave the reader for the list."""
        if self.history and self.reader.winfo_manager():
            prev = self.history[-1]
            return self.reader.show(prev)
        super().close_reader()
        self.history, self.cur = [], None
        self.status.config(text=getattr(self, "_list_status", ""))

    def restart(self):
        """Menu click: All archives, empty search, the archive cards."""
        self.history, self.cur = [], None   # first, so closing the reader really closes it
        super().restart()
        self.q.set("")
        self.scope.set("All archives")
        if self.shelf.info:
            self.show_archives()
        self.body.top()

    def on_show(self):
        if not self.reader.winfo_ismapped():
            self.search_entry.focus_set()

    def jump(self, where):
        if self.reader.winfo_ismapped():
            return self.reader.jump(where)
        (self.body.go_top if where == "top" else self.body.go_bottom)()
