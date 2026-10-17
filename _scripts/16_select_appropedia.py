"""Select Appropedia documents:
  * hand-picked single pages (_work/appropedia_candidates.json + appropedia_keep_*.txt)
  * whole manuals (BOOKS): the root page + all sub-pages combined into one document, in the order the
    root page links them (remaining sub-pages appended alphabetically)
  * series kept as separate short documents (SERIES): Practical Action briefs, NREMT skill sheets
Categories are assigned by topic keywords (BOOK_CAT overrides for manuals)."""
import glob, json, os, re, sys
from urllib.parse import unquote
from bs4 import BeautifulSoup
from libzim.reader import Archive
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
z = Archive(os.path.join(RESEARCH, "_sources", "zim", "appropedia_en_all_maxi_2026-02.zim"))
A = json.load(open(os.path.join(W, "appropedia_articles.json"), encoding="utf-8"))
C = json.load(open(os.path.join(W, "appropedia_candidates.json"), encoding="utf-8"))

BOOK_CAT = {
    "Root Crops": "food-production", "Three Acres and Liberty": "food-production",
    "Bioconversion of Organic Residues for Rural Communities": "energy-power",
    "Peace Corps appropriate community technology": "tools-crafts-skills",
    "Solar and Energy Conserving Food Technologies": "food-storage-preservation",
    "Micro-livestock": "food-production", "Back Yard and Commercial Rabbit Production": "food-production",
    "Wood Harvesting with Hand Tools": "tools-crafts-skills", "Neem": "medicine-pharmacology",
    "Clay Brick and Tile Moulding Equipment": "shelter-construction", "Concrete Block Producing Equipment": "shelter-construction",
    "Soil Preparation Equipment": "food-production", "Traditional Field Crops": "food-production",
    "Keeping Chickens": "food-production", "Raising Ducks": "food-production", "Small-scale maize milling": "food-storage-preservation",
    "Small-scale oil extraction from groundnuts and copra": "food-storage-preservation",
    "Small Scale Vegetable Oil Extraction": "food-storage-preservation",
    "Small-scale manufacture of compound animal feed": "food-production",
    "Small Scale Production of Lime for Building": "shelter-construction",
    "Ferrocement Applications in Developing Countries": "shelter-construction", "Traditional Cheesemaking": "food-storage-preservation",
    "Household Cyclopedia": "tools-crafts-skills", "Sheep and Goat Breeding": "food-production", "Amaranth": "food-production",
    "The Winged Bean": "food-production", "Leucaena": "food-production", "Farmers of Forty Centuries": "food-production",
    "Living with the Soil": "food-production", "Understanding Solar Stills": "water", "Building with Pumice": "shelter-construction",
    "The Water Buffalo": "food-production", "Aluminium recovery manual": "tools-crafts-skills",
    "Bananas (Better Farming Series)": "food-production", "STAR-TIDES Field Manual": "emergency-preparedness",
    "Analysis of the various types of mills": "food-storage-preservation",
    "The Use of Organic Residues in Rural Communities": "energy-power", "Hexayurt project": "shelter-construction",
    "PTC Course": "medical-first-aid", "CrashSavers Trauma": "medical-first-aid", "Are You Ready?": "emergency-preparedness",
    "Aerosol pandemics": "emergency-preparedness", "Plastics recovery manual": "tools-crafts-skills",
    "The Oil Palm": "food-production", "The Rubber Tree": "food-production",
}
SERIES = {"Practical Action": None, "NREMT Skillset": "medical-first-aid", "NREMT Paramedic Skillset": "medical-first-aid"}

