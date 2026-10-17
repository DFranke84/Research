"""Shared helpers for reading the offline Wikipedia ZIM."""
import json, re
from urllib.parse import unquote
from libzim.reader import Archive
from bs4 import BeautifulSoup

import os
_NAME = "wikipedia_en_all_maxi_2026-08.zim"
# the library's own copy: <library>\_sources\zim (found relative to this script, so the library can move)
ZIM_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_sources", "zim", _NAME)
ZIM_DATE = "2026-08-25"
_zim = None

MAINT_RE = re.compile(
    r"^(Articles|All |Pages|Wikipedia|Use |CS1|Webarchive|Short description|Commons|Harv|"
    r"Good articles|Featured articles|Official website|Coordinates|Vague|Accuracy|Engvar|"
    r"Instances of|Template|Wikidata|Interlanguage|EngvarB|Coordinates on|Redirects|Disambiguation|"
    r"Incomplete|Dynamic lists|Lists with|Webarchive|AC with|Taxonbars|Taxobox|Automatic taxobox|"
    r"Articles containing|Articles with|Articles needing|Articles lacking|Articles to be|Articles using)",
    re.I)


def zim():
    global _zim
    if _zim is None:
        _zim = Archive(ZIM_PATH)
    return _zim


def resolve(title_or_path):
    """Return the final (non-redirect) entry for a title or path, or None."""
    z = zim()
    cands = [title_or_path, title_or_path.replace(" ", "_")]
    e = None
    for c in cands:
        try:
            e = z.get_entry_by_path(c); break
        except KeyError:
            pass
    if e is None:
        try:
            e = z.get_entry_by_title(title_or_path.replace("_", " "))
        except KeyError:
            return None
    hops = 0
    while e.is_redirect and hops < 5:
        e = e.get_redirect_entry(); hops += 1
    return e


def page_meta(html):
    m = re.search(r'RLCONF = (\{.*?\});?\s*\n', html)
    meta = {}
    if m:
        try:
            meta = json.loads(m.group(1))
        except Exception:
            pass
    return meta


def content_cats(meta):
    return [c for c in meta.get("wgCategories", []) if not MAINT_RE.match(c)]


def first_para(soup):
    root = soup.find(id="mw-content-text") or soup
    for p in root.find_all("p"):
        t = " ".join(p.get_text(" ", strip=True).split())
        if len(t) > 60:
            return re.sub(r"\s*\[\s*\d+\s*\]", "", t)
    return ""


def img_path(entry_path, src):
    import posixpath
    return unquote(posixpath.normpath(posixpath.join(posixpath.dirname(entry_path), src)))


DROP_SECTIONS = {"references", "notes", "footnotes", "citations", "sources", "bibliography", "further reading",
                 "external links", "notes and references", "references and notes", "works cited", "literature",
                 "explanatory notes", "general and cited references", "cited sources", "general references"}
ICON_RE = re.compile(r"(Symbol_|Commons-logo|Wiki[a-z]+-logo|Edit-clear|Question_book|Ambox|Padlock|Folder_Hexagonal|"
                     r"OOjs_UI|Speakerlink|Sound-icon|Nuvola|Crystal_Clear|Portal-puzzle|P_vip|Increase2|Decrease|"
                     r"Steady2|Status_iucn|Red_Pencil|Text_document|Flag_of_|Lock-|Wiktionary|Wikisource|Wikiquote|"
                     r"Wikivoyage|Wikispecies|Wikibooks|Wikinews|Wikidata|Semi-protection|Disambig|Emblem-)", re.I)
