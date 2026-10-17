"""Add web pages (any site: CDC, Ready.gov, extension services, home-preservation guides...) to the library as
clean text pages - just the article, without the site's menus, ads and footers.

Each page is fetched from the live site; if that fails (blocked, moved, gone) the Internet Archive's latest good
capture is used instead. Pages already in the library (same address) are skipped.

Usage:
  68_add_web_page.py [--check] --file list.txt     lines: URL|CODE[|title][|publisher]   (CODE from common.CODES)
  68_add_web_page.py [--check] --category CODE URL [URL ...]
--check prints the title, word count and opening text without writing. Run 20_catalog.py + 21_readme.py afterwards."""
import json, os, re, sys, time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ResearchLibrary/1.0 (personal offline archive)"}
DROP_TEXT = re.compile(r"^(Skip directly to|Skip to main content|An official website|Here's how you know|Official websites use|"
                       r"Secure \.gov|Share sensitive|On This Page|Breadcrumb|Print|Share|Facebook|Twitter|LinkedIn|Email|"
                       r"Sources|Content Source)", re.I)
GOV = re.compile(r"\.(gov|mil)$", re.I)


def get(url, **kw):
    """requests.get with backoff - the Internet Archive refuses connections when hit too fast."""
    for wait in (0, 20, 60, 120):
        time.sleep(wait)
        try:
            r = requests.get(url, headers=H, timeout=90, **kw)
            if r.status_code not in (429, 503):
                return r
        except requests.RequestException:
            pass
    return None


def capture(url):
    """(timestamp, html, final url) of the Internet Archive's latest 200 capture, following meta-refresh redirects."""
    for _ in range(4):
        r = get("https://web.archive.org/cdx/search/cdx",
                params={"url": url, "filter": "statuscode:200", "output": "json", "limit": -1, "fl": "timestamp"})
        rows = r.json()[1:] if r is not None and r.ok and r.text.strip() else []
        if not rows:
            return None, None, url
        html = ts = None
        for (t,) in reversed(rows[-6:]):       # newest first; skip captures of Wayback's own pages
            time.sleep(3)
            h = get(f"https://web.archive.org/web/{t}id_/{url}")
            h = h.text if h is not None else ""
            if h and "Wayback Machine" not in (BeautifulSoup(h, "html.parser").title or BeautifulSoup("", "html.parser")).get_text():
                html, ts = h, t
                break
        if html is None:
            return None, None, url
        m = re.search(r'http-equiv="refresh"\s+content="\d+;\s*url=([^"]+)"', html, re.I)
        if m and len(html) < 3000:
            url = urljoin(url, m.group(1))
            time.sleep(2)
            continue
        return ts, html, url
    return None, None, url


def _text_len(el):
    return len(el.get_text(" ", strip=True))


def _link_heavy(el):
    """A menu / sidebar / 'related pages' block: most of its text is links."""
    total = _text_len(el)
    return total > 0 and sum(_text_len(a) for a in el.find_all("a")) / total > 0.6


