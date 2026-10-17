"""Download the recipes behind browser bookmarks (chosen folders of a favorites export) into the personal recipe collection.

For every bookmark:
  video sites (YouTube, Facebook, Vimeo, TikTok) -> the video (<=720p, mp4) + a page with its title/description
  recipe web pages -> recipe .md (schema.org Recipe data, else page text), PDF print of the page, the recipe's main photo,
                      and the site's own recipe video when the page publishes one; dead/blocked pages fall back to the
                      Internet Archive (helpers from 57_fetch_facebook_saved.py)
Output: recipes/personal-recipe-collection/bookmarks/<folder>/ with a <folder>.md list page; log in bookmarks/fetch_log.json.
Resumable (finished links are skipped).

  _scripts\\.venv\\Scripts\\python _scripts\\58_fetch_bookmarks.py <favorites.html> "<folder>" ["<folder>" ...]
"""
import importlib, json, os, re, subprocess, sys, time
from urllib.parse import quote, urlparse
sys.path.insert(0, os.path.dirname(__file__))
import requests
from bs4 import BeautifulSoup
from common import RESEARCH, TODAY, front_matter, slugify
import bookmarks
import recipe_clean as rc

fb = importlib.import_module("57_fetch_facebook_saved")
ing = importlib.import_module("50_ingest_folder")
COLL = os.path.join(RESEARCH, "recipes", "personal-recipe-collection")
OUT = os.path.join(COLL, "bookmarks")
LOG = os.path.join(OUT, "fetch_log.json")
VIDEO_SITES = re.compile(r"(youtube\.com|youtu\.be|facebook\.com|fb\.watch|vimeo\.com|tiktok\.com|instagram\.com)", re.I)
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = None
FOLDER_SLUG = {"food recipes": "food-recipes", "food recipes - air fryer": "air-fryer", "food recipies - instantpot": "instant-pot", "facebook saved links": "facebook-links"}
L = lambda p: quote(p.replace(os.sep, "/"), safe="/")


def ytdlp(url, out_noext, max_h=720):
    fmt = f"bv*[height<={max_h}][ext=mp4]+ba[ext=m4a]/b[height<={max_h}][ext=mp4]/b[height<={max_h}]/b" if FFMPEG else "b[ext=mp4]/b"
    cmd = [fb.PY, "-m", "yt_dlp", "-q", "--no-warnings", "--no-playlist", "-f", fmt, "--merge-output-format", "mp4",
           "--write-info-json", "-o", out_noext + ".%(ext)s", url]
    if FFMPEG:
        cmd[3:3] = ["--ffmpeg-location", FFMPEG]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    d = os.path.dirname(out_noext); b = os.path.basename(out_noext)
    vids = [f for f in os.listdir(d) if f.startswith(b + ".") and f.rsplit(".", 1)[-1] in ("mp4", "webm", "mkv", "mov")]
    info = {}
    ij = out_noext + ".info.json"
    if os.path.exists(ij):
        try:
            info = json.load(open(ij, encoding="utf-8"))
        except Exception:
            pass
        os.remove(ij)
    err = (r.stderr or r.stdout).strip().splitlines()
    return (vids[0] if vids else None), info, (err[-1] if err else "")


def first_url(x):
    if isinstance(x, str): return x
    if isinstance(x, list) and x: return first_url(x[0])
    if isinstance(x, dict): return x.get("url") or x.get("contentUrl") or first_url(x.get("@list", []))
    return None


STOP = {"recipe", "recipes", "easy", "best", "the", "and", "with", "how", "make", "homemade", "video", "minute", "minutes", "from"}


def related(a, b):
    """True when two titles share a meaningful word (keeps a site's unrelated promo/ad video from being saved)."""
    w = lambda s: {x for x in re.findall(r"[a-z]{4,}", (s or "").lower()) if x not in STOP}
    return bool(w(a) & w(b))


def download_image(url, out_noext, archived=None):
    if not url or re.search(r"logo|icon|avatar|favicon|sprite|placeholder|default[-_]?image|gravatar", url, re.I):
        return None
    got = _download_image(url, out_noext)
    full = re.sub(r"-\d{2,4}x\d{2,4}(\.\w+)$", r"\1", url)   # WordPress thumbnail name-225x225.webp -> the full-size photo
    if not got and full != url:
        got = _download_image(full, out_noext)
    if not got and archived:   # photo gone from the live site: the archive's copy of it
        ts = re.search(r"/web/(\d{14})", archived)
        if ts:
            got = _download_image(f"https://web.archive.org/web/{ts.group(1)}im_/{url}", out_noext)
    return got