MIME_EXT = {"image/webp": ".webp", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/svg+xml": ".svg"}


def _file_name(src):
    name = unquote(unquote(src.rsplit("/", 1)[-1]))
    name = re.sub(r"^(lossy-page\d+-|page\d+-)?(\d+px-)?", "", name)
    return name


def article_md(entry, max_images=40, archive=None, root=None, drop=()):
    """Convert a ZIM article entry to clean Markdown.
    archive: libzim Archive the entry belongs to (default: the Wikipedia ZIM).
    root: CSS selector for the main content element (default: Wikipedia's #mw-content-text, else <body>).
    drop: extra CSS selectors to remove (site navigation, footers, ...).
    Returns dict(title, md, images=[{zim_path, file_name, caption, mimetype, bytes}], meta)."""
    from markdownify import markdownify
    z = archive or zim()
    html = bytes(entry.get_item().content).decode("utf-8", "replace")
    meta = page_meta(html)
    soup = BeautifulSoup(html, "lxml")
    body = (soup.select_one(root) if root else None) or soup.find(id="mw-content-text") or soup.body
    for sel in list(drop) + ["style", "script", "link", "sup.reference", ".reference", ".mw-editsection", ".reflist", ".references",
                ".navbox", ".vertical-navbox", ".sidebar", ".metadata", ".ambox", ".hatnote", ".noprint", ".mw-empty-elt",
                ".shortdescription", ".sistersitebox", ".portalbox", ".portal", ".toc", "#toc", ".mbox-small",
                ".side-box", ".navbox-styles", ".authority-control", ".mw-authority-control", ".catlinks",
                "span.mw-cite-backlink", ".plainlinks.hlist", ".nomobile", ".infobox-below.noprint"]:
        for t in body.select(sel):
            t.decompose()
    for h in body.find_all(["h2", "h3"]):
        if h.get_text(" ", strip=True).lower() in DROP_SECTIONS:
            sec = h.find_parent("section")
            if sec is not None:
                sec.decompose()
            else:
                h.decompose()
    images, seen = [], set()
    for n, img in enumerate(body.find_all("img")):
        if img.parent is None or img.find_parent(id="mw-content-text") is None and body.get("id") == "mw-content-text":
            continue
        src = img.get("src", "")
        try:
            w = int(img.get("data-file-width") or img.get("width") or 0)
            dw = int(img.get("width") or 0)
        except ValueError:
            w, dw = 0, 0
        fname = _file_name(src)
        if not src or src.startswith("data:") or ICON_RE.search(fname) or (dw and dw < 60) or (w and w < 90):
            img.replace_with("")
            continue
        zp = img_path(entry.path, src)
        if zp in seen or len(images) >= max_images:
            img.replace_with("")
            continue
        try:
            it = z.get_entry_by_path(zp).get_item()
        except KeyError:
            img.replace_with("")
            continue
        seen.add(zp)
        fig = img.find_parent(["figure", "div"], class_=re.compile("thumb|gallerybox|tsingle|infobox-image"))
        cap = ""
        if img.find_parent("figure") is not None:
            fc = img.find_parent("figure").find("figcaption")
            cap = fc.get_text(" ", strip=True) if fc else ""
        if not cap:
            cap = img.get("alt", "") or fname
        cap = re.sub(r"\s+", " ", cap).strip()[:300]
        idx = len(images)
        images.append({"zim_path": zp, "file_name": fname, "caption": cap, "mimetype": it.mimetype, "bytes": bytes(it.content)})
        marker = soup.new_tag("p")
        marker.string = f"@@IMG{idx}@@"
        figp = img.find_parent("figure")
        target = figp if (figp is not None and len(figp.find_all("img")) == 1) else img
        try:
            target.replace_with(marker)
        except ValueError:
            img.replace_with(marker)
    for fc in body.find_all("figcaption"):
        fc.decompose()
    # infobox -> key/value list
    for ib in body.find_all("table", class_=re.compile("infobox")):
        lines = []
        for tr in ib.find_all("tr"):
            cells = [c for c in tr.find_all(["th", "td"]) if c.find_parent("tr") is tr]
            texts = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in cells]
            texts = [t for t in texts if t]
            if len(texts) >= 2:
                lines.append(f"- **{texts[0].rstrip(':')}:** {' '.join(texts[1:])}")
            elif len(texts) == 1 and cells and cells[0].name == "th":
                lines.append(f"\n**{texts[0]}**")
            elif len(texts) == 1:
                lines.append(f"- {texts[0]}")
        new = soup.new_tag("div")
        new.string = "@@IB@@" + "\n".join(lines) + "@@IBEND@@"
        ib.replace_with(new)
    md = markdownify(str(body), heading_style="ATX", strip=["a"], bullets="-")
    md = re.sub(r"@@IB@@(.*?)@@IBEND@@", lambda m: "\n\n" + m.group(1).replace("\\*", "*").replace("\\_", "_") + "\n\n", md, flags=re.S)
    md = re.sub(r"\[\s*\d+\s*\]", "", md)
    md = re.split(r"This (?:page|article) is issued from ", md)[0]
    md = md.replace("Pages displaying short descriptions of redirect targets", "").replace("Pages displaying wikidata descriptions as a fallback", "")
    md = re.sub(r"\n[ \t]+\n", "\n\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return {"title": entry.title, "md": md, "images": images, "meta": meta}


def save_article_images(art, dest_dir, rel_prefix, start=0, source_page=None):
    """Write the article's images into dest_dir and replace @@IMGn@@ markers.
    start: offset for image file numbering (when several pages share one images folder).
    source_page: function(file_name) -> source page URL (default: Wikipedia File: page).
    Returns (md, image_records)."""
    import os
    os.makedirs(dest_dir, exist_ok=True) if art["images"] else None
    recs, md = [], art["md"]
    used = set()
    for i, im in enumerate(art["images"]):
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.splitext(im["file_name"])[0])[:80].strip("_") or f"image_{i}"
        ext = MIME_EXT.get(im["mimetype"], ".img")
        fn = f"{i + start + 1:02d}_{base}{ext}"
        while fn in used:
            fn = f"{i + 1:02d}b_{base}{ext}"
        used.add(fn)
        with open(os.path.join(dest_dir, fn), "wb") as f:
            f.write(im["bytes"])
        cap = im["caption"].replace("[", "(").replace("]", ")")
        md = md.replace(f"@@IMG{i}@@", f"![{cap}]({rel_prefix}/{fn})")
        if source_page:
            recs.append({"file": fn, "caption": im["caption"], "source_file_page": source_page(im),
                         "license": "Same as the page it appears in unless credited otherwise"})
        else:
            recs.append({"file": fn, "caption": im["caption"],
                         "source_file_page": "https://en.wikipedia.org/wiki/File:" + im["file_name"].replace(" ", "_"),
                         "license": "See source file page (Wikimedia Commons / Wikipedia; mostly CC BY-SA or public domain)"})
    md = re.sub(r"@@IMG\d+@@", "", md)
    return md, recs


def taxonomy(entry):
    """Return {rank: name} from the article's taxobox (Kingdom, Phylum, Class, Order, Family, Genus)."""
    html = bytes(entry.get_item().content).decode("utf-8", "replace")
    soup = BeautifulSoup(html, "lxml")
    out = {}
    ib = soup.find("table", class_=re.compile("infobox biota|biota"))
    if ib is None:
        return out
    for tr in ib.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            k = tds[0].get_text(" ", strip=True).rstrip(":").strip()
            v = tds[1].get_text(" ", strip=True)
            if k in ("Domain", "Kingdom", "Phylum", "Division", "Class", "Order", "Family", "Genus", "Clade", "Subphylum", "Superclass") and k not in out or k == "Clade":
                if k == "Clade":
                    out.setdefault("Clades", []).append(v)
                else:
                    out[k] = v
    return out
