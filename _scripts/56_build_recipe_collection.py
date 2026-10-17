"""Turn a personal recipe folder (videos, recipe-card images, documents, a saved Facebook "Saved items" page, a cocktail
spreadsheet) into a browsable collection in the library:

  recipes/<slug>.md                        collection index
  recipes/<slug>/videos/                   recipe videos            (listed + linked on the index)
  recipes/<slug>/recipe-cards/             images + recipe-cards.md (OCR text of every card, image embedded)
  recipes/<slug>/documents/                docx/epub/mht/xlsx originals, each with a full-text .md
  recipes/<slug>/facebook-saved/           original saved page (opens offline) + facebook-saved-food.md

Files are MOVED (same drive). Archives that only duplicate another file here, and download-site junk, stay behind.

  _scripts\\.venv\\Scripts\\python _scripts\\56_build_recipe_collection.py E:\\Recipes [--apply]
"""
import email, hashlib, importlib, os, re, shutil, sys
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter, slugify

ing = importlib.import_module("50_ingest_folder")
ocr = importlib.import_module("31_ocr_pdfs")
import fb_saved

SLUG = "personal-recipe-collection"
TITLE = "Personal Recipe Collection (videos, recipe cards, saved Facebook recipes)"
CAT = "recipes"
BASE = os.path.join(RESEARCH, CAT, SLUG)
VID, IMG = {".mp4", ".m4v", ".mov", ".webm"}, {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOCS = {".docx", ".doc", ".epub", ".pdf", ".txt", ".mht", ".xlsx"}
LICENSE = "Personal collection - recipes gathered from web/social media; personal use only"
L = lambda p: quote(p.replace(os.sep, "/"), safe="/")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def ocr_image(path):
    import cv2, numpy as np
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return ""
    if max(img.shape[:2]) < 1000:   # small social-media images read better upscaled
        f = 1000 / max(img.shape[:2])
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    res, _ = ocr.engine()(img)
    boxes = [{"x0": min(p[0] for p in q), "x1": max(p[0] for p in q), "y0": min(p[1] for p in q), "y1": max(p[1] for p in q),
              "t": t.strip()} for q, t, s in (res or []) if float(s) >= ocr.MIN_SCORE and t.strip()]
    return "\n".join(ocr._lines(boxes))


CARD_TITLES = {   # hand titles where the image's own text makes a poor title
    "153474112_10218718516649842_2417044873141511219_n.jpg": "Sweet Hawaiian Crockpot Chicken",
    "pork 002.jpg": "Pork Cuts - Where They Come From and How to Cook Them",
    "pork-chart.jpg": "Pork Chart - Retail Cuts and How to Cook Them",
    "d23195d5f5bca7026f9d282e2835575d.jpg": "Baileys Chocolate Cherry Signature Shots",
    "22221886_10156610261949256_7345715350803845080_n.jpg": "Instant Pot Cooking Times - Rice and Grains",
    "dvdnguyen on instagram garlic butter lemon pepper lobster tails.jpg": "Garlic Butter Lemon Pepper Lobster Tails",
    "instapot keylime cheesecake.jpg": "Instant Pot Key Lime Cheesecake",
    "xmas eve hot chocolate.jpg": "Christmas Eve Crockpot Hot Chocolate",
    "shrimp.png": "Baked Lemon Butter Shrimp",
    "12109141_877862685637661_5708121178295424057_n.jpg": "Holiday Drink (Baileys Coffee Cubes)",
}


def card_title(path, text):
    name = os.path.splitext(os.path.basename(path))[0]
    if os.path.basename(path).lower() in CARD_TITLES:
        return CARD_TITLES[os.path.basename(path).lower()]
    if re.search(r"[A-Za-z]{3,}.*[A-Za-z]{3,}", name) and not re.match(r"^[\d_a-f]+(_n)?$", name):
        return re.sub(r"\s+\d{3}$", "", name.replace("-", " ")).strip()
    for line in text.splitlines():
        if 4 <= len(line) <= 60 and re.search(r"[A-Za-z]{4}", line):
            return line.strip().title() if line.isupper() else line.strip()
    return name


def mht_text(path):
    m = email.message_from_binary_file(open(path, "rb"))
    for part in m.walk():
        if part.get_content_type() == "text/html":
            return ing.strip_html(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace"))
    return "", ""


def xlsx_drinks(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out = []
    for ws in wb:
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(h or "").lower() for h in rows[0]]
        g = lambda r, k: (r[hdr.index(k)] if k in hdr and r[hdr.index(k)] is not None else "")
        for r in rows[1:]:
            if not g(r, "d_name"):
                continue
            ingr = "\n".join(f"- {x.strip()}" for x in str(g(r, "d_ingredients")).split("|") if x.strip())
            out.append(f"### {g(r, 'd_name')}\n\n*{g(r, 'd_cat')} - {g(r, 'd_alcohol')} - {g(r, 'd_glass')}*\n\n{ingr}\n\n{g(r, 'd_instructions')}\n")
    wb.close()   # read-only workbooks keep the file locked until closed
    return out


def page(path, meta, body):
    open(path, "w", encoding="utf-8").write(front_matter(meta) + "\n".join(body).rstrip() + "\n")


def main():
    src = sys.argv[1]
    apply = "--apply" in sys.argv
    vids, imgs, docs, fb, leave = [], [], [], None, []
    for root, dirs, fs in os.walk(src):
        if root.endswith("_files"):
            dirs[:] = []; continue          # assets of a saved web page travel with the page
        for f in fs:
            p, ext = os.path.join(root, f), os.path.splitext(f)[1].lower()
            if ext in VID: vids.append(p)
            elif ext in IMG: imgs.append(p)
            elif ext in (".html", ".htm") and "facebook" in f.lower(): fb = p
            elif ext in DOCS: docs.append(p)
            else: leave.append(p)
    # a .zip that only wraps an e-book already here is a duplicate
    print(f"videos {len(vids)}, recipe cards {len(imgs)}, documents {len(docs)}, facebook page {'yes' if fb else 'no'}, left behind {len(leave)}")
    for p in leave: print("   leave:", p)
    if not apply:
        return
    for d in ("videos", "recipe-cards", "documents", "facebook-saved"):
        os.makedirs(os.path.join(BASE, d), exist_ok=True)
    common = {"category": CAT, "publisher": "Personal collection", "source_url": None, "collection": SLUG, "license": LICENSE}

    # videos and images: move in, then list whatever the collection holds (so a rerun/resume rebuilds complete pages)
    for p in vids:
        shutil.move(p, os.path.join(BASE, "videos", os.path.basename(p)))
    for p in imgs:
        shutil.move(p, os.path.join(BASE, "recipe-cards", os.path.basename(p)))
    vnames = sorted((f for f in os.listdir(os.path.join(BASE, "videos")) if os.path.splitext(f)[1].lower() in VID), key=str.lower)
    cards = []
    for fn in sorted(os.listdir(os.path.join(BASE, "recipe-cards")), key=str.lower):
        if os.path.splitext(fn)[1].lower() in IMG:
            dst = os.path.join(BASE, "recipe-cards", fn)
            text = ocr_image(dst)
            cards.append((card_title(dst, text), fn, text))
    body = [f"# Recipe cards\n", f"Part of [{TITLE}](../../{SLUG}.md). Text below each card was read by OCR - check the image for exact amounts.\n"]
    for t, fn, text in sorted(cards, key=lambda c: c[0].lower()):
        body += [f"## {t}\n", f"![{t}]({L(fn)})\n", "```text", text or "(no text found)", "```\n"]
    page(os.path.join(BASE, "recipe-cards", "recipe-cards.md"),
         {"title": "Recipe Cards (images with OCR text)", "source_type": "image-collection", **common,
          "provenance": f"User-provided images from {src} (added {TODAY}); text by RapidOCR", "images": len(cards), "compiled": TODAY}, body)

    # documents
    dlist = []
    for p in sorted(docs):
        ext, fn = os.path.splitext(p)[1].lower(), os.path.basename(p)
        s = sha(p)
        if ext == ".mht":
            title, text = mht_text(p)
        elif ext == ".xlsx":
            title, text = "Cocktail and Drink Recipes (Liquor database)", "\n".join(xlsx_drinks(p))
        else:
            title, text, _ = ing.extract(p)
        if ext != ".xlsx":   # personal files are named by their owner; embedded titles are often junk ("desconhecido")
            name = re.sub(r"[_]+", " ", os.path.splitext(fn)[0]).strip()
            title = name if len(re.findall(r"[A-Za-z]{3,}", name)) >= 2 else ing.guess_title(title, text, p)
        slug = slugify(title)[:90]
        dst = os.path.join(BASE, "documents", slug + ext); shutil.move(p, dst)
        page(os.path.join(BASE, "documents", slug + ".md"),
             {"title": title, "source_type": "document", "file": slug + ext, **common,
              "provenance": f"User-provided file: {p} (added {TODAY})", "sha256": s, "words": len(text.split()), "compiled": TODAY},
             [f"# {title}\n", f"Part of [{TITLE}](../../{SLUG}.md).  ", f"**Original file:** [{slug + ext}]({L(slug + ext)})\n",
              "## Full text\n", text.strip()])
    for f in sorted(os.listdir(os.path.join(BASE, "documents"))):
        if f.endswith(".md"):
            t = re.search(r'^title: "(.*)"$', open(os.path.join(BASE, "documents", f), encoding="utf-8").read(2000), re.M).group(1)
            dlist.append((t, f"{SLUG}/documents/{f}"))

    # facebook saved page
    fbn = 0
    fb_list = os.path.join(BASE, "facebook-saved", "facebook-saved.md")   # one-entry-per-recipe folder (59_build_facebook_recipes.py)
    if os.path.exists(fb_list):
        fb = None
    elif not fb:   # resume: page already moved into the collection
        c = [os.path.join(BASE, "facebook-saved", f) for f in os.listdir(os.path.join(BASE, "facebook-saved")) if f.lower().endswith((".html", ".htm"))]
        fb = c[0] if c else None
    if fb:
        items = fb_saved.parse(fb)
        fbn = len(items)
        assets = os.path.splitext(fb)[0] + "_files"
        dst = os.path.join(BASE, "facebook-saved", os.path.basename(fb))
        if fb != dst:
            shutil.move(fb, dst)
        if os.path.isdir(assets) and fb != dst:
            shutil.move(assets, os.path.join(BASE, "facebook-saved", os.path.basename(assets)))
        body = [f"# Facebook Saved Food Recipes\n", f"Part of [{TITLE}](../../{SLUG}.md). {fbn} items from the Facebook "
                f"\"Saved > Food\" collection. Links need internet; the full saved page opens offline: "
                f"[{os.path.basename(dst)}]({L(os.path.basename(dst))}).\n"]
        for kind in ("Post", "Link", "Video"):
            sel = sorted((i for i in items if i["kind"] == kind), key=lambda i: i["title"].lower())
            if not sel: continue
            body.append(f"## {kind}s ({len(sel)})\n")
            for i in sel:
                body.append(f"### {i['title']}\n")
                body.append(f"*Saved from {i['source']}*" + (f" - [open]({i['url']})" if i["url"] else "") + "\n")
                if i["text"]:
                    body += ["```text", i["text"], "```\n"]
        page(os.path.join(BASE, "facebook-saved", "facebook-saved-food.md"),
             {"title": "Facebook Saved Food Recipes", "source_type": "saved-links", **common,
              "provenance": f"User-provided saved web page {fb} (added {TODAY})", "items": fbn, "compiled": TODAY}, body)

    # index
    body = [f"# {TITLE}\n", "Personal recipes gathered over the years. Videos open in your default player.\n",
            "## Collections\n",
            f"- [Recipe cards]({SLUG}/recipe-cards/recipe-cards.md) - {len(cards)} images with OCR text",
            (f"- [Facebook saved food recipes]({SLUG}/facebook-saved/facebook-saved.md) - "
             + " and ".join(f"{m.group(2)} {m.group(1)}" for m in re.finditer(r"^(recipes|videos): (\d+)", open(fb_list, encoding='utf-8').read(2000), re.M))
             + " saved offline" if os.path.exists(fb_list) else
             f"- [Facebook saved food recipes]({SLUG}/facebook-saved/facebook-saved-food.md) - {fbn} saved posts, links and videos")]
    body += [f"- [{t}]({L(r)})" for t, r in dlist]
    em = os.path.join(BASE, "email-recipes", "email-recipes.md")   # recipe emails (62_build_email_recipes.py)
    if os.path.exists(em):
        n = re.search(r"^recipes: (\d+)", open(em, encoding="utf-8").read(2000), re.M)
        body.append(f"- [Email recipes]({SLUG}/email-recipes/email-recipes.md) - {n.group(1) if n else ''} recipes from the Outlook Recipes folder")
    bm = os.path.join(BASE, "bookmarks")   # recipes downloaded from browser bookmarks (58_fetch_bookmarks.py)
    if os.path.isdir(bm):
        for sub in sorted(os.listdir(bm)):
            pg = os.path.join(bm, sub, sub + ".md")
            if os.path.exists(pg):
                h = open(pg, encoding="utf-8").read(3000)
                t = re.search(r'^title: "(.*)"$', h, re.M).group(1)
                sv = re.search(r"^saved: (\d+)", h, re.M); tot = re.search(r"^bookmarks: (\d+)", h, re.M)
                body.append(f"- [{t}]({SLUG}/bookmarks/{sub}/{sub}.md)" + (f" - {sv.group(1)} of {tot.group(1)} saved offline" if sv and tot else ""))
    body += ["", f"## Recipe videos ({len(vnames)})\n"] + [f"- [{os.path.splitext(v)[0].strip()}]({L(SLUG + '/videos/' + v)})" for v in vnames]
    page(os.path.join(RESEARCH, CAT, SLUG + ".md"),
         {"title": TITLE, "source_type": "collection", **common,
          "provenance": f"User-provided recipe folder {src} (organised {TODAY})", "videos": len(vnames), "recipe_cards": len(cards),
          "facebook_items": fbn, "documents": len(dlist), "compiled": TODAY}, body)
    print(f"built {BASE}: {len(vnames)} videos, {len(cards)} cards, {len(dlist)} documents, {fbn} facebook items")


if __name__ == "__main__":
    main()