def _download_image(url, out_noext):
    try:
        r = requests.get(url, headers={"User-Agent": fb.UA}, timeout=60)
        ct = r.headers.get("content-type", "")
        if r.status_code >= 400 or not ct.startswith("image/") or len(r.content) < 10000:   # skip icons/thumbnails
            return None
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(ct.split(";")[0], ".jpg")
        open(out_noext + ext, "wb").write(r.content)
        return os.path.basename(out_noext + ext)
    except Exception:
        return None


def get_page(url):
    class R: pass
    try:
        r = requests.get(url, headers={"User-Agent": fb.UA}, timeout=30, allow_redirects=True)
        if r.status_code < 400 and len(r.text) > 3000:
            out = R(); out.text, out.url, out.archived = r.text, r.url, None
            return out, None
        first = f"HTTP {r.status_code}"
    except Exception as e:
        first = f"{type(e).__name__}"
    a = fb.wayback(url)
    if a is not None:
        return a, None
    try:
        p = subprocess.run([fb.CHROME, "--headless=new", "--disable-gpu", f"--user-agent={fb.UA}", "--virtual-time-budget=10000",
                            "--dump-dom", url], capture_output=True, timeout=75)
        dom = p.stdout.decode("utf-8", "replace")
        if len(dom) > 5000 and not re.search(r"Just a moment|Access denied|Attention Required|403 Forbidden", dom[:20000], re.I):
            out = R(); out.text, out.url, out.archived = dom, url, None
            return out, None
    except subprocess.TimeoutExpired:
        pass
    return None, f"{first}; no archived copy; live page blocked or hung"


def do_video(title, url, d, slug, meta_base):
    vid, info, err = ytdlp(url, os.path.join(d, slug))
    if not vid:
        return {"status": "failed", "error": err[:200] or "no video"}
    desc = (info.get("description") or "").strip()
    meta = {**meta_base, "title": info.get("title") or title, "source_type": "video", "file": vid,
            "publisher": info.get("uploader") or info.get("channel") or urlparse(url).netloc,
            "duration_min": round((info.get("duration") or 0) / 60, 1) or None}
    md = [front_matter(meta), f"# {meta['title']}\n", f"**Video:** [{vid}]({L(vid)})  ", f"**Source:** <{url}>\n"]
    if desc:
        md += ["## Description\n", desc]
    open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    return {"status": "ok", "type": "video", "md": slug + ".md", "video": vid,
            "mb": round(os.path.getsize(os.path.join(d, vid)) / 1e6, 1)}


CACHE = os.path.join(RESEARCH, "_work", "recipe_page_cache")


def cached_page(url, archive=False):
    """Fetch (live, else bot-safe browser) or the Internet Archive copy; raw pages are cached so re-processing never re-downloads."""
    import hashlib
    os.makedirs(CACHE, exist_ok=True)
    key = os.path.join(CACHE, hashlib.sha1(((("A|" if archive else "L|") + url)).encode()).hexdigest())
    class R: pass
    if os.path.exists(key + ".json"):
        m = json.load(open(key + ".json", encoding="utf-8"))
        if not m.get("ok"):
            return None, m.get("error")
        out = R(); out.text = open(key + ".html", encoding="utf-8").read(); out.url, out.archived = m["url"], m.get("archived")
        return out, None
    if archive:   # archive copies are indexed without tracking codes (fbclid, utm_*, ...)
        bare = re.sub(r"[?&](fbclid|utm_[a-z]+|ref|mibextid|epik|recipe_id|crlt\.pid|amp)=[^&#]*", "", url).rstrip("?&")
        resp, err = fb.wayback(bare), "no archived copy"
        if resp is None and bare != url:
            resp = fb.wayback(url)
        if resp is not None: err = None
    else:
        resp, err = get_page_live(url)
    if resp is None:
        if not archive:   # archive misses are not remembered: the archive is often briefly down (503) or rate-limiting
            json.dump({"ok": False, "error": err}, open(key + ".json", "w", encoding="utf-8"))
        return None, err
    open(key + ".html", "w", encoding="utf-8").write(resp.text)
    json.dump({"ok": True, "url": resp.url, "archived": resp.archived}, open(key + ".json", "w", encoding="utf-8"))
    return resp, None


