"""Build the Local Area section (Kalispell / Flathead County, Montana): <library>\\local-area\\

  69_build_local_area.py                      build everything in local_area_specs (plants + guides + references + pests)
  69_build_local_area.py "Honeycrisp Apple"   only these plants (titles or slugs); the shared documents are still checked
  --refresh                                   re-download pages (otherwise the download cache in _work/local_area is reused)
  --no-video                                  skip downloading the growing-guide videos

Layout (everything stored locally - nothing needs the internet to view):
  local-area/start-here-kalispell.md                  zone, frost dates, how the section is organised
  local-area/plants/<plant>.md + _images/             one page per plant/variety (source_type local-profile; 'group' = type)
  local-area/guides/stark-<series>.md + .pdf          Stark Bro's growing guides (+ _images, _videos)
  local-area/references/<doc>.md + .pdf               MSU / Flathead County / USDA / USFS documents (full text + original)
  local-area/pests-problems/<kind>-<name>.md + .pdf   MSU 'Guide to Pests, Problems and Identification' - one page per problem
Then runs 20_catalog.py + 21_readme.py.
Reader rule: links must be plain [text](relative/path) - not <path>, not inside **bold** (the reader ignores those).
"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter, slugify
import local_area as L
import local_area_specs as SP
import veg_pages as VP
from bs4 import BeautifulSoup

CAT = "local-area"
D = os.path.join(RESEARCH, CAT)
PLANT_DIR, GUIDE_DIR, REF_DIR, PEST_DIR = (os.path.join(D, x) for x in ("plants", "guides", "references", "pests-problems"))
REFRESH, NO_VIDEO = "--refresh" in sys.argv, "--no-video" in sys.argv
STARK_LICENSE = "(c) Stark Bro's Nurseries & Orchards Co. - saved for personal offline reference only; do not redistribute"
MTFG_LICENSE = "Montana Field Guide, Montana Natural Heritage Program / Montana FWP; photos (c) the photographers - personal reference"
R = SP.REGION
ZONE_NUM = int(re.match(r"\d+", R["zone"]).group())


def rel(path, start):
    return os.path.relpath(path, start).replace("\\", "/")


def link(text, path, start):
    return f"[{text}]({rel(path, start)})"


def fm_title(text):
    m = re.search(r'^title: "(.*)"', text, re.M)
    return m.group(1).replace('\\"', '"') if m else "?"


# ================================================================== the plant list
def parse_table():
    plants, group = [], None
    for line in SP.PLANT_TABLE.splitlines():
        line = line.strip()
        if line.startswith("## "):
            group = line[3:].strip(); continue
        if "|" not in line:
            continue
        parts = [x.strip() for x in line.split("|")]
        title, sci, kind = parts[:3]
        extra = {}
        for kv in (parts[3] if len(parts) > 3 else "").split(";"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                extra[k.strip()] = v.strip()
        kw = [k.strip() for k in extra.get("kw", "").split(",") if k.strip()]
        base = re.sub(r"\s*'.*", "", sci).strip()
        short = re.sub(r"\s*\(.*\)", "", title)
        kws = kw or [short.split(" ")[0] if kind == "cultivar" else short]
        slug = slugify(short)
        mine = L.type_overrides().get(f"{CAT}/plants/{slug}.md")   # the user's own choice (Change type... in the app)
        plants.append({"title": title, "sci": sci, "base": base, "kind": kind, "group": mine or group, "slug": slug,
                       "keywords": kws, **{k: v for k, v in extra.items() if k != "kw"}})
    return plants


def unwrap(text):
    """Join PDF lines that were broken mid-sentence ('...tomatoes, and' + newline + 'peppers...'); keep paragraph and page breaks."""
    text = re.sub(r"(\w)-\n(?=[a-z])", r"\1", text)
    return re.sub(r"(?<![.!?:\n])[ \t]*\n(?![\n\[]|\s*[-•*|#])", " ", text)


def matches(p, targets):
    """Does a 'for' list (group names, scientific-name prefixes, '*') include this plant?"""
    for t in targets:
        if t == "*" or t == p["group"] or p["sci"].startswith(t) or p["base"].startswith(t):
            return True
    return False


def best_prefix(p, table):
    hits = [k for k in table if p["sci"].startswith(k) or p["base"].startswith(k)]
    return table[max(hits, key=len)] if hits else None


# ================================================================== shared documents
def write_doc(md_path, meta, head, body):
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    open(md_path, "w", encoding="utf-8").write(front_matter(meta) + head + body + "\n")


def build_pdf_doc(key, title, url, publisher, topic, folder, license=None, fetch_url=None, extra=None):
    slug = slugify(key)
    md_path, pdf_path = os.path.join(folder, slug + ".md"), os.path.join(folder, slug + ".pdf")
    if os.path.exists(md_path) and os.path.exists(pdf_path) and not REFRESH:
        return md_path
    print("  document:", title, flush=True)
    L.save_bin(fetch_url or url, pdf_path)
    text, pages = L.pdf_text(pdf_path)
    meta = {"title": title, "category": CAT, "source_type": "local-reference", "topic": topic, "publisher": publisher,
            "source_url": url, "file": slug + ".pdf", "license": license or f"{publisher} publication - personal reference copy",
            "pages": pages, **(extra or {}), "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    write_doc(md_path, meta, f"# {title}\n\n**Source:** {publisher} - <{url}>  \n**Original file:** [{slug}.pdf]({slug}.pdf)\n\n",
              f"## Full text\n\n{text}")
    return md_path


def build_html_doc(key, title, url, publisher, topic, folder, root=None, license=None, source_type="local-reference", extra=None):
    slug = slugify(key)
    md_path, pdf_path = os.path.join(folder, slug + ".md"), os.path.join(folder, slug + ".pdf")
    if os.path.exists(md_path) and os.path.exists(pdf_path) and not REFRESH:
        return md_path
    print("  page:", title, flush=True)
    os.makedirs(folder, exist_ok=True)
    s = BeautifulSoup(L.fetch(url), "html.parser")
    el = (s.select_one(root) if root else None) or s.select_one("#rightpane") or s.select_one("main") or s.body
    for h in el.select("h1"):
        h.decompose()
    for bad in el.select(".breadcrumb, .breadcrumbs, #breadcrumbs"):
        bad.decompose()
    md, frag, imgs = L.article_to_local(el, url, os.path.join(folder, slug + "_images"), slug + "_images")
    L.html_pdf(title, frag, pdf_path, f"Source: {publisher} - {url} (saved {TODAY})", folder)
    meta = {"title": title, "category": CAT, "source_type": source_type, "topic": topic, "publisher": publisher,
            "source_url": url, "file": slug + ".pdf", "license": license or f"{publisher} publication - personal reference copy",
            "images": imgs, **(extra or {}), "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    write_doc(md_path, meta, f"# {title}\n\n**Source:** {publisher} - <{url}>  \n**Original file:** [{slug}.pdf]({slug}.pdf)\n\n", md)
    return md_path


def build_references():
    """-> list of (md_path, text, for-list)"""
    out = []
    for key, r in SP.REFS.items():
        try:
            ex = {"group": r["group"]} if r.get("group") else None   # shown under that Local Area topic tile
            if r["kind"] == "pdf":
                p = build_pdf_doc(key, r["title"], r["url"], r["publisher"], r.get("topic"), REF_DIR, r.get("license"), r.get("fetch_url"), extra=ex)
            else:
                p = build_html_doc(key, r["title"], r["url"], r["publisher"], r.get("topic"), REF_DIR, r.get("root"), r.get("license"), extra=ex)
            out.append((p, open(p, encoding="utf-8").read(), r.get("for", [])))
        except Exception as e:
            print(f"  FAILED {key}: {e}", flush=True)
    for slug, fors in SP.MSU_PUBS.items():
        if slug.startswith("a-guide-to-pests"):
            continue
        try:
            got = L.msu_pub(slug)
            if not got:
                print(f"  FAILED {slug}: no free PDF", flush=True); continue
            title, sku, pdf = got
            title = re.sub(r"\s*-\s*" + re.escape(sku) + r"$", "", title) if sku else title
            topic = "Pests & diseases" if re.search(r"codling|deer|pest|wrong|blight", slug) else "MSU Extension MontGuides"
            p = build_pdf_doc("msu-" + slug[:70], f"{title} (MSU Extension {sku})".replace(" ()", ""), pdf,
                              "Montana State University Extension", topic, REF_DIR, extra={"msu_sku": sku})
            out.append((p, open(p, encoding="utf-8").read(), fors))
        except Exception as e:
            print(f"  FAILED {slug}: {e}", flush=True)
    for path, fors in SP.LIBRARY_DOCS.items():
        p = os.path.join(RESEARCH, path)
        if os.path.exists(p):
            out.append((p, open(p, encoding="utf-8").read(), fors))
    return out


# ------------------------------------------------------------------ MSU pests & problems guide
def build_pests():
    """-> (pages {slug: md_path}, hosts {Genus: [(title, slug)]})"""
    pages, hosts = L.pests_index()
    out = {}
    kinds = {"diseases": "Disease", "insects": "Insect / mite", "abiotic-issues": "Weather, site & animal damage", "plant-id": "Tree identification"}
    for sec, slug, title in pages:
        try:
            p = build_html_doc(f"{sec}-{slug}", f"{title} ({kinds[sec]} - MSU)", L.PESTS_BASE + f"{sec}/{slug}.html",
                               "Montana State University Extension - A Guide to Pests, Problems and Identification of Ornamental Shrubs and Trees in Montana",
                               "Pests & diseases" if sec != "plant-id" else "Tree identification", PEST_DIR,
                               source_type="local-pest", extra={"pest_kind": kinds[sec]})
            out[slug] = p
        except Exception as e:
            print(f"  FAILED pest page {slug}: {e}", flush=True)
    try:
        build_pdf_doc("msu-pests-guide-complete", "A Guide to Pests, Problems and Identification of Ornamental Shrubs and Trees in Montana (complete PDF)",
                      L.PESTS_BASE + "Index.pdf", "Montana State University Extension", "Pests & diseases", PEST_DIR)
    except Exception as e:
        print("  FAILED complete pests PDF:", e)
    return out, hosts


# ------------------------------------------------------------------ Stark growing guides
def build_guide(series):
    slug = "stark-" + slugify(series.rsplit("/", 1)[-1])
    md_path = os.path.join(GUIDE_DIR, slug + ".md")
    info_path = os.path.join(GUIDE_DIR, slug + "_chapters.json")
    if os.path.exists(md_path) and os.path.exists(info_path) and not REFRESH:
        return md_path, json.load(open(info_path, encoding="utf-8"))
    os.makedirs(GUIDE_DIR, exist_ok=True)
    name = series.rsplit("/", 1)[-1].replace("-", " ").title()
    title = f"How to Grow {name} - Stark Bro's Growing Guide"
    print("  growing guide:", title, flush=True)
    arts = L.stark_guide(series, os.path.join(GUIDE_DIR, slug + "_images"), slug + "_images")
    vdir = os.path.join(GUIDE_DIR, slug + "_videos")
    parts, frags, chapters, vids = [], [], [], []
    for a in arts:
        body = re.sub(r"^#\s.*\n", "", a["md"]).strip()
        body = re.sub(r"^(#{1,5}) ", lambda m: "#" * min(len(m.group(1)) + 2, 6) + " ", body, flags=re.M)
        vlines = []
        for v in a["videos"]:
            f = None if NO_VIDEO else L.youtube(v["id"], os.path.join(vdir, slugify(v["title"])[:70] + ".mp4"))
            if f:
                vlines.append(f"- ▶ [{v['title']}]({rel(f, GUIDE_DIR)}) (video)")
                if not any(x["youtube"] == v["id"] for x in vids):
                    vids.append({"title": v["title"], "file": rel(f, D), "youtube": v["id"]})
        parts.append(f"## {a['title']}\n\n" + ("Videos:\n\n" + "\n".join(vlines) + "\n\n" if vlines else "") + body)
        frags.append(f"<h2>{a['title']}</h2>{a['html']}")
        chapters.append({"title": a["title"], "slug": a["slug"], "url": a["url"]})
    pdf = os.path.join(GUIDE_DIR, slug + ".pdf")
    L.html_pdf(title, "".join(frags), pdf, f"Source: Stark Bro's Growing Guide - {L.STARK}/growing-guide/how-to-grow/{series} (saved {TODAY})", GUIDE_DIR)
    toc = "\n".join(f"{i}. {c['title']}" for i, c in enumerate(chapters, 1))
    meta = {"title": title, "category": CAT, "source_type": "growing-guide", "topic": "Growing guides",
            "publisher": "Stark Bro's Nurseries & Orchards", "source_url": f"{L.STARK}/growing-guide/how-to-grow/{series}",
            "file": slug + ".pdf", "license": STARK_LICENSE, "chapters": [c["title"] for c in chapters], "videos": vids,
            "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    head = (f"# {title}\n\n**Source:** Stark Bro's - <{meta['source_url']}>  \n**Original file:** [{slug}.pdf]({slug}.pdf)  \n"
            f"**License:** {STARK_LICENSE}\n\nChapters:\n\n{toc}\n\n")
    write_doc(md_path, meta, head, "\n\n".join(parts))
    info = {"title": title, "chapters": chapters, "videos": vids}
    json.dump(info, open(info_path, "w", encoding="utf-8"), indent=1)
    return md_path, info


# ------------------------------------------------------------------ Wikipedia (local ZIM)
def mt_status(mt):
    """Montana Field Guide status, re-read from the cached page (older caches hold a wrong 'Noxious Weed')."""
    if not mt:
        return ""
    if "_status" not in mt:
        try:
            mt["_status"] = L.mtfg_status(mt["elcode"]) if mt.get("elcode") else mt.get("facts", {}).get("Status", "")
        except Exception:
            mt["_status"] = ""
    return mt["_status"]


def wiki_entry(p, title):
    """The Wikipedia article for this plant - only if it is really about the plant (its genus, or the fruit word, appears
    near the top). 'Duchess of Oldenburg' alone is the German duchy; 'Duchess of Oldenburg (apple)' is the apple."""
    from zimlib import resolve
    genus = p["base"].split()[0].lower()
    fruit = {"malus": "apple", "pyrus": "pear", "prunus": "cherr|plum|apricot|prunus", "rubus": "berr", "rosa": "rose"}.get(genus, genus)
    tries = [title] + [f"{title} ({w})" for w in ("apple", "pear", "cherry", "plum", "plant", "grape") if w in fruit or w == "plant"]
    for tt in tries:
        e = resolve(tt)
        if e is None:
            continue
        head = bytes(e.get_item().content)[:60000].decode("utf-8", "replace").lower()
        if genus in head or re.search(fruit, head):
            return e
    return None


def wiki_section(title, img_dir, img_rel, p=None):
    from zimlib import resolve, article_md, save_article_images
    e = wiki_entry(p, title) if p else resolve(title)
    if e is None:
        print("  wikipedia: no article about the plant for", title)
        return None, None
    art = article_md(e, max_images=14)
    art["images"] = [im for im in art["images"] if not L.junk_pic(im["file_name"], im["caption"])][:10]
    md, imgs = save_article_images(art, img_dir, img_rel, start=0)
    md = re.sub(r"^\s*#\s.*\n", "", md)
    md = re.sub(r"^(#{1,4}) ", lambda m: "#" * min(len(m.group(1)) + 2, 6) + " ", md, flags=re.M)
    return md, {"url": "https://en.wikipedia.org/wiki/" + e.path, "title": e.title}


# ================================================================== per-plant data
MTFG_IDX = None


def mtfg_code(p):
    global MTFG_IDX
    if MTFG_IDX is None:
        d = json.load(open(os.path.join(L.W, "mtfg_plants.json"), encoding="utf-8"))
        MTFG_IDX = {}
        for k, v in d.items():
            MTFG_IDX.setdefault(v[1].lower(), k)
    name = p.get("mt") or SP.MTFG_ALIAS.get(p["base"], p["base"])
    if re.fullmatch(r"P[A-Z0-9]{9}", name):
        return name
    return MTFG_IDX.get(name.lower())


OP_IDX = None


def op_path(p):
    global OP_IDX
    if OP_IDX is None:
        f = os.path.join(L.W, "op_index.json")
        OP_IDX = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    if p.get("op") in OP_IDX:
        return p["op"]
    fruit = {"Malus": "apples", "Pyrus": "pears", "Prunus avium": "cherries", "Prunus cerasus": "cherries",
             "Prunus domestica": "plums", "Prunus armeniaca": "apricots"}
    f = next((v for k, v in fruit.items() if p["sci"].startswith(k)), None)
    if not f or p["kind"] != "cultivar":
        return None
    name = re.sub(r"[^a-z0-9 ]", "", re.search(r"'([^']+)'", p["sci"]).group(1).lower()) if "'" in p["sci"] else None
    return f"{f}/{name.replace(' ', '-')}" if name and f"{f}/{name.replace(' ', '-')}" in OP_IDX else None


PLANT_WORDS = {"Malus": ["apple", "malus", "crab"], "Pyrus": ["pear", "pyrus"], "Prunus avium": ["cherry", "cherries", "prunus"],
               "Prunus cerasus": ["cherry", "cherries", "prunus"], "Prunus x kerrasis": ["cherry", "cherries", "prunus"],
               "Prunus armeniaca": ["apricot", "prunus"], "Prunus": ["plum", "prune", "prunus"], "Rosa": ["rose", "rosa"],
               "Vitis": ["grape", "vitis"], "Sambucus": ["elderberry", "elderberries", "sambucus"], "Acer": ["maple", "acer"], "Tilia": ["linden", "basswood", "tilia"],
               "Populus": ["poplar", "populus", "cottonwood"], "Fraxinus": ["ash", "fraxinus"]}


def add_op_photos(d, o, img_dir):
    for n, u in enumerate(o.get("photos") or [], 1):
        name = f"op_{n:02d}.jpg"
        try:
            L.save_bin(u, os.path.join(img_dir, name))
        except Exception as e:
            print("  orange pippin photo failed", e); continue
        if not any(x["file"] == name for x in d["photos"]):
            d["photos"].append({"file": name, "credit": "Orange Pippin (variety identification photo)"})


def fallback_photos(p, d, img_dir):
    """A garden variety with few photos: use its Wikimedia Commons CATEGORY if one exists (curated by people, e.g.
    "Dolgo (apple)"). No free-text search - that found birds, cats, buildings and paintings."""
    m = re.search(r"'([^']+)'", p["sci"])
    if not m or p.get("commons"):
        return
    words = best_prefix(p, PLANT_WORDS) or []
    cat = L.commons_category(m.group(1), words, p["base"].split()[0])
    if not cat:
        print(f"  no Commons category for {p['title']}", flush=True)
        return
    ph = L.commons_photos(cat, img_dir, n=6, start=40)
    d["photos"] += [{"file": x["file"], "credit": f"Wikimedia Commons: {x['attribution']} ({x['license']})"} for x in ph]
    if ph:
        d["sources"].append(("Wikimedia Commons", "https://commons.wikimedia.org/wiki/Category:" + cat.replace(" ", "_")))
        d["lic"].append("Wikimedia Commons photos: per photo (CC licenses as noted)")
    print(f"  Commons category {cat!r} for {p['title']}: {len(ph)} photos", flush=True)


def fix_photos(plants):
    """Rebuild every plant's Commons, Orange Pippin and Wikipedia pictures with the photo rules (photos only, curated
    sources only, Wikipedia article must be about the plant); also fill in iNaturalist photos that were skipped."""
    for p in plants:
        cache = os.path.join(L.W, "plants", p["slug"] + ".json")
        if not os.path.exists(cache):
            continue
        d = json.load(open(cache, encoding="utf-8"))
        img_dir = os.path.join(PLANT_DIR, p["slug"] + "_images")
        os.makedirs(img_dir, exist_ok=True)
        redo = lambda f: f.startswith(("commons_", "op_", "inat_")) or re.match(r"\d\d[b]?_", f)
        for f in os.listdir(img_dir):
            if redo(f):
                os.remove(os.path.join(img_dir, f))
        d["photos"] = [x for x in d["photos"] if not redo(x["file"])]
        d["sources"] = [s for s in d["sources"] if s[0] not in ("Wikimedia Commons", "iNaturalist", "Wikipedia")]
        d["lic"] = [x for x in d["lic"] if not x.startswith(("Wikimedia", "iNaturalist", "Wikipedia"))]
        d.pop("wiki_md", None); d.pop("wiki", None)
        if d.get("op") or op_path(p):   # re-read Orange Pippin (cached page): older saved data had no photo list
            o = L.orange_pippin(op_path(p) or d["op"]["url"].split("/varieties/", 1)[-1])
            if o:
                d["op"] = o
                if not any(s[0] == "Orange Pippin variety database" for s in d["sources"]):
                    d["sources"].append(("Orange Pippin variety database", o["url"]))
                add_op_photos(d, o, img_dir)
        if p["kind"] != "cultivar" and " " in p["base"]:
            try:
                t_, ph = L.inat_photos(p["base"], img_dir)
                if t_:
                    d["sources"].append(("iNaturalist", f"https://www.inaturalist.org/taxa/{t_['id']}"))
                    d["photos"] += [{"file": x["file"], "credit": f"iNaturalist: {x['attribution']} ({x['license']})"} for x in ph]
                    d["lic"].append("iNaturalist photos: per photo (CC licenses as noted)")
            except Exception as e:
                print("  inat failed", p["title"], e)
        if p.get("commons"):
            try:
                ph = L.commons_photos(p["commons"], img_dir)
                d["photos"] += [{"file": x["file"], "credit": f"Wikimedia Commons: {x['attribution']} ({x['license']})"} for x in ph]
                if ph:
                    d["sources"].append(("Wikimedia Commons", "https://commons.wikimedia.org/wiki/Category:" + p["commons"].replace(" ", "_")))
                    d["lic"].append("Wikimedia Commons photos: per photo (CC licenses as noted)")
            except Exception as e:
                print("  commons failed", p["title"], e)
        elif len(d["photos"]) < 3 and p["kind"] == "cultivar":
            try:
                fallback_photos(p, d, img_dir)
            except Exception as e:
                print("  commons category failed", p["title"], e)
        if p.get("wiki"):
            try:
                md, w = wiki_section(p["wiki"], img_dir, p["slug"] + "_images", p)
                if w:
                    d["wiki_md"], d["wiki"] = md, w
                    d["sources"].append(("Wikipedia", w["url"]))
                    d["lic"].append("Wikipedia text: CC BY-SA 4.0 (offline Kiwix archive)")
            except Exception as e:
                print("  wiki failed", p["title"], e)
        json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  photos rebuilt: {p['title']} ({len(d['photos'])} photos)", flush=True)


def gather(p):
    """Download everything for one plant -> data dict (cached as json)."""
    img_dir = os.path.join(PLANT_DIR, p["slug"] + "_images")
    cache = os.path.join(L.W, "plants", p["slug"] + ".json")
    if os.path.exists(cache) and not REFRESH:
        return json.load(open(cache, encoding="utf-8"))
    print(f"{p['title']}", flush=True)
    os.makedirs(img_dir, exist_ok=True)
    d = {"photos": [], "sources": [], "lic": []}
    if p.get("stark"):
        try:
            st = L.stark_variety(p["stark"], img_dir)
            d["stark"] = st
            d["sources"].append(("Stark Bro's variety page", st["url"]))
            d["photos"] += [{"file": x["file"], "credit": "Stark Bro's"} for x in st["photos"]]
            d["lic"].append("Stark Bro's: " + STARK_LICENSE)
        except Exception as e:
            print("  stark failed", e)
    op = op_path(p)
    if op:
        o = L.orange_pippin(op)
        if o:
            d["op"] = o
            d["sources"].append(("Orange Pippin variety database", o["url"]))
            add_op_photos(d, o, img_dir)
            d["lic"].append("Orange Pippin data: (c) Orange Pippin Ltd - facts quoted for personal reference")
    veg = p["kind"] == "vegetable"
    code = mtfg_code(p) if not veg else None
    if code:
        try:
            mt = L.mtfg_species(code, img_dir, "")
            d["mtfg"] = mt
            d["sources"].append(("Montana Field Guide", mt["url"]))
            if p["kind"] != "cultivar":   # Field Guide photos show the WILD species - not a garden variety
                d["photos"] += [{"file": x["file"], "credit": f"Montana Field Guide - {x['photographer'] or x['copyright']}"} for x in mt["photos"][:8]]
            d["lic"].append("Montana Field Guide: " + MTFG_LICENSE)
        except Exception as e:
            print("  mtfg failed", e)
    if p["kind"] not in ("cultivar", "vegetable") and p["base"] and " " in p["base"]:
        try:
            t, ph = L.inat_photos(p["base"], img_dir)
            if t:
                d["sources"].append(("iNaturalist", f"https://www.inaturalist.org/taxa/{t['id']}"))
                d["photos"] += [{"file": x["file"], "credit": f"iNaturalist: {x['attribution']} ({x['license']})"} for x in ph]
                d["lic"].append("iNaturalist photos: per photo (CC licenses as noted)")
        except Exception as e:
            print("  inat failed", e)
    if p.get("commons"):
        try:
            ph = L.commons_photos(p["commons"], img_dir)
            d["photos"] += [{"file": x["file"], "credit": f"Wikimedia Commons: {x['attribution']} ({x['license']})"} for x in ph]
            if ph:
                d["sources"].append(("Wikimedia Commons", "https://commons.wikimedia.org/wiki/Category:" + p["commons"].replace(" ", "_")))
        except Exception as e:
            print("  commons failed", e)
    if len(d["photos"]) < 3 and p["kind"] == "cultivar":
        try:
            fallback_photos(p, d, img_dir)
        except Exception as e:
            print("  commons search failed", e)
    if p.get("wiki"):
        try:
            md, w = wiki_section(p["wiki"], img_dir, p["slug"] + "_images", p)
            if w:
                d["wiki_md"], d["wiki"] = md, w
                d["sources"].append(("Wikipedia", w["url"]))
                d["lic"].append("Wikipedia text: CC BY-SA 4.0 (offline Kiwix archive)")
                if veg:   # vegetable photos: the article's own pictures (Wikimedia Commons)
                    d["photos"] += [{"file": os.path.basename(x), "credit": "Wikipedia article photo (Wikimedia Commons)"}
                                    for x in re.findall(r"\]\(" + re.escape(p["slug"]) + r"_images/([^)]+)\)", md)[:4]]
        except Exception as e:
            print("  wiki failed", e)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return d


# ================================================================== facts at the top of every page
def zone_range(p, d, msu_zone):
    lo = hi = None
    src = []
    if d.get("stark") and d["stark"]["chars"].get("Hardiness Zone Range"):
        z = re.findall(r"\d+", d["stark"]["chars"]["Hardiness Zone Range"])
        if z:
            lo, hi = int(z[0]), int(z[-1]); src.append(f"Stark: zones {z[0]}-{z[-1]}")
    if d.get("op") and d["op"]["facts"].get("Cold hardiness (USDA)"):
        z = [int(x) for x in re.findall(r"Zone (\d+)", d["op"]["facts"]["Cold hardiness (USDA)"])]
        if z:
            lo = min(z) if lo is None else min(lo, min(z)); src.append(f"Orange Pippin: zone {min(z)}+")
    if msu_zone:
        z = re.findall(r"\d+", msu_zone)
        if z:
            lo = int(z[0]) if lo is None else lo; src.append(f"MSU: zone {msu_zone}")
    return lo, hi, src


def hardy_line(p, d, lo, src):
    if p["kind"] == "native" or (d.get("mtfg") and mt_status(d["mtfg"]).endswith("Native Species")):
        return f"Yes - native to Montana (Kalispell is zone {R['zone']})"
    if p["kind"] in ("noxious",):
        return f"Yes - an invasive weed here (zone {R['zone']})"
    if lo is None:
        return f"Kalispell is zone {R['zone']} ({R['zone_range']}); no zone rating found in the sources - see the documents below"
    if lo <= ZONE_NUM - 1:
        verdict = f"Yes - hardy to zone {lo}"
    elif lo == ZONE_NUM:
        verdict = f"Borderline - rated to zone {lo}; Kalispell is {R['zone']}: choose a sheltered spot"
    else:
        verdict = f"No - rated only to zone {lo}; Kalispell is {R['zone']}"
    return verdict + (f" ({'; '.join(src)})" if src else "")


FLOWER_GROUPS = {"1": "very early", "2": "early", "3": "early-mid", "4": "mid-season", "5": "mid-late", "6": "late", "7": "very late"}


def fruit_family(p):
    for k, v in (("Malus", "apple"), ("Pyrus", "pear"), ("Prunus avium", "sweet cherry"), ("Prunus cerasus", "sour cherry"),
                 ("Prunus x kerrasis", "sour cherry"), ("Prunus domestica", "European plum"), ("Prunus 'T", "hybrid plum"),
                 ("Prunus 'P", "hybrid plum"), ("Prunus 'S", "hybrid plum"), ("Prunus 'W", "hybrid plum"),
                 ("Prunus americana", "hybrid plum"), ("Prunus armeniaca", "apricot"), ("Prunus mandshurica", "apricot")):
        if p["sci"].startswith(k):
            return v
    return None


def partners(p, d, everyone):
    """Varieties on the user's own list that bloom at the same time (Orange Pippin flowering group +/- 1)."""
    fam = fruit_family(p)
    if not fam:
        return []
    mine = d.get("op", {}).get("facts", {}).get("Flowering group")
    out = []
    for q, qd in everyone:
        if q is p or fruit_family(q) != fam:
            continue
        g = qd.get("op", {}).get("facts", {}).get("Flowering group")
        if mine and g and mine.isdigit() and g.isdigit() and abs(int(mine) - int(g)) <= 1:
            out.append((q, f"flowering group {g}"))
        elif fam == "apple" and q["sci"].startswith("Malus '") and q is not p:   # crabapples
            out.append((q, "crabapple - long bloom, universal pollinizer"))
        elif fam == "hybrid plum" and "'Toka'" in q["sci"]:
            out.append((q, "the standard hybrid-plum pollinizer"))
        elif fam == "sweet cherry" and ("'Lapins'" in q["sci"] or "'Stella'" in q["sci"]):
            out.append((q, "self-fertile universal sweet-cherry pollinizer"))
        elif fam == "pear" and not mine:
            out.append((q, "another pear"))
    seen, res = set(), []
    for q, why in out:
        if q["slug"] not in seen:
            seen.add(q["slug"]); res.append((q, why))
    return res


