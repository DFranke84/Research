"""Make the Facebook "Saved > Food" items of the personal recipe collection available offline.

  - Link items  -> fetch the recipe web page: recipe .md (schema.org Recipe data when the site has it, else page text)
                   + a PDF print of the page (headless Chrome) in facebook-saved/web-recipes/
  - Video items -> download the video with yt-dlp (public videos only, no login) to facebook-saved/videos/
Then rewrites facebook-saved-food.md so every item links its local copy. Resumable: finished items are skipped.
Results are logged to facebook-saved/fetch_log.json.

  _scripts\\.venv\\Scripts\\python _scripts\\57_fetch_facebook_saved.py [--links] [--videos]   (default: both)
"""
import glob, json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import requests
from bs4 import BeautifulSoup
from common import RESEARCH, TODAY, front_matter, slugify, find_browser
import fb_saved

COLL = os.path.join(RESEARCH, "recipes", "personal-recipe-collection")
FB = os.path.join(COLL, "facebook-saved")
WEB, VID = os.path.join(FB, "web-recipes"), os.path.join(FB, "videos")
LOG = os.path.join(FB, "fetch_log.json")
CHROME = find_browser()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
PY = sys.executable


def recipe_from_jsonld(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                t = d.get("@type")
                if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
                    return d
                stack += d.get("@graph", []) if isinstance(d.get("@graph"), list) else []
            elif isinstance(d, list):
                stack += d
    return None


def steps(instr):
    out = []
    for x in instr if isinstance(instr, list) else [instr]:
        if isinstance(x, str):
            out.append(BeautifulSoup(x, "lxml").get_text(" ", strip=True))
        elif isinstance(x, dict):
            if x.get("@type") == "HowToSection":
                out.append(f"**{x.get('name', '')}**")
                out += steps(x.get("itemListElement", []))
            else:
                out.append(BeautifulSoup(x.get("text", ""), "lxml").get_text(" ", strip=True))
    return [s for s in out if s]


def recipe_md(r):
    val = lambda k: r.get(k) if not isinstance(r.get(k), list) else ", ".join(map(str, r.get(k)))
    lines = []
    if r.get("description"):
        lines += [BeautifulSoup(str(r["description"]), "lxml").get_text(" ", strip=True), ""]
    info = [f"**{k}:** {val(v)}" for k, v in (("Yield", "recipeYield"), ("Prep", "prepTime"), ("Cook", "cookTime"), ("Total", "totalTime")) if r.get(v)]
    if info:
        lines += ["  \n".join(info), ""]
    lines += ["## Ingredients", ""] + [f"- {BeautifulSoup(str(i), 'lxml').get_text(' ', strip=True)}" for i in r.get("recipeIngredient", [])] + [""]
    lines += ["## Instructions", ""] + [f"{n}. {s}" for n, s in enumerate(steps(r.get("recipeInstructions", [])), 1)]
    return "\n".join(lines)


def wayback(url):
    """Latest Internet Archive snapshot of url as a response-like object (raw page, no Wayback toolbar), or None."""
    def get(u, **kw):   # the archive rate-limits (HTTP 429): back off and retry
        for wait in (0, 10, 30, 60):
            time.sleep(wait)
            r = requests.get(u, timeout=90, headers={"User-Agent": UA}, **kw)
            if r.status_code != 429:
                return r
        return r
    try:
        bare = re.sub(r"^https?://(www\.)?", "", url).split("#")[0]
        r = get("http://web.archive.org/cdx/search/cdx", params={"url": bare, "limit": "-5", "filter": "statuscode:200",
                                                                 "fl": "timestamp,original"})
        rows = [l.split(" ", 1) for l in r.text.strip().splitlines() if re.match(r"^\d{14} https?://", l)]   # ignore error pages
        for ts, orig in reversed(rows):   # newest first
            snap = f"https://web.archive.org/web/{ts}/{orig}"
            p = get(f"https://web.archive.org/web/{ts}id_/{orig}")
            if p.status_code < 400 and len(p.text) > 3000:
                class R: pass
                out = R(); out.text, out.url, out.archived = p.text, url, snap
                return out
            time.sleep(3)
    except Exception:
        pass
    return None


def fetch_link(item, log):
    key = item["url"]
    if log.get(key, {}).get("status") == "ok":
        return
    slug = slugify(item["title"])[:80] or "recipe"
    rec = {"title": item["title"], "url": key}
    try:
        class R: pass
        try:
            resp = requests.get(key, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}")
        except Exception as first:
            resp = wayback(key)     # blocked, dead or removed pages: the Internet Archive's latest snapshot
            if resp is None:        # last resort: let a real (headless) browser load the live page
                try:
                    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-agent={UA}", "--virtual-time-budget=10000",
                                        "--dump-dom", key], capture_output=True, timeout=75)
                    dom = p.stdout.decode("utf-8", "replace")
                except subprocess.TimeoutExpired:
                    dom = ""
                if len(dom) < 5000 or re.search(r"Just a moment|Access denied|Attention Required|403 Forbidden", dom[:20000], re.I):
                    raise RuntimeError(f"{first}; no archived copy; live page blocked or hung")
                resp = R(); resp.text, resp.url = dom, key
        rec["final_url"] = resp.url
        soup = BeautifulSoup(resp.text, "lxml")
        r = recipe_from_jsonld(soup)
        if r:
            body, kind = recipe_md(r), "structured recipe"
        else:
            import importlib
            _, body = importlib.import_module("50_ingest_folder").strip_html(resp.text)
            body, kind = body[:60000], "page text (no structured recipe found)"
        if len(body.split()) < 30:
            raise RuntimeError("page has no usable recipe text (removed or blocked)")
        pdf = os.path.join(WEB, slug + ".pdf")
        archived = getattr(resp, "archived", None)
        target = re.sub(r"/web/(\d+)/", r"/web/\1id_/", archived, count=1) if archived else resp.url
        try:   # a page print is nice to have - never fail the recipe over it
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                            "--virtual-time-budget=10000", target], capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            pass
        has_pdf = os.path.exists(pdf) and os.path.getsize(pdf) > 5000
        if archived:
            kind += f"; from the Internet Archive snapshot {archived}"
        meta = {"title": item["title"], "category": "recipes", "source_type": "web-recipe", "file": slug + ".pdf" if has_pdf else None,
                "publisher": item["source"], "source_url": resp.url, "collection": "personal-recipe-collection",
                "provenance": f"Facebook Saved > Food link, page fetched {TODAY}",
                "license": "Copyright of the recipe site - personal offline copy, do not redistribute", "compiled": TODAY}
        md = [front_matter(meta), f"# {item['title']}\n", f"**Source:** <{resp.url}>  ", f"*Saved on Facebook from {item['source']}; content: {kind}.*  "]
        if has_pdf:
            md.append(f"**Page print (PDF):** [{slug}.pdf]({slug}.pdf)")
        md += ["", body.strip()]
        open(os.path.join(WEB, slug + ".md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
        rec.update(status="ok", md=f"web-recipes/{slug}.md", pdf=f"web-recipes/{slug}.pdf" if has_pdf else None, kind=kind)
    except Exception as e:
        rec.update(status="failed", error=f"{type(e).__name__}: {e}"[:200])
    log[key] = rec
    print(f"  {rec['status']:6} {item['title'][:60]}  {rec.get('kind') or rec.get('error', '')}", flush=True)


def fetch_video(item, log):
    key = item["url"]
    if log.get(key, {}).get("status") == "ok":
        return
    slug = slugify(item["title"])[:80] or "video"
    rec = {"title": item["title"], "url": key}
    out = os.path.join(VID, slug + ".%(ext)s")
    r = subprocess.run([PY, "-m", "yt_dlp", "-q", "--no-warnings", "--no-playlist", "-f", "best[ext=mp4]/best",
                        "-o", out, key], capture_output=True, text=True, timeout=900)
    got = glob.glob(os.path.join(VID, glob.escape(slug) + ".*"))
    got = [g for g in got if not g.endswith((".part", ".ytdl"))]
    if r.returncode == 0 and got:
        rec.update(status="ok", file=f"videos/{os.path.basename(got[0])}", mb=round(os.path.getsize(got[0]) / 1e6, 1))
    else:
        err = (r.stderr or r.stdout).strip().splitlines()
        rec.update(status="failed", error=(err[-1] if err else f"exit {r.returncode}")[:200])
    log[key] = rec
    print(f"  {rec['status']:6} {item['title'][:60]}  {rec.get('mb', '')}{'MB' if rec.get('mb') else rec.get('error', '')}", flush=True)


def rewrite_page(items, log):
    page = os.path.join(FB, "facebook-saved-food.md")
    head, _, _ = open(page, encoding="utf-8").read().partition("\n---\n")
    html = next(f for f in os.listdir(FB) if f.lower().endswith(".html"))
    from urllib.parse import quote
    L = lambda p: quote(p.replace(os.sep, "/"), safe="/")
    ok = lambda i: log.get(i["url"] or "", {}).get("status") == "ok"
    n_local = sum(1 for i in items if i["text"].strip() or ok(i))
    body = [f"# Facebook Saved Food Recipes\n",
            f"Part of [Personal Recipe Collection](../../personal-recipe-collection.md). {len(items)} items from the Facebook "
            f"\"Saved > Food\" collection; {n_local} are readable offline (recipe text in the post, a saved copy of the recipe page, "
            f"or a downloaded video). Items marked *online only* could not be saved. The original saved page: [{html}]({L(html)}).\n"]
    for kind in ("Post", "Link", "Video"):
        sel = sorted((i for i in items if i["kind"] == kind), key=lambda i: i["title"].lower())
        body.append(f"## {kind}s ({len(sel)})\n")
        for i in sel:
            e = log.get(i["url"] or "", {})
            local = []
            if e.get("status") == "ok" and e.get("md"):
                local.append(f"[offline recipe]({L(e['md'])})")
                if e.get("pdf"):
                    local.append(f"[page PDF]({L(e['pdf'])})")
            if e.get("status") == "ok" and e.get("file"):
                local.append(f"[video]({L(e['file'])})")
            tag = " - ".join(local) if local else ("" if i["text"].strip() else "*online only*")
            body.append(f"### {i['title']}\n")
            body.append(f"*Saved from {i['source']}*" + (f" - {tag}" if tag else "") + (f" - [original]({i['url']})" if i["url"] else "") + "\n")
            if i["text"].strip():
                body += ["```text", i["text"].strip(), "```\n"]
    head = re.sub(r"^compiled: .*$", f'compiled: "{TODAY}"\noffline_items: {n_local}', head, flags=re.M) if "offline_items" not in head else \
        re.sub(r"^offline_items: .*$", f"offline_items: {n_local}", head, flags=re.M)
    open(page, "w", encoding="utf-8").write(head + "\n---\n" + "\n".join(body).rstrip() + "\n")
    return n_local


def main():
    both = not ({"--links", "--videos"} & set(sys.argv))
    os.makedirs(WEB, exist_ok=True); os.makedirs(VID, exist_ok=True)
    items = fb_saved.parse(os.path.join(FB, next(f for f in os.listdir(FB) if f.lower().endswith(".html"))))
    log = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else {}
    if both or "--links" in sys.argv:
        links = [i for i in items if i["kind"] == "Link" and i["url"]]
        print(f"Fetching {len(links)} recipe pages", flush=True)
        for i in links:
            fetch_link(i, log); json.dump(log, open(LOG, "w", encoding="utf-8"), indent=1); time.sleep(1)
    if both or "--videos" in sys.argv:
        vids = [i for i in items if i["kind"] == "Video" and i["url"]]
        print(f"Downloading {len(vids)} videos", flush=True)
        for i in vids:
            fetch_video(i, log); json.dump(log, open(LOG, "w", encoding="utf-8"), indent=1)
    n = rewrite_page(items, log)
    st = {}
    for v in log.values():
        st[v["status"]] = st.get(v["status"], 0) + 1
    print("done:", st, f"- {n} of {len(items)} items now readable offline")


if __name__ == "__main__":
    main()
