"""Add individual Wikipedia articles (same output format as the library's other Wikipedia pages).

Usage:
  67_add_wiki_articles.py --check "Title:CODE" ...     show what each title resolves to (writes nothing)
  67_add_wiki_articles.py "Title:CODE" ...             build them (CODE = category code from common.CODES)
  67_add_wiki_articles.py --file list.txt [--check]    one "Title:CODE" per line
Uses a Wikipedia archive (.zim) in _sources if there is one, otherwise fetches from wikipedia.org.
Skips articles already in the library (built_wiki.json / species / CATALOG source_url). Removes the
title from EXCLUDED_wikipedia_titles.csv once added. Run 20_catalog.py + 21_readme.py afterwards."""
import csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry
from zimlib import resolve, article_md, save_article_images, content_cats, first_para, SOURCE_LABEL
from bs4 import BeautifulSoup

W = os.path.join(RESEARCH, "_work")


def existing_paths():
    have = set()
    for f in ("built_wiki.json",):
        p = os.path.join(W, f)
        if os.path.exists(p):
            have |= {b["path"] for b in json.load(open(p, encoding="utf-8"))}
    sp = os.path.join(W, "species_paths.json")   # older libraries only
    if os.path.exists(sp):
        have |= set(json.load(open(sp, encoding="utf-8")))
    cp = os.path.join(RESEARCH, "CATALOG.json")   # a new library has none until its first item
    cat = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else []
    cat = cat if isinstance(cat, list) else cat.get("items", [])
    for r in cat:
        u = r.get("source_url") or ""
        if "wikipedia.org/wiki/" in u:
            have.add(u.split("/wiki/", 1)[1])
    return have


def main():
    args = sys.argv[1:]
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    if args[:1] == ["--file"]:
        args = [l.strip() for l in open(args[1], encoding="utf-8") if l.strip() and not l.startswith("#")]
    items = []
    for a in args:
        title, code = a.rsplit(":", 1)
        if code not in CODES:
            sys.exit(f"unknown category code {code!r} for {title!r}")
        items.append((title.strip(), code))
    have = existing_paths()
    built_file = os.path.join(W, "built_wiki.json")
    built = json.load(open(built_file, encoding="utf-8")) if os.path.exists(built_file) else []
    reg = None if check else SlugRegistry()
    added = []
    for title, code in items:
        e = resolve(title)
        if e is None:
            print(f"not found: {title}")
            continue
        path = e.path
        if path in have:
            print(f"already in library: {title} -> {path}")
            continue
        if check:
            soup = BeautifulSoup(bytes(e.get_item().content).decode("utf-8", "replace"), "html.parser")
            print(f"{title} -> {path} [{CODES[code]}]\n    {first_para(soup)[:220]}")
            continue
        art = article_md(e, max_images=30)
        category = CODES[code]
        slug = reg.claim(slugify(e.title), "wiki:" + path)
        d = cat_dir(category)
        md, imgs = save_article_images(art, os.path.join(d, slug + "_images"), slug + "_images")
        rev = art["meta"].get("wgCurRevisionId")
        url = "https://en.wikipedia.org/wiki/" + path
        meta = {"title": e.title, "category": category, "source_type": "wikipedia-article",
                "publisher": "Wikipedia (English)", "source_url": url,
                "revision_url": f"https://en.wikipedia.org/w/index.php?oldid={rev}" if rev else None,
                "retrieved_from": SOURCE_LABEL,
                "license": "CC BY-SA 4.0 (text: Wikipedia contributors); images: see each file page",
                "wikipedia_categories": content_cats(art["meta"])[:12],
                "images": imgs, "words": len(md.split()), "compiled": TODAY,
                "date_added": TODAY, "date_source": "added to the library"}
        head = (f"# {e.title}\n\n**Source:** Wikipedia - <{url}>" + (f" (revision <{meta['revision_url']}>)" if rev else "")
                + f"  \n**License:** CC BY-SA 4.0 - Wikipedia contributors\n\n")
        body = re.sub(r"^\s*#\s.*\n", "", md)
        open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + body + "\n")
        built.append({"path": path, "slug": slug, "category": category, "title": e.title})
        have.add(path)
        added.append((e.title, path))
        print(f"added: {category}/{slug}.md ({meta['words']} words, {len(imgs)} images)", flush=True)
    if check or not added:
        return
    os.makedirs(W, exist_ok=True)
    json.dump(built, open(built_file, "w", encoding="utf-8"), ensure_ascii=False)
    reg.save()
    # drop the added titles from the exclusion list
    ex = os.path.join(RESEARCH, "EXCLUDED_wikipedia_titles.csv")
    if not os.path.exists(ex):   # only libraries built from the full Wikipedia selection have this list
        print(f"done: {len(added)} added"); return
    gone = {p for _, p in added} | {t for t, _ in added}
    rows = list(csv.DictReader(open(ex, encoding="utf-8-sig")))
    keep = [r for r in rows if r["wikipedia_path"] not in gone and r["title"] not in gone]
    with open(ex, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(keep)
    print(f"done: {len(added)} added, {len(rows) - len(keep)} rows removed from EXCLUDED_wikipedia_titles.csv")


main()
