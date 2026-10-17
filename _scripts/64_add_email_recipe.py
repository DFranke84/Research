"""Add one new recipe email (Outlook folder Email/Recipes) to recipes/personal-recipe-collection/email-recipes/ without
rebuilding the other emails.

The email is found by words in its subject and exported read-only (like 61_export_outlook_folder.ps1) to
_work/email_export_new/<n>/. Its text is cleaned with 62's rules (no addresses, signatures, forwarding headers, link noise).
  - an email holding SEVERAL recipes (e.g. "6 Chocolate Desserts", recipe blocks split by ━━━ lines or SHOUTED titles
    followed by Makes/Serves/INGREDIENTS) -> ONE entry with every recipe complete in it (own ingredient groups, method,
    tips), a contents list, and a PDF with all of them
  - a single recipe -> one entry, parsed like 62 (59.post_recipe; multi-part recipes stay one recipe)
Recipe photos are kept (signature icons/logos skipped); the list page, collection page and catalog are refreshed.

  _scripts\\.venv\\Scripts\\python _scripts\\64_add_email_recipe.py "<words from the subject>" [--force] [--check]
  --dir <_work/email_export_new/NNNN>  rebuild from an earlier export instead of Outlook;  --check  only show what it finds
"""
import html as _html, json, os, re, shutil, subprocess, sys
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))
import importlib
from common import RESEARCH, TODAY, front_matter, slugify
import recipe_clean as rc

er = importlib.import_module("62_build_email_recipes")
fbr = er.fbr
OUT = er.OUT
STAGE = os.path.join(RESEARCH, "_work", "email_export_new")
L = lambda p: quote(p.replace(os.sep, "/"), safe="/")
SEP = re.compile(r"^\s*([━─═_*~=-])\1{5,}\s*$")
INFO = re.compile(r"^(makes|serves|servings?|yield|yields|pan|bake|baking|cook|cooking|prep|chill|chilling|total|time|freeze|oven|temp)\b[^:]{0,15}:\s*(.+)$", re.I)
STEPS = re.compile(r"^(?:(?:detailed|full|easy|simple|step[- ]by[- ]step|cooking|baking|making) )?(process|method|directions?|instructions?|steps?|preparation|how to make( it)?|(the )?recipe)\s*:?$", re.I)
ING_HEAD = re.compile(r"^(the )?ingredients?( list)?\s*:?$", re.I)
ING_INLINE = re.compile(r"^(?:the )?ingredients?(?: list)?\s*:\s*(\S.*[,;].*)$", re.I)   # "Ingredients: a, b, c" on one line


def split_inline(items):
    """'500g wings, 3 tbsp honey (or maple, to taste); 1 tsp salt' -> one ingredient each (commas inside () stay)."""
    out, cur, depth = [], "", 0
    for ch in items:
        depth += ch in "([" and 1 or (ch in ")]" and -1 or 0)
        if ch in ",;" and depth <= 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    out.append(cur)
    out = [x.strip().rstrip(".") for x in out if x.strip()]
    for k in range(len(out) - 1, 0, -1):   # "..., 2 dried chilies, optional" -> the note stays with its ingredient
        if re.fullmatch(r"(optional|to taste|divided|for serving|for garnish)", out[k], re.I):
            out[k - 1] += ", " + out.pop(k)
    if len(out) >= 3 and re.match(r"[\d½¼¾⅓⅔]", out[-1]):   # "a, b, 40 g flour and neutral oil for frying" -> last two apart
        m = re.match(r"(.+?) and (?!(?:\w+ed|\w+ly)\b)(.+)$", out[-1])
        if m and "(" not in out[-1]:
            out[-1:] = [m.group(1), m.group(2)]
    return out
STEPS_INLINE = re.compile(r"^(?:(?:detailed|full|easy|simple|step[- ]by[- ]step|cooking|baking) )?(?:method|directions?|instructions?|steps?|preparation|how to make(?: it)?)\s*:\s*(\S.{20,})$", re.I)
GROUP_INLINE = re.compile(r"^([A-Z][\w'’&/ -]{1,30}?)\s*:\s*(\S.*,.*,.*)$")   # "Sauce: 3 tbsp soy sauce, 1 tsp sugar, ..."


def split_steps(text):
    """'Coat chicken. Fry in batches 5–7 minutes. Drain. Toss in sauce.' -> sentences; very short ones join the one before."""
    out = []
    for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip()):
        if out and len(x.split()) < 4:
            out[-1] += " " + x
        else:
            out.append(x)
    return out
