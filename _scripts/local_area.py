"""Local Area (Montana) knowledge base - fetch helpers and extractors.

Everything is downloaded and stored inside the library (text, photos, PDFs, maps, videos) so it can be viewed
offline. Used by 69_build_local_area.py.
Sources: Montana Field Guide (MTNHP), MSU Extension / Western Ag Research Center, NRCS, Montana DNRC,
Stark Bro's growing guides + variety pages, Wikipedia (from the local Kiwix ZIM), iNaturalist photos.
"""
import base64, hashlib, html as _html, json, os, re, subprocess, time, urllib.parse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

from common import RESEARCH, find_browser

W = os.path.join(RESEARCH, "_work", "local_area")
CACHE = os.path.join(W, "cache")
os.makedirs(CACHE, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
S = requests.Session()
S.headers["User-Agent"] = UA
CHROME = find_browser()
HOST_FAILS = {}   # host -> failures in a row this run


def fetch(url, data=None, binary=False, cache=True):
    """GET (or POST with data) through a disk cache. Returns text, or bytes when binary=True."""
    key = hashlib.md5((url + json.dumps(data, sort_keys=True)).encode()).hexdigest()
    p = os.path.join(CACHE, key + (".bin" if binary else ".html"))
    if cache and os.path.exists(p) and os.path.getsize(p) > 0:
        b = open(p, "rb").read()
        return b if binary else b.decode("utf-8", "replace")
    host = urllib.parse.urlparse(url).netloc
    if HOST_FAILS.get(host, 0) >= 3:   # a server that failed 3 times this run is skipped (saves hours of timeouts)
        raise RuntimeError(f"server not answering: {host}")
    for attempt in range(4):
        try:
            # Wikimedia asks tools to name themselves (a browser-like name gets throttled/blocked)
            hdr = {"User-Agent": "ResearchLibraryLocalArea/1.0 (personal offline plant library; python-requests)"} \
                if host.endswith(("wikimedia.org", "wikipedia.org")) else None
            r = S.post(url, data=data, headers=hdr, timeout=(15, 90)) if data else S.get(url, headers=hdr, timeout=(15, 90))
            if host.endswith("wikimedia.org"):
                time.sleep(1.0)   # be gentle
            if r.status_code == 200:
                HOST_FAILS[host] = 0   # it answers again - forget earlier blips
                break
            if r.status_code in (403, 404, 410):
                raise RuntimeError(f"HTTP {r.status_code} {url}")
            if r.status_code == 429:   # rate limited (Wikimedia): wait as asked, then try again
                time.sleep(min(int(r.headers.get("Retry-After", "20") or 20), 120) + 5 * attempt)
                continue
        except (requests.ConnectionError, requests.Timeout) as e:
            if isinstance(e, requests.ConnectTimeout) or "NameResolution" in str(e) or attempt == 1:
                HOST_FAILS[host] = HOST_FAILS.get(host, 0) + 1
                raise RuntimeError(f"server not answering: {host}")
        except requests.RequestException as e:
            if attempt == 3:
                raise RuntimeError(f"{e} {url}")
        time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError(f"HTTP {r.status_code} {url}")
    open(p, "wb").write(r.content)
    time.sleep(0.7)
    return r.content if binary else r.content.decode(r.encoding or "utf-8", "replace") if not r.content.startswith(b"\xef\xbb\xbf") else r.content.decode("utf-8-sig")


def save_bin(url, dest, data=None):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    b = fetch(url, data=data, binary=True)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "wb").write(b)
    return dest


def ext_of(url, default=".jpg"):
    e = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    return e if e in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf") else default


def clean_text(s):
    return re.sub(r"[ \t]+", " ", s.replace("\xa0", " ")).strip()