def get_page_live(url):
    class R: pass
    try:
        r = requests.get(url, headers={"User-Agent": fb.UA}, timeout=30, allow_redirects=True)
        if r.status_code < 400 and len(r.text) > 3000:
            if not re.search(r"charset", r.headers.get("content-type", ""), re.I):   # undeclared: sniff (usually UTF-8)
                r.encoding = r.apparent_encoding or "utf-8"
            out = R(); out.text, out.url, out.archived = r.text, r.url, None
            return out, None
        first = f"HTTP {r.status_code}"
    except Exception as e:
        first = type(e).__name__
    try:
        p = subprocess.run([fb.CHROME, "--headless=new", "--disable-gpu", f"--user-agent={fb.UA}", "--virtual-time-budget=10000",
                            "--dump-dom", url], capture_output=True, timeout=75)
        dom = p.stdout.decode("utf-8", "replace")
        if len(dom) > 5000 and not re.search(r"Just a moment|Access denied|Attention Required|403 Forbidden", dom[:20000], re.I):
            out = R(); out.text, out.url, out.archived = dom, url, None
            return out, None
    except subprocess.TimeoutExpired:
        pass
    return None, f"{first}; live page blocked or hung"


SHORTENER = re.compile(r"^https?://(www\.)?(bit\.ly|tinyurl\.com|goo\.gl|ow\.ly|t\.co|buff\.ly|fb\.me|is\.gd|rebrand\.ly|"
                       r"shorturl\.at|cutt\.ly|tiny\.cc|lnkd\.in|trib\.al|dlvr\.it)/", re.I)


def unshorten(url):
    """bit.ly & co -> the real address (read from the redirect, so it works even when the destination site is down)."""
    for _ in range(5):
        if not SHORTENER.match(url):
            break
        try:
            r = requests.get(url, allow_redirects=False, timeout=30, headers={"User-Agent": fb.UA})
        except Exception:
            break
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            url = requests.compat.urljoin(url, r.headers["Location"])
        else:
            break
    return url


def do_page(title, url, d, slug, meta_base):
    url = unshorten(url)
    """Only the recipe: title, photo, yield/times, ingredients, steps -> .md + clean one-page PDF (+ matching recipe video)."""
    rec = None
    resp, err = cached_page(url)
    if resp is not None and not resp.archived:
        p0, p1 = urlparse(url).path.strip("/"), urlparse(resp.url).path.strip("/")
        if p0 and (not p1 or re.match(r"^(category|tag|recipes?|blog|search|home|index\.\w+)(/[^/]*)?$", p1, re.I)) and p1 != p0:
            err = f"link now leads to {resp.url} (the recipe was removed)"   # homepage/category redirect: use the archive
            resp = None
    if resp is not None:
        rec = rc.extract(resp.text)
        if rec is None or rec.get("article"):   # teaser/shop/video page: follow its "See Recipe" link to the full recipe
            for link in rc.recipe_links(resp.text, resp.url):
                r2page, _ = cached_page(link)
                r2 = rc.extract(r2page.text) if r2page is not None else None
                if r2 and not r2.get("article"):
                    resp, rec = r2page, r2
                    break
    if rec is None:   # removed, changed, blocked or no recognisable recipe: try the Internet Archive copy
        a, aerr = cached_page(url, archive=True)
        if a is not None:
            r2 = rc.extract(a.text)
            if r2:
                resp, rec = a, r2
    if rec is None:
        for old in [f for f in os.listdir(d) if (f.startswith(slug + ".") or f.startswith(slug + "-video.")) and f != slug + ".txt"]:
            os.remove(os.path.join(d, old))   # drop anything an earlier, looser attempt saved for this link
        why = err or ("link now leads to " + resp.url if resp is not None and resp.url.rstrip("/") != url.rstrip("/")
                      else "no recipe found on the page")
        return {"status": "failed", "error": f"{why}; no archived copy with the recipe"[:200]}
    title = rc.clean(rec.get("name") or title)   # also repairs mis-decoded text from the bookmark file
    for old in [f for f in os.listdir(d) if (f.startswith(slug + ".") or f.startswith(slug + "-video.")) and f != slug + ".txt"]:
        os.remove(os.path.join(d, old))   # replace any earlier attempt (your note, slug.txt, is kept)
    img = download_image(rec.get("image"), os.path.join(d, slug), resp.archived) if rec.get("image") else None
    vid, v = None, rec.get("video")
    def minutes(s):   # ISO-8601 "PT1H5M30S" -> 65
        h = re.search(r"(\d+)H", s or ""); m = re.search(r"(\d+)M", (s or "").split("T")[-1])
        return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    if isinstance(v, dict) and related(v.get("name") or v.get("description"), title) and minutes(v.get("duration")) <= 30:
        for cand in (v.get("contentUrl"), v.get("embedUrl")):
            if cand:
                vid, info, _ = ytdlp(cand, os.path.join(d, slug + "-video"))
                if vid and (info.get("duration") or 0) > 1800:   # longer than 30 min: not a recipe clip
                    os.remove(os.path.join(d, vid)); vid = None
                if vid: break
    src = re.sub(r"[?&](fbclid|utm_[a-z]+|ref|mibextid|epik|recipe_id)=[^&#]*", "", resp.url if not resp.archived else url).rstrip("?&")
    has_pdf = rc.to_pdf(rec, title, src, os.path.join(d, img) if img else None, os.path.join(d, slug + ".pdf"))
    kind = rec["method"] + (f"; from the Internet Archive snapshot {resp.archived}" if resp.archived else "")
    meta = {**meta_base, "title": title, "source_type": "web-recipe", "file": slug + ".pdf" if has_pdf else None,
            "publisher": urlparse(resp.url).netloc.replace("www.", ""), "source_url": url,
            "ingredients": len(rec["ingredients"]), "steps": len(rec["instructions"])}
    md = [front_matter(meta), f"# {title}\n", f"**Source:** <{src}>  ", f"*Extracted from: {kind}.*  "]
    if has_pdf: md.append(f"**Recipe PDF:** [{slug}.pdf]({L(slug + '.pdf')})  ")
    if vid: md.append(f"**Recipe video:** [{vid}]({L(vid)})  ")
    md.append("")
    if img: md += [f"![{title}]({L(img)})", ""]
    md.append(rc.to_markdown(rec))
    open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    return {"status": "ok", "type": "page", "md": slug + ".md", "pdf": slug + ".pdf" if has_pdf else None,
            "image": img, "video": vid, "kind": kind, "title": title}