INLINE_TIP = re.compile(r"^((?:pro |chef'?s? |baking |quick |top |(?:grandma|grandpa|mom|nana|granny)['’]?s )?tips?|little touch|notes?|variations?|serving suggestions?)\s*:\s*(\S.*)$", re.I)
TIPS = re.compile(r"^((pro |chef'?s? |baking |dessert )?tips?|notes?|variations?)\s*:?$", re.I)
BULLET = re.compile(r"^[•●▪◦·*-]\s*")
NUM = re.compile(r"^(\d{1,2})[.)]\s+")
STEP_NO = re.compile(r"^step\s*\d{1,2}\s*[:.)-]\s*", re.I)   # "Step 3: Whisk the eggs"
END = re.compile(r"^(save,? share|follow\b|#\w|see less|see more|for more (easy )?recipes)", re.I)
SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def tc(s):
    """SHOUTED TITLE -> Title Case (keeps 'Self-Saucing', 'Don't', small words lower)."""
    if re.search(r"[a-z]", s):
        return s
    words = s.lower().split()
    return " ".join(w if (i and w in SMALL) else "-".join(p[:1].upper() + p[1:] for p in w.split("-")) for i, w in enumerate(words))


def is_heading(l):
    """A section/recipe heading: short, no bullet, all capitals (or ending in ':'). A numbered SHOUTED line
    ("1. HUNAN CHICKEN") is a recipe title - numbered steps are written in normal case."""
    if NUM.match(l):
        rest = NUM.sub("", l)
        return 3 <= len(rest) <= 60 and bool(re.search(r"[A-Z]{3}", rest)) and not re.search(r"[a-z]", rest)
    return len(l) <= 60 and not BULLET.match(l) and not INFO.match(l) and \
        (re.search(r"[A-Z]{3}", l) and not re.search(r"[a-z]", l) or (l.endswith(":") and len(l) <= 30))


def heading_text(l):
    return tc(NUM.sub("", l).rstrip(":").strip())


def title_like(l):
    """Could start a recipe: a heading, or a short title line ("1. Cheesy Steak & Potato Foil Packets")."""
    if INFO.match(l) or ING_HEAD.match(l) or ING_INLINE.match(l) or STEPS.match(l) or TIPS.match(l.rstrip(":")) or INLINE_TIP.match(l) \
            or STEPS_INLINE.match(l):
        return False   # section labels ("Pro Tip:", "Ingredients", "Method:") are never recipe titles
    if is_heading(l):
        return True
    return 3 <= len(NUM.sub("", l)) <= 90 and not BULLET.match(l) and not l.endswith((".", ",", ";")) and \
        not (INFO.match(l) or ING_HEAD.match(l) or STEPS.match(l) or TIPS.match(l) or INLINE_TIP.match(l))


def parse_block(lines, need_steps=True):
    """One recipe block -> {name, info, desc, groups[(name, [items])], steps, tips}; None when it is not a recipe.
    need_steps=False: an ingredients-only list counts too (emails that give no method for any recipe)."""
    r = {"name": "", "info": [], "desc": [], "groups": [], "steps": [], "tips": [], "tip_label": "Pro tip", "rest": []}
    mode = "head"
    for k, l in enumerate(lines):
        if not r["name"] and (is_heading(l) and not ING_HEAD.match(l) or k == 0 and title_like(l)):
            r["name"] = heading_text(l); continue
        t = INLINE_TIP.match(l)
        if t and (r["steps"] or r["groups"]):   # "Little touch: ..." / "Tip: ..." on one line
            if not r["tips"]: r["tip_label"] = t.group(1)[:1].upper() + t.group(1)[1:].lower()
            r["tips"].append(t.group(2)); mode = "inline_tip"; continue
        if mode == "inline_tip" and title_like(l) and not BULLET.match(l):   # a heading after a one-line tip: the email's closing section
            r["rest"] = lines[k:]; break
        if mode == "inline_tip": mode = "tips"
        m = INFO.match(l)
        if m and mode in ("head", "ing") and not r["steps"]:
            for part in l.split(" | ") if " | " in l else [l]:   # "Servings: 12 | Prep Time: 20 minutes | Chill Time: 6 hours"
                pm = INFO.match(part.strip())
                if pm: r["info"].append((tc(pm.group(1)).title(), pm.group(2).strip()))
            continue
        if STEPS.match(l):
            mode = "steps"; continue
        sm = STEPS_INLINE.match(l)
        if sm and (r["groups"] or r["steps"]):   # "Method: Coat the chicken... Toss in sauce." - all steps on one line
            r["steps"] += split_steps(sm.group(1)); mode = "after_inline_steps"; continue
        if mode == "after_inline_steps":   # a plain line after a one-line method is a note
            r["tips"].append(l); r["tip_label"] = r["tip_label"] if r["tips"][:-1] else "Tip"; mode = "tips"; continue
        if TIPS.match(l.rstrip(":")) or TIPS.match(l):
            mode = "tips"; continue
        if ING_HEAD.match(l):
            r["groups"].append(("", [])); mode = "ing"; continue
        im = ING_INLINE.match(l)
        if im and not r["steps"]:
            r["groups"].append(("", split_inline(im.group(1)))); mode = "ing"; continue
        gm = GROUP_INLINE.match(l)
        if gm and mode == "ing" and r["groups"] and not r["steps"] and not INLINE_TIP.match(l):   # "Sauce: a, b, c" after the ingredients
            r["groups"].append((gm.group(1).strip(), split_inline(gm.group(2)))); continue
        if is_heading(l) and mode != "tips":
            g = heading_text(l)
            r["groups"].append(("" if re.fullmatch(r"ingredients?", g, re.I) else g, [])); mode = "ing"; continue
        if BULLET.match(l) and mode in ("head", "ing"):
            if not r["groups"]: r["groups"].append(("", []))
            r["groups"][-1][1].append(BULLET.sub("", l)); mode = "ing"; continue
        if mode == "steps":
            r["steps"].append(STEP_NO.sub("", BULLET.sub("", NUM.sub("", l)))); continue
        if mode == "tips":
            r["tips"].append(l); continue
        if mode == "ing" and r["groups"]:   # unbulleted ingredient line
            r["groups"][-1][1].append(l); continue
        r["desc"].append(l)
    r["groups"] = [(g, items) for g, items in r["groups"] if items]
    if sum(len(i) for _, i in r["groups"]) < (2 if need_steps else 3) or need_steps and not r["steps"] or not need_steps and not r["name"]:
        return None
    return r