def facts_block(p, d, msu_zone, everyone, doc_texts=()):
    st = (d.get("stark") or {}).get("chars", {})
    op = (d.get("op") or {}).get("facts", {})
    mt = d.get("mtfg") or {}
    wiki = d.get("wiki_md") or ""
    mtext = " ".join((mt.get("sections") or {}).values())
    rows = []
    lo, hi, src = zone_range(p, d, msu_zone)
    kwpat = r"\b(" + "|".join(re.escape(k) for k in p["keywords"]) + r")"
    if lo is None:
        for name, text in [("Wikipedia", wiki)] + [("MSU", x) for x in doc_texts]:
            for s in L.sentences(text, r"\bzones?\s+\d", n=8, maxlen=500):
                if name == "MSU" and not re.search(kwpat, s, re.I):
                    continue
                m = re.search(r"zones?\s+(\d+)[ab]?\s*(?:–|-|to|through)\s*(\d+)", s, re.I) or re.search(r"zone\s+(\d+)", s, re.I)
                if m:
                    lo = int(m.group(1)); src.append(f"{name}: “{s[:160]}”"); break
            if lo is not None:
                break
    rows.append(("Grows in Kalispell?", hardy_line(p, d, lo, src)))
    if p["kind"] == "poisonous":
        rows.append(("⚠ POISONOUS", "Do not eat any part - see Edibility below and the Wikipedia section."))
    if p["kind"] == "noxious":
        rows.append(("⚠ Noxious weed", "Listed as a noxious weed in Montana - report/control it; do not plant."))
    if mt_status(mt):
        f = mt["facts"]
        rows.append(("Montana status", mt_status(mt) + (f" (state rank {f['State Rank']})" if f.get("State Rank") else "")))
    # bloom
    bloom = []
    if st.get("Bloom Time"):
        bloom.append(f"{st['Bloom Time']} (Stark)")
    if op.get("Flowering group"):
        g = op["Flowering group"].split(",")[0].strip()
        bloom.append(f"flowering group {g}" + (f" = {FLOWER_GROUPS[g]}" if g in FLOWER_GROUPS else "") + " (Orange Pippin)")
    months = L.sentences(mtext + "\n" + wiki, r"\b(flower|bloom|blossom)\w*\b.*\b" + L.MONTHS + r"|\b" + L.MONTHS + r"\b.*\b(flower|bloom|blossom)", n=1, maxlen=260)
    if months:
        bloom.append(f"“{months[0]}”")
    if not bloom:
        for x in doc_texts:
            s = [y for y in L.sentences(x, kwpat + r".*\b(bloom|flower|blossom)\w*|\b(bloom|flower|blossom)\w*.*" + kwpat, n=1, maxlen=300)]
            if s:
                bloom.append(f"“{s[0]}” (MSU)"); break
    if bloom:
        rows.append(("Bloom / pollination time", "; ".join(bloom)))
    # pollination
    pol = []
    if op.get("Self-fertility"):
        pol.append(op["Self-fertility"])
    elif st.get("Pollination"):
        pol.append(st["Pollination"])
    note = best_prefix(p, SP.POLLINATION)
    if note:
        pol.append(note + " (general horticultural guidance)")
    if pol:
        rows.append(("Pollination", " - ".join(pol)))
    pr = partners(p, d, everyone)
    if pr:
        rows.append(("Pollination partners on your list", ", ".join(f"[{q['title']}]({q['slug']}.md) ({why})" for q, why in pr[:10])))
    if d.get("stark") and d["stark"].get("partners"):
        rows.append(("Pollinators Stark Bro's recommends", ", ".join(d["stark"]["partners"][:8])))
    # harvest
    hv = []
    if st.get("Ripens/Harvest"):
        hv.append(f"{st['Ripens/Harvest']} (Stark)")
    if op.get("Picking period"):
        hv.append(f"{op['Picking period']} (Orange Pippin)")
    elif op.get("Picking season"):
        hv.append(f"{op['Picking season']} season (Orange Pippin)")
    if op.get("Keeping (of fruit)"):
        hv.append(f"keeps {op['Keeping (of fruit)']}")
    if not hv and p["group"] not in ("Noxious weeds", "Poisonous plants", "Trees - Conifers", "Trees - Shade & ornamental", "Shrubs & hedges"):
        s = L.sentences(wiki, r"\b(ripen|harvest|fruit\w*)\b.*\b" + L.MONTHS, n=1, maxlen=260)
        if s:
            hv.append(f"“{s[0]}” (Wikipedia)")
    if not hv and p["kind"] not in ("noxious", "poisonous"):
        for x in doc_texts:
            s = L.sentences(x, kwpat + r".*\b(ripen|harvest|pick)\w*|\b(ripen|harvest|pick)\w*.*" + kwpat, n=1, maxlen=300)
            if s:
                hv.append(f"“{s[0]}” (MSU)"); break
    if hv:
        rows.append(("Harvest", "; ".join(hv)))
    if st.get("Years to Bear"):
        rows.append(("Years to first crop", st["Years to Bear"]))
    if d.get("stark"):
        size = d["stark"]["size"]
        half = len(size) // 2 or len(size)
        if size[:half]:
            rows.append(("Mature size", "; ".join(f"{k}: {v}" for k, v in size[:half])))
        if size[half:]:
            rows.append(("Spacing", "; ".join(f"{k}: {v}" for k, v in size[half:])))
    for k, lab in (("Shade/Sun", "Sun"), ("Soil Moisture", "Soil"), ("Soil pH Level", "Soil pH")):
        if st.get(k):
            rows.append((lab, st[k]))
    if mt.get("sections", {}).get("Habitat"):
        rows.append(("Montana habitat", re.sub(r"\s*\(Lesica.*?\)\.?", ".", mt["sections"]["Habitat"])[:300]))
    # edibility / uses
    ed = []
    if st.get("Taste"):
        ed.append(f"taste: {st['Taste']}" + (f", {st['Texture']}" if st.get("Texture") else ""))
    if op.get("Food uses"):
        ed.append(f"uses: {op['Food uses']}")
    tox = L.sentences(wiki + "\n" + mtext, r"\b(toxic|poison\w*|edible|cyanide|inedible)\b", n=2, maxlen=300)
    ed += [f"“{s}”" for s in tox]
    if ed:
        rows.append(("Edibility & uses", " ".join(x if x.startswith("“") else x + ";" for x in ed).rstrip(";")))
    # disease resistance
    dis = [f"{k}: {v}" for k, v in op.items() if k in ("Scab (Apple and Pear)", "Fire blight", "Powdery mildew", "Cedar apple rust",
                                                        "Bitter pit", "Disease resistance", "Black knot", "Brown rot")]
    if dis:
        rows.append(("Disease resistance (Orange Pippin)", "; ".join(dis)))
    if p.get("note"):
        rows.insert(1, ("Note", p["note"]))
    return rows


