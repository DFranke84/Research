"""Pull just the recipe out of a web page and render it cleanly (Markdown + a one-page PDF), without the site's
menus, ads, comments and link lists.

extract(html) -> {"name", "description", "image", "yield", "prep", "cook", "total", "ingredients": [...],
                  "instructions": [...], "notes": [...], "video": {...} or None, "method": "..."}  or None
Order of methods: schema.org JSON-LD -> schema.org microdata -> recipe-card plugin markup (WP Recipe Maker, Tasty,
Mediavine Create, ...) -> "Ingredients" / "Directions" headings in the article body.
"""
import html as _html, json, os, re, subprocess, sys
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import find_browser

CHROME = find_browser()   # Chrome, or Edge when Chrome isn't installed
MEASURE = re.compile(r"(\d|½|¼|¾|⅓|⅔|\bone\b|\btwo\b|\ba\b)\s*[\d/ .½¼¾⅓⅔-]*\s*(cups?|c\.|tbsps?|tablespoons?|tsps?|teaspoons?|oz|ounces?|"
                     r"lbs?|pounds?|grams?|g\b|kg|ml|l\b|liters?|quarts?|pints?|cans?|packages?|pkgs?|sticks?|cloves?|pinch|dash|"
                     r"slices?|large|medium|small|whole|heads?|bunch|box(es)?|bags?|jars?|bottles?|envelopes?|packets?|containers?|cartons?|blocks?|tubs?|oz\b)", re.I)
JUNK = re.compile(r"^(advertisement|ad|jump to recipe|print( recipe)?|pin( recipe)?|save|rate (this )?recipe|share|"
                  r"cook mode.*|prevent your screen.*|watch( the)? video|video|skip to content|\d+ comments?|"
                  r"click here.*|subscribe.*|sign up.*|log in.*)$", re.I)
NEXT_SECTION = re.compile(r"^(notes?|nutrition( facts| information)?|tips?|comments?|reviews?|leave a (reply|comment)|"
                          r"you (may|might) also like|related( posts| recipes)?|more recipes|share this|about (the )?author|"
                          r"recipe notes?|storage|faqs?|frequently asked)\b", re.I)
ING_HEAD = re.compile(r"^(the )?ingredients?( list)?\s*:?$|^you('| wi)ll need:?$|^what you('| wi)ll need:?$", re.I)
STEP_HEAD = re.compile(r"^(directions?|instructions?|method|preparation|how to make( it)?|steps?|to make|itinerary|procedure)( for .*)?\s*:?$", re.I)


MOJIBAKE = re.compile(r"Â[\s ¼½¾°]|â€|â\x80|Ã[\x80-\xbf]|â[\u0080-¿]")


