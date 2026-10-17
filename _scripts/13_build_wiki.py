"""Build one Markdown source file per selected Wikipedia article from the
offline ZIM (full text + images saved beside it). Selection/category come
from the manual review decision files:
  pass 1: _work/wiki_review.json + _work/wiki_keep_*.txt
  pass 2: _work/wiki_review2.json + _work/wiki2_keep_*.txt   (link/seed expansion)
Articles already written as species profiles (_work/species_paths.json) are skipped.
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry
from zimlib import zim, article_md, save_article_images, content_cats, ZIM_DATE

W = os.path.join(RESEARCH, "_work")


def load(review_file, keep_glob):
    R = json.load(open(os.path.join(W, review_file), encoding="utf-8"))
    out = []
    for f in sorted(glob.glob(os.path.join(W, keep_glob))):
        for tok in open(f).read().split():
            i, c = tok.split(":")
            out.append((R[int(i)], c))
    return out


def main():
    passes = sys.argv[1:] or ["1"]
    items = []
    if "1" in passes:
        items += load("wiki_review.json", "wiki_keep_*.txt")
    if "2" in passes:
        items += load("wiki_review2.json", "wiki2_keep_*.txt")
    species = set(json.load(open(os.path.join(W, "species_paths.json"), encoding="utf-8")))
    built_file = os.path.join(W, "built_wiki.json")
    built = json.load(open(built_file, encoding="utf-8")) if os.path.exists(built_file) else []
    done = {b["path"] for b in built}
    reg = SlugRegistry()
    z = zim()
    skipped = 0
    for n, (rec, code) in enumerate(items):
        path = rec["path"]
        if path in done or path in species:
            skipped += 1
            continue
        e = z.get_entry_by_path(path)
        art = article_md(e, max_images=30)
        if len(art["md"].split()) < 60:
            skipped += 1
            continue
        category = CODES[code]
        slug = reg.claim(slugify(e.title), "wiki:" + path)
        d = cat_dir(category)
        md, imgs = save_article_images(art, os.path.join(d, slug + "_images"), slug + "_images")
        rev = art["meta"].get("wgCurRevisionId")
        url = "https://en.wikipedia.org/wiki/" + path
        meta = {"title": e.title, "category": category, "source_type": "wikipedia-article",
                "publisher": "Wikipedia (English)", "source_url": url,
                "revision_url": f"https://en.wikipedia.org/w/index.php?oldid={rev}" if rev else None,
                "retrieved_from": f"Kiwix ZIM wikipedia_en_all_maxi_2026-08.zim (snapshot {ZIM_DATE})",
                "license": "CC BY-SA 4.0 (text: Wikipedia contributors); images: see each file page",
                "wikipedia_categories": content_cats(art["meta"])[:12],
                "images": imgs, "words": len(md.split()), "compiled": TODAY}
        head = (f"# {e.title}\n\n**Source:** Wikipedia - <{url}>" + (f" (revision <{meta['revision_url']}>)" if rev else "")
                + f"  \n**License:** CC BY-SA 4.0 - Wikipedia contributors\n\n")
        body = re.sub(r"^\s*#\s.*\n", "", md)
        open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + body + "\n")
        built.append({"path": path, "slug": slug, "category": category, "title": e.title})
        done.add(path)
        if len(built) % 100 == 0:
            json.dump(built, open(built_file, "w", encoding="utf-8"), ensure_ascii=False)
            reg.save()
            print(len(built), flush=True)
    json.dump(built, open(built_file, "w", encoding="utf-8"), ensure_ascii=False)
    reg.save()
    print("built", len(built), "skipped", skipped)


main()