# ================================================================== "what the timing words mean", in Kalispell terms
FROST = None


def frost_stats():
    """Spring / fall freeze statistics from the Flathead Valley frost-free days chart (MSU Creston station)."""
    global FROST
    if FROST is not None:
        return FROST
    import datetime, statistics
    FROST = {}
    p = os.path.join(REF_DIR, "flathead-frost-free-days.md")
    if not os.path.exists(p):
        return FROST
    lines = [l.strip() for l in open(p, encoding="utf-8").read().split("## Full text", 1)[-1].splitlines()
             if l.strip() and not l.startswith("[Page")]
    mon = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
    rows, i = [], 0
    while i + 5 < len(lines):
        a, b, c = lines[i + 1], lines[i + 3], lines[i + 5]
        ma, mb = re.match(r"([A-Za-z]{3})\w*\.?\s+(\d+)", a), re.match(r"([A-Za-z]{3})\w*\.?\s+(\d+)", b)
        if re.fullmatch(r"(19|20)\d\d", lines[i]) and ma and mb and c.isdigit() and ma[1].lower() in mon and mb[1].lower() in mon:
            rows.append((int(lines[i]), datetime.date(2001, mon[ma[1].lower()], int(ma[2])).timetuple().tm_yday,
                         datetime.date(2001, mon[mb[1].lower()], int(mb[2])).timetuple().tm_yday, int(c)))
            i += 6
        else:
            i += 1
    if len(rows) < 5:
        return FROST
    day = lambda n: (datetime.date(2001, 1, 1) + datetime.timedelta(days=round(n) - 1)).strftime("%B %d").replace(" 0", " ")
    last, first, ff = [r[1] for r in rows], [r[2] for r in rows], [r[3] for r in rows]
    june1 = datetime.date(2001, 6, 1).timetuple().tm_yday
    sep10 = datetime.date(2001, 9, 10).timetuple().tm_yday
    FROST = {"years": f"{rows[0][0]}-{rows[-1][0]}", "n": len(rows),
             "last": day(statistics.median(last)), "last_early": day(min(last)), "last_late": day(max(last)),
             "june": sum(1 for x in last if x >= june1),
             "first": day(statistics.median(first)), "first_early": day(min(first)), "first_late": day(max(first)),
             "sept10": sum(1 for x in first if x < sep10),
             "season": round(statistics.median(ff)), "season_lo": min(ff), "season_hi": max(ff)}
    return FROST


