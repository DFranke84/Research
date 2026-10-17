"""Stack Exchange Q&A from the Kiwix archives.

  index  <site>   : index every question (title, score, tags, answer count, accepted?) -> _work/se_<site>_index.json
  build  <site>   : build the selected questions (_work/se_<site>_select.json, list of question paths + category)
                    into Markdown: question + accepted answer + up to 2 more top-scored answers, with authors credited.
Sites: diy gardening mechanics bicycles cooking outdoors woodworking pets ham homebrew sustainability crafts lifehacks
"""
import json, os, re, sys
from bs4 import BeautifulSoup
from libzim.reader import Archive
from markdownify import markdownify
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry
from archives import need

W = os.path.join(RESEARCH, "_work")
LICENSE = "CC BY-SA 4.0 (Stack Exchange contributors; see each post's author credit)"


def archive(site):
    """The newest copy of the site's archive in _sources\\zim."""
    return Archive(need("se-" + site))


def index(site):
    z = archive(site)
    out = []
    for i in range(z.entry_count):
        e = z._get_entry_by_id(i)
        if e.is_redirect or not re.match(r"questions/\d+/", e.path):
            continue
        html = bytes(e.get_item().content).decode("utf-8", "replace")
        m = re.search(r'itemprop="upvoteCount"[^>]*data-value="(-?\d+)"', html) or re.search(r'js-vote-count[^>]*>\s*(-?\d+)', html)
        score = int(m.group(1)) if m else 0
        tags = re.findall(r'class="post-tag[^"]*"[^>]*>([^<]+)<', html)
        answers = len(re.findall(r'class="answer[ "]', html))
        accepted = "accepted-answer" in html
        out.append([e.path, e.title, score, sorted(set(tags)), answers, accepted])
        if len(out) % 5000 == 0:
            print(site, len(out), flush=True)
    json.dump(out, open(os.path.join(W, f"se_{site}_index.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(site, "indexed", len(out))


def post_md(el):
    body = el.select_one(".js-post-body, .s-prose")
    if body is None:
        return ""
    for t in body.select("script, style, .snippet-code, .js-post-menu"):
        t.decompose()
    md = markdownify(str(body), heading_style="ATX", strip=["a", "img"])
    md = re.sub(r"(?m)^#", "####", md)             # keep post-internal headings below the answer headings
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def author(el):
    """Name of the post's author: the user card whose time reads 'asked'/'answered' (an edited post also carries
    an 'edited' card for the editor)."""
    sigs = el.select(".post-signature")
    for sig in sigs:
        t = sig.select_one(".s-user-card--time")
        if t and re.match(r"\s*(asked|answered)", t.get_text()):
            link = sig.select_one(".s-user-card--link")
            if link and link.get_text(strip=True):
                return link.get_text(strip=True)
    for sig in reversed(sigs):
        link = sig.select_one(".s-user-card--link")
        if link and link.get_text(strip=True):
            return link.get_text(strip=True)
    return "a deleted/anonymous user"


def build(site, sel=None):
    """sel: the questions to build (default: _work/se_<site>_select.json) - Build Starter Library passes a pack's items."""
    z = archive(site)
    if sel is None:
        sel = json.load(open(os.path.join(W, f"se_{site}_select.json"), encoding="utf-8"))
    os.makedirs(W, exist_ok=True)
    bf = os.path.join(W, f"built_se_{site}.json")
    built = json.load(open(bf, encoding="utf-8")) if os.path.exists(bf) else []
    done = {b["key"] for b in built}
    reg = SlugRegistry()
    for s in sel:
        p, cat = s["path"], s["category"]
        if p in done:
            continue
        soup = BeautifulSoup(bytes(z.get_entry_by_path(p).get_item().content).decode("utf-8", "replace"), "lxml")
        q = soup.select_one(".question")
        if q is None:
            continue
        title = soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else p
        tags = sorted({t.get_text(strip=True) for t in q.select(".post-tag")})
        qscore = q.select_one(".js-vote-count")
        answers = []
        for a in soup.select(".answer"):
            sc = a.select_one(".js-vote-count")
            answers.append((("accepted-answer" in a.get("class", [])), int(sc.get_text(strip=True) or 0) if sc else 0, a))
        answers.sort(key=lambda x: (not x[0], -x[1]))
        keep = [a for a in answers if a[0] or a[1] >= 2][:3]
        if not keep:
            continue
        url = f"https://{site}.stackexchange.com/{p}"
        parts = [f"## Question\n\n*Score {qscore.get_text(strip=True) if qscore else '?'} - asked by {author(q)}*\n\n{post_md(q)}"]
        for acc, sc, a in keep:
            parts.append(f"## {'Accepted answer' if acc else 'Answer'} (score {sc}) - by {author(a)}\n\n{post_md(a)}")
        text = "\n\n".join(parts)
        slug = reg.claim(slugify(f"{site} {title}")[:100], f"se-{site}:{p}")
        meta = {"title": f"{title} ({site}.stackexchange)", "category": cat, "source_type": "q-and-a",
                "publisher": f"Stack Exchange - {site}.stackexchange.com", "source_url": url,
                "retrieved_from": f"Kiwix ZIM {os.path.basename(z.filename)}",
                "license": LICENSE, "tags": tags, "answers_included": len(keep), "words": len(text.split()), "compiled": TODAY}
        head = f"# {title}\n\n**Source:** {site}.stackexchange.com - <{url}>  \n**License:** {LICENSE}\n\n"
        open(os.path.join(cat_dir(cat), slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + text + "\n")
        built.append({"key": p, "slug": slug, "category": cat, "title": title})
        if len(built) % 200 == 0:
            json.dump(built, open(bf, "w", encoding="utf-8"), ensure_ascii=False); reg.save()
            print(site, len(built), flush=True)
    json.dump(built, open(bf, "w", encoding="utf-8"), ensure_ascii=False)
    reg.save()
    print(site, "built", len(built))


if __name__ == "__main__":
    {"index": index, "build": build}[sys.argv[1]](sys.argv[2])