def demojibake(s):
    """Repair UTF-8 text that was decoded as Latin-1/cp1252 ("Â¼ cup" -> "¼ cup", "Shepherdâ€™s" -> "Shepherd’s")."""
    if not MOJIBAKE.search(s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            return s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s.replace("Â", "")


def clean(s):
    s = demojibake(str(s))
    s = _html.unescape(BeautifulSoup(s, "lxml").get_text(" ", strip=True)) if "<" in s else _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip(" \u00a0▢□☐•-")


def first_url(x):
    if isinstance(x, str): return x
    if isinstance(x, list) and x: return first_url(x[0])
    if isinstance(x, dict): return x.get("url") or x.get("contentUrl")
    return None


def iso_min(s):
    if not s or not isinstance(s, str): return None
    h = re.search(r"(\d+)H", s); m = re.search(r"(\d+)M", s.split("T")[-1])
    t = (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return (f"{t // 60} hr {t % 60} min" if t >= 60 else f"{t} min") if t else None


def drop(t):
    """Remove page junk - but never the page body or the post itself (themes put words like "social" on <body>)."""
    if t.attrs is None or t.name in ("html", "body", "main", "article") or CONTENT.search(" ".join(t.get("class") or [])):
        return
    t.decompose()

# ---------------------------------------------------------------- 1) JSON-LD
def _jsonld(soup):
    for tag in soup.find_all("script", type=re.compile("ld\\+json")):
        try:
            data = json.loads(tag.string or tag.get_text() or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack += d
            elif isinstance(d, dict):
                t = d.get("@type")
                if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
                    return d
                if isinstance(d.get("@graph"), list):
                    stack += d["@graph"]
    return None


def _steps(instr):
    out = []
    for x in instr if isinstance(instr, list) else [instr]:
        if isinstance(x, list):   # some sites nest the steps one level deeper: [[step, step, ...]]
            out += _steps(x)
        elif isinstance(x, str):
            out += [clean(p) for p in re.split(r"\n+|(?<=\.)\s+(?=\d+\.\s)", BeautifulSoup(x, "lxml").get_text("\n")) if clean(p)]
        elif isinstance(x, dict):
            if x.get("@type") == "HowToSection":
                out.append(f"**{clean(x.get('name', ''))}**")
                out += _steps(x.get("itemListElement", []))
            else:
                out.append(clean(x.get("text") or x.get("name") or ""))
    return [s for s in out if s and not JUNK.match(s)]


def from_jsonld(soup):
    r = _jsonld(soup)
    if not r or not (r.get("recipeIngredient") or r.get("recipeInstructions")):
        return None
    y = r.get("recipeYield")
    v = r.get("video"); v = v[0] if isinstance(v, list) and v else v
    return {"name": clean(r.get("name") or ""), "description": clean(r.get("description") or ""),
            "image": first_url(r.get("image")), "yield": clean(y[0] if isinstance(y, list) and y else y or ""),
            "prep": iso_min(r.get("prepTime")), "cook": iso_min(r.get("cookTime")), "total": iso_min(r.get("totalTime")),
            "ingredients": [clean(i) for i in r.get("recipeIngredient") or [] if clean(i)],
            "instructions": _steps(r.get("recipeInstructions") or []), "notes": [],
            "video": v if isinstance(v, dict) else None, "method": "structured recipe data (schema.org)"}


# ---------------------------------------------------------------- 2) microdata
def from_microdata(soup):
    box = soup.find(attrs={"itemtype": re.compile(r"schema\.org/Recipe", re.I)})
    if not box:
        return None
    ing = [clean(x.get_text(" ")) for x in box.find_all(attrs={"itemprop": re.compile(r"^(recipeIngredient|ingredients)$")})]
    ins_nodes = box.find_all(attrs={"itemprop": "recipeInstructions"})
    ins = []
    for n in ins_nodes:
        items = n.find_all(["li", "p"]) or [n]
        ins += [clean(i.get_text(" ")) for i in items]
    name = box.find(attrs={"itemprop": "name"})
    img = box.find(attrs={"itemprop": "image"})
    ing, ins = [i for i in ing if i], [i for i in ins if i and not JUNK.match(i)]
    if len(ing) < 2 or not ins:
        return None
    return {"name": clean(name.get_text(" ")) if name else "", "description": "",
            "image": (img.get("src") or img.get("content") or img.get("href")) if img else None,
            "yield": "", "prep": None, "cook": None, "total": None, "ingredients": ing, "instructions": ins, "notes": [],
            "video": None, "method": "recipe microdata (schema.org)"}


# ---------------------------------------------------------------- 3) recipe-card plugins
CARD = re.compile(r"wprm-recipe-container|wprm-recipe\b|tasty-recipes\b|mv-create-card|easyrecipe|recipe-card\b|h-recipe|hrecipe|"
                  r"zlrecipe|recipe-container|recipe-callout|ERSRecipe|cooked-recipe|recipe-summary", re.I)


def from_card(soup):
    for box in soup.find_all(class_=CARD):
        ing_nodes = box.find_all(class_=re.compile(r"ingredient", re.I))
        ins_nodes = box.find_all(class_=re.compile(r"instruction|direction|method|step", re.I))
        ing = [clean(li.get_text(" ")) for n in ing_nodes for li in (n.find_all("li") or [])]
        ins = [clean(li.get_text(" ")) for n in ins_nodes for li in (n.find_all(["li", "p"]) or [])]
        ing = list(dict.fromkeys(i for i in ing if i and not JUNK.match(i)))
        ins = list(dict.fromkeys(i for i in ins if i and not JUNK.match(i)))
        if len(ing) >= 2 and ins:
            name = box.find(class_=re.compile(r"(recipe-)?(name|title)", re.I)) or box.find(["h2", "h3"])
            img = box.find("img")
            return {"name": clean(name.get_text(" ")) if name else "", "description": "",
                    "image": (img.get("data-src") or img.get("src")) if img else None, "yield": "", "prep": None,
                    "cook": None, "total": None, "ingredients": ing, "instructions": ins, "notes": [], "video": None,
                    "method": "recipe card on the page"}
    return None


# ---------------------------------------------------------------- 4) headings in the article
def from_headings(soup):
    for t in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe", "noscript"]):
        drop(t)
    for t in soup.find_all(class_=re.compile(r"comment|sidebar|related|share|social|newsletter|advert|\bad\b|widget|footer|menu", re.I)):
        drop(t)
    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "strong", "b", "dt", "dd"]):
        if el.find(["p", "li", "h2", "h3", "h4"]):   # containers: their children are visited on their own
            continue
        for br in el.find_all("br"):
            br.replace_with("\u2028")
        for part in el.get_text("").split("\u2028"):   # a paragraph broken by <br> is several recipe lines
            txt = clean(part)
            if txt and (not lines or lines[-1][1] != txt):
                lines.append((el.name, txt))
    for i, (_, t) in enumerate(lines):
        if not ING_HEAD.match(t):
            continue
        ing, ins, j, mode = [], [], i + 1, "ing"
        while j < len(lines) and len(ing) + len(ins) < 120:
            tag, s = lines[j]
            if STEP_HEAD.match(s):
                mode = "ins"
            elif NEXT_SECTION.match(s) and (ins or tag.startswith("h")):
                break
            elif ING_HEAD.match(s) and ins:
                break
            elif not JUNK.match(s) and len(s) < 600:
                (ing if mode == "ing" else ins).append(s)
            j += 1
        if mode == "ing":   # no directions heading: split at the first long sentence-like line
            k = next((n for n, s in enumerate(ing) if len(s) > 90 and not MEASURE.search(s[:25])), None)
            if k: ing, ins = ing[:k], ing[k:]
        if sum(1 for s in ing if MEASURE.search(s)) >= 2 and ins:
            return {"name": "", "description": "", "image": None, "yield": "", "prep": None, "cook": None, "total": None,
                    "ingredients": ing, "instructions": ins[:60], "notes": [], "video": None,
                    "method": "Ingredients/Directions sections of the page"}
    return None


# ---------------------------------------------------------------- 5) the post body of a prose recipe
CONTENT = re.compile(r"entry-content|post-content|post-body|article-body|article-content|blog-post|post-entry|"
                     r"main-content|content-area|storycontent|entry\b|single-post", re.I)


def from_article(soup):
    """Older blogs write the recipe as prose: keep only the main post text (no menus, sidebars, comments)."""
    for t in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe", "noscript", "figure", "button"]):
        drop(t)
    for t in soup.find_all(class_=re.compile(r"comment|sidebar|related|share|social|newsletter|advert|\bads?\b|widget|"
                                             r"footer|menu|author|breadcrumb|pagination|subscribe|popular", re.I)):
        drop(t)
    cands = soup.find_all("article") + soup.find_all(class_=CONTENT) + soup.find_all(id=CONTENT) + soup.find_all("main")
    if not cands:   # no marked-up post body: the block holding the most paragraph text
        cands = [max(soup.find_all(["div", "td"]), key=lambda d: sum(len(p.get_text()) for p in d.find_all("p", recursive=False)),
                     default=None)]
    box = max((c for c in cands if c), key=lambda c: len(c.get_text()), default=None)
    if box is None:
        return None
    paras = []
    for el in box.find_all(["h2", "h3", "h4", "p", "li"]):
        if el.find(["p", "li"]):
            continue
        for br in el.find_all("br"):
            br.replace_with("\u2028")
        for part in el.get_text("").split("\u2028"):
            t = clean(part)
            if not t or JUNK.match(t):
                continue
            if NEXT_SECTION.match(t) and paras and len(" ".join(paras).split()) > 150:
                break
            paras.append(("### " + t) if el.name in ("h2", "h3", "h4") else t)
    text = " ".join(paras)
    if len(MEASURE.findall(text)) < 3 or len(text.split()) < 60:
        return None
    if len(re.findall(r"\$\s?\d+\.\d\d", text)) >= 4:   # a shopping list / store page, not a recipe
        return None
    if len(re.findall(r"\[…\]|\[\.\.\.\]|\[&hellip;\]|\bRead More\b|\bContinue Reading\b", text, re.I)) >= 3:
        return None   # a homepage / category listing of post teasers, not a recipe
    out, words = [], 0
    for p in paras:   # keep it to the recipe-length part of the post
        out.append(p); words += len(p.split())
        if words > 2500: break
    return {"name": "", "description": "", "image": None, "yield": "", "prep": None, "cook": None, "total": None,
            "ingredients": [], "instructions": [], "article": out, "notes": [], "video": None,
            "method": "recipe text from the post (no recipe card on the page)"}


BAD_IMG = re.compile(r"facebook\.com/tr|gravatar|avatar|logo|icon|sprite|pixel|spacer|blank\.|badge|button|banner|"
                     r"/ads?/|doubleclick|pinterest|share|emoji|placeholder|lazy[-_]?load|data:image", re.I)


def main_image(soup):
    """The first full-size photo in the post body (for pages that publish no recipe/share image)."""
    def src(img):
        s = img.get("data-lazy-src") or img.get("data-src") or img.get("data-original") or img.get("src") or ""
        if not s and img.get("srcset"):
            s = img["srcset"].split(",")[0].split()[0]
        return s
    def big(img, s):
        try:
            w = int(re.sub(r"\D", "", str(img.get("width") or "")) or 0)
        except ValueError:
            w = 0
        dims = re.search(r"-(\d{2,4})x(\d{2,4})\.\w+$", s)   # WordPress thumbnails: name-65x65.jpg
        if dims and max(int(dims.group(1)), int(dims.group(2))) < 250:
            return False
        return w == 0 or w >= 250
    for t in soup.find_all(class_=re.compile(r"related|sidebar|widget|comment|footer|author|popular|recent", re.I)):
        drop(t)
    scopes = soup.find_all("article") + soup.find_all(class_=CONTENT) + [soup]
    for scope in scopes:
        for img in scope.find_all("img"):
            s = src(img)
            if s.startswith("http") and not BAD_IMG.search(s) and big(img, s):
                return s
    return None


def extract(html):
    soup = BeautifulSoup(html, "lxml")
    for f in (from_jsonld, from_microdata, from_card):
        r = f(soup)
        if r:
            break
    else:
        r = from_headings(BeautifulSoup(html, "lxml")) or from_article(BeautifulSoup(html, "lxml"))
    if r and not r.get("article") and not r.get("instructions"):   # recipe data without steps: take them from the page
        for f in (lambda: from_card(BeautifulSoup(html, "lxml")), lambda: from_headings(BeautifulSoup(html, "lxml"))):
            r2 = f()
            if r2 and r2.get("instructions"):
                r["instructions"], r["method"] = r2["instructions"], r["method"] + " + steps from the page"
                break
        if not r["instructions"]:
            return None   # an ingredient list alone is not a usable recipe
    if r and not r.get("image"):
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        r["image"] = (og.get("content") if og else None) or main_image(BeautifulSoup(html, "lxml"))
    if r and not r.get("name"):
        og = soup.find("meta", property="og:title")
        r["name"] = clean(og.get("content")) if og else (clean(soup.title.get_text()) if soup.title else "")
    return r


RECIPE_LINK = re.compile(r"^\s*(see|view|get|go to|jump to|full|print|click here for( the)?|read)( the| full)?( full)?\s+recipe\b", re.I)


def recipe_links(html, base):
    """Links such as "See Recipe" / "Get the Recipe" that lead from a teaser, shop or video page to the full recipe."""
    from urllib.parse import urljoin, urldefrag
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        if RECIPE_LINK.match(a.get_text(" ", strip=True) or ""):
            u = urldefrag(urljoin(base, a["href"]))[0]
            if u.startswith("http") and u.split("?")[0].rstrip("/") != base.split("?")[0].rstrip("/") and u not in out:
                out.append(u)
    return out[:2]


# ---------------------------------------------------------------- rendering
STEPNUM = re.compile(r"^(step\s*)?\d{1,2}\s*[.):-]?\s+(?=[A-Z(])", re.I)


def tidy(r):
    """Drop the site's own step numbers ("1 Heat the oven" -> "Heat the oven") and repeated lines."""
    r["instructions"] = [STEPNUM.sub("", s) for s in r["instructions"]]
    r["ingredients"] = [x for k, x in enumerate(r["ingredients"]) if k == 0 or x != r["ingredients"][k - 1]]   # parts may repeat items
    return r


def to_markdown(r):
    r = tidy(r)
    if r.get("article"):
        return "\n\n".join(r["article"])
    out = []
    if r.get("description"): out += [r["description"], ""]
    info = [f"**{k}:** {r[v]}" for k, v in (("Yield", "yield"), ("Prep", "prep"), ("Cook", "cook"), ("Total", "total")) if r.get(v)]
    if info: out += ["  \n".join(info), ""]
    out += ["## Ingredients", ""] + [(f"\n{i}\n" if i.startswith("**") else f"- {i}") for i in r["ingredients"]] + [""]
    n, steps = 0, []
    for s in r["instructions"]:
        if s.startswith("**"):
            steps.append(f"\n{s}\n"); n = 0   # each part of a multi-part recipe numbers its steps from 1
        else:
            n += 1; steps.append(f"{n}. {s}")
    if steps:
        out += ["## Instructions", ""] + steps
    return "\n".join(out).strip()


def to_pdf(r, title, source, image_path, pdf_path):
    """One clean page: title, photo, ingredients, numbered steps, source line. Rendered by headless Chrome."""
    r = tidy(r)
    e = _html.escape
    img = f'<img src="{os.path.basename(image_path)}">' if image_path else ""
    info = " &nbsp;·&nbsp; ".join(f"<b>{k}</b> {e(r[v])}" for k, v in (("Yield", "yield"), ("Prep", "prep"), ("Cook", "cook"),
                                                                       ("Total", "total")) if r.get(v))
    ing = "".join(f"<h4>{e(i.strip('*'))}</h4>" if i.startswith("**") else f"<li>{e(i)}</li>" for i in r["ingredients"])
    steps = "".join(f"</ol><h4>{e(s.strip('*'))}</h4><ol>" if s.startswith("**") else f"<li>{e(s)}</li>" for s in r["instructions"])
    article = "".join(f"<h3>{e(p[4:])}</h3>" if p.startswith("### ") else f"<p>{e(p)}</p>" for p in r.get("article") or [])
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
      body{{font-family:Georgia,serif;margin:28px 36px;color:#222;font-size:12.5pt;line-height:1.4}}
      h1{{font-size:21pt;margin:0 0 6px}} .src{{color:#666;font-size:9pt;word-break:break-all}}
      img{{max-width:100%;max-height:300px;display:block;margin:10px 0;border-radius:6px}}
      .info{{margin:6px 0 10px;font-size:11pt}} h2{{font-size:14pt;border-bottom:1px solid #ccc;margin:14px 0 6px}}
      h4{{margin:8px 0 2px}} li{{margin:3px 0}} .desc{{font-style:italic}}</style></head><body>
      <h1>{e(title)}</h1>{'<div class="desc">' + e(r['description']) + '</div>' if r.get('description') else ''}
      {img}<div class="info">{info}</div>{article if r.get("article") else f"<h2>Ingredients</h2><ul>{ing}</ul>" + (f"<h2>Instructions</h2><ol>{steps}</ol>" if steps else "")}
      <p class="src">Source: {e(source)}</p></body></html>"""
    tmp = os.path.splitext(pdf_path)[0] + ".print.html"
    open(tmp, "w", encoding="utf-8").write(page)
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                        f"--print-to-pdf={pdf_path}", "file:///" + tmp.replace("\\", "/")], capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        pass
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2000
