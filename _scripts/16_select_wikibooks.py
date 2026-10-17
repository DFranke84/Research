"""Select Wikibooks content:
  * BOOKS: whole books combined into one document each (root page + sub-pages; order from the root page's
    links where possible, else alphabetical)
  * COOKBOOK themes: hand-picked Cookbook: pages (indices into _work/cookbook_candidates2.json) grouped into
    themed documents about cooking from staples."""
import json, os, re, sys
from urllib.parse import unquote
from bs4 import BeautifulSoup
from libzim.reader import Archive
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
z = Archive(os.path.join(RESEARCH, "_sources", "zim", "wikibooks_en_all_nopic_2026-04.zim"))

BOOKS = {
    "First_Aid": "medical-first-aid", "Community_Health_Worker_Manual": "medical-first-aid",
    "Open_Source_Handbook_of_Nursing": "medical-first-aid", "Emergency_Medicine": "medical-conditions",
    "What_You_Should_Know_About_Medicines": "medicine-pharmacology", "Pharmacology": "medicine-pharmacology",
    "Home_Remedies": "medicine-pharmacology", "Women's_Health": "medical-conditions", "Pediatric_Medicine": "medical-conditions",
    "Stress-related_Disorders": "medical-conditions", "Teach_Cough_Hygiene_Everywhere": "sanitation-hygiene",
    "The_Housework_Manual": "sanitation-hygiene", "Drinking_Water": "water",
    "Knots": "tools-crafts-skills", "Carpentry": "tools-crafts-skills", "Woodworking": "tools-crafts-skills",
    "Woodturning": "tools-crafts-skills", "Down'n'dirty_Blacksmithing": "tools-crafts-skills", "Welding": "tools-crafts-skills",
    "Sewing": "tools-crafts-skills", "Short_introduction_to_the_use_of_sewing_machines": "tools-crafts-skills",
    "Raku_Pottery": "tools-crafts-skills", "Locksmithing": "security-defense",
    "Beekeeping": "food-production", "Raising_Chickens": "food-production", "Equine_Nutrition": "food-production",
    "Veterinary_Medicine": "food-production", "Building_Haycocks": "food-production", "Agriculture": "food-production",
    "Horticultural_Gardening_Tips": "food-production", "Soil_Erosion_by_Water": "food-production",
    "Brewing": "food-storage-preservation", "Wine": "food-storage-preservation",
    "Fundamentals_of_Human_Nutrition": "food-storage-preservation",
    "River_Fishing": "hunting-fishing-trapping",
    "Backpack_Camping_and_Woodland_Survival": "wilderness-survival", "Outdoor_Survival": "wilderness-survival",
    "Sailing": "wilderness-survival", "Swimming_Manual": "wilderness-survival", "Rock_Climbing": "wilderness-survival",
    "Straw_Bale_Construction": "shelter-construction", "House_Construction": "shelter-construction",
    "Weatherization": "shelter-construction",
    "Bicycles": "mechanical-vehicles", "Automobile_Repair": "mechanical-vehicles", "Automotive_Systems": "mechanical-vehicles",
    "Field_Repairs_of_Tractors_and_Trailers_for_the_Driver": "mechanical-vehicles",
    "Amateur_Radio_Manual": "communications-radio", "Practical_Electronics": "communications-radio",
    "Electronics_Fundamentals": "communications-radio",
    "Renewable_Energy": "energy-power", "Electric_Motors_And_Generators": "energy-power",
    "Meteorology": "weather", "Introductory_Agrometeorology": "weather",
    "Natural_Disasters": "emergency-preparedness", "Disaster_and_WMD_Defence_Guide": "cbrn-hazmat",
}

COOKBOOK = {
    "Breads and flatbreads": [5, 29, 32, 59, 95, 96, 132, 177, 181, 183, 239, 242, 243, 312, 313, 366, 391, 437, 451, 453, 457, 459, 463],
    "Grains and legumes": [0, 4, 8, 14, 16, 24, 27, 39, 57, 85, 98, 100, 106, 108, 114, 133, 179, 182, 184, 214, 238, 244, 246, 247, 249,
                           250, 253, 255, 256, 277, 286, 315, 321, 326, 364, 385, 401, 403, 405, 408, 446, 447, 452, 455],
    "Preserving and fermenting": [56, 105, 130, 131, 211, 212, 213, 270, 271, 274, 275, 276, 310, 314, 324, 350, 351, 353, 354, 355, 356,
                                  358, 361, 369, 372, 379, 424, 444, 445],
    "Dairy, eggs and fats": [42, 49, 60, 64, 84, 110, 135, 136, 137, 234, 464],
    "Cooking methods and the kitchen": [25, 26, 38, 107, 134, 138, 166, 175, 185, 228, 311, 348, 349, 386, 412, 413, 417, 418, 419, 420,
                                        421, 423, 425, 368],
    "Wild greens": [104, 240],
}

paths = []
for i in range(z.entry_count):
    e = z._get_entry_by_id(i)
    if not e.is_redirect:
        paths.append(e.path)
pset = set(paths)
subs = {}
META = re.compile(r"/(Print_version|Printable_version|Cover|Authors?|Contributors?|To_?do|Requested|License|GFDL|"
                  r"About(_the_book|_this_book)?|Sandbox|Template|Collections?|PDF|Wikibook|Planning|Development|Stage|"
                  r"How_to_contribute|Contributing|Editing|Style_guide|Feedback|Discussion)", re.I)
for p in paths:
    if "/" in p and ":" not in p.split("/")[0] and not META.search(p):
        subs.setdefault(p.split("/")[0], []).append(p)

docs = []
for book, cat in BOOKS.items():
    parts = sorted(subs.get(book, []), key=str.lower)
    order = []
    if book in pset:
        soup = BeautifulSoup(bytes(z.get_entry_by_path(book).get_item().content).decode("utf-8", "replace"), "lxml")
        for a in soup.find_all("a", href=True):
            h = unquote(a["href"]).split("#")[0].lstrip("./")
            if h in parts and h not in order:
                order.append(h)
    order += [p for p in parts if p not in order]
    ps = ([book] if book in pset else []) + order
    if not ps:
        print("missing", book); continue
    docs.append({"key": "book:" + book, "title": book.replace("_", " ") + " (Wikibooks)", "category": cat, "paths": ps,
                 "source_url": "https://en.wikibooks.org/wiki/" + book, "min_words": 150,
                 "extra": {"content_type": "book (combined from %d Wikibooks pages)" % len(ps)}})

CB = json.load(open(os.path.join(W, "cookbook_candidates2.json"), encoding="utf-8"))
for theme, idx in COOKBOOK.items():
    ps = [CB[i][0] for i in idx]
    docs.append({"key": "cookbook:" + theme, "title": f"Cookbook - {theme} (Wikibooks)",
                 "category": "cooking-fire" if theme.startswith("Cooking") else
                             "foraging-wild-food" if theme == "Wild greens" else "food-storage-preservation",
                 "paths": ps, "source_url": "https://en.wikibooks.org/wiki/Cookbook:Table_of_Contents", "min_words": 150, "chapters": "all",
                 "extra": {"content_type": "themed collection of %d Wikibooks Cookbook pages" % len(ps),
                           "source_pages": ["https://en.wikibooks.org/wiki/" + p for p in ps]}})

json.dump(docs, open(os.path.join(W, "zimsel_wikibooks.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
print(len(docs), "documents,", sum(len(d["paths"]) for d in docs), "pages")
