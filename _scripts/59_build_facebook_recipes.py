"""Rebuild recipes/personal-recipe-collection/facebook-saved/ like the bookmark folders: one entry per recipe
(.md + clean PDF + photo/video), and a facebook-saved.md list page. Only recipes that are available offline are kept.

Sources, per item of the Facebook "Saved > Food" page:
  Post  -> its "Full Recipe" link when there is one (recipe page extracted like a bookmark), else the recipe written in
           the post itself (needs ingredients and steps); other posts are dropped
  Link  -> the clean recipe already saved by 58_fetch_bookmarks.py (bookmarks/facebook-links), moved in
  Video -> the downloaded video, one entry each
The original saved page is kept in facebook-saved/original-saved-page/.

  _scripts\\.venv\\Scripts\\python _scripts\\59_build_facebook_recipes.py [--apply]
"""
import collections, importlib, json, os, re, shutil, sys
from urllib.parse import quote, urlparse
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter, slugify
import fb_saved, recipe_clean as rc

bm = importlib.import_module("58_fetch_bookmarks")
COLL = os.path.join(RESEARCH, "recipes", "personal-recipe-collection")
FB = os.path.join(COLL, "facebook-saved")
NEW = os.path.join(COLL, "facebook-saved.new")
ORIG = "original-saved-page"
L = lambda p: quote(p.replace(os.sep, "/"), safe="/")
URL = re.compile(r"https?://[^\s)\]]+")
PROMO = re.compile(r"members who exchange|join (our|the) (backup )?group|please (join|share|say hi)|follow (me|us)|"
                   r"don.?t lose this recipe|a recipe you don.?t wann|^full recipe\s*:?|^recipe\s*:?\s*https?|#\w+", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def nice_title(t):
    import unicodedata
    t = unicodedata.normalize("NFKC", t)   # 𝗕𝘂𝘁𝘁𝗲𝗿 (mathematical bold) -> Butter
    t = EMOJI.sub("", re.sub(r"[*#_]+", "", t))
    t = re.sub(r"\s*[-–~|:]\s*(don.?t? lose this recipe|a recipe you don.?t? wann\w*.*)$", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -–~:!.")
    if not re.search(r"[a-z]", t):   # SHOUTED TITLE / mathematical bold letters
        t = t.title()
    return t[:90] or "Saved recipe"


TITLE_FIX = {   # start of the Facebook title -> the dish (posts whose first sentence is not the recipe name)
    "INDIAN FRYBREAD": "Indian Frybread",
    "My famous homemade shepherds pie": "Homemade Shepherd's Pie",
    "No-Bake Pineapple Cream Dessert": "No-Bake Pineapple Cream Dessert",
    "Homemade Krispy Kremes": "Homemade Krispy Kremes",
    "Four Layer Delight": "Four Layer Delight",
    "3-4 russet potato": "Baked Loaded Potato Slices",
    "I had some requests for my Copycat Panda": "Copycat Panda Express Cream Cheese Rangoons",
    "I air fried these babies": "Air Fryer Chicken Wings",
    "Edit: I got about 15 cups of pumpkin": "Instant Pot Pumpkin Puree",
    "Instant Pot **sesame chicken": "Instant Pot Sesame Chicken",
    "Good with graham crackers": "Cream Cheese Marshmallow Fluff Dip",
    "This would be so Good Christmas Morning": "Cherry Bars",
    "Canned pumpkin shortage": "Instant Pot Whole Pie Pumpkin Puree",
    "I was a kid who grew up on beans": "Instant Pot Pinto Beans (No Soak)",
    "Be Alert!! If you're active": "Best Chocolate Chip Cookies",
    "OUTNUMBERED ~ ONE HOUR CINNAMON ROLLS": "One Hour Cinnamon Rolls",
    "BEST EVER Chicken and Rice Casserole": "Best Ever Chicken and Rice Casserole",
}


def post_title(title, text):
    """Facebook gives the post's first sentence as its title; prefer the dish name when the post states one."""
    for k, v in TITLE_FIX.items():
        if title.strip().lstrip("#* ").startswith(k):
            return v
    t = nice_title(title)
    chatty = len(t) > 45 or re.search(r"[!?]|^(i |my |this |these |good |edit|be alert|had some|sounds)", t, re.I)
    if not chatty:
        return t
    for l in [title] + text.splitlines()[:12]:
        if not re.search(r"[A-Za-z]{3}", l):
            continue
        l = nice_title(l)
        if 4 <= len(l) <= 50 and not re.search(r"[!?]|https?:|^(i |my |this |these |edit|be alert|ingredients?|directions?)", l, re.I) \
                and not rc.MEASURE.search(l[:30]) and re.search(r"[A-Za-z]{4}", l):
            return l
    m = re.search(r"(best|easy|homemade|copycat|famous)?\s*([A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+){1,5})", title)
    return nice_title(m.group(0)) if m else t[:45].rsplit(" ", 1)[0]


def full_recipe_links(text, common_urls):
    """URLs in the post that lead to the full recipe (the group-invite link shared by every post is ignored)."""
    out = []
    for u in URL.findall(text):
        u = u.rstrip(".,!;")
        if u in common_urls or re.search(r"facebook\.com|pinterest\.|instagram\.com", u):
            continue
        out.append(u)
    return out


PART_WORDS = (r"sauce|chicken|beef|pork|meat|fish|shrimp|glaze|rub|marinade|filling|dough|crust|topping|frosting|icing|"
              r"dressing|batter|gravy|broth|base|cake|bars?|cookies?|rice|beans|vegetables|veggies|syrup|streusel|crumble|"
              r"assembly|to assemble|to serve|serving|garnish|dip|salsa|seasoning|spice mix|brine|cure")
PART_HEAD = re.compile(rf"^(?P<h>(for the |the )?([A-Z][\w'’&/ ]{{0,28}}?\b)?({PART_WORDS})(\s+[\w'’&/]+){{0,2}})\s*(:\s*(?P<n1>.*)|\s+[–-]\s+(?P<n2>.+))?$", re.I)
SEPARATOR = re.compile(r"^[-_=~*•.]{3,}$")


def _part_head(l):
    """'Chicken', 'Sauce:', 'Apple Cider Glaze:', 'Sauce – once chicken is done ...' -> (heading, note) or None."""
    m = PART_HEAD.match(l)
    if not m or rc.MEASURE.search(l[:25]) or m.group("h").rstrip().endswith("."):
        return None
    words = m.group("h").split()
    core = [w for w in words if w.lower() not in ("for", "the")]
    part = re.compile(rf"^({PART_WORDS})$", re.I)
    if len(words) > 4 or not core:
        return None
    if m.group("n2") is not None and (not part.match(words[0]) or len(words) > 3):   # "Sauce – note": starts with the part
        return None
    if m.group("n1") is None and m.group("n2") is None and not (len(core) <= 3 and part.match(core[-1])):
        return None   # a bare line must be a short part name ("Chicken", "Apple Cider Glaze")
    return smart_title(m.group("h").strip()), (m.group("n1") or m.group("n2") or "").strip()


def _split(lines):
    """Ingredient lines vs step lines of one recipe part (same rules as a single-part recipe)."""
    ing, ins, mode = [], [], None
    lines = [re.sub(r"^[-•*]\s+", "", l) for l in lines]
    qty = re.compile(r"^(\d+(\s*[-/]\s*\d+)?(\s+\d/\d)?|\d+\s+(or|to)\s+\d+|[½¼¾⅓⅔⅛]|one|two|three|a few|a pinch|pinch)\s+\S", re.I)
    for l in lines:
        is_qty = qty.match(l) and not re.match(r"^\d+\s*[.)]\s", l) and len(l) < 100   # "2 egg whites", "3 or 4 chicken breasts"
        if is_qty or (rc.MEASURE.search(l[:40]) and len(l) < 120 and mode != "ins") \
                or (mode is None and re.match(r"^(oil|salt|pepper|kosher salt|water)\b", l, re.I) and len(l) < 60):
            ing.append(l); mode = "ing"
        elif mode in ("ing", "ins") or ing:
            ins.append(l); mode = "ins"
        else:
            ins.append(l)
    return ing, ins


def sectioned_recipe(lines):
    """Recipes written in parts (Chicken / Sauce, Crust / Filling, Rub / Glaze ...): one recipe, ingredients and steps
    grouped per part. Prose before the first part becomes the description; parts without ingredients after them become
    the finishing steps."""
    segs, cur = [], [None, None, []]
    for l in lines:
        if SEPARATOR.match(l):
            if cur[2] or cur[0]: segs.append(cur)
            cur = [None, None, []]; continue
        h = _part_head(l)
        if h:
            if cur[2] or cur[0]: segs.append(cur)
            cur = [h[0], h[1], []]; continue
        cur[2].append(l)
    if cur[2] or cur[0]: segs.append(cur)
    named = [s for s in segs if s[0] and any(rc.MEASURE.search(x[:40]) for x in s[2])]
    if len(named) < 2:
        return None
    desc, ing, ins, seen_part = [], [], [], False
    for head, note, body in segs:
        has_ing = any(rc.MEASURE.search(x[:40]) for x in body)
        if not has_ing and not seen_part:   # intro / planning notes before the recipe parts
            desc += ([head] if head and not body else []) + body; continue
        if not has_ing:   # after the parts: combining, serving, tips
            ins.append(f"**{head or 'Finish'}**"); ins += ([note] if note else []) + body; continue
        seen_part = True
        i, s = _split(body)
        ing.append(f"**{head or 'Ingredients'}**"); ing += i
        ins.append(f"**{head or 'Steps'}**"); ins += ([note[:1].upper() + note[1:]] if note else []) + s
    return {"name": "", "description": " ".join(desc), "image": None, "yield": "", "prep": None, "cook": None, "total": None,
            "ingredients": ing, "instructions": ins, "notes": [], "video": None, "method": "recipe written in parts"}


ING_LINE = re.compile(r"^((the )?ingredients?( you('|’)ll need| needed| list)?|what you('|’)ll need|what you need|you('|’)ll need)\s*:?$", re.I)
INS_LINE = re.compile(r"^(directions?|instructions?|method|preparation|steps|how to make( it)?|to make)\s*:?$", re.I)


def smart_title(s):
    """'BBQ CHICKEN RUB' -> 'BBQ Chicken Rub' (short all-caps words stay acronyms)."""
    keep = {"BBQ", "BLT", "IP", "XL", "USA", "KFC", "PB&J", "BBQ'D"}
    return " ".join(w if w.upper() in keep else w.capitalize() for w in s.split())


def block_recipe(lines):
    """Several complete recipes in one text, each with its own Ingredients/Instructions headings (e.g. a rub, the
    main dish, an alternative rub): one recipe whose parts are named after the title line above each block."""
    heads = [i for i, l in enumerate(lines) if ING_LINE.match(l)]
    if len(heads) < 2:
        return None
    blocks, starts = [], []
    for h in heads:   # the part's title: nearest ALL-CAPS line above its Ingredients heading (description lines between)
        t = next((j for j in range(h - 1, max(-1, h - 9), -1)
                  if lines[j].isupper() and 1 <= len(lines[j].split()) <= 7 and not rc.MEASURE.search(lines[j])), None)
        starts.append(t if t is not None else h)
    desc = [l for l in lines[:starts[0]]]
    note = ""
    for n, (s, h) in enumerate(zip(starts, heads)):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        title = smart_title(lines[s]) if s != h else f"Part {n + 1}"
        about = lines[s + 1:h] if s != h else []
        body = lines[h + 1:end]
        k = next((i for i, l in enumerate(body) if INS_LINE.match(l)), None)
        ing, ins = (body[:k], body[k + 1:]) if k is not None else _split(body)
        nxt_note = ""
        if ins and ins[-1].endswith(":") and n + 1 < len(starts):   # "Another Rub that can be used:" introduces the next part
            nxt_note = ins.pop()
        blocks.append((title + (f" ({note.rstrip(':').lower()})" if note else ""), about, ing, ins))
        note = nxt_note
    ingl, insl = [], []
    for title, about, ing, ins in blocks:
        ingl += [f"**{title}**"] + ing
        insl += [f"**{title}**"] + ins
    return {"name": "", "description": " ".join(desc), "image": None, "yield": "", "prep": None, "cook": None, "total": None,
            "ingredients": ingl, "instructions": insl, "notes": [], "video": None, "method": "recipe written in parts"}


QTY = re.compile(r"^(\d+(\s*[-/]\s*\d+)?(\s+\d/\d)?|\d+\s+(or|to)\s+\d+|[½¼¾⅓⅔⅛]|one|two|three|a few|a pinch|pinch)[\s-]+\S", re.I)
STEP_START = re.compile(r"^(in|on|to|combine|place|stir|mix|add|pour|bake|cook|heat|preheat|remove|let|serve|put|bring|turn|"
                        r"take|cover|brush|spread|fill|rim|shake|blend|whisk|beat|cut|slice|chop|season|sprinkle|store|garnish|"
                        r"i|we|you|use|drain|rinse|melt|fry|grill|smoke|inject|transfer|discard|return|top|layer|roll|fold|"
                        r"refrigerate|chill|freeze|boil|simmer|saut[eé]|wrap|insert|repeat|when|while|once|after|before|then|"
                        r"if|note|build|rub|marinate|this|these|it|there|talk|and|so|press|spoon|dip|toss|set|allow|make|prepare|line|"
                        r"grease|spray|flip|carefully|gently|slowly|lightly|generously|evenly|quickly|first|next|finally|meanwhile)\b", re.I)
YIELD = re.compile(r"^(makes|serves|yields?|servings?)\b", re.I)


def _is_step(l):
    return bool(STEP_START.match(l)) or l.startswith("(") or bool(re.search(r"\b(I|I'm|I've|my|we)\b", l)) \
        or len(re.findall(r"[.!?](\s|$)", l)) >= 2 or (l.endswith(".") and len(l) > 60)


def _is_ing(l, in_ing=False):
    if len(l) > 110:
        return False
    if QTY.match(l) and not re.match(r"^\d+\s*[.)]\s", l) and not STEP_START.match(l):
        return True   # starts with an amount: an ingredient, even with a note ("2 jars apple jelly (I used Plum Jelly)")
    if _is_step(l):
        return False
    if (QTY.match(l) and not re.match(r"^\d+\s*[.)]\s", l)) or rc.MEASURE.search(l[:40]):
        return True
    return in_ing and len(l) <= 40 and len(l.split()) <= 5 and not l.endswith((".", ":"))   # "Cherry", "Orange slice"


META = re.compile(r"\b(prep|total|cook|active|inactive)( time)?\b|\brating|\bpin\b|\bprint|\bvideo\b|next recipe|details|"
                  r"submit|cancel|amount per|nutrition|calories|servings?\b|yield|difficulty|recommended tools|level:|"
                  r"\d+(\.\d+)?k\b|share|tweet|jump to|=20", re.I)


def _title_like(l):
    words = [w for w in re.findall(r"[A-Za-z’']+", l) if len(w) > 3 and w.lower() not in ("with", "from", "your", "this", "that")]
    return l[:1].isupper() and (l.isupper() or not words or sum(w[0].isupper() for w in words) >= max(1, len(words) * 0.6))


def _is_head(lines, i):
    """A part title: a short name line followed (within a few description lines) by its ingredients or a yield line."""
    l = lines[i]
    if META.search(l) or l.startswith(("-", "#", "•")) or re.match(r"^\d", l) or _is_step(l) \
            or re.search(r"\d+(/\d+)?\s*[A-Za-z]{0,3}\.?$", l):   # "Garlic Salt 1/2 C": an ingredient written name-first
        return False
    if not re.match(r"^for ", l, re.I) and re.search(r"\b(salt|pepper|taste|juice|zest|optional|pinch|dash|drops|parsley|"
                                                   r"to season|for (deep[- ])?frying|for dusting|for garnish)\b", l, re.I):
        return False
    prev = lines[i - 1] if i > 0 else ""
    if prev and _is_ing(prev) and not (_part_head(l) or re.match(r"^for (the )?[A-Za-z]", l, re.I)):
        return False   # inside an ingredient list only a real part name ("Frosting", "For the sauce") starts a new part
    if _part_head(l):
        return True
    if not _title_like(l) or re.search(r"\b(salt|pepper|taste|juice|zest|optional|pinch|dash|drops|to season|for (deep[- ])?frying|for dusting|for garnish)\b", l, re.I):
        return False
    if not (2 <= len(l) <= 50 and len(l.split()) <= 6) or l.endswith((".", ",", ";")) or rc.MEASURE.search(l[:25]) \
            or ING_LINE.match(l) or INS_LINE.match(l) or YIELD.match(l) or QTY.match(l) or _is_step(l) or ":" in l.rstrip(":"):
        return False
    for j in range(i + 1, min(i + 6, len(lines))):
        n = lines[j]
        if ING_LINE.match(n) or YIELD.match(n):
            return True
        if _is_ing(n):
            return j == i + 1          # ingredients right under the title
        if INS_LINE.match(n) or (len(n) < 40 and not n.endswith((".", "!", "?"))):
            return False               # steps, or another short line: not a part title
    return False                       # (longer lines in between are the part's description)


def parse_parts(lines):
    """Recipes made of sub-recipes or parts (Rub / Injection / Sauce / Glaze + the main recipe; Chicken / Sauce; several
    drinks in one article): one recipe, ingredients and steps grouped per part. A part starts at a short title line
    followed by its ingredients or yield; a new ingredient list after steps (without a title) is the main recipe."""
    parts, desc, cur, sep = [], [], None, False

    def new(title):
        p = {"title": title, "yield": "", "note": [], "ing": [], "ins": [], "mode": None}
        parts.append(p); return p

    for i, l in enumerate(lines):
        if SEPARATOR.match(l):
            sep = True; continue
        just_titled = cur is not None and cur["title"] and not (cur["ing"] or cur["ins"] or cur["note"] or cur["yield"])
        if _is_head(lines, i) and not just_titled:   # "Chicken" then "Oil for deep frying": the second line is content
            h = _part_head(l)
            title, note = (h if h else (smart_title(l.rstrip(":")) if l.isupper() else l.rstrip(":").strip(), ""))
            if cur and cur["ins"]:
                last = cur["ins"][-1]
                if last.endswith(":") and len(last) < 60:   # "Another Rub that can be used:"
                    cur["ins"].pop(); title += f" ({last.rstrip(':').lower()})"
                elif len(last) > 60 and any(w.lower() in last.lower() for w in re.findall(r"[A-Za-z]{4,}", title)):
                    cur["ins"].pop()   # the article's sentence introducing this part
            cur = new(title); sep = False
            if note: cur["note"].append(note[:1].upper() + note[1:])
            continue
        if ING_LINE.match(l):
            if cur is None or cur["ins"]: cur = new(None)
            cur["mode"] = "ing"; continue
        if INS_LINE.match(l):
            if cur is None: cur = new(None)
            cur["mode"] = "ins"; continue
        if cur and YIELD.match(l) and not cur["ing"]:
            cur["yield"] = l; continue
        if _is_ing(l, cur is not None and (cur["mode"] == "ing" or (cur["mode"] is None and cur["title"] and not cur["note"]))):
            if cur is None or sep:
                cur = new(None); sep = False
            elif cur["mode"] == "ins":   # ingredients after steps without a title: the main recipe - only in a recipe that
                run = 0                   # already has named parts, and only for a real ingredient list (2+ lines)
                for x in lines[i:i + 3]:
                    if _is_ing(x): run += 1
                    else: break
                if run >= 2 and any(p["title"] for p in parts):
                    cur = new(None)
                else:
                    cur["ins"].append(l); continue
            cur["ing"].append(re.sub(r"^[-•*]\s+", "", l)); cur["mode"] = "ing"; continue
        if not any(p["ing"] for p in parts):
            desc.append(l); continue
        if sep:
            cur = new("Finish"); sep = False; cur["mode"] = "ins"
        if cur["mode"] is None and not cur["ing"]:
            cur["note"].append(l); continue   # description under a part title
        cur["ins"].append(l); cur["mode"] = "ins"
    parts = [p for p in parts if p["ing"] or p["ins"]]
    merged = []   # an untitled part in the middle continues the part above it
    for k, p in enumerate(parts):
        if merged and p["title"] is None and 0 < k < len(parts) - 1:
            merged[-1]["ing"] += p["ing"]; merged[-1]["ins"] += p["note"] + p["ins"]
        else:
            merged.append(p)
    parts = merged
    if sum(1 for p in parts if p["ing"]) < 2 or not any(p["title"] and p["title"] != "Finish" for p in parts):
        return None   # not really a multi-part recipe
    ing, ins, n_unnamed = [], [], 0
    for k, p in enumerate(parts):
        t = p["title"] or ("{MAIN}" if k == len(parts) - 1 or not any(q["title"] is None for q in parts[k + 1:]) else f"Part {k + 1}")
        if p["yield"]: t += f" ({p['yield'][0].lower() + p['yield'][1:]})"
        if p["ing"]: ing += [f"**{t}**"] + p["ing"]
        if p["ins"] or p["note"]: ins += [f"**{t}**"] + p["note"] + p["ins"]
    return {"name": "", "description": " ".join(desc), "image": None, "yield": "", "prep": None, "cook": None, "total": None,
            "ingredients": ing, "instructions": ins, "notes": [], "video": None, "method": "recipe written in parts"}


def post_recipe(text):
    """Split a recipe written in the post into ingredients / steps, or None when it is not a full recipe."""
    lines = [EMOJI.sub("", l).strip(" \t\u00a0•*–▪️✔️") for l in text.splitlines()]
    lines = [l for l in lines if l and not PROMO.search(l) and not URL.fullmatch(l)]
    if any(l.endswith(("...", "…")) for l in lines[-2:]):   # cut off by Facebook ("See more"): not complete
        return None
    parts = parse_parts(lines)
    if parts:
        return parts
    lines = [l.strip("-") for l in lines if not SEPARATOR.match(l)]
    ing, ins, mode, pre = [], [], None, []
    for l in lines:
        if ":" in l and not ING_LINE.match(l) and not INS_LINE.match(l):
            tail = l.split(":", 1)[1].strip()   # "Mix together:  1 box cake mix" -> the ingredient after the label
            if tail and _is_ing(tail) and not _is_ing(l.split(":", 1)[0]):
                l = tail
        if mode is None and not ing and _is_step(l) and not rc.MEASURE.search(l[:40]):
            pre.append(l); continue   # a step written before the ingredient list ("Lightly grease a 9x13 pan.")
        if rc.ING_HEAD.match(l.rstrip(":") + ":") or re.match(r"^ingredients?\b", l, re.I):
            mode = "ing"; rest = re.sub(r"^ingredients?\s*:?\s*", "", l, flags=re.I)
            if rest: ing.append(rest)
            continue
        if rc.STEP_HEAD.match(l) or re.match(r"^(directions?|instructions?|method|how to make)\b", l, re.I):
            mode = "ins"; rest = re.sub(r"^\w+\s*:?\s*", "", l)
            if rest and len(rest) > 15: ins.append(rest)
            continue
        if mode == "ing" or (mode is None and rc.MEASURE.search(l[:40]) and len(l) < 120):
            if mode is None: mode = "ing"
            if len(l) > 120 or (ing and not rc.MEASURE.search(l[:40]) and len(l) > 60):
                mode = "ins"; ins.append(l)
            else:
                ing.append(l)
        elif mode == "ins" or (mode is None and ing):
            mode = "ins"; ins.append(l)
    if not ins and sum(1 for l in ing if rc.MEASURE.search(l)) >= 3 and len(ing) <= 15:
        pass   # a drink / mix: measured ingredients are the whole recipe
    elif not (len(ing) >= 2 and ins):
        # a short "how I made it" post: cooking method with times/temperatures, kept as written
        how = " ".join(lines)
        if re.search(r"\b\d+\s*(min|mins|minutes|hours?|hrs?)\b|\d+\s*°|\bdegrees\b|\bhigh pressure\b|\bnatural release\b|\bNR\b", how, re.I) \
                and re.search(r"\b(bake|cook|air fr|fry|boil|simmer|pressure|roast|grill|smoke|mix|stir|season)", how, re.I) \
                and len(how.split()) >= 15:
            return {"name": "", "description": "", "image": None, "yield": "", "prep": None, "cook": None, "total": None,
                    "ingredients": [], "instructions": [], "article": lines, "notes": [], "video": None,
                    "method": "cooking method written in the Facebook post"}
        return None
    if ing:
        return {"name": "", "description": "", "image": None, "yield": "", "prep": None, "cook": None, "total": None,
                "ingredients": ing, "instructions": pre + ins, "notes": [], "video": None, "method": "recipe written in the Facebook post"}
    return None


def write_recipe(d, slug, title, rec, src_url, saved_from, kind, img=None, vid=None, extra_meta=None):
    pdf_ok = rc.to_pdf(rec, title, src_url or f"Facebook post saved from {saved_from}", os.path.join(d, img) if img else None,
                       os.path.join(d, slug + ".pdf"))
    meta = {"title": title, "category": "recipes", "source_type": "web-recipe" if src_url else "facebook-post",
            "file": slug + ".pdf" if pdf_ok else None, "publisher": saved_from, "source_url": src_url,
            "collection": "personal-recipe-collection", "provenance": f"Facebook Saved > Food item saved from {saved_from}; {kind}",
            "license": "Copyright of the original creator - personal offline copy, do not redistribute",
            "ingredients": len(rec.get("ingredients") or []), "steps": len(rec.get("instructions") or []), "compiled": TODAY,
            **(extra_meta or {})}
    md = [front_matter(meta), f"# {title}\n"]
    md.append(f"**Source:** <{src_url}>  " if src_url else f"**Source:** Facebook post saved from {saved_from}  ")
    md.append(f"*Extracted from: {kind}.*  ")
    if pdf_ok: md.append(f"**Recipe PDF:** [{slug}.pdf]({L(slug + '.pdf')})  ")
    if vid: md.append(f"**Recipe video:** [{vid}]({L(vid)})  ")
    md.append("")
    if img: md += [f"![{title}]({L(img)})", ""]
    md.append(rc.to_markdown(rec))
    open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


def main():
    apply = "--apply" in sys.argv
    html_dir = FB if any(f.lower().endswith(".html") for f in os.listdir(FB)) else os.path.join(FB, ORIG)
    page = os.path.join(html_dir, next(f for f in os.listdir(html_dir) if f.lower().endswith(".html")))
    items = fb_saved.parse(page)
    flog = json.load(open(os.path.join(FB, "fetch_log.json"), encoding="utf-8")) if os.path.exists(os.path.join(FB, "fetch_log.json")) else {}
    blog = json.load(open(bm.LOG, encoding="utf-8"))
    counts = collections.Counter(u.rstrip(".,!;") for i in items for u in URL.findall(i["text"]))
    common = {u for u, n in counts.items() if n >= 3}   # e.g. the group-invite link appended to every post
    plan, used = [], set()

    def slug_for(t):
        s = slugify(t)[:70] or "recipe"
        while s in used: s += "-2"
        used.add(s); return s

    for i in items:
        title = nice_title(i["title"])
        if i["kind"] == "Link":
            e = blog.get(i["url"], {})
            if e.get("status") == "ok":   # recipe found by the bookmark run
                plan.append(("link", i, e.get("title") or title, e))
        elif i["kind"] == "Video":
            e = flog.get(i["url"] or "", {})
            vf = os.path.join(FB, e.get("file") or "_none_")
            if e.get("status") == "ok" and os.path.isfile(vf):
                plan.append(("video", i, title, vf))
        elif i["kind"] == "Post" and i["text"].strip():
            links = full_recipe_links(i["text"], common)
            plan.append(("post", i, post_title(i["title"], i["text"]), links))
    print(f"{len(items)} saved items -> {sum(1 for p in plan if p[0]=='link')} recipe links, "
          f"{sum(1 for p in plan if p[0]=='video')} videos, {sum(1 for p in plan if p[0]=='post')} posts with text to check")
    if not apply:
        for k, i, t, x in plan:
            if k == "post": print(f"   post: {t[:50]:50} full-recipe links: {x}")
        return

    shutil.rmtree(NEW, ignore_errors=True); os.makedirs(NEW)
    rows = []
    for kind, i, title, x in plan:
        if kind == "link":   # render the recipe again from the page cache (same extractor as the bookmarks)
            slug = slug_for(title)
            r = bm.do_page(title, i["url"], NEW, slug, {"category": "recipes", "collection": "personal-recipe-collection",
                                                        "provenance": f"Recipe link saved on Facebook from {i['source']}",
                                                        "license": "Copyright of the original site - personal offline copy",
                                                        "compiled": TODAY})
            if r.get("status") == "ok":
                rows.append(("Recipe", r.get("title") or title, slug, i["source"], bool(r.get("video"))))
            else:
                used.discard(slug)
            print(f"   link {'kept   ' if r.get('status') == 'ok' else 'dropped'} {title[:60]}", flush=True)
        elif kind == "video":
            slug = slug_for(title)
            vid = slug + os.path.splitext(x)[1]
            shutil.copy2(x, os.path.join(NEW, vid))
            desc = i["text"].strip()
            meta = {"title": title, "category": "recipes", "source_type": "video", "file": vid, "publisher": i["source"],
                    "source_url": i["url"], "collection": "personal-recipe-collection",
                    "provenance": f"Facebook Saved > Food video saved from {i['source']}",
                    "license": "Copyright of the original creator - personal offline copy, do not redistribute", "compiled": TODAY}
            md = [front_matter(meta), f"# {title}\n", f"**Video:** [{vid}]({L(vid)})  ", f"**Source:** <{i['url']}>  ",
                  f"*Saved on Facebook from {i['source']}.*\n"] + (["## Description\n", desc] if desc else [])
            open(os.path.join(NEW, slug + ".md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
            rows.append(("Video", title, slug, i["source"], True))
        else:   # post: the full recipe behind its link, else the recipe written in the post
            done = False
            for u in x:
                slug = slug_for(title)
                r = bm.do_page(title, u, NEW, slug, {"category": "recipes", "collection": "personal-recipe-collection",
                                                     "provenance": f"Full-recipe link in a Facebook post saved from {i['source']}",
                                                     "license": "Copyright of the original site - personal offline copy",
                                                     "compiled": TODAY})
                if r.get("status") == "ok":
                    rows.append(("Recipe", r.get("title") or title, slug, i["source"], bool(r.get("video"))))
                    done = True; break
                used.discard(slug)
            if not done:
                rec = post_recipe(i["text"])
                if rec:
                    slug = slug_for(title)
                    write_recipe(NEW, slug, title, rec, None, i["source"], "recipe written in the Facebook post")
                    rows.append(("Recipe", title, slug, i["source"], False))
                    done = True
            print(f"   post {'kept   ' if done else 'dropped'} {title[:60]}", flush=True)

    # keep the original saved page (opens offline) in a subfolder
    dst = os.path.join(NEW, ORIG); os.makedirs(dst, exist_ok=True)
    for f in os.listdir(html_dir):
        if f.lower().endswith(".html") or f.endswith("_files"):
            p = os.path.join(html_dir, f)
            (shutil.copytree if os.path.isdir(p) else shutil.copy2)(p, os.path.join(dst, f))

    # list page
    rows.sort(key=lambda r: r[1].lower())
    nrec, nvid = sum(1 for r in rows if r[0] == "Recipe"), sum(1 for r in rows if r[0] == "Video")
    body = [f"# Facebook Saved Food Recipes\n",
            f"Part of [Personal Recipe Collection](../../personal-recipe-collection.md). Recipes and videos from the Facebook "
            f"\"Saved > Food\" collection that are available offline: {nrec} recipes (recipe, clean PDF, photo) and {nvid} videos. "
            f"Saved items that only pointed online, or had no recipe, were left out. "
            f"The original saved Facebook page is in [{ORIG}]({ORIG}/).\n", f"## Recipes ({nrec})\n"]
    body += [f"- [{t}]({L(s + '.md')})" + (" - video" if v else "") + f" *(saved from {src})*" for k, t, s, src, v in rows if k == "Recipe"]
    body += ["", f"## Videos ({nvid})\n"]
    body += [f"- [{t}]({L(s + '.md')}) *(saved from {src})*" for k, t, s, src, v in rows if k == "Video"]
    meta = {"title": "Facebook Saved Food Recipes", "category": "recipes", "source_type": "bookmark-collection",
            "publisher": "Personal collection", "source_url": None, "collection": "personal-recipe-collection",
            "provenance": f"Facebook Saved > Food collection, rebuilt {TODAY}",
            "license": "Recipes copyright their creators - personal offline copies, do not redistribute",
            "recipes": nrec, "videos": nvid, "saved": nrec + nvid, "compiled": TODAY}
    open(os.path.join(NEW, "facebook-saved.md"), "w", encoding="utf-8").write(front_matter(meta) + "\n".join(body) + "\n")

    # replace the folder's contents (the folder itself may be open in Explorer, so it is not renamed)
    def rm(p):
        if os.path.isdir(p):
            shutil.rmtree(p, onerror=lambda f, q, e: (os.chmod(q, 0o666), f(q)))
        else:
            os.chmod(p, 0o666); os.remove(p)
    for f in os.listdir(FB):
        rm(os.path.join(FB, f))
    for f in os.listdir(NEW):
        shutil.move(os.path.join(NEW, f), os.path.join(FB, f))
    os.rmdir(NEW)
    shutil.rmtree(os.path.join(bm.OUT, "facebook-links"), ignore_errors=True)
    for k in [k for k, v in blog.items() if v.get("folder") == "facebook-links"]:
        del blog[k]
    json.dump(blog, open(bm.LOG, "w", encoding="utf-8"), indent=1)
    print(f"facebook-saved rebuilt: {nrec} recipes, {nvid} videos")


if __name__ == "__main__":
    main()