def frost_lines(refs="../references/"):
    f = frost_stats()
    if not f:
        return []
    chart = f"[Flathead frost-free days chart]({refs}flathead-frost-free-days.md)"
    return [f"- Our season (MSU Creston station, Flathead Valley, {f['years']}, from the {chart}): the **last spring freeze** is "
            f"usually around **{f['last']}** (earliest {f['last_early']}, latest {f['last_late']} - a freeze on or after "
            f"June 1 happened in {f['june']} of {f['n']} years). The **first fall freeze** is usually around **{f['first']}** "
            f"(earliest {f['first_early']}, latest {f['first_late']}). That leaves about **{f['season']} frost-free days** "
            f"({f['season_lo']}-{f['season_hi']})."]


def timing_box(p, rows):
    """Plain-language box under Key facts: what Early / Mid / Late, flowering groups and harvest words mean here."""
    r = dict(rows)
    bloom, harvest = r.get("Bloom / pollination time", ""), r.get("Harvest", "")
    if not (bloom or harvest) or p["kind"] in ("noxious", "poisonous"):
        return ""
    f = frost_stats()
    out = ["### What the timing words mean - in Kalispell terms\n"]
    out += frost_lines()
    out.append("- **Bloom time** words (*Early, Mid, Late*, or Orange Pippin's *flowering group* 1 = earliest to 6-7 = latest) "
               "compare this variety with **other varieties of the same fruit** - they are not calendar dates. In a warm spring "
               "everything blooms sooner, in a cold one later, but the order stays about the same.")
    if fruit_family(p):
        out.append("- **Pollination:** two trees can only pollinate each other if their blossoms are open at the same time - "
                   "the same flowering group or one group apart. A tree that needs a partner gets little or no fruit if the "
                   "partner blooms a week earlier or later. Bees do the work, so cold, windy or rainy weather during bloom "
                   "also means a smaller crop.")
    # this variety's bloom, in plain words
    g = re.search(r"flowering group (\d)", bloom)
    word = bloom.split("(")[0].strip().lower()
    early = (g and int(g.group(1)) <= 2) or word.startswith("early") or "very early" in word
    late = (g and int(g.group(1)) >= 5) or word.startswith(("late", "mid - late", "mid-late"))
    last = f.get("last", "late May")
    if early:
        out.append(f"- **This one blooms early.** Early blossoms open while Kalispell can still get a hard freeze (usually up to "
                   f"about {last}), so they are the most likely to be frosted. Plant it where cold air drains away (a slope, not a low "
                   "spot) and be ready to cover small trees on a frosty night in bloom."
                   + (" MSU notes plums bloom before apples and pears and are more prone to frost damage."
                      if fruit_family(p) in ("hybrid plum", "European plum", "apricot") else ""))
    elif late:
        out.append(f"- **This one blooms later than most.** Later blossoms usually miss the last spring freezes (around {last}), "
                   "which makes it a safer cropper here.")
    elif bloom:
        out.append(f"- **This one blooms mid-season** - in the middle of the pack for its fruit. A freeze after the blossoms open "
                   f"(Kalispell's last freeze is usually around {last}) can still cut the crop in some years.")
    if harvest:
        out.append("- **Harvest dates** from nurseries are for warmer places: Stark Bro's grows in Missouri (zone 6), where the season "
                   "starts earlier and runs longer than ours, so **expect harvest a bit later in Kalispell**. Orange Pippin's "
                   "*Early / Mid / Late season* again compares varieties of the same fruit. *Keeps ...* is how long the fruit stores "
                   "after picking (cool storage).")
        h = harvest.lower()
        if re.search(r"\boctober\b|\blate season\b|\blate september\b|late fall", h):
            out.append(f"- **This one ripens late.** That is close to Kalispell's usual first fall freeze (around {f.get('first', 'September 20')}; "
                       f"before September 10 in {f.get('sept10', 'a few')} of {f.get('n', 'the')} years). In a short year you may need to pick "
                       "it before a hard freeze, even if it is not fully ripe - so late-ripening varieties are the riskier choice here.")
        elif re.search(r"\bjuly\b|\baugust\b|\bearly september\b|\bearly season\b|\bmid season\b|\bmid-season\b", h):
            out.append(f"- **This one ripens early to mid-season,** well ahead of the usual first fall freeze (around "
                       f"{f.get('first', 'September 20')}), so it should ripen fully in most Kalispell years.")
    return "\n".join(out) + "\n"