def split_recipes(lines):
    """Blocks of a multi-recipe email: by separator lines, else at title lines followed by Serves:/Ingredients."""
    if sum(1 for l in lines if SEP.match(l)) >= 2:
        blocks, cur = [], []
        for l in lines:
            if SEP.match(l):
                blocks.append(cur); cur = []
            else:
                cur.append(l)
        return blocks + [cur]
    starts = [i for i, l in enumerate(lines) if title_like(l) and
              any(INFO.match(x) or ING_HEAD.match(x) or ING_INLINE.match(x) for x in lines[i + 1:i + 4])]
    starts = [i for k, i in enumerate(starts) if not (k + 1 < len(starts) and starts[k + 1] - i < 3)]   # the line nearest its recipe
    if len(starts) < 2:
        return [lines]
    return [lines[:starts[0]]] + [lines[a:b] for a, b in zip(starts, starts[1:] + [len(lines)])]


def note_blocks(lines):
    """Closing section lines -> blocks; a new block starts at a heading line once the current one has bullet points."""
    out = []
    for l in lines:
        if out and title_like(l) and not BULLET.match(l) and any(BULLET.match(x) for x in out[-1][1:]):
            out.append([l])
        elif out:
            out[-1].append(l)
        else:
            out.append([l])
    return out


def note_text(b):
    """A closing block -> note string: 'Heading: text', with bullet points kept as '\n- ' lines."""
    head = b[0] if len(b) > 1 and (is_heading(b[0]) or title_like(b[0]) and not BULLET.match(b[0])) else ""
    body = b[1:] if head else b
    if any(BULLET.match(x) for x in body):
        txt = "\n".join("- " + BULLET.sub("", x) if BULLET.match(x) else x for x in body)
        return (heading_text(head) + ":\n" if head else "") + txt
    return (heading_text(head) + ("" if head.endswith(("?", "!")) else ":") + " " if head else "") + " ".join(body)


def recipe_md(r, level="##"):
    out = [f"{level} {r['name']}", ""]
    if r["info"]: out += ["  \n".join(f"**{k}:** {v}" for k, v in r["info"]), ""]
    if r["desc"]: out += [" ".join(r["desc"]), ""]
    out += [f"{level}# Ingredients", ""]
    for g, items in r["groups"]:
        if g: out += ["", f"**{g}**", ""]
        out += [f"- {x}" for x in items]
    if r["steps"]:
        out += ["", f"{level}# Method", ""] + [f"{n}. {s}" for n, s in enumerate(r["steps"], 1)]
    if r["tips"]: out += ["", f"**{r['tip_label']}:** {' '.join(r['tips'])}"]
    return out + [""]


# ---------------------------------------------------------------- recipes that are pictures (no recipe text in the email)
PICTURE_TITLES = {   # pictures whose heading the OCR can't read (fancy lettering): (email subject, card number) -> title
    ("classic bbq sauce recipes", 4): "Carolina Mustard BBQ Sauce",
}
CARD_WORDS = re.compile(r"^(ingredients?|method|directions?|instructions?|best with|chef'?s tip|tips?|serves?|notes?)$", re.I)
KEEP_CAPS = {"Bbq": "BBQ", "F&b": "F&B", "Diy": "DIY", "Usa": "USA"}


def card_title(t):
    t = re.sub(r"(?<=[A-Z])(SAUCE|STYLE)\b", r" \1", t)  # 'BBQSAUCE'
    t = re.sub(r"\s+", " ", t).strip(" -:")
    return " ".join(KEEP_CAPS.get(w, w) for w in tc(t).split())