RULES = [  # first match wins
    ("emergency-preparedness", r"staying cool|hot weather|heat wave|cool homes|famine|global food|catastroph|industry is disabled"),
    ("food-storage-preservation", r"store root|root vegetables|processing|chips|juice|fruit|nut|nuts|cashew|sugar|jaggery|sauce|"
                                  r"spice|herbs and spices|staple grain|tomato"),
    ("energy-power", r"biogas|biofuel|biodiesel|ethanol|plant oil|wood gas|gasif"),
    ("mechanical-vehicles", r"boat|bicycle|bike|cart|trailer|engine|wheelbarrow|ropeway"),
    ("medical-first-aid", r"first aid|wound|trauma|splint|bandag|CPR|airway|NREMT|bleeding|burn(s)?\b|fracture|resuscitat|suction|oxygen"),
    ("medical-conditions", r"malaria|cholera|schistosom|AIDS|disease|health|mental|vaccin|incubator|infant"),
    ("medicine-pharmacology", r"herbal|tincture|medicinal|neem|honey for wound|medicinal clay|valerian"),
    ("sanitation-hygiene", r"toilet|latrine|sanitat|humanure|feces|urine|greywater|grey water|wastewater|sewage|soap|hygien|handwash|"
                           r"hand-washing|mosquito|fly control|bedbug|fire ants|pad|detergent|laundry|washing|night soil|arborloo|fossa|ecosan|waste"),
    ("water", r"water|rain|well|pump|filter|purif|chlorin|sodis|distill|still|desalin|dew|cistern|sand dam|swale|irrigat(?!ion device)|UV"),
    ("food-storage-preservation", r"preserv|drying|dehydrat|dryer|drier|smok|pickl|ferment|sauerkraut|cheese|yog|canning|salt|storage|"
                                  r"cellar|zeer|cool|refrigerat|jam|vinegar|wine|beer|mead|butcher|plucking|meat|milling|grain|mill|oil|ghee|hominy|bread|yeast|flour"),
    ("cooking-fire", r"stove|cook|oven|solar cooker|fireless|haybox|charcoal|briquet|firewood|kiln|fire|fuel|tandoor|rocket|lorena|jiko"),
    ("energy-power", r"solar|wind|hydro|turbine|electric|battery|batteries|generator|pedal|power|biogas|digest|gasif|charge|LED|lamp|light|"
                     r"heat|stirling|inverter|wiring|kerosene|plant oil|ethanol|biodiesel|energy"),
    ("shelter-construction", r"build|house|home|shelter|adobe|cob|earth|straw|bamboo|brick|block|roof|insulat|wall|mortar|cement|concrete|"
                             r"ferrocement|lime|papercrete|timber|wattle|yurt|thermal|passive|ventilat|flood|earthquake|wofati|walipini"),
    ("food-production", r"garden|farm|crop|seed|soil|compost|worm|vermi|chicken|duck|goat|sheep|rabbit|pig|livestock|bee|hive|fish|tilapia|"
                        r"aquapon|greenhouse|coldframe|cloche|mulch|plant|tree|orchard|pest|weed|manure|fertili|grafting|polyculture|permaculture|"
                        r"forest|tillage|harvest|dovecote|pigeon|hugel|keyline|potato|bean|soy|sesame|amaranth|moringa|tuber|cassava|legume"),
    ("mechanical-vehicles", r"bicycle|bike|cart|trailer|engine|wheelbarrow|ropeway"),
    ("tools-crafts-skills", r"tool|metal|weld|solder|forg|temper|chisel|vise|clamp|saw|plane|wood|carv|rope|knot|sew|stitch|textile|dye|"
                            r"weav|basket|candle|mattress|paint|potash|lye|glue|pottery|clay|drill|shears|mortise|household|hints"),
    ("emergency-preparedness", r"disaster|emergency|drought|tsunami|survive|catastroph|industry is disabled|feeding everyone|kit"),
]


def category(title):
    for cat, pat in RULES:
        if re.search(pat, title, re.I):
            return cat
    return "tools-crafts-skills"


def url(p):
    return "https://www.appropedia.org/" + p


docs, used = [], set()
subs = {}
for p, t, cats, w in A:
    if "/" in t:
        subs.setdefault(t.split("/")[0], []).append((p, t))
by_title = {t: p for p, t, cats, w in A}

# whole manuals
for book, cat in BOOK_CAT.items():
    root = by_title.get(book)
    parts = sorted(subs.get(book, []), key=lambda x: x[1].lower())
    order = []
    if root:
        try:
            soup = BeautifulSoup(bytes(z.get_entry_by_path(root).get_item().content).decode("utf-8", "replace"), "lxml")
            linked = [unquote(a.get("href", "")).split("#")[0] for a in soup.find_all("a", href=True)]
            pmap = {p.rsplit("/", 1)[-1]: p for p, _ in parts}
            for h in linked:
                k = h.rsplit("/", 1)[-1]
                if k in pmap and pmap[k] not in order:
                    order.append(pmap[k])
        except KeyError:
            pass
    order += [p for p, _ in parts if p not in order]
    paths = ([root] if root else []) + order
    if not paths:
        print("missing book", book); continue
    docs.append({"key": "book:" + book, "title": book, "category": cat, "paths": paths,
                 "source_url": url(root or order[0]), "min_words": 150,
                 "extra": {"content_type": "manual (combined from %d Appropedia pages)" % len(paths)}})
    used.update(paths)

# series of separate short documents
for s, cat in SERIES.items():
    for p, t in sorted(subs.get(s, []), key=lambda x: x[1].lower()):
        if p in used or t.endswith("/Quiz"):
            continue
        name = t.split("/", 1)[1]
        docs.append({"key": p, "title": f"{name} ({s})", "category": cat or category(name), "paths": [p], "source_url": url(p)})
        used.add(p)

# hand-picked single pages
idx = [int(x) for f in sorted(glob.glob(os.path.join(W, "appropedia_keep_*.txt"))) for x in open(f).read().split()]
for i in sorted(set(idx)):
    p, t, w, s, fp = C[i]
    if p in used or t in BOOK_CAT:
        continue
    name = t.replace("GEN Solution Library/", "").replace("Appropriate Technology Sourcebook/", "")
    docs.append({"key": p, "title": name, "category": category(name), "paths": [p], "source_url": url(p)})
    used.add(p)

json.dump(docs, open(os.path.join(W, "zimsel_appropedia.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
from collections import Counter
print(len(docs), "documents from", len(used), "pages")
print(Counter(d["category"] for d in docs).most_common())