def facts_table(rows):
    """The Key facts table. The reader shows table cells as plain text (links inside a table are not clickable), so
    cells show link names only and the clickable links follow under the table."""
    link = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    lines = "\n".join(f"| {a} | {link.sub(r'\1', b)} |" for a, b in rows)
    extra = [f"- {a}: " + ", ".join(f"[{t}]({u})" for t, u in link.findall(b)) for a, b in rows if link.search(b)]
    return "## Key facts for Kalispell\n\n| | |\n|---|---|\n" + lines + "\n" + ("\n" + "\n".join(extra) + "\n" if extra else "")


# ================================================================== write a plant page
def build_page(p, d, docs, guide, guide_info, pest_pages, hosts, everyone):
    img = p["slug"] + "_images"
    msu_zone = None
    for path, text, fors in docs:
        if path.endswith("msu-apple-cultivars.md") and p["sci"].startswith("Malus"):
            for k in p["keywords"]:
                m = re.search(r"^\|?\s*" + re.escape(k) + r"\s*\|\s*([^|]+)\|\s*([^|\n]+)", text, re.M | re.I)
                if m:
                    msu_zone = m.group(2).strip(); break
    doc_texts = [t.split("---\n", 2)[-1] for pth, t, fors in docs if matches(p, fors)]
    veg = p["kind"] == "vegetable"
    rows = VP.facts(p, frost_stats()) if veg else facts_block(p, d, msu_zone, everyone, doc_texts)
    out = [f"# {p['title']}\n\n*{p['sci']}*  \nType: {p['group']}  \n"
           + {"cultivar": "Garden variety (cultivar)", "native": "Native to Montana", "introduced": "Introduced / garden plant",
              "noxious": "Noxious weed (Montana)", "poisonous": "Poisonous plant", "vegetable": "Vegetable (home garden)"}[p["kind"]] + "\n"]
    out.append(facts_table(rows))
    box = "" if veg else timing_box(p, rows)
    if box:
        out.append(box)
    imgdir = os.path.join(PLANT_DIR, img)
    mine_ph = sorted(f for f in os.listdir(imgdir) if f.lower().startswith("my_") and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))) \
        if os.path.isdir(imgdir) else []
    src_p = os.path.join(imgdir, "my_photo_sources.json")   # web photos the user picked (70_photo_candidates.py keep)
    web = {x["file"]: x for x in json.load(open(src_p, encoding="utf-8"))} if os.path.exists(src_p) else {}

    def my_credit(f):
        s = web.get(f)
        if not s:
            return "My photo"
        site = re.sub(r"^www\.", "", (s.get("source_page") or s.get("image_url") or "").split("/")[2] if "//" in (s.get("source_page") or s.get("image_url") or "") else "")
        return f"Web photo from {site} - chosen by me, personal reference only"
    d = dict(d, photos=[{"file": f, "credit": my_credit(f)} for f in mine_ph] + d["photos"])   # your own photos ('my_...') first
    if web:
        d["sources"] = d["sources"] + [(f"Web photo ({my_credit(f).split(' - ')[0].replace('Web photo from ', '')})", s.get("source_page") or s["image_url"])
                                       for f, s in web.items()]
    if d["photos"]:
        out.append("## Photos\n\n" + "\n\n".join(f"![{p['title']} - {x['credit']}]({img}/{x['file']})  \n*{x['credit']}*" for x in d["photos"][:12]) + "\n")
    if veg:
        out.append(VP.sections(p, frost_stats()))
    st = d.get("stark")
    if st and st["description"]:
        out.append("## Description\n\n" + "\n\n".join(st["description"]) + f"\n\n*From Stark Bro's ({st['url']}).*\n")
    if d.get("op") and d["op"].get("description"):
        out.append("## Variety notes (Orange Pippin)\n\n" + "\n\n".join(d["op"]["description"]) + f"\n\n*From {d['op']['url']}*\n")
    if d.get("op"):
        f = d["op"]["facts"]
        keep = [k for k in f if k not in ("Cold hardiness (USDA)",) and len(f[k]) < 120 and not k.startswith("Summer average")]
        out.append("## Variety data (Orange Pippin)\n\n" + "\n".join(f"- {k}: {f[k]}" for k in keep[:40]) + "\n")
    mt = d.get("mtfg")
    if mt and (mt["sections"] or mt["maps"]):
        part = [f"### {k}\n\n{v}" for k, v in mt["sections"].items()]
        if mt.get("communities"):
            part.append(f"### Montana plant communities it grows in\n\n{mt['communities']}")
        maps = "\n\n".join(f"![{m['caption']}]({img}/{m['file']})  \n*{m['caption']} (Montana Field Guide)*" for m in [m for m in mt["maps"] if "chart" not in m["file"]
                                                              and os.path.exists(os.path.join(PLANT_DIR, img, m["file"]))][:4])
        reps = ([f"- [Montana Field Guide species report (PDF)]({img}/{mt['report']})"] if mt.get("report") else []) + \
               ([f"- [Montana conservation status report (PDF)]({img}/{mt['rank_report']})"] if mt.get("rank_report") else [])
        head = "## Montana Field Guide" + (f" - the wild species ({p['base']})\n\nThis section is about the wild/species plant in Montana, "
                                            "not this garden variety." if p["kind"] == "cultivar" else "")
        out.append(head + "\n\n" + "\n\n".join(part) + ("\n\n### Range maps and charts\n\n" + maps if maps else "")
                   + ("\n\n" + "\n".join(reps) if reps else "") + f"\n\nSource: {mt['url']}\n")
    # what Montana documents say
    mine = [(pth, t) for pth, t, fors in docs if matches(p, fors)]
    hits = []
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in p["keywords"]) + r")", re.I if p["kind"] != "cultivar" else 0)
    for pth, t in mine + [(pp, open(pp, encoding="utf-8").read()) for pp in []]:
        body = t.split("---\n", 2)[-1]
        if "[Page " in body:   # PDF text keeps the printed line breaks - join them so quotes are whole sentences
            body = unwrap(body)
        hs = [s for s in L.sentences(body, pat.pattern if p["kind"] != "cultivar" else r"\b(" + "|".join(re.escape(k) for k in p["keywords"]) + r")\b", n=6, maxlen=600)
              if not s.startswith(("Source:", "Original file")) and "___" not in s
              and not re.search(r"\d+-\d+\s+\d+\s+\d+-\d+", s)]   # not scraps of a table (fill-in blanks, rows of numbers)
        if hs:
            hits.append((pth, hs))
    if hits:
        out.append(f"## What Montana sources say about {p['title']}\n\n" + "\n\n".join(
            f"From {link(fm_title(t), pth, PLANT_DIR)}:\n\n" + "\n".join(f"> {h}" for h in hs)
            for (pth, hs), t in zip(hits, [open(h[0], encoding='utf-8').read() for h in hits])) + "\n")
    care, pests = [], []
    if guide_info:
        care.append(f"{link(guide_info['title'], guide, PLANT_DIR)} - chapters: " + ", ".join(c["title"] for c in guide_info["chapters"]))
    for pth, t in mine:
        topic = re.search(r'^topic: "(.*)"', t, re.M)
        (pests if topic and topic.group(1) == "Pests & diseases" else care).append(link(fm_title(t), pth, PLANT_DIR))
    if care:
        out.append("## Planting & care\n\n" + "\n".join("- " + c for c in care) + "\n")
    if veg:
        pests = VP.pest_links(p, PLANT_DIR) + pests
    genus = p["base"].split()[0]
    hp = [(t, s) for t, s in hosts.get(genus, []) if s in pest_pages]
    if hp:
        pests = [link(t, pest_pages[s], PLANT_DIR) for t, s in hp] + pests
    if guide_info:
        pests += [f"{link(guide_info['title'], guide, PLANT_DIR)} - chapter: {c['title']}" for c in guide_info["chapters"]
                  if re.search(r"pest|disease|spray", c["title"], re.I)]
    if pests:
        out.append("## Pests, diseases & problems\n\n" + "\n".join("- " + c for c in pests) + "\n")
    if guide_info and guide_info["videos"]:
        out.append("## Videos\n\n" + "\n".join(f"- ▶ [{v['title']}]({rel(os.path.join(D, v['file']), PLANT_DIR)})" for v in guide_info["videos"]) + "\n")
    if d.get("wiki_md"):
        out.append(f"## Wikipedia: {d['wiki']['title']}\n\n" + d["wiki_md"] + "\n")
    out.append("## Sources\n\n" + "\n".join(f"- {n}: <{u}>" for n, u in d["sources"]) + "\n\nLicenses: " + "; ".join(dict.fromkeys(d["lic"])) + "\n")
    meta = {"title": p["title"], "category": CAT, "source_type": "local-profile", "group": p["group"], "plant_type": p["kind"],
            "scientific_name": p["sci"], "source_url": d["sources"][0][1] if d["sources"] else None,
            "sources": [{"name": n, "url": u} for n, u in d["sources"]], "license": "Mixed - see Sources",
            "key_facts": {a: re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", b) for a, b in rows},
            "keywords": p["keywords"], "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    if mt and mt.get("report"):
        meta["file"] = f"{img}/{mt['report']}"
    if not meta["source_url"]:
        meta["provenance"] = "Compiled from the library's Montana reference documents"
    write_doc(os.path.join(PLANT_DIR, p["slug"] + ".md"), meta, "", "\n".join(out))


# ================================================================== start page
def build_veg_calendar(plants):
    """local-area/plants/kalispell-vegetable-planting-calendar.md - month by month, from MSU's planting table + our frost dates."""
    veg = [p for p in plants if p["kind"] == "vegetable"]
    if not veg:
        return None
    path = os.path.join(PLANT_DIR, "kalispell-vegetable-planting-calendar.md")
    title = "Kalispell Vegetable Planting Calendar"
    body = f"# {title}\n\nType: Vegetables  \nMonth-by-month planting guide for the home garden and an unheated greenhouse\n\n" + VP.calendar(veg, frost_stats())
    meta = {"title": title, "category": CAT, "source_type": "local-profile", "group": "Vegetables", "plant_type": "guide",
            "license": "Compiled from MSU Extension, NMSU and University of Wyoming publications - see links",
            "provenance": "Compiled from the library's Montana reference documents", "compiled": TODAY, "date_added": TODAY,
            "date_source": "added to the library"}
    write_doc(path, meta, "", body)
    return path


def build_start(plants, docs):
    frost = next((t for pth, t, f in docs if pth.endswith("flathead-frost-free-days.md")), "")
    groups = {}
    for p in plants:
        groups.setdefault(p["group"], []).append(p)
    out = [f"# Local Area - {R['town']}, {R['county']}, Montana\n",
           "## Growing conditions\n",
           f"| | |\n|---|---|\n| USDA hardiness zone | {R['zone']} ({R['zone_range']}) - {R['zone_source']} |\n"
           f"| Frost-free season | about {frost_stats().get('season', 124)} days - see Frost dates below (MSU Creston station) |\n"
           f"| County Extension office | MSU Extension - Flathead County, Kalispell (https://www.montana.edu/extension/flathead/) |\n"]
    if frost_stats():
        out.append("### Frost dates\n\n" + "\n".join(frost_lines("references/"))   # links inside tables are not clickable in the reader
                   + "\n- The full chart, year by year: [Frost-Free Days Chart for the Flathead Valley](references/flathead-frost-free-days.md)\n")
    out.append("### What the timing words on the plant pages mean\n\n"
               "- **Bloom time** (*Early, Mid, Late*, or Orange Pippin's *flowering group* 1 = earliest to 6-7 = latest) compares a "
               "variety with other varieties of the same fruit - not a calendar date. A warm spring moves everything earlier and a "
               "cold one later, but the order stays about the same.\n"
               "- **Early bloomers** open while a late-spring freeze is still likely here, so their blossoms are the most often "
               "frosted - plant them where cold air drains away and cover small trees on frosty nights in bloom. **Late bloomers** "
               "usually miss those freezes.\n"
               "- **Pollination partners** must have blossoms open at the same time: the same flowering group or one apart. "
               "Crabapples bloom over a long stretch and pollinate most apples.\n"
               "- **Harvest dates** from nurseries are for warmer places (Stark Bro's is in Missouri, zone 6) - expect them a bit "
               "later in Kalispell. Varieties that ripen in late September or October finish close to our usual first fall freeze, "
               "so in a short year they may have to be picked early; early and mid-season varieties are the safer choice.\n"
               "- **Keeps ...** is how long the fruit stores after picking, in cool storage.\n")
    out.append("## Plants by type\n")
    for g, ps in groups.items():
        out.append(f"### {g}\n\n" + "\n".join(f"- [{q['title']}](plants/{q['slug']}.md) - *{q['sci']}*" for q in ps) + "\n")
    out.append("## Guides & references\n\n- Growing guides (Stark Bro's): folder `guides`\n- MSU, Flathead County, USDA and USFS documents: folder `references`\n"
               "- Pests, diseases & problems (MSU guide, one page each): folder `pests-problems`\n")
    meta = {"title": f"Start Here - Growing in {R['town']} ({R['county']}, Montana)", "category": CAT, "source_type": "local-overview",
            "topic": "Kalispell climate", "publisher": "Compiled for this library", "provenance": "Compiled from the documents in this section",
            "license": "Mixed - see linked documents", "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    write_doc(os.path.join(D, "start-here-kalispell.md"), meta, "", "\n".join(out))


# ================================================================== main
def main():
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    plants = parse_table()
    if want:
        keys = {w.lower() for w in want}
        todo = [p for p in plants if p["title"].lower() in keys or p["slug"] in keys]
    else:
        todo = plants
    for x in (PLANT_DIR, GUIDE_DIR, REF_DIR, PEST_DIR):
        os.makedirs(x, exist_ok=True)
    print("== references", flush=True)
    docs = build_references()
    print("== pests & problems guide", flush=True)
    pest_pages, hosts = build_pests()
    if "--fix-photos" in sys.argv:
        print("== fixing photos", flush=True)
        fix_photos(todo)
    print("== plants", flush=True)
    data = {}
    for p in plants:   # all plants' data is needed for the pollination partners
        if p in todo or os.path.exists(os.path.join(L.W, "plants", p["slug"] + ".json")):
            try:
                data[p["slug"]] = gather(p)
            except Exception as e:
                print(f"  FAILED {p['title']}: {e}", flush=True)
    everyone = [(p, data[p["slug"]]) for p in plants if p["slug"] in data]
    guides = {}
    for p in todo:
        if p["slug"] not in data:
            continue
        series = None if p["kind"] in SP.NO_GUIDE_KINDS else (best_prefix(p, SP.GENUS_GUIDE) or SP.GROUP_GUIDE.get(p["group"]))
        g = gi = None
        if series:
            if series not in guides:
                try:
                    guides[series] = build_guide(series)
                except Exception as e:
                    print("  guide FAILED", series, e); guides[series] = (None, None)
            g, gi = guides[series]
        build_page(p, data[p["slug"]], docs, g, gi, pest_pages, hosts, everyone)
        print(f"  page: plants/{p['slug']}.md", flush=True)
    if any(p["kind"] == "vegetable" for p in todo):
        print("  page:", build_veg_calendar(plants), flush=True)
    build_start(plants, docs)
    py = sys.executable
    for s in ("20_catalog.py", "21_readme.py"):
        subprocess.run([py, os.path.join(os.path.dirname(__file__), s)])


if __name__ == "__main__":   # 71_build_local_wildlife.py imports this file
    main()