def read_card(path):
    """OCR one recipe picture -> {"title", "sub", "n", "total", "text"} (title: the big capital-letter heading below the
    banner; sub: the line just under it; n/total: a '3/8' card number; text: everything readable, line by line)."""
    import cv2, numpy as np
    ocr = importlib.import_module("31_ocr_pdfs")
    out = {"title": "", "sub": "", "n": None, "total": None, "text": ""}
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return out
    if max(img.shape[:2]) < 1000:
        f = 1000 / max(img.shape[:2]); img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    H = img.shape[0]
    res, _ = ocr.engine()(img)
    boxes = [{"x0": min(q[0] for q in pts), "x1": max(q[0] for q in pts), "y0": min(q[1] for q in pts), "y1": max(q[1] for q in pts),
              "t": t.strip()} for pts, t, sc in (res or []) if float(sc) >= ocr.MIN_SCORE and t.strip()]
    out["text"] = "\n".join(ocr._lines(boxes))
    for b in boxes:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", b["t"].replace(" ", ""))
        if m and 1 <= int(m[1]) <= int(m[2]) <= 30:
            out["n"], out["total"] = int(m[1]), int(m[2]); break
    band = [b for b in boxes if 0.12 * H <= b["y0"] <= 0.7 * H and re.search(r"[A-Za-z]{3}", b["t"]) and not CARD_WORDS.match(b["t"])]
    caps = [b for b in band if not re.search(r"[a-z]", b["t"])]
    pool = caps or band
    if pool:
        h = max(b["y1"] - b["y0"] for b in pool)
        big = sorted((b for b in pool if b["y1"] - b["y0"] >= 0.35 * h), key=lambda b: b["y0"])
        top = max(big, key=lambda b: b["y1"] - b["y0"])
        run = [top]   # the biggest line plus big lines right next to it (two-line titles)
        for b in big[big.index(top) + 1:]:
            if b["y0"] - run[-1]["y1"] < 0.05 * H: run.append(b)
            else: break
        for b in reversed(big[:big.index(top)]):
            if run[0]["y0"] - b["y1"] < 0.05 * H: run.insert(0, b)
            else: break
        out["title"] = card_title(" ".join(b["t"] for b in run))
        below = sorted((b for b in band if b["y0"] >= run[-1]["y1"] - 0.02 * H and b not in run and re.search(r"[a-z]", b["t"])), key=lambda b: b["y0"])
        if below and below[0]["y0"] - run[-1]["y1"] < 0.06 * H:
            out["sub"] = re.sub(r",(?=\S)", ", ", below[0]["t"])
    return out


def picture_recipes(subject, title, photo_paths):
    """(cards, separate): cards = [(photo path, card info)].
    Numbered recipe cards ('1/8' ... '8/8', each number once) -> separate recipes in card order, titled from each card.
    Anything else (one picture, or photos of one dish) -> one recipe called `title`, pictures in email order."""
    cards = [(p, read_card(p)) for p in photo_paths]
    nums = [c["n"] for _, c in cards]
    separate = len(cards) > 1 and all(nums) and len(set(nums)) == len(nums)
    if separate:
        cards.sort(key=lambda pc: pc[1]["n"])
        for k, (p, c) in enumerate(cards, 1):
            c["title"] = PICTURE_TITLES.get((subject.strip().lower(), c["n"])) or c["title"] or f"Recipe {k}"
    else:
        for p, c in cards:
            c["title"], c["sub"] = title, ""
    return cards, separate


