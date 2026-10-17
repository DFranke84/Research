"""Turn exported recipe emails (61_export_outlook_folder.ps1) into recipes/personal-recipe-collection/email-recipes/:
one entry per email (.md + clean PDF + its photos/videos/documents) and an email-recipes.md list page.

  - duplicates across PST files are merged (same subject + same text)
  - forwarding headers, signatures, names/addresses/phone numbers and MIME noise are stripped - only the recipe is kept
  - emails that are mainly links to recipe sites: each linked recipe is fetched (like the bookmarks)
  - attached Word/PDF files are kept with their text; recipe photos and videos are kept (logos/signature images skipped)
  - photo-only emails: the recipe text is read from the picture (OCR)

  _scripts\\.venv\\Scripts\\python _scripts\\62_build_email_recipes.py [<export dir>]
"""
import glob, hashlib, html, importlib, json, os, re, shutil, sys
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter, slugify
import recipe_clean as rc

ing = importlib.import_module("50_ingest_folder")
bm = importlib.import_module("58_fetch_bookmarks")
fbr = importlib.import_module("59_build_facebook_recipes")
col = importlib.import_module("56_build_recipe_collection")
EXPORT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RESEARCH, "_work", "email_export")
OUT = os.path.join(RESEARCH, "recipes", "personal-recipe-collection", "email-recipes")
L = lambda p: quote(p.replace(os.sep, "/"), safe="/")
IMG, VID, DOC = (".jpg", ".jpeg", ".png", ".gif", ".webp"), (".mp4", ".mov", ".m4v", ".avi", ".wmv"), (".pdf", ".docx", ".doc", ".txt", ".rtf")