# ---------------------------------------------------------------- generic article -> local md + images
def article_to_local(el, base_url, img_dir, img_rel, prefix=""):
    """Rewrite an article element: download its images into img_dir, drop scripts/forms/nav, return
    (markdown, html_fragment, [image files])."""
    for bad in el.select("script, style, noscript, form, iframe, nav, button, .context-menu, .share, .social"):
        bad.decompose()
    files = []
    for n, img in enumerate(el.select("img"), 1):
        src = img.get("data-src") or img.get("src") or ""
        tpl = img.get("data-src-template")
        if tpl:   # Stark Bro's lazy images: base64 of '/images/...{width}x0-fillh.gif'
            try:
                src = base64.b64decode(tpl).decode().replace("{width}", "800")
            except Exception:
                pass
        if not src or src.startswith("data:"):
            img.decompose(); continue
        url = urllib.parse.urljoin(base_url, src)
        if "youtube.com/vi/" in url:      # video thumbnails - videos are handled separately
            img.decompose(); continue
        name = f"{prefix}{n:02d}{ext_of(url)}"
        try:
            save_bin(url, os.path.join(img_dir, name))
        except Exception as e:
            print("  image failed:", url, e)
            img.decompose(); continue
        files.append(name)
        img.attrs = {"src": f"{img_rel}/{name}", "alt": clean_text(img.get("alt") or img.get("title") or "")}
    for a in el.select("a[href]"):
        a["href"] = urllib.parse.urljoin(base_url, a["href"])
    md = markdownify(str(el), heading_style="ATX", bullets="-")
    md = re.sub(r"\*\*(\[[^\]]+\]\([^)]+\))\*\*", r"\1", md)   # the reader ignores links inside **bold**
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md, str(el), files


