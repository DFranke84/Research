"""Add US-government web pages (CDC, DOE Energy Saver, ...) to the library, in the same format as the other web-page entries.

The live sites often block scripts or have moved pages, so each page is taken from the Internet Archive's
latest good capture (CDX API, statuscode 200; meta-refresh redirects followed).

Usage:
  68_add_gov_page.py [--check] --file list.txt     lines: URL|CODE|publisher-key[|title override]
  publisher keys: cdc, doe
--check prints the title, word count and opening text without writing. Run 20_catalog.py + 21_readme.py afterwards."""
import json, os, re, sys, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry

PUBLISHERS = {"cdc": "US Centers for Disease Control and Prevention (CDC)",
              "doe": "US Department of Energy - Energy Saver"}
H = {"User-Agent": "ResearchLibrary/1.0 (personal offline archive)"}
DROP_TEXT = re.compile(r"^(Skip directly to|An official website|Here's how you know|Official websites use|Secure \.gov|Share sensitive|"
                       r"On This Page|Breadcrumb|Print|Share|Facebook|Twitter|LinkedIn|Email|Sources|Content Source)", re.I)


def get(url, **kw):
    """requests.get with backoff - the Internet Archive refuses connections when hit too fast."""
    for wait in (0, 20, 60, 120):
        time.sleep(wait)
        try:
            r = requests.get(url, headers=H, timeout=90, **kw)
            if r.status_code not in (429, 503):
                return r
        except requests.ConnectionError:
            pass
    raise SystemExit(f"Internet Archive unreachable: {url}")


def capture(url):
    """Return (timestamp, html) of the latest 200 capture, following meta-refresh redirects."""
    for _ in range(4):
        r = get("https://web.archive.org/cdx/search/cdx",
                         params={"url": url, "filter": "statuscode:200", "output": "json", "limit": -1, "fl": "timestamp"})
        rows = r.json()[1:] if r.ok else []
        if not rows:
            return None, None, url
        html = ts = None
        for (t,) in reversed(rows[-6:]):       # newest first; skip captures of Wayback's own pages
            time.sleep(3)
            h = get(f"https://web.archive.org/web/{t}id_/{url}").text
            if "Wayback Machine" not in (BeautifulSoup(h, "html.parser").title or BeautifulSoup("", "html.parser")).get_text():
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


def extract(html):
    s = BeautifulSoup(html, "html.parser")
    title = (s.find("h1").get_text(" ", strip=True) if s.find("h1") else (s.title.string or "").strip())
    main = s.find("main") or s.find(id="content") or s.body
    for t in main.select("script, style, nav, footer, form, button, noscript, iframe, svg, .breadcrumb, "
                         ".usa-breadcrumb, "
                         "[role=navigation], .cdc-page-title-bar, .dfe-section__nav, .dfe-block--keep_reading, .page-share"):
        t.decompose()
    if main.find("h1"):
        main.find("h1").decompose()
    md = markdownify(str(main), heading_style="ATX", strip=["img", "a"])
    lines = []
    for l in md.splitlines():
        l = l.rstrip()
        if DROP_TEXT.match(l.strip("#* ").strip()):
            continue
        lines.append(l)
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return title, md


def main():
    args = sys.argv[1:]
    check = "--check" in args
    lines = [l.strip() for l in open(args[args.index("--file") + 1], encoding="utf-8") if l.strip() and not l.startswith("#")]
    reg = None if check else SlugRegistry()
    for line in lines:
        parts = line.split("|")
        url, code, pub = parts[0], parts[1], parts[2]
        ts, html, final = capture(url)
        if not html:
            print(f"no capture: {url}")
            continue
        title, md = extract(html)
        if len(parts) > 3 and parts[3]:
            title = parts[3]
        title = re.sub(r"\s*\|\s*(CDC|Department of Energy)\s*$", "", title)
        words = len(md.split())
        if check:
            print(f"{url} -> {final} @{ts}\n    {title} [{CODES[code]}] {words} words: {' '.join(md.split())[:200]}")
            continue
        category = CODES[code]
        slug = reg.claim(slugify(f"{pub}-{title}"), "web:" + final)
        meta = {"title": title, "category": category, "source_type": "web-page", "publisher": PUBLISHERS[pub],
                "source_url": final, "license": "Public Domain (US Govt work)",
                "retrieved_from": f"Internet Archive capture https://web.archive.org/web/{ts}/{final}",
                "provenance": f"listed in AIPortable library.db as {url} (no text kept there); fetched {TODAY} from the Internet Archive",
                "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
        head = f"# {title}\n\n**Source:** {PUBLISHERS[pub]} - <{final}>  \n**License:** Public Domain (US Govt work)\n"
        open(os.path.join(cat_dir(category), slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + "\n" + md + "\n")
        print(f"added: {category}/{slug}.md ({words} words)", flush=True)
        time.sleep(2)
    if reg:
        reg.save()


main()
