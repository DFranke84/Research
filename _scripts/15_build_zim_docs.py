"""Build library files from the additional Kiwix archives in _sources/zim.

Selections are made per source by 16_select_<source>.py (or by hand) and saved as
_work/zimsel_<source>.json: a list of documents
    {"key": unique id, "title": str, "category": folder, "paths": [ZIM entry paths, in order],
     "source_url": str, "extra": {optional front-matter fields}}
This script converts each document's pages to Markdown (with images), and writes
<category>/<slug>.md (+ <slug>_images/). Resumable via _work/built_zim_<source>.json.

Usage: 15_build_zim_docs.py <source>      e.g.  15_build_zim_docs.py nhs
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from libzim.reader import Archive
from common import RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry
from zimlib import article_md, save_article_images

W = os.path.join(RESEARCH, "_work")
Z = os.path.join(RESEARCH, "_sources", "zim")

# Per-source settings. root/drop are CSS selectors for the page's main content and junk to strip.
SOURCES = {
    "nhs": dict(zim="nhs.uk_en_medicines_2026-09b.zim", source_type="web-page", publisher="NHS (UK National Health Service)",
                license="Open Government Licence v3.0 (Crown copyright)", root="main",
                drop=[".nhsuk-breadcrumb", ".nhsuk-review-date", ".nhsuk-related-nav", ".nhsuk-contents-list",
                      ".nhsuk-pagination", ".app-page-feedback", ".beta-hub-related-links", "nav"],
                images=0),
    "medlineplus": dict(zim="medlineplus.gov_en_all_2025-01.zim", source_type="web-page",
                        publisher="MedlinePlus (U.S. National Library of Medicine)",
                        license="Public Domain (US Government work) unless a page credits another copyright holder",
                        root="#mplus-content, #d-article, article, main",
                        drop=["#mplus-share", ".page-info", "#toc", ".mp-refs", "nav", "#References", "#references", "#ency_refs",
                              "section#Methodology", ".ency-image-slider", "#patientinstructions", ".mp-lastupdate", "#mplus-subscribe",
                              ".ency-refs", "#section-References", "#section-Patient-Instructions", "#breadcrumbs", ".page-url",
                              "#citation-how-to", ".ency-citation"],
                        images=6),
    "appropedia": dict(zim="appropedia_en_all_maxi_2026-02.zim", source_type="wiki-article", publisher="Appropedia",
                       license="CC BY-SA 4.0 (Appropedia contributors) unless the page states otherwise", root=None, drop=[".template-databox"],
                       images=20),
    "energypedia": dict(zim="energypedia_en_all_maxi_2026-06.zim", source_type="wiki-article", publisher="energypedia",
                        license="CC BY-SA 4.0 (energypedia contributors)", root=None, drop=[], images=20),
    "wikem": dict(zim="wikem_en_all_maxi_2026-07.zim", source_type="wiki-article", publisher="WikEM",
                  license="CC BY-SA 3.0 (WikEM contributors)", root=None, drop=[], images=10),
    "wikibooks": dict(zim="wikibooks_en_all_nopic_2026-04.zim", source_type="wiki-book", publisher="Wikibooks",
                      license="CC BY-SA 4.0 (Wikibooks contributors)", root=None, drop=[], images=0),
    "ifixit": dict(zim="ifixit_en_all_2025-12.zim", source_type="repair-guide", publisher="iFixit",
                   license="CC BY-NC-SA 3.0 (iFixit contributors; author named in the guide)", root="#mainBody, #main, body",
                   drop=["nav", "footer", "header", "#comments", ".comments", "#banner", ".banner-content"],
                   images=12),
}
SE_SITES = ["diy", "gardening", "mechanics", "bicycles", "cooking", "outdoors", "woodworking", "pets", "ham",
            "homebrew", "sustainability", "crafts", "lifehacks"]
for s in SE_SITES:
    date = "2026-07" if s in ("cooking", "crafts") else "2026-08"
    SOURCES["se-" + s] = dict(zim=f"{s}.stackexchange.com_en_all_{date}.zim", source_type="q-and-a",
                              publisher=f"Stack Exchange - {s}.stackexchange.com",
                              license="CC BY-SA 4.0 (Stack Exchange contributors; attribution required)",
                              root="#mainbar, main, #content, body", drop=[".js-post-menu", ".post-signature .user-gravatar32", "form", ".bottom-notice", "#sidebar", "nav", "footer", "header"],
                              images=8)


def drop_empty_sections(text):
    """Remove headings that have no content before the next heading of the same or higher level."""
    lines = text.split("\n")
    keep = [True] * len(lines)
    heads = [(i, len(l) - len(l.lstrip("#"))) for i, l in enumerate(lines) if re.match(r"#{2,6} ", l)]
    for j, (i, lvl) in enumerate(heads):
        nxt = next((k for k in range(i + 1, len(lines)) if lines[k].strip()), None)
        if nxt is None:
            keep[i] = False
        elif re.match(r"#{1,6} ", lines[nxt]) and len(lines[nxt]) - len(lines[nxt].lstrip("#")) <= lvl:
            keep[i] = False
    return re.sub(r"\n{3,}", "\n\n", "\n".join(l for l, k in zip(lines, keep) if k)).strip()


def build(source):
    cfg = SOURCES[source]
    zpath = os.path.join(Z, cfg["zim"])
    z = Archive(zpath)
    docs = json.load(open(os.path.join(W, f"zimsel_{source}.json"), encoding="utf-8"))
    built_file = os.path.join(W, f"built_zim_{source}.json")
    built = json.load(open(built_file, encoding="utf-8")) if os.path.exists(built_file) else []
    done = {b["key"] for b in built}
    reg = SlugRegistry()
    skipped = 0
    for n, d in enumerate(docs):
        if d["key"] in done:
            continue
        mds, imgs = [], []
        slug = reg.claim(slugify(d.get("slug") or (source.split("-")[0] + " " + d["title"] if source in ("nhs", "medlineplus") else d["title"])),
                         f"{source}:{d['key']}")
        cat = d["category"]
        img_dir = os.path.join(cat_dir(cat), slug + "_images")
        for i, p in enumerate(d["paths"]):
            try:
                e = z.get_entry_by_path(p)
                while e.is_redirect:
                    e = e.get_redirect_entry()
            except KeyError:
                continue
            art = article_md(e, max_images=max(cfg["images"] - len(imgs), 0), archive=z, root=cfg["root"], drop=cfg["drop"])
            page_url = cfg.get("page_url", lambda p: d["source_url"])(e.path)
            md, recs = save_article_images(art, img_dir, slug + "_images", start=len(imgs),
                                           source_page=lambda im, u=page_url: u)
            imgs += recs
            md = md.strip()
            multi = len(d["paths"]) > 2
            if multi and (i > 0 or d.get("chapters") == "all"):
                # multi-chapter document: every chapter gets its own "## title" heading; the page's own headings
                # nest one level below it, and a leading H1 repeating the page title is dropped
                ch = re.sub(r"^Cookbook:", "", e.title.rsplit("/", 1)[-1]).replace("_", " ").strip()
                md = re.sub(r"^# .*\n+", "", md, count=1)
                md = re.sub(r"(?m)^(#{1,5}) ", r"#\1 ", md)
                md = f"## {ch}\n\n" + md
            elif i > 0:   # demote a sub-page's own H1 so the document keeps one title
                md = re.sub(r"^# ", "## ", md, count=1)
            mds.append(md)
        text = "\n\n".join(m for m in mds if m)
        text = re.sub(r"^\s*# .*\n", "", text, count=1)          # title is written from metadata below
        text = re.sub(r"(?m)^#+ More in .*$", "", text)
        # link-only sections (lists of related pages that are not part of this document)
        text = re.sub(r"(?m)^# ", "## ", text)   # the document title is the only H1
        text = re.sub(r"(?m)^- #+ \*\*(Step \d+)\*\*\s*$", r"### \1", text)   # iFixit step markers
        text = re.sub(r"(?ms)^#{2,6} (Patient Instructions|Related MedlinePlus Health Topics|Related conditions|Useful resources|"
                      r"See [Aa]lso|External [Ll]inks|References|Further [Ii]nformation|Further [Rr]eading|Sources|Notes)\s*\n.*?(?=^#{2,6} |\Z)",
                      "", text)
        text = drop_empty_sections(text)
        if len(text.split()) < d.get("min_words", 60) or "no public knowledge currently available from this page" in text:
            skipped += 1
            continue
        meta = {"title": d["title"], "category": cat, "source_type": cfg["source_type"], "publisher": cfg["publisher"],
                "source_url": d["source_url"], "retrieved_from": f"Kiwix ZIM {cfg['zim']}", "license": cfg["license"]}
        meta.update(d.get("extra") or {})
        meta.update({"images": imgs or None, "words": len(text.split()), "compiled": TODAY})
        head = f"# {d['title']}\n\n**Source:** {cfg['publisher']} - <{d['source_url']}>  \n**License:** {meta['license']}\n\n"
        open(os.path.join(cat_dir(cat), slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + text + "\n")
        built.append({"key": d["key"], "slug": slug, "category": cat, "title": d["title"]})
        if len(built) % 100 == 0:
            json.dump(built, open(built_file, "w", encoding="utf-8"), ensure_ascii=False); reg.save()
            print(len(built), flush=True)
    json.dump(built, open(built_file, "w", encoding="utf-8"), ensure_ascii=False)
    reg.save()
    print(source, "built", len(built), "skipped(short)", skipped)


if __name__ == "__main__":
    build(sys.argv[1])