def folder_page(name, fslug, links, log):
    d = os.path.join(OUT, fslug)
    rows = {"ok": [], "failed": []}
    for sub, title, url, _ in links:
        e = log.get(url, {})
        rows["ok" if e.get("status") == "ok" else "failed"].append((title, url, e))
    body = [f"# Bookmarked recipes: {name}\n",
            f"Part of [Personal Recipe Collection](../../../personal-recipe-collection.md). {len(links)} bookmarks from the browser "
            f"folder \"{name}\"; {len(rows['ok'])} saved offline (recipe, clean PDF, photo and any recipe video).\n",
            f"## Saved offline ({len(rows['ok'])})\n"]
    for title, url, e in sorted(rows["ok"], key=lambda x: (x[2].get("title") or x[0]).lower()):
        extra = []
        if e.get("pdf"): extra.append(f"[PDF]({L(e['pdf'])})")
        if e.get("video"): extra.append(f"[video]({L(e['video'])})")
        body.append(f"- [{e.get('title') or title}]({L(e['md'])})" + (" - " + ", ".join(extra) if extra else "")
                    + (f" *({'added' if e.get('date_source') == 'added by link' else 'bookmarked'} {e['date_added']})*" if e.get("date_added") else ""))
    body += ["", f"## Online only - could not be saved ({len(rows['failed'])})\n"]
    for title, url, e in sorted(rows["failed"], key=lambda x: x[0].lower()):
        body.append(f"- [{title or url}]({url}) - {e.get('error', 'not attempted')[:90]}")
    meta = {"title": f"Bookmarked Recipes - {name}", "category": "recipes", "source_type": "bookmark-collection",
            "publisher": "Personal collection", "source_url": None, "collection": "personal-recipe-collection",
            "provenance": f"Browser bookmarks folder \"{name}\" (favorites export), pages fetched {TODAY}",
            "license": "Recipes copyright their sites - personal offline copies, do not redistribute",
            "bookmarks": len(links), "saved": len(rows["ok"]), "compiled": TODAY}
    open(os.path.join(d, fslug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + "\n".join(body) + "\n")
    return len(rows["ok"])


def main():
    fbmode = "--facebook" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--facebook", "--rerender")]
    fav, names = args[0], args[1:]
    folders = bookmarks.folder_links(fav, names) if names else {}
    if fbmode:   # the recipe-site links saved on Facebook get the same clean treatment
        import fb_saved
        fbdir = os.path.join(COLL, "facebook-saved")
        page = os.path.join(fbdir, next(f for f in os.listdir(fbdir) if f.lower().endswith(".html")))
        folders["Facebook Saved Links"] = [("", i["title"], i["url"], None) for i in fb_saved.parse(page) if i["kind"] == "Link" and i["url"]]
    os.makedirs(OUT, exist_ok=True)
    log = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else {}
    for name, links in folders.items():
        fslug = FOLDER_SLUG.get(name.lower(), slugify(name))
        d = os.path.join(OUT, fslug); os.makedirs(d, exist_ok=True)
        print(f"== {name}: {len(links)} bookmarks", flush=True)
        # file names already owned by saved recipes in this folder: a different bookmark must never reuse (and delete) them
        used = {os.path.splitext(e["md"])[0] for e in log.values() if e.get("status") == "ok" and e.get("folder") == fslug and e.get("md")}
        for n, (sub, title, url, added) in enumerate(links, 1):
            if not url or not url.startswith("http"):
                continue
            done = log.get(url, {})
            if done.get("status") == "ok" and "--rerender" in sys.argv and done.get("type") == "page":
                pass   # re-render every saved recipe from the page cache (no re-download)
            elif done.get("status") == "ok" and not (done.get("kind") or "").startswith("recipe text from the post"):
                mdp = os.path.join(d, done.get("md") or "")
                head = open(mdp, encoding="utf-8").read(1500) if os.path.isfile(mdp) else ""
                if not re.search(r"^steps: 0$", head, re.M) and (done.get("image") or done.get("type") != "page"):
                    continue   # re-checked: weaker "post text" captures, recipes saved without steps or without a photo
            if done.get("md"):   # re-processing a saved recipe: keep its own file name
                slug = os.path.splitext(done["md"])[0]
            else:
                slug = slugify(title or urlparse(url).path)[:70] or f"recipe-{n}"
                while slug in used: slug += "-2"
            used.add(slug)
            meta_base = {"category": "recipes", "collection": "personal-recipe-collection", "bookmark_folder": name,
                         "source_url": url, "provenance": f"Browser bookmark \"{title}\" in \"{name}\", fetched {TODAY}",
                         "license": "Copyright of the original site/creator - personal offline copy, do not redistribute",
                         "compiled": TODAY}
            try:
                rec = (do_video if VIDEO_SITES.search(urlparse(url).netloc) else do_page)(title, url, d, slug, meta_base)
            except Exception as e:
                rec = {"status": "failed", "error": f"{type(e).__name__}: {e}"[:200]}
            rec.setdefault("title", title); rec["folder"] = fslug
            log[url] = rec
            json.dump(log, open(LOG, "w", encoding="utf-8"), indent=1)
            print(f"  [{n}/{len(links)}] {rec['status']:6} {title[:55]}  {rec.get('error', '') or rec.get('type', '')}", flush=True)
            time.sleep(1)
        ok = folder_page(name, fslug, links, log)
        print(f"   {name}: {ok}/{len(links)} saved", flush=True)
    if fbmode:   # point the Facebook page's link items at these clean copies and drop the old full-page prints
        flog_p = os.path.join(COLL, "facebook-saved", "fetch_log.json")
        flog = json.load(open(flog_p, encoding="utf-8")) if os.path.exists(flog_p) else {}
        for _, t, u, _ in folders["Facebook Saved Links"]:
            e = log.get(u, {})
            flog[u] = ({"status": "ok", "title": t, "url": u, "kind": e.get("kind"),
                        "md": "../bookmarks/facebook-links/" + e["md"],
                        "pdf": ("../bookmarks/facebook-links/" + e["pdf"]) if e.get("pdf") else None}
                       if e.get("status") == "ok" else {"status": "failed", "title": t, "url": u, "error": e.get("error")})
        json.dump(flog, open(flog_p, "w", encoding="utf-8"), indent=1)
        import shutil, fb_saved
        shutil.rmtree(os.path.join(COLL, "facebook-saved", "web-recipes"), ignore_errors=True)
        fbdir = os.path.join(COLL, "facebook-saved")
        fb.rewrite_page(fb_saved.parse(os.path.join(fbdir, next(f for f in os.listdir(fbdir) if f.lower().endswith(".html")))), flog)
    st = {}
    for v in log.values(): st[v["status"]] = st.get(v["status"], 0) + 1
    print("done:", st)


if __name__ == "__main__":
    main()