# lines that are e-mail plumbing or personal details, not recipe
DROP = re.compile(r"^(-{2,}\s*[^\s-]|_{5,}\s*[^\s_]|This message is in MIME format|Since your mail reader|some or all of this message|Content-Type:|"
                  r"charset=|Content-Transfer|------_=_|From:|Sent:|To:|Cc:|Bcc:|Subject:|Date:|Reply-To:|"
                  r"Sent from my|Get Outlook for|Begin forwarded message|-+ ?Original Message|-+ ?Forwarded message|"
                  r"On .{5,80} wrote:$|\*?\s*Phone:|\*?\s*Fax:|\*?\s*Cell:|\*?\s*Mobile:|Tel[:.]|Direct:|Office:|"
                  r"\*?\s*mailto:|.*\bunsubscribe\b|.*\bconfidential\b|.*\bintended recipient\b|<<.*>>$)", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
ADDRESS = re.compile(r"^\d{2,6}\s+\w+.*\b(ave|avenue|st|street|rd|road|blvd|dr|drive|suite|ste|lane|ln|way|pkwy)\b", re.I)
CITYZIP = re.compile(r"^[A-Za-z .]+,\s*[A-Z]{2}\s+\d{5}(-\d{4})?$")


SUPERSEDED = {   # (subject, date received) of emails replaced by a later, more complete version of the same recipe
    ("jade red chicken - chinos", "2012-11-30"): "replaced by the 2016 'Jade Red Chicken' email (same recipe, written in parts)",
}
OVERRIDES = {   # (subject, date received) -> hand corrections the owner asked for
    ("recipes", "2000-11-21"): {"title": "Chicken Tetrazzini (Wayne Hollock)", "credit": "From Wayne Hollock",
                                "start_at": "The recipe for the Chicken Tetrazzini is"},
    ("texas roadhouse margarita recipes", "2020-06-23"): {
        "title": "Texas Roadhouse Drinks (Kenny's Cooler, Armadillo Punch, Jamaican Cowboy, Sangria Red)",
        "description": "Four Texas Roadhouse signature drinks, as published by the restaurant in June 2020. The Hurricane "
                       "Margarita recipe from the same article was only shown as a picture on Pinterest and is not included."},
}
RECIPE_FOR = re.compile(r"\brecipe for (the |my |our )?(?P<name>[A-Z][\w'’ -]{3,40}?)\s+(is|are)\s*:?\s*$", re.I)


def plain_part(text):
    """Old MIME mails arrive with the raw parts in the body: keep only the text/plain part, never the HTML copy."""
    text = text.replace("\r", "")
    if re.search(r"^-{2,}=?_?[=_]?NextPart|^Content-Type:", text, re.M):
        parts = re.split(r"^-{2,}=?_?[=_]?NextPart\S*\s*$", text, flags=re.M)
        plain = next((p for p in parts if re.search(r"^Content-Type:\s*text/plain", p, re.M | re.I)), None)
        if plain:
            text = plain.split("\n\n", 1)[-1] if re.match(r"\s*Content-Type", plain) else plain
    cut = re.search(r"^\s*<(!DOCTYPE|html|head|meta|div|body)\b", text, re.M | re.I)
    return text[:cut.start()] if cut else text


def unwrap(lines):
    """Rejoin text that the old mail program hard-wrapped at ~76 characters."""
    out = []
    for l in lines:
        if out and out[-1] and l and len(out[-1]) >= 30 and not out[-1].endswith((".", ":", "!", "?", ")")) \
                and l[0].islower() and not rc.MEASURE.match(l):   # mid-sentence continuation (narrow columns too); never an ingredient line
            out[-1] = out[-1] + " " + l
        else:
            out.append(l)
    return out


def clean_body(text, subject):
    text = plain_part(text)
    out, sig = [], False
    for raw in text.split("\n"):
        l = re.sub(r"^(>\s?)+", "", raw.strip()).strip().strip("​")   # quoted reply text: keep it, drop the ">" marks
        if not l:
            if out and out[-1] != "": out.append("")
            continue
        if DROP.match(l) or ADDRESS.match(l) or CITYZIP.match(l) or re.fullmatch(r"[\w.]+ [\w.]+(,? [\w.]+)?", l) and sig \
                or l.startswith("<") or re.match(r"^(this format|format, some|may not be legible)", l, re.I):
            continue
        if re.match(r"^(thanks|thank you|cheers|regards|best( regards)?|love|enjoy)\b.{0,40}?[,!.]*$", l, re.I) and len(l) < 50:
            sig = True   # sign-off: what follows is a signature
            continue
        if sig and (len(l) < 40 or EMAIL.search(l) or PHONE.search(l)):
            continue
        # pasted web articles: "Texas Roadhouse <https://...>" credit/link-only lines go; inline <https://...> markup goes
        if re.fullmatch(r"(.{0,40}?)\s*<https?://[^>]*>?\s*(·.*)?", l) or re.match(r"^(SHARE|PIN IT|PRINT|TWEET)\b", l):
            continue
        l = re.sub(r"\s*<https?://[^>]*>?", "", l)
        l = re.sub(r"<\s*mailto:\s*>|\[\s*mailto:\s*\]|\(\s*\)", "", PHONE.sub("", EMAIL.sub("", l))).strip(" <>[]")
        if l:
            out.append(l)
    while out and out[-1] == "":
        out.pop()
    out = [re.sub(r"\b([a-z]{2,})-(er|ers|son|ing|tion|ment|ly)\b", r"\1\2", l) for l in out]   # newspaper hyphens: contain-er
    return [l for l in unwrap([l for l in out if l != ""])]


def title_of(subject, lines):
    t = re.sub(r"^((fw|fwd|re)\s*:\s*)+", "", subject or "", flags=re.I).strip()
    if not re.search(r"[A-Za-z]{3}", t) or t.lower() in ("recipe", "recipes", "cookbook", "another one"):
        t = next((l for l in lines if 4 <= len(l) <= 60 and re.search(r"[A-Za-z]{3}", l) and not rc.MEASURE.search(l[:20])), t or "Recipe")
    return fbr.nice_title(t)


def ocr_text(path):
    try:
        return col.ocr_image(path)
    except Exception:
        return ""


def main():
    os.makedirs(OUT, exist_ok=True)
    emails, seen = [], set()
    for d in sorted(glob.glob(os.path.join(EXPORT, "*"))):
        m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8-sig"))
        body = open(os.path.join(d, "body.txt"), encoding="utf-8-sig").read()
        key = hashlib.md5((re.sub(r"^((fw|fwd|re)\s*:\s*)+", "", m["subject"].lower()) + re.sub(r"\s+", " ", body)[:600]).encode()).hexdigest()
        if key in seen or (m["subject"].strip().lower(), m["received"][:10]) in SUPERSEDED:
            continue
        seen.add(key); emails.append((d, m, body))
    print(f"{len(emails)} unique recipe emails", flush=True)
    used, rows = set(), []

    def slug_for(t):
        s = slugify(t)[:70] or "recipe"
        while s in used: s += "-2"
        used.add(s); return s

    for d, m, body in emails:
        lines = clean_body(body, m["subject"])
        ov = OVERRIDES.get((m["subject"].strip().lower(), m["received"][:10]), {})
        if not ov:   # generic subject + "The recipe for the X is:" -> the recipe is X, starting at that line
            k = next((i for i, l in enumerate(lines) if RECIPE_FOR.search(l)), None)
            if k is not None and re.fullmatch(r"(fw:|re:|fwd:|\s)*(recipes?|cookbook|another one)?\s*", m["subject"].strip(), re.I):
                ov = {"title": RECIPE_FOR.search(lines[k]).group("name"), "start_at": lines[k]}
        if ov.get("start_at"):
            k = next((i for i, l in enumerate(lines) if l.startswith(ov["start_at"])), 0)
            lines = lines[k + 1:] if k or lines[0].startswith(ov["start_at"]) else lines
        text = "\n".join(lines)
        title = ov.get("title") or title_of(m["subject"], lines)
        main_name = re.sub(r"\s*\(.*?\)\s*$", "", title)
        atts = [a for a in m.get("attachments", []) if a.get("file")]
        apath = lambda a: os.path.join(d, "attachments", a["file"])
        cid_used = set(re.findall(r'src="cid:([^"]+)"', open(os.path.join(d, "body.html"), encoding="utf-8-sig", errors="replace").read()))
        imgs = [a for a in atts if a["name"].lower().endswith(IMG) and a.get("size", 0) >= 15000
                and not re.search(r"logo|signature|banner|facebook|twitter|instagram|pinterest|icon", a["name"], re.I)]
        vids = [a for a in atts if a["name"].lower().endswith(VID)]
        docs = [a for a in atts if a["name"].lower().endswith(DOC)]
        links = [u.rstrip(".,);>") for u in re.findall(r"https?://[^\s<>\"]+", text)
                 if not re.search(r"facebook\.com|twitter|instagram|pinterest|mailto|unsubscribe|outlook|google\.com/maps", u)]
        prose_words = len(re.sub(r"https?://\S+", "", text).split())

        # 1) emails that are essentially links to recipes: fetch each linked recipe
        if links and prose_words < 60 and not docs:
            for u in dict.fromkeys(links):
                slug = slug_for(title if len(links) == 1 else f"{title} {len(rows) + 1}")
                r = bm.do_page(title, u, OUT, slug, {"category": "recipes", "collection": "personal-recipe-collection",
                                                     "provenance": f"Recipe link in an email ({m['received'][:10]})",
                                                     "license": "Copyright of the original site - personal offline copy", "compiled": TODAY})
                if r.get("status") == "ok":
                    rows.append((r.get("title") or title, slug, m["received"][:10], "link"))
                else:
                    used.discard(slug)
            if prose_words < 15:
                continue

        slug = slug_for(title)
        media = []
        # 2) copy photos / videos / documents
        for a in imgs:
            ext = os.path.splitext(a["name"])[1].lower()
            fn = f"{slug}-{len(media) + 1}{ext}" if media or len(imgs) > 1 else slug + ext
            shutil.copy2(apath(a), os.path.join(OUT, fn)); media.append(("img", fn, a))
        for a in vids:
            fn = f"{slug}-video{'' if len(vids) == 1 else '-' + str(vids.index(a) + 1)}{os.path.splitext(a['name'])[1].lower()}"
            shutil.copy2(apath(a), os.path.join(OUT, fn)); media.append(("vid", fn, a))
        doc_text = []
        for a in docs:
            fn = f"{slug}-{slugify(os.path.splitext(a['name'])[0])[:40]}{os.path.splitext(a['name'])[1].lower()}"
            shutil.copy2(apath(a), os.path.join(OUT, fn)); media.append(("doc", fn, a))
            try:
                _, t, _ = ing.extract(os.path.join(OUT, fn))
                doc_text.append((a["name"], fn, t.strip()))
            except Exception:
                pass
        # 3) photo-only recipe: read the text in the picture
        ocr_parts = []
        if prose_words < 40 and not doc_text:
            for k, fn, a in media:
                if k == "img":
                    t = ocr_text(os.path.join(OUT, fn))
                    if len(t.split()) >= 15:
                        ocr_parts.append((fn, t))
        if prose_words < 4 and not media:   # (a short ingredient list - e.g. a drink - is still a recipe)
            used.discard(slug)
            continue
        # 4) the recipe: structured when the email has ingredients + steps, else as written
        rec = fbr.post_recipe(text) if prose_words >= 4 else None
        if rec:   # the untitled main part of a multi-part recipe carries the recipe's own name
            rec["ingredients"] = [x.replace("{MAIN}", main_name) for x in rec["ingredients"]]
            rec["instructions"] = [x.replace("{MAIN}", main_name) for x in rec["instructions"]]
            if ov.get("description"):
                rec["description"] = ov["description"]
        if rec is None:
            paras = [l for l in lines if l] or [f"(recipe is in the attached {'document' if doc_text else 'picture'})"]
            rec = {"name": "", "description": "", "image": None, "yield": "", "prep": None, "cook": None, "total": None,
                   "ingredients": [], "instructions": [], "article": paras, "notes": [], "video": None,
                   "method": "recipe as written in the email"}
        if ocr_parts:   # photo-only recipe: the email's words plus the text read from the picture(s)
            paras = rec.get("article") or [l for l in lines if l]
            for fn, t in ocr_parts:
                paras = paras + ["### Recipe text from the picture"] + [x for x in t.splitlines() if x.strip()]
            rec = {**rec, "article": paras, "method": rec["method"] + " + text read from the picture"}
        first_img = next((fn for k, fn, a in media if k == "img"), None)
        pdf_ok = rc.to_pdf(rec, title, (ov["credit"] + " - r" if ov.get("credit") else "R") + f"ecipe email received {m['received'][:10]}", os.path.join(OUT, first_img) if first_img else None,
                           os.path.join(OUT, slug + ".pdf"))
        meta = {"title": title, "category": "recipes", "source_type": "email-recipe", "file": slug + ".pdf" if pdf_ok else None,
                "publisher": "Personal email", "source_url": None, "collection": "personal-recipe-collection",
                "provenance": f"Outlook folder Email/Recipes, received {m['received'][:10]}",
                "license": "Personal recipe collection - personal use", "received": m["received"][:10],
                "photos": sum(1 for k, *_ in media if k == "img"), "videos": sum(1 for k, *_ in media if k == "vid"), "compiled": TODAY}
        if ov.get("credit"):
            meta["publisher"] = ov["credit"].replace("From ", "")
        md = [front_matter(meta), f"# {title}\n", f"*{ov['credit'] + ' - r' if ov.get('credit') else 'R'}ecipe email, {m['received'][:10]}.*  "]
        if pdf_ok: md.append(f"**Recipe PDF:** [{slug}.pdf]({L(slug + '.pdf')})  ")
        for k, fn, a in media:
            if k == "vid": md.append(f"**Video:** [{fn}]({L(fn)})  ")
            if k == "doc": md.append(f"**Attached document:** [{a['name']}]({L(fn)})  ")
        md.append("")
        md += [f"![{title}]({L(fn)})" for k, fn, a in media if k == "img"] + [""]
        md.append(rc.to_markdown(rec))
        for name, fn, t in doc_text:
            md += ["", f"## From the attached document: {name}", "", t]
        open(os.path.join(OUT, slug + ".md"), "w", encoding="utf-8").write("\n".join(md).rstrip() + "\n")
        rows.append((title, slug, m["received"][:10], "video" if any(k == "vid" for k, *_ in media) else "email"))
        print(f"  {title[:60]}", flush=True)

    rows.sort(key=lambda r: r[0].lower())
    body = ["# Email Recipes\n", f"Part of [Personal Recipe Collection](../../personal-recipe-collection.md). {len(rows)} recipes from "
            "the Outlook folder Email/Recipes (duplicates merged; names, addresses and signatures removed).\n",
            f"## Recipes ({len(rows)})\n"]
    body += [f"- [{t}]({L(s + '.md')}) *({dt}{', video' if k == 'video' else ', from a link' if k == 'link' else ''})*" for t, s, dt, k in rows]
    meta = {"title": "Email Recipes", "category": "recipes", "source_type": "bookmark-collection", "publisher": "Personal email",
            "source_url": None, "collection": "personal-recipe-collection", "provenance": f"Outlook folder Email/Recipes, exported {TODAY}",
            "license": "Personal recipe collection - personal use", "recipes": len(rows), "saved": len(rows), "compiled": TODAY}
    open(os.path.join(OUT, "email-recipes.md"), "w", encoding="utf-8").write(front_matter(meta) + "\n".join(body) + "\n")
    print(f"email-recipes built: {len(rows)} recipes")


if __name__ == "__main__":
    main()