def pictures_pdf(title, cards, files, source, pdf_path, separate=True):
    e = _html.escape
    secs = "".join(f'<section{"" if separate or k else " class=first"}><h2>{e(c["title"]) if separate else ""}</h2>' + (f'<p class="sub">{e(c["sub"])}</p>' if c["sub"] else "")
                   + f'<img src="{e(f)}"></section>' for k, ((p, c), f) in enumerate(zip(cards, files)))   # one picture-recipe starts on page 1
    toc = "".join(f"<li>{e(c['title'])}</li>" for _, c in cards) if separate else ""
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
      @page{{size:letter;margin:0.45in}}
      body{{font-family:Georgia,serif;color:#222;font-size:11.5pt;margin:0}}
      h1{{font-size:22pt;margin:0 0 6px}} .src{{color:#666;font-size:9pt}}
      section{{page-break-before:always;text-align:center}}
      section.first{{page-break-before:auto;margin-top:10px}} section.first img{{max-height:8.1in}}
      h2{{font-size:16pt;margin:0 0 2px}} .sub{{font-style:italic;margin:0 0 8px;color:#555}}
      img{{max-width:100%;max-height:8.6in;display:block;margin:0 auto;border-radius:6px}}
      </style></head><body><h1>{e(title)}</h1>{f"<p><b>{len(cards)} recipes:</b></p><ol>{toc}</ol>" if separate else ""}
      <p class="src">Source: {e(source)}. {"Each recipe is a picture - the next pages show them in order." if separate else
      "The recipe is in the picture" + ("s" if len(cards) > 1 else "") + " below."}</p>{secs}</body></html>"""
    tmp = os.path.splitext(pdf_path)[0] + ".print.html"
    open(tmp, "w", encoding="utf-8").write(page)
    try:
        subprocess.run([rc.CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                        f"--print-to-pdf={pdf_path}", "file:///" + tmp.replace("\\", "/")], capture_output=True, timeout=180)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2000


def has_recipe_text(lines):
    """Is there writing of its own in the email? Picture recipes are emails with (almost) none: a few words at most."""
    return sum(len(l.split()) for l in lines) >= 15


def to_pdf(title, desc, recipes, notes, source, image, pdf_path):
    e = _html.escape
    def note_html(n):
        if "\n- " not in n:
            return f'<section><p class="tip">{e(n)}</p></section>'
        head, _, items = n.partition("\n")
        lis = "".join(f"<li>{e(x[2:])}</li>" if x.startswith("- ") else f"</ul><p>{e(x)}</p><ul>" for x in items.split("\n"))
        return f'<section><h3>{e(head.rstrip(":"))}</h3><ul>{lis}</ul></section>'.replace("<ul></ul>", "")
    def one(r):
        info = " &nbsp;·&nbsp; ".join(f"<b>{e(k)}</b> {e(v)}" for k, v in r["info"])
        ing = "".join((f"<h4>{e(g)}</h4>" if g else "") + "<ul>" + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>" for g, items in r["groups"])
        steps = "".join(f"<li>{e(s)}</li>" for s in r["steps"])
        tip = f'<p class="tip"><b>{e(r["tip_label"])}:</b> {e(" ".join(r["tips"]))}</p>' if r["tips"] else ""
        return f'<section><h2>{e(r["name"])}</h2><div class="info">{info}</div><div class="cols"><div><h3>Ingredients</h3>{ing}</div>' \
               f'<div>{f"<h3>Method</h3><ol>{steps}</ol>" if steps else ""}</div></div>{tip}</section>'
    img = f'<img src="{os.path.basename(image)}">' if image else ""
    toc = "".join(f"<li>{e(r['name'])}</li>" for r in recipes)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
      body{{font-family:Georgia,serif;margin:24px 32px;color:#222;font-size:11.5pt;line-height:1.35}}
      h1{{font-size:21pt;margin:0 0 6px}} .desc{{font-style:italic}} .src{{color:#666;font-size:9pt}}
      img{{max-width:100%;max-height:520px;display:block;margin:10px auto;border-radius:6px}}
      section{{break-inside:avoid;page-break-inside:avoid;border-top:1px solid #ccc;margin-top:14px;padding-top:6px}}
      h2{{font-size:15pt;margin:4px 0}} h3{{font-size:12pt;margin:6px 0 2px}} h4{{margin:6px 0 0;font-size:11pt}}
      .info{{font-size:10.5pt;margin-bottom:4px}} .cols{{display:grid;grid-template-columns:2fr 3fr;gap:18px}}
      ul,ol{{margin:2px 0;padding-left:20px}} li{{margin:2px 0}} .tip{{background:#f6f1ea;padding:5px 8px;border-radius:4px}}
      </style></head><body><h1>{e(title)}</h1><div class="desc">{e(desc)}</div>{img}
      <p><b>{len(recipes)} recipes:</b></p><ol>{toc}</ol>{"".join(one(r) for r in recipes)}
      {"".join(note_html(n) for n in notes)}<p class="src">Source: {e(source)}</p></body></html>"""
    tmp = os.path.splitext(pdf_path)[0] + ".print.html"
    open(tmp, "w", encoding="utf-8").write(page)
    try:
        subprocess.run([rc.CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                        f"--print-to-pdf={pdf_path}", "file:///" + tmp.replace("\\", "/")], capture_output=True, timeout=120)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2000


def export_email(words):
    """Read-only export of the newest email in Email/Recipes whose subject contains the words."""
    os.makedirs(STAGE, exist_ok=True)
    n = 1 + max([int(x) for x in os.listdir(STAGE) if x.isdigit()] or [0])
    d = os.path.join(STAGE, f"{n:04d}")
    ps = r"""
$words = $args[0]; $d = $args[1]
$ol = New-Object -ComObject Outlook.Application; $ns = $ol.GetNamespace("MAPI"); $best = $null
foreach ($s in $ns.Stores) { $f = $s.GetRootFolder(); try { $f = $f.Folders.Item("Email").Folders.Item("Recipes") } catch { continue }
  foreach ($m in $f.Items) { if ($m.Class -eq 43 -and $m.Subject -like "*$words*" -and ($best -eq $null -or $m.ReceivedTime -gt $best.ReceivedTime)) { $best = $m; $store = $s; $fold = $f } } }
if ($best -eq $null) { "NOTFOUND"; exit }
New-Item -ItemType Directory -Force (Join-Path $d "attachments") | Out-Null
[IO.File]::WriteAllText((Join-Path $d "body.txt"), [string]$best.Body, [Text.Encoding]::UTF8)
[IO.File]::WriteAllText((Join-Path $d "body.html"), [string]$best.HTMLBody, [Text.Encoding]::UTF8)
$atts = @(); $i = 0
foreach ($a in $best.Attachments) { $i++; $name = ($a.FileName -replace '[\\/:*?"<>|]', '_'); if (-not $name) { $name = "attachment$i" }
  $p = Join-Path (Join-Path $d "attachments") ("{0:D2}_{1}" -f $i, $name); $a.SaveAsFile($p)
  $atts += @{ file = (Split-Path $p -Leaf); name = $a.FileName; size = (Get-Item $p).Length } }
$meta = [ordered]@{ store = $store.FilePath; folder = $fold.FolderPath; subject = [string]$best.Subject; sender = [string]$best.SenderName
  received = $best.ReceivedTime.ToString("yyyy-MM-dd HH:mm"); attachments = $atts }
[IO.File]::WriteAllText((Join-Path $d "meta.json"), ($meta | ConvertTo-Json -Depth 5), [Text.Encoding]::UTF8)
"OK"
"""
    script = os.path.join(STAGE, "_export_one.ps1")
    open(script, "w", encoding="utf-8-sig").write(ps)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, words, d], capture_output=True, text=True)
    if "OK" not in r.stdout:
        sys.exit(f"no email in Email/Recipes with \"{words}\" in the subject" if "NOTFOUND" in r.stdout else r.stderr[-500:])
    return d


def update_lists(title, slug, received):
    page = os.path.join(OUT, "email-recipes.md")
    txt = open(page, encoding="utf-8").read()
    head, _, rest = txt.partition("## Recipes (")
    _, _, items = rest.partition("\n")
    rows = [l for l in items.splitlines() if l.startswith("- [")]
    rows = [l for l in rows if f"]({L(slug + '.md')})" not in l] + [f"- [{title}]({L(slug + '.md')}) *({received})*"]
    rows.sort(key=lambda l: l[3:].lower())
    n = len(rows)
    head = re.sub(r"^(recipes|saved): \d+", lambda m: f"{m.group(1)}: {n}", head, flags=re.M)
    head = re.sub(r"\. \d+ recipes from", f". {n} recipes from", head)
    open(page, "w", encoding="utf-8").write(head + f"## Recipes ({n})\n\n" + "\n".join(rows) + "\n")
    coll = os.path.join(RESEARCH, "recipes", "personal-recipe-collection.md")
    c = open(coll, encoding="utf-8").read()
    c = re.sub(r"(\(personal-recipe-collection/email-recipes/email-recipes\.md\)) - \d+ recipes", rf"\1 - {n} recipes", c)
    open(coll, "w", encoding="utf-8").write(c)
    return n


INVISIBLE = re.compile("[\u200b-\u200f\u2060\ufeff\u034f\u00ad]")
FWD_HEAD = re.compile(r"^\s*From:.*\n(?:\s*\n)*\s*(?:Sent|Date):.*\n(?:\s*\n)*\s*To:.*\n(?:(?:\s*\n)*\s*Cc:.*\n)?(?:\s*\n)*\s*Subject:.*\n", re.M | re.I)


def unforward(body):
    """Text of a forwarded/replied email: when the part above the first 'From: / Sent: / To: / Subject:' header holds
    no recipe (just a signature, a confidentiality notice, 'see below'), keep only what follows the header."""
    body = INVISIBLE.sub("", body.replace("\r\n", "\n"))
    m = FWD_HEAD.search(body)
    if m:
        top = body[:m.start()]
        if not any(ING_HEAD.match(x.strip()) or STEPS.match(x.strip()) or ING_INLINE.match(x.strip()) for x in top.split("\n")):
            body = body[m.end():]
    return "\n".join("" if re.fullmatch(r"[\s.]+", l) else l for l in body.split("\n"))   # ". ‍ ‍ ‍" filler lines


def main():
    args = [a for a in sys.argv[1:] if a not in ("--force", "--check")]
    if "--dir" in args:   # rebuild from an earlier export (no Outlook)
        i = args.index("--dir"); d = args[i + 1]; del args[i:i + 2]
    elif args:
        d = export_email(" ".join(args))
    else:
        sys.exit(__doc__)
    m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8-sig"))
    body = open(os.path.join(d, "body.txt"), encoding="utf-8-sig").read()
    lines = er.clean_body(unforward(body), m["subject"])
    cut = next((i for i, l in enumerate(lines) if END.match(l)), len(lines))   # social-media footer: share/follow/hashtags
    lines = [l for l in lines[:cut] if l.strip()]
    received = m["received"][:10]
    blocks = split_recipes(lines)
    parsed = [(b, parse_block(b)) for b in blocks]
    if len(blocks) > 2 and not any(r for _, r in parsed):   # no recipe has a method: ingredient lists only ("6 Famous Southern BBQ Dinners")
        loose = [(b, parse_block(b, need_steps=False)) for b in blocks]
        if sum(1 for _, r in loose if r) >= 2: parsed = loose
    recipes = [r for _, r in parsed if r]
    intro = next((b for b, r in parsed if r is None), []) if parsed and parsed[0][1] is None else []
    tail = [x for b in [b for b, r in parsed[1:] if r is None and b] + [r["rest"] for _, r in parsed if r] for x in note_blocks(b)]
    notes = [note_text(b) for b in tail] if len(recipes) > 1 else []   # closing tips after the recipes
    multi = len(recipes) > 1
    if multi:
        heading = next((l for l in intro if is_heading(l)), None) or \
            next((l for l in intro[:1] if len(l) <= 90 and not l.endswith((".", "!", "?"))), None)   # "6 Saucy ... Better Than Takeout"
        title = heading_text(heading) if heading else er.title_of(m["subject"], lines)
        desc = " ".join(l for l in intro if l != heading)
        if not any(r["steps"] for r in recipes):
            desc = (desc + " " if desc else "") + "(The email lists the ingredients only - it gives no cooking steps.)"
    else:
        title, desc = er.title_of(m["subject"], lines), ""
    title = re.sub(r"\b(Bbq|Diy|Usa|Kfc|Blt)\b", lambda w: w.group(1).upper(), fbr.nice_title(title))
    slug = slugify(title)[:70] or "recipe"
    imgs = [a for a in m.get("attachments", []) if a.get("file") and a["name"].lower().endswith(er.IMG) and a.get("size", 0) >= 15000
            and not re.search(r"logo|signature|banner|facebook|twitter|instagram|pinterest|icon", a["name"], re.I)]
    pictures, separate = None, False
    if not multi and imgs and not has_recipe_text(lines):   # the recipes are the pictures
        pictures, separate = picture_recipes(m["subject"], title, [os.path.join(d, "attachments", a["file"]) for a in imgs])
    if "--check" in sys.argv and pictures:
        print(f"{title}  ({len(pictures)} picture recipes)" if separate else f"{title}  (1 recipe in {len(pictures)} picture{'s' if len(pictures) > 1 else ''})")
        for p, c in pictures:
            print(f"   - {c['title']}" + (f"  [card {c['n']}/{c['total']}]" if c["n"] else "") + (f"  - {c['sub']}" if c["sub"] else "")
                  + f"  ({len(c['text'].split())} words read)")
        return
    if "--check" in sys.argv:   # show what would be saved, write nothing
        print(f"{title}  ({len(recipes)} recipes)" + (f"\n  intro: {desc[:100]}" if multi and desc else ""))
        for r in recipes if multi else []:
            print(f"   - {r['name']}: " + ", ".join(f"{g or 'Ingredients'} {len(i)}" for g, i in r["groups"])
                  + f"; {len(r['steps'])} steps; info {[k for k, _ in r['info']]}" + ("; tip" if r["tips"] else ""))
        for n in notes: print(f"  closing note: {n[:90]}")
        return
    if os.path.exists(os.path.join(OUT, slug + ".md")) and "--force" not in sys.argv:
        sys.exit(f"already in the collection: email-recipes/{slug}.md  (use --force to replace it)")
    for f in os.listdir(OUT):   # replacing: drop the earlier copy's files
        if re.match(re.escape(slug) + r"(-\d+)?\.(md|pdf|jpg|jpeg|png|gif|webp)$", f): os.remove(os.path.join(OUT, f))
    if pictures:   # copy in recipe order
        imgs = [next(a for a in imgs if os.path.join(d, "attachments", a["file"]) == p) for p, _ in pictures]
    photos = []
    for k, a in enumerate(imgs, 1):
        fn = slug + (f"-{k}" if len(imgs) > 1 else "") + os.path.splitext(a["name"])[1].lower()
        shutil.copy2(os.path.join(d, "attachments", a["file"]), os.path.join(OUT, fn)); photos.append(fn)
    src = f"Recipe email received {received}"
    meta = {"title": title, "category": "recipes", "source_type": "email-recipe", "file": slug + ".pdf",
            "publisher": "Personal email", "source_url": None, "collection": "personal-recipe-collection",
            "provenance": f"Outlook folder Email/Recipes, received {received} (added with 64_add_email_recipe.py)",
            "license": "Personal recipe collection - personal use", "received": received,
            "photos": len(photos), "videos": 0, "compiled": TODAY, "date_added": received, "date_source": "email received"}
    if pictures:
        meta["recipes_are_pictures"] = True
        if separate:
            meta["recipes"] = len(pictures); meta["recipe_names"] = [c["title"] for _, c in pictures]
        meta["provenance"] += "; recipe text read from the picture" + ("s" if len(pictures) > 1 else "") + " by RapidOCR"
        ok = pictures_pdf(title, pictures, photos, src, os.path.join(OUT, slug + ".pdf"), separate)
        md = [f"# {title}\n", f"*Recipe email, {received}.*  "]
        if ok: md.append(f"**Recipe PDF:** [{slug}.pdf]({L(slug + '.pdf')})  ")
        note = "the text under each picture was read from it - check the picture for exact amounts"
        if separate:
            md += ["", f"**{len(pictures)} recipes** (each is a picture; {note}):", ""]
            md += [f"{n}. [{c['title']}](#{slugify(c['title'])})" for n, (_, c) in enumerate(pictures, 1)] + [""]
        else:
            md += ["", f"*The recipe is in the picture{'s' if len(pictures) > 1 else ''} below; {note}.*", ""]
        for (p, c), f in zip(pictures, photos):
            if separate:
                md += [f"## {c['title']}", ""] + ([f"*{c['sub']}*", ""] if c["sub"] else [])
            md += [f"![{c['title']}]({L(f)})", ""]
            if c["text"]:
                md += ["```text", c["text"], "```", ""]
    elif multi:
        meta["recipes"] = len(recipes); meta["recipe_names"] = [r["name"] for r in recipes]
        ok = to_pdf(title, desc, recipes, notes, src, os.path.join(OUT, photos[0]) if photos else None, os.path.join(OUT, slug + ".pdf"))
        md = [f"# {title}\n", f"*Recipe email, {received}.*  "]
        if ok: md.append(f"**Recipe PDF:** [{slug}.pdf]({L(slug + '.pdf')})  ")
        md += [""] + [f"![{title}]({L(p)})" for p in photos] + [""]
        if desc: md += [desc, ""]
        md += [f"**{len(recipes)} recipes:**", ""] + [f"{n}. [{r['name']}](#{slugify(r['name'])})" for n, r in enumerate(recipes, 1)] + [""]
        for r in recipes: md += recipe_md(r)
        for n in notes:
            if "\n- " in n:
                head, _, items = n.partition("\n")
                md += [f"### {head.rstrip(':')}", "", items, ""]
            else:
                md += [f"> {n}", ""]
    else:
        rec = fbr.post_recipe("\n".join(lines))
        if rec is None:
            rec = {"name": "", "description": "", "image": None, "yield": "", "prep": None, "cook": None, "total": None,
                   "ingredients": [], "instructions": [], "article": lines, "notes": [], "video": None, "method": "recipe as written in the email"}
        main_name = re.sub(r"\s*\(.*?\)\s*$", "", title)
        rec["ingredients"] = [x.replace("{MAIN}", main_name) for x in rec["ingredients"]]
        rec["instructions"] = [x.replace("{MAIN}", main_name) for x in rec["instructions"]]
        ok = rc.to_pdf(rec, title, src, os.path.join(OUT, photos[0]) if photos else None, os.path.join(OUT, slug + ".pdf"))
        md = [f"# {title}\n", f"*Recipe email, {received}.*  "] + ([f"**Recipe PDF:** [{slug}.pdf]({L(slug + '.pdf')})  "] if ok else [])
        md += [""] + [f"![{title}]({L(p)})" for p in photos] + ["", rc.to_markdown(rec)]
    if not ok: meta["file"] = None
    open(os.path.join(OUT, slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + "\n".join(md).rstrip() + "\n")
    n = update_lists(title, slug, received)
    for script in ("20_catalog.py", "21_readme.py"):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), script)], capture_output=True)
    print(f"added: {title}  ->  email-recipes/{slug}.md" + (" (+ PDF)" if ok else "") + (f" (+ {len(photos)} photo)" if photos else ""))
    if pictures and separate:
        print(f"  {len(pictures)} picture recipes in it:")
        for _, c in pictures:
            print(f"   - {c['title']}")
    elif pictures:
        print(f"  the recipe is in {len(pictures)} picture(s); their text was read by OCR")
    if multi:
        print(f"  {len(recipes)} recipes in it:")
        for r in recipes:
            print(f"   - {r['name']}: {sum(len(i) for _, i in r['groups'])} ingredients"
                  + (f" in {len(r['groups'])} groups" if len(r["groups"]) > 1 else "") + f", {len(r['steps'])} steps" + (", tip" if r["tips"] else ""))
    print(f"email list: {n} recipes")


if __name__ == "__main__":
    main()