def extract(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s.select("script, style, nav, footer, header, aside, form, button, noscript, iframe, svg, .breadcrumb, "
                      ".usa-breadcrumb, [role=navigation], [role=complementary], .sidebar, #sidebar, .cdc-page-title-bar, "
                      ".dfe-section__nav, .dfe-block--keep_reading, .page-share, .share, .social"):
        t.decompose()
    for t in s.find_all(["ul", "ol", "div", "section", "table"]):
        if t.parent is not None and _link_heavy(t):
            t.decompose()
    # the article: the page's own main/article block if it holds most of the paragraph text,
    # else the smallest block around the longest paragraph that does
    ptext = lambda el: sum(_text_len(p) for p in el.find_all("p"))
    total = ptext(s) or 1
    # (a page's own <main>/<article> wins whenever it holds real text - side boxes outside it can outweigh it)
    arts = sorted(s.find_all("article"), key=_text_len, reverse=True)[:1]
    main = next((c for c in [s.find("main"), *arts, s.find(id="content"), s.find(id="main-content")]
                 if c is not None and (_text_len(c) >= 1500 or ptext(c) >= 0.5 * total)), None)
    if main is None:
        longest = max(s.find_all("p"), key=_text_len, default=None)
        main = longest.parent if longest is not None else (s.body or s)
        while main.parent is not None and ptext(main) < 0.6 * total:
            main = main.parent
    h1 = main.find("h1") or s.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    # the browser-tab title minus the site name ("Freezing Apples | National Center ..."), when it says more
    tab = re.split(r"\s+[|–—-]\s+", s.title.get_text(" ", strip=True))[0].strip() if s.title else ""
    heads = {h.get_text(" ", strip=True).lower() for h in main.find_all(["h1", "h2", "h3"])}
    if tab and (not title or tab.lower() in heads or (title.lower() in tab.lower() and len(tab) > len(title))):
        title = tab
    if main.find("h1"):
        main.find("h1").decompose()
    md = markdownify(str(main), heading_style="ATX", strip=["img", "a"])
    lines = [l.rstrip() for l in md.splitlines() if not DROP_TEXT.match(l.strip("#* ").strip())]
    md = re.sub(r"\*{4,}", "**", "\n".join(lines))   # bold inside bold
    return title, re.sub(r"\n{3,}", "\n\n", md).strip()


def fetch(url):
    """(title, markdown, final url, where it came from) - live site first, Internet Archive as the fallback."""
    r = get(url)
    if r is not None and r.ok and "html" in r.headers.get("Content-Type", ""):
        title, md = extract(r.content)   # bytes: the page's own charset decides the encoding
        if len(md.split()) >= 80:
            return title, md, r.url, f"{r.url} (fetched {TODAY})"
    ts, html, final = capture(url)
    if not html:
        return None, None, url, None
    title, md = extract(html)
    return title, md, final, f"Internet Archive capture https://web.archive.org/web/{ts}/{final}"


def in_library():
    f = os.path.join(RESEARCH, "CATALOG.json")
    return {r.get("source_url") for r in json.load(open(f, encoding="utf-8"))} if os.path.exists(f) else set()


def add_pages(items, check=False):
    """items: dicts with url, category (folder) and optional title, publisher, license. Returns how many were added."""
    have, reg, added = in_library(), (None if check else SlugRegistry()), 0
    for it in items:
        url = it["url"]
        if url in have:
            print(f"already in library: {url}")
            continue
        title, md, final, came_from = fetch(url)
        if not md:
            print(f"could not get: {url}")
            continue
        title = it.get("title") or title or urlparse(final).path.strip("/").split("/")[-1] or final
        host = urlparse(final).netloc.lower().removeprefix("www.")
        publisher = it.get("publisher") or host
        license = it.get("license") or ("Government publication - check the source page for terms" if GOV.search(host) else
                                        "Copyright of the original site - personal offline copy, see the source page")
        words = len(md.split())
        if check:
            print(f"{url} -> {final}\n    {title} [{it['category']}] {words} words: {' '.join(md.split())[:200]}")
            continue
        slug = reg.claim(slugify(f"{host.split('.')[0]}-{title}")[:100], "web:" + final)
        meta = {"title": title, "category": it["category"], "source_type": "web-page", "publisher": publisher,
                "source_url": final, "license": license, "retrieved_from": came_from,
                "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
        head = f"# {title}\n\n**Source:** {publisher} - <{final}>  \n**License:** {license}\n"
        open(os.path.join(cat_dir(it["category"]), slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + "\n" + md + "\n")
        have.add(final); have.add(url); added += 1
        print(f"added: {it['category']}/{slug}.md ({words} words)", flush=True)
        if added % 25 == 0:
            reg.save()
        time.sleep(1)
    if reg:
        reg.save()
    return added


def main():
    args = sys.argv[1:]
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    items = []
    if "--file" in args:
        for line in open(args[args.index("--file") + 1], encoding="utf-8"):
            if line.strip() and not line.startswith("#"):
                p = line.strip().split("|") + ["", ""]
                items.append({"url": p[0], "category": CODES[p[1]], "title": p[2], "publisher": p[3]})
    elif "--category" in args:
        i = args.index("--category")
        items = [{"url": u, "category": CODES[args[i + 1]]} for a, u in enumerate(args) if a not in (i, i + 1)]
    else:
        sys.exit(__doc__)
    add_pages(items, check)


if __name__ == "__main__":
    main()
