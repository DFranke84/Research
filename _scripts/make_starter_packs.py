"""Write the starter packs (<library>\\starter\\*.json) from what is in THIS library, so someone else can build the
same base library from the same free sources with 'Build Starter Library.bat'.

A pack only lists items that are still in the library (anything deleted or moved since is respected: the
category is the item's current one). Packs hold titles, archive paths and categories - no page text.

  _scripts\\.venv\\Scripts\\python _scripts\\make_starter_packs.py
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY
from archives import ARCHIVES, SE_SITES

W = os.path.join(RESEARCH, "_work")
OUT = os.path.join(RESEARCH, "starter")

ABOUT = {
    "wikipedia": "Wikipedia articles on water, food, medicine, energy, tools, survival and more. Fetched from wikipedia.org "
                 "(or from a Wikipedia archive if you have one) - no big download needed.",
    "ifixit": "Step-by-step repair guides for tools, appliances, vehicles, electronics and household items.",
    "medlineplus": "Plain-language health topics, drug information and the medical encyclopedia.",
    "nhs": "UK NHS guides to common medicines: what they are for, how to take them, side effects.",
    "appropedia": "Appropriate technology and DIY: water, sanitation, solar, building, farming projects.",
    "energypedia": "Off-grid and small-scale energy: solar, wind, micro-hydro, cooking stoves.",
    "wikem": "Emergency-medicine reference: diagnosis and treatment of injuries and illnesses.",
    "wikibooks": "Whole how-to books (combined into one document each), e.g. the Cookbook.",
}


def main():
    rows = json.load(open(os.path.join(RESEARCH, "CATALOG.json"), encoding="utf-8"))
    cat_of = {r["source_url"]: r["category"] for r in rows if r.get("source_url")}
    os.makedirs(OUT, exist_ok=True)
    packs = []

    def write(key, kind, title, items, archive=None, about=""):
        items = [d for d in items if d["category"] != "local-area"]   # Local Area is one person's own area, not a starter
        items = sorted(items, key=lambda d: (d["category"], d["title"].lower()))
        json.dump({"pack": key, "kind": kind, "title": title, "about": about, "archive": archive,
                   "made": TODAY, "items": items}, open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
        packs.append({"pack": key, "kind": kind, "title": title, "archive": archive, "items": len(items)})
        print(f"{key:18} {len(items):6} items")

    # Wikipedia: every article page in the library (not the Local Area species pages)
    wp = [{"title": r["title"], "path": r["source_url"].split("/wiki/", 1)[1], "category": r["category"]}
          for r in rows if r.get("source_type") == "wikipedia-article" and "/wiki/" in (r.get("source_url") or "")]
    write("wikipedia", "wikipedia", "Wikipedia articles", wp, about=ABOUT["wikipedia"])

    # archive sources built by 15_build_zim_docs.py: the original selection, kept items only
    for f in sorted(glob.glob(os.path.join(W, "zimsel_*.json"))):
        src = os.path.basename(f)[len("zimsel_"):-len(".json")]
        if src not in ARCHIVES:
            continue
        items = []
        for d in json.load(open(f, encoding="utf-8")):
            if d.get("source_url") in cat_of:
                items.append(dict(d, category=cat_of[d["source_url"]]))
        write(src, "zim", ARCHIVES[src][2], items, archive=src, about=ABOUT.get(src, ""))

    # Stack Exchange sites built by 18_stackexchange.py
    for site in SE_SITES:
        f = os.path.join(W, f"se_{site}_select.json")
        if not os.path.exists(f):
            continue
        items = []
        for d in json.load(open(f, encoding="utf-8")):
            url = f"https://{site}.stackexchange.com/{d['path']}"
            if url in cat_of:
                items.append({"path": d["path"], "title": d["title"], "category": cat_of[url]})
        write("se-" + site, "stackexchange", f"Stack Exchange - {site}", items, archive="se-" + site,
              about=f"Top-voted questions with their best answers from {site}.stackexchange.com.")

    # web pages and PDFs with a public address (not the ones taken from an archive, not personal material)
    web = []
    for r in rows:
        url = r.get("source_url") or ""
        if (r.get("source_type") not in ("web-page", "pdf", "document") or not url.startswith("http")
                or r["file"].startswith("recipes/personal") or (r.get("publisher") or "").startswith("User-provided")):
            continue
        head = open(os.path.join(RESEARCH, r["file"]), encoding="utf-8", errors="replace").read(4000)
        if "retrieved_from: \"Kiwix" in head:
            continue
        web.append({"url": url, "title": r["title"], "category": r["category"], "kind": "page" if r["source_type"] == "web-page" else "pdf",
                    "publisher": r.get("publisher") or "", "license": r.get("license") or ""})
    write("web", "web", "Web pages & PDFs (public sites)", web,
          about="Guides from public websites (US government, extension services, home food preservation) and free PDF "
                "manuals (archive.org, publishers). Downloaded one by one - slow but no archive needed.")

    json.dump({"made": TODAY, "packs": packs}, open(os.path.join(OUT, "packs.json"), "w", encoding="utf-8"), indent=1)
    print(f"{sum(p['items'] for p in packs):,} items in {len(packs)} packs -> {OUT}")


if __name__ == "__main__":
    main()