def html_pdf(title, fragment, pdf_path, source_line, base_dir):
    """Print a clean page (our own HTML, local images) to PDF with headless Chrome/Edge."""
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{_html.escape(title)}</title><style>
 body{{font-family:Georgia,serif;margin:26px 34px;color:#222;font-size:11.5pt;line-height:1.45}}
 h1{{font-size:20pt;margin:0 0 8px}} h2{{font-size:14.5pt;border-bottom:1px solid #ccc;margin:18px 0 6px}}
 h3{{font-size:12.5pt;margin:14px 0 4px}} img{{max-width:100%;max-height:420px;display:block;margin:8px 0}}
 table{{border-collapse:collapse;margin:8px 0}} td,th{{border:1px solid #bbb;padding:3px 7px;font-size:10.5pt;vertical-align:top}}
 a{{color:#225;text-decoration:none}} .src{{color:#666;font-size:9pt;word-break:break-all;margin-top:18px}}
</style></head><body><h1>{_html.escape(title)}</h1>{fragment}<p class="src">{_html.escape(source_line)}</p></body></html>"""
    tmp = os.path.join(base_dir, "_print_" + hashlib.md5(pdf_path.encode()).hexdigest()[:8] + ".html")
    open(tmp, "w", encoding="utf-8").write(page)
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                        f"--print-to-pdf={pdf_path}", "file:///" + tmp.replace("\\", "/")], capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        pass
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2000


def pdf_text(path):
    import pymupdf
    d = pymupdf.open(path)
    out = [f"[Page {i}]\n\n{p.get_text().strip()}" for i, p in enumerate(d, 1)]
    return "\n\n".join(out), d.page_count


# pictures that are not photos of the plant: paintings, illustrations, charts, badges, heraldry, buildings, computers...
JUNK_PIC = re.compile(r"pomolog|watercol|painting|paint|illustrat|drawing|sketch|lithograph|engraving|plate[ _]|tafel|"
                      r"k(o|oe|ö)hler|hedrick|botanical[ _]magazine|curtis|herbier|still[ _]life|stilleben|nature[ _]morte|"
                      r"chart|graph|production|statistic|status[ _]|iucn|tnc[ _]|coat[ _]of[ _]arms|wappen|flag[ _]|logo|"
                      r"schloss|castle|church|palace|map[ _]of|kft|macintosh|stamp|poster|label|seal[ _]|\.svg|portrait|"
                      r"museum|cookbook|recipe", re.I)


def junk_pic(*texts):
    return any(JUNK_PIC.search(x or "") for x in texts)


# ---------------------------------------------------------------- Montana Field Guide
MTFG = "https://fieldguide.mt.gov/"
MTFG_SECTIONS = ["General Description", "Diagnostic Characteristics", "Phenology", "Species Range", "Range Comments",
                 "Habitat", "Ecology", "Reproductive Characteristics", "Management", "Food Habits",
                 "Stewardship Responsibility", "Ethnobotany", "Origin of this species in Montana", "Invasive Status",
                 "Similar Species", "Species Description", "Migration", "Diagnostic Characteristics of Tracks",
                 "Hunting", "Fishing", "Status"]


def status_from_flat(flat):
    """The species' status line, which sits between the photo credit link and 'Global Rank' - e.g. 'Native Species',
    'Non-native Species', 'Noxious Weed: Priority 2B; Non-native Species', 'Species of Concern; Native Species'.
    (Searching the whole page for 'Noxious Weed' was wrong: the sidebar links to the noxious weed lists on every page.)"""
    i = flat.find("Global Rank")
    if i < 0:
        return ""
    seg = flat[:i]
    j = seg.rfind("Image Copyright and Usage Information")
    seg = seg[j + len("Image Copyright and Usage Information"):] if j >= 0 else seg[-160:]
    seg = re.sub(r"\s+", " ", seg).strip()
    if not seg or len(seg) > 160:
        return ""
    seg = re.sub(r"\s+(?=(Native|Non-native|Native/Non-native) Species)", "; ", seg)
    return re.sub(r"(Species|Origin)\s+(?=(Accidental|Not Documented|Hybrid|Native|Non-native))", r"\1; ", seg)


def mtfg_status(elcode):
    """Status line for a species from its (cached) Montana Field Guide page."""
    h = fetch(f"{MTFG}speciesDetail.aspx?elcode={elcode}")
    txt = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", h)
    return status_from_flat(clean_text(_html.unescape(re.sub(r"<[^>]+>", " ", txt))))


def mtfg_species(elcode, dest_dir, rel):
    """Montana Field Guide species page -> dict(sections, photos, maps, report pdf)."""
    url = f"{MTFG}speciesDetail.aspx?elcode={elcode}"
    h = fetch(url)
    s = BeautifulSoup(h, "html.parser")
    out = {"url": url, "elcode": elcode, "sections": {}, "photos": [], "maps": [], "facts": {}}
    txt = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", h)
    # rank / native facts
    flat = clean_text(_html.unescape(re.sub(r"<[^>]+>", " ", txt)))
    for k, pat in (("Global Rank", r"Global Rank\s*:\s*(\w+)"), ("State Rank", r"State Rank\s*:\s*(\w+)"),
                   ("C-value", r"C-value\s*:\s*(\d+)")):
        m = re.search(pat, flat)
        if m:
            out["facts"][k] = m.group(1)
    st = status_from_flat(flat)
    if st:
        out["facts"]["Status"] = st
    # sections: headings are divs with class 'pageHeading2'/'fglbl' etc.; fall back to text splitting
    lines = [clean_text(l) for l in _html.unescape(re.sub(r"<[^>]+>", "\n", txt)).split("\n")]
    lines = [l for l in lines if l]
    stops = set(MTFG_SECTIONS) | {"Observations in Montana Natural Heritage Program Database", "References",
                                  "Predicted Suitable Habitat Model", "Ecological Communities Associated with this Species",
                                  "Range Descriptions", "Montana Range", "Additional References", "Literature Cited Above",
                                  "Number of Observations:", "Web Search Engines for Articles on", "Additional Sources of Information Related to"}
    cur = None
    for l in lines:
        if l in MTFG_SECTIONS:
            cur = l; out["sections"].setdefault(cur, []); continue
        if l in stops or l.startswith("Web Search Engines") or l.startswith("(Click on the following"):
            cur = None; continue
        if cur:
            out["sections"][cur].append(l)
    for k, v in list(out["sections"].items()):
        t = re.sub(r"\s+([,.;:)])", r"\1", " ".join(v)).replace("( ", "(")
        t = re.sub(r"\s*\(\s*see\s*$", "", t).strip()
        if t and t not in ("Native", "(see"):
            out["sections"][k] = t
        else:
            del out["sections"][k]
    # ecological communities
    m = re.search(r"Ecological Communities Associated with this Species(.*?)Stewardship Responsibility", flat)
    if m:
        out["communities"] = re.sub(r"\b(HGCN|HOPC)\b", "", m.group(1)).strip()
    # photos (full size via thumbnail service)
    seen = set()
    for m in re.finditer(r"defaultGen\.aspx\?itemid=(\d+)&names=([^&\"']*)&copyright=([^&\"']*)&photographer=([^&\"']*)", h):
        iid = m.group(1)
        if iid in seen:
            continue
        seen.add(iid)
        name = f"mtfg_{len(seen):02d}.jpg"
        purl = f"https://mtnhp.org/thumbnail/defaultGen.aspx?itemid={iid}&maxWidth=1024&maxHeight=768"
        try:
            save_bin(purl, os.path.join(dest_dir, name))
        except Exception as e:
            print("  mtfg photo failed", iid, e); continue
        out["photos"].append({"file": name, "photographer": _html.unescape(urllib.parse.unquote(m.group(4))),
                              "copyright": _html.unescape(urllib.parse.unquote(m.group(3))),
                              "source": f"Montana Field Guide (MTNHP) photo {iid}"})
    for kind, label in (("RangeMap_{e}.jpg", "Montana range map"), ("GenObsMap_{e}_FS.jpg", "Observations in Montana (density)"),
                        ("RecencyMap_{e}_FS.jpg", "Observation recency map"), ("ElevChart_{e}_FS.png", "Elevation of observations"),
                        ("AnnualChart_{e}.png", "Observations by month")):
        f = kind.format(e=elcode)
        if f.replace("_FS", "") not in h and f not in h:
            continue
        try:
            save_bin(f"{MTFG}RangeMaps/{f}", os.path.join(dest_dir, "mtfg_" + f.replace("_" + elcode, "").lower()))
            out["maps"].append({"file": "mtfg_" + f.replace("_" + elcode, "").lower(), "caption": label})
        except Exception as e:
            print("  map failed", f, e)
    # the field guide's own species PDF report
    title = s.title.get_text(strip=True).split(" - ")[0] if s.title else elcode
    pdf = os.path.join(dest_dir, f"montana-field-guide-report.pdf")
    try:
        save_bin(MTFG + "DownloadPDF.aspx", pdf, data={"title": title, "elcodes": elcode, "cite": "https://FieldGuide.mt.gov",
                                                       "sort": "2", "referrer": "/CustomFieldGuidePDF/FieldGuide/" + elcode})
        out["report"] = os.path.basename(pdf)
    except Exception as e:
        print("  report failed", e)
    m = re.search(r'href="(https://mtnhp\.org/rankreports/[^"]+\.pdf)"', h)
    if m:
        try:
            save_bin(m.group(1), os.path.join(dest_dir, "montana-conservation-status-report.pdf"))
            out["rank_report"] = "montana-conservation-status-report.pdf"
        except Exception as e:
            print("  rank report failed", e)
    return out


# ---------------------------------------------------------------- Stark Bro's
STARK = "https://www.starkbros.com"


def stark_variety(path, dest_dir):
    """Stark Bro's product page -> description paragraphs, characteristics, size/spacing, pollination, main photo."""
    url = f"{STARK}/products/{path}"
    s = BeautifulSoup(fetch(url), "html.parser")
    out = {"url": url, "chars": {}, "size": [], "pollination": "", "partners": [], "description": [], "photos": []}
    d = s.select_one(".product-guide-section.description .description-content") or s.select_one(".description-content")
    if d:
        for el in d.find_all(["p", "h2", "h3", "h4", "li"]):
            t = clean_text(el.get_text(" ", strip=True))
            t = re.sub(r"\s*[^.!?]*›\s*$", "", t).strip()
            if t:
                out["description"].append(("### " + t) if el.name.startswith("h") else ("- " + t) if el.name == "li" else t)
    c = s.select_one(".product-guide-section.characteristics")
    if c:
        for tr in c.select("tr"):
            tds = [clean_text(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(tds) == 2 and tds[0] != "Characteristic Name":
                out["chars"][tds[0]] = tds[1]
    z = s.select_one(".product-guide-section.size-and-spacing")
    if z:
        for tr in z.select("tr"):
            tds = [clean_text(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(tds) == 2 and tds[0] != "Mature Size":
                out["size"].append(tds)
    p = s.select_one(".product-guide-section.pollination-details")
    if p:
        ps = [clean_text(x.get_text(" ", strip=True)) for x in p.select("p")]
        out["pollination"] = " ".join(x for x in ps if x and "$" not in x)[:600]
        for a in p.select('a[href*="/products/"]'):
            n = clean_text(a.get_text(" ", strip=True))
            n = re.sub(r"\b(Out of Stock|On Sale|Compare|A Stark\S* Exclusive!?)\b|\(\d+\)|[®™]", "", n)
            n = re.sub(r"\s+", " ", n).strip()
            if n and len(n) < 60 and "View All" not in n and "$" not in n and n not in out["partners"] and not n.startswith("("):
                out["partners"].append(n)
    # photos: ld+json product image + gallery images of this product
    imgs = []
    for j in s.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(j.string)
        except Exception:
            continue
        me = data.get("mainEntity") if isinstance(data, dict) else None
        if me and me.get("image"):
            imgs.append(me["image"])
    for a in s.select("[data-zoom-image], .product-image a[href*='/images/dynamic/'], .gallery a[href*='/images/dynamic/']"):
        imgs.append(urllib.parse.urljoin(STARK, a.get("data-zoom-image") or a.get("href")))
    seen = []
    for u in imgs:
        u = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", u)
        if u not in seen:
            seen.append(u)
    for n, u in enumerate(seen[:6], 1):
        name = f"stark_{n:02d}{ext_of(u)}"
        try:
            save_bin(u, os.path.join(dest_dir, name))
            out["photos"].append({"file": name, "source": "Stark Bro's", "url": u})
        except Exception as e:
            print("  stark photo failed", u, e)
    return out


def stark_guide(plant, guide_dir, rel):
    """All articles of a Stark Bro's growing-guide series (e.g. 'fruit-trees/apple-trees'), images downloaded,
    YouTube videos listed. Returns list of {slug,title,url,md,html,videos}."""
    base = f"{STARK}/growing-guide/how-to-grow/{plant}"
    h = fetch(base)
    s = BeautifulSoup(h, "html.parser")
    pages = [base]
    for a in s.select(f'a[href^="/growing-guide/how-to-grow/{plant}/"]'):
        u = STARK + a["href"].split("#")[0]
        if u not in pages:
            pages.append(u)
    arts = []
    for i, u in enumerate(pages):
        s = BeautifulSoup(fetch(u), "html.parser")
        h1 = s.find("h1")
        body = h1.find_parent("div", class_="col-lg-8") if h1 else None
        if body is None:
            continue
        videos = []
        for img in body.select("img[src*='youtube.com/vi/']"):
            vid = re.search(r"/vi/([\w-]+)/", img["src"]).group(1)
            videos.append({"id": vid, "title": clean_text((img.get("alt") or "").replace("Video preview for ", ""))})
        for note in body.find_all(string=re.compile(r"This is part")):
            par = note.find_parent(["p", "div"])
            if par:
                par.decompose()
        # drop 'related articles' / product promos at the end
        for bad in body.select(".article-link, .product-card, .cross-sell-group, [class*=video], .related, .lazy-video"):
            bad.decompose()
        slug = u.rstrip("/").rsplit("/", 1)[-1] if u != base else "introduction"
        md, frag, files = article_to_local(body, u, guide_dir, rel, prefix=f"{i:02d}_")
        arts.append({"slug": slug, "title": clean_text(h1.get_text()), "url": u, "md": md, "html": frag, "videos": videos})
    return arts


def youtube(vid, dest):
    """Download a YouTube video (<=720p mp4) with yt-dlp so it can be watched offline."""
    if os.path.exists(dest):
        return dest
    import yt_dlp
    opts = {"format": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]",
            "merge_output_format": "mp4", "outtmpl": dest, "quiet": True, "no_warnings": True, "noprogress": True}
    try:
        import imageio_ffmpeg
        opts["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([f"https://www.youtube.com/watch?v={vid}"])
    except Exception as e:
        print("  video failed", vid, e)
    return dest if os.path.exists(dest) else None


# ---------------------------------------------------------------- iNaturalist photos
def inat_photos(sci, dest_dir, n=4):
    r = json.loads(fetch(f"https://api.inaturalist.org/v1/taxa?q={urllib.parse.quote(sci)}&rank=species,variety,subspecies"))
    norm = lambda s: s.lower().replace(" x ", " × ").replace("× ", "×")
    tx = next((t for t in r["results"] if norm(t["name"]) == norm(sci)), None)   # exact name only - never a look-alike
    if not tx:
        return None, []
    t = json.loads(fetch(f"https://api.inaturalist.org/v1/taxa/{tx['id']}"))["results"][0]
    out = []
    for p in t.get("taxon_photos", []):
        ph = p["photo"]
        lic = ph.get("license_code")
        if not lic:                    # all rights reserved -> skip
            continue
        url = ph.get("large_url") or ph["url"].replace("square", "large")
        name = f"inat_{len(out) + 1:02d}.jpg"
        try:
            save_bin(url, os.path.join(dest_dir, name))
        except Exception as e:
            print("  inat failed", e); continue
        out.append({"file": name, "source": "iNaturalist", "attribution": ph.get("attribution"), "license": lic})
        if len(out) >= n:
            break
    return t, out


# ---------------------------------------------------------------- Wikimedia Commons photos (garden varieties)
def commons_photos(category, dest_dir, n=6, start=1):
    """Photos from a Wikimedia Commons category (e.g. 'Honeycrisp'), ~1024 px, with author + license."""
    api = ("https://commons.wikimedia.org/w/api.php?action=query&generator=categorymembers&gcmtype=file&gcmlimit=40"
           f"&gcmtitle=Category:{urllib.parse.quote(category)}&prop=imageinfo&iiprop=url|extmetadata|mime&iiurlwidth=1024&format=json")
    data = json.loads(fetch(api))
    out = []
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p["title"])
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/webp"):   # png = charts/diagrams, not photos
            continue
        md = ii.get("extmetadata", {})
        if junk_pic(pg.get("title"), (md.get("ImageDescription") or {}).get("value", ""), (md.get("Categories") or {}).get("value", "")):
            continue
        g = lambda k: clean_text(re.sub(r"<[^>]+>", "", _html.unescape((md.get(k) or {}).get("value", ""))))
        name = f"commons_{start + len(out):02d}{ext_of(ii['thumburl'].split('?')[0])}"
        try:
            save_bin(ii["thumburl"].split("?")[0], os.path.join(dest_dir, name))
        except Exception as e:
            print("  commons failed", e); continue
        out.append({"file": name, "source": "Wikimedia Commons", "attribution": g("Artist") or "unknown author",
                    "license": g("LicenseShortName"), "page": ii.get("descriptionurl"), "caption": g("ImageDescription")[:200]})
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- Orange Pippin (fruit variety data)
def orange_pippin(path):
    """orangepippin.com variety page -> {label: value} for the growing/using/climate/disease facts + description."""
    url = f"https://www.orangepippin.com/varieties/{path}"
    try:
        h = fetch(url)
    except Exception as e:
        print("  orange pippin:", e)
        return None
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", h)
    lines = [clean_text(x) for x in _html.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n")]
    lines = [x for x in lines if x]
    facts = {}
    for i, x in enumerate(lines[:-1]):
        if x.endswith(":") and 2 < len(x) < 45:
            k, v = x[:-1].strip(), lines[i + 1]
            if v.endswith(":"):
                continue
            facts.setdefault(k, [])
            if v not in facts[k]:
                facts[k].append(v)
    if not facts.get("Flowering group") and not facts.get("Picking season") and not facts.get("Species"):
        return None
    s = BeautifulSoup(h, "html.parser")
    desc = []
    for p in s.select("#variety-description p, .variety-description p, .description p")[:6]:
        tx = clean_text(p.get_text(" ", strip=True))
        if len(tx) > 60:
            desc.append(tx)
    photos = []
    for u in re.findall(r'src="(https://ik\.imagekit\.io/orangepippin/tr:[^"/]+/\d+/[^"]+\.(?:jpe?g|png))"', h, re.I):
        u = re.sub(r"/tr:[^/]+/", "/tr:n-0500j/", u)
        if u not in photos:
            photos.append(u)
    return {"url": url, "facts": {k: ", ".join(v) for k, v in facts.items()}, "description": desc, "photos": photos[:6]}


# ---------------------------------------------------------------- MSU Extension store publications
def msu_pub(slug):
    """extension-store.montana.edu product slug -> (title, sku, pdf_url) or None."""
    base = "https://extension-store.montana.edu"
    h = fetch(f"{base}/products/{slug}")
    title = re.search(r"<title>\s*([^<]+)", h)
    title = _html.unescape(title.group(1)).split(" - Extension Store")[0].strip() if title else slug
    sku = re.search(r"SKU:\s*([A-Z0-9]+)", re.sub(r"<[^>]+>", " ", h))
    pdf = re.search(r'href="([^"]+\.pdf)"', h)
    if not pdf:
        try:
            pdf = re.search(r'href="([^"]+\.pdf)"', fetch(f"{base}/montguides/{slug}"))
        except Exception:
            pdf = None
    if not pdf:
        return None
    return title, (sku.group(1) if sku else ""), urllib.parse.urljoin(base, pdf.group(1))


# ---------------------------------------------------------------- MSU pests & problems guide (one page per pest)
PESTS_BASE = "https://www.montana.edu/extension/Full_HTML_Pubs/a-guide-to-pests-problems-and-identification-of-ornamental-shrubs-and-trees-in-montana/"


def pests_index():
    """-> pages [(section, slug, title)], hosts {GENUS: [(pest title, slug)]}"""
    s = BeautifulSoup(fetch(PESTS_BASE), "html.parser")
    pages = []
    for a in s.select("a[href]"):
        m = re.search(r"/(abiotic-issues|diseases|insects|plant-id)/([\w-]+)\.html$", urllib.parse.urljoin(PESTS_BASE, a["href"]))
        if m and m.group(2) != "index" and (m.group(1), m.group(2)) not in [(p[0], p[1]) for p in pages]:
            pages.append((m.group(1), m.group(2), clean_text(a.get_text(" ", strip=True))))
    hs = BeautifulSoup(fetch(PESTS_BASE + "pests-listed-by-host.html"), "html.parser")
    body = hs.select_one("#rightpane") or hs
    hosts, cur = {}, None
    for el in body.find_all(["p", "h2", "h3", "h4", "li", "a", "strong"]):
        tx = clean_text(el.get_text(" ", strip=True))
        m = re.fullmatch(r"\(([A-Z][a-z]+)\)", tx)
        if m:
            cur = m.group(1); hosts.setdefault(cur, []); continue
        if cur and el.name == "a" and el.get("href"):
            m2 = re.search(r"/(diseases|insects|abiotic-issues)/([\w-]+)\.html", urllib.parse.urljoin(PESTS_BASE, el["href"]))
            if m2 and (tx, m2.group(2)) not in hosts[cur]:
                hosts[cur].append((tx, m2.group(2)))
    return pages, hosts


# ---------------------------------------------------------------- facts from free text (Wikipedia / Field Guide / documents)
MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"


def sentences(text, pattern, n=3, maxlen=400):
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)|\[([^\]]+)\]\([^)]*\)", r"\1", text)
    out = []
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])|\n+", text):
        s = re.sub(r"\s+", " ", s).strip(" -*#>|")
        if 25 < len(s) < maxlen and re.search(pattern, s, re.I) and s not in out:
            out.append(s)
            if len(out) >= n:
                break
    return out


def op_index(fruit):
    """All Orange Pippin variety paths for a fruit ('apples', 'pears', 'plums', 'cherries') from its A-Z pages."""
    out = {}
    for letter in "abcdefghijklmnopqrstuvwxyz":
        try:
            h = fetch(f"https://www.orangepippin.com/varieties/{fruit}/{letter}")
        except Exception:
            continue
        for slug in re.findall(r'href="(?:(?:\.\./)+varieties/|/varieties/|https://www\.orangepippin\.com/varieties/)' + fruit + r'/([a-z0-9-]{2,})"', h):
            out[f"{fruit}/{slug}"] = slug.replace("-", " ")
    return out


def commons_search(query, dest_dir, n=4, start=1, must=(), plant_words=()):
    """Fallback photos: Wikimedia Commons file search. STRICT: a file is used only if its file name contains every
    word in `must` (the variety name) AND one of `plant_words` (apple/Malus/crab...) - a name-only search found
    birds for 'Chestnut' and a cat for 'Goodland'. No photo is better than a wrong one."""
    api = ("https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrlimit=30"
           f"&gsrsearch={urllib.parse.quote(query)}&prop=imageinfo&iiprop=url|extmetadata|mime&iiurlwidth=1024&format=json")
    data = json.loads(fetch(api))
    out = []
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp") or not ii.get("thumburl"):
            continue
        fname = re.sub(r"[_\-.]+", " ", pg.get("title", "")).lower()
        if any(w.lower() not in fname for w in must) or (plant_words and not any(w.lower() in fname for w in plant_words)):
            continue
        md = ii.get("extmetadata", {})
        g = lambda k: clean_text(re.sub(r"<[^>]+>", "", _html.unescape((md.get(k) or {}).get("value", ""))))
        name = f"commons_{start + len(out):02d}{ext_of(ii['thumburl'].split('?')[0])}"
        try:
            save_bin(ii["thumburl"].split("?")[0], os.path.join(dest_dir, name))
        except Exception as e:
            print("  commons failed", e); continue
        out.append({"file": name, "source": "Wikimedia Commons", "attribution": g("Artist") or "unknown author",
                    "license": g("LicenseShortName"), "page": ii.get("descriptionurl")})
        if len(out) >= n:
            break
    return out


def commons_category(variety, plant_words, genus=""):
    """Find the Wikimedia Commons CATEGORY for a variety (e.g. "Dolgo (apple)", "Haralson apple"). Categories are
    curated by people, so their photos really are that variety. STRICT: the category must contain the variety name
    together with a fruit/plant word right after it or in brackets ("Haralson apple", "Frontenac (grape)"), or the
    Latin genus - 'John Adams Elder' (a person) and 'Will Redmond' must not match. Returns the name or None."""
    if not plant_words and not genus:
        return None
    api = ("https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=14&srlimit=20&format=json"
           f"&srsearch={urllib.parse.quote(variety + ' ' + (plant_words[0] if plant_words else genus))}")
    v = re.escape(variety.lower())
    pw = "|".join(re.escape(w.lower()) for w in plant_words) or "zzzz"
    for hit in json.loads(fetch(api)).get("query", {}).get("search", []):
        title = hit["title"].split(":", 1)[-1]
        low = title.lower()
        if re.search(r"\s(in|at|from|by)\s", low):   # 'X in Ruhland', 'X by photographer' - places/people, not the plant
            continue
        if re.search(rf"\b{v}\b\s+(?:{pw})\w*\b|\b{v}\b\s*\((?:[^)]*\b)?(?:{pw})\w*\b[^)]*\)", low) or                 (genus and re.search(rf"\b{re.escape(genus.lower())}\b.*\b{v}\b", low)):
            return title
    return None


# ---------------------------------------------------------------- the user's own type choices (Library Manager "Change type...")
TYPE_OVERRIDES_FILE = os.path.join(W, "type_overrides.json")   # {"local-area/plants/x.md": "Trees - Shade & ornamental"}


def type_overrides():
    try:
        return json.load(open(TYPE_OVERRIDES_FILE, encoding="utf-8"))
    except Exception:
        return {}
