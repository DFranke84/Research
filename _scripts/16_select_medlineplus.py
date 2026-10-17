"""Select MedlinePlus documents from the reviewed lists:
  drugs  : _work/mplus_drugs.json 'keep' (matched to the WHO Model Formulary) + hand-picked indices of 'rest'
           in _work/mplus_drugs_extra_*.txt
  herbs  : every druginfo/natural monograph (herbs & supplements)
  ency   : hand-picked indices of _work/mplus_ency.json in _work/mplus_ency_keep_*.txt
Note on licensing: MedlinePlus is an NLM site, but these three collections are licensed content
(ASHP AHFS drug monographs, Natural Medicines herb monographs, A.D.A.M. encyclopedia) - labelled per document."""
import glob, json, os, re, sys
from libzim.reader import Archive
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
z = Archive(os.path.join(RESEARCH, "_sources", "zim", "medlineplus.gov_en_all_2025-01.zim"))
LIC_DRUG = "(c) American Society of Health-System Pharmacists (AHFS Patient Medication Information), via MedlinePlus - personal/reference use"
LIC_HERB = "(c) Therapeutic Research Faculty (Natural Medicines), via MedlinePlus - personal/reference use"
LIC_ENCY = "(c) A.D.A.M., Inc. (A.D.A.M. Medical Encyclopedia), via MedlinePlus - personal/reference use"


def ints(pattern):
    return [int(t) for f in sorted(glob.glob(os.path.join(W, pattern))) for t in open(f).read().split()]


docs = []
d = json.load(open(os.path.join(W, "mplus_drugs.json")))
drugs = [(p, t) for p, t, c in d["keep"]] + [(d["rest"][i][0], d["rest"][i][1]) for i in ints("mplus_drugs_extra_*.txt")]
for p, t in drugs:
    docs.append({"key": p, "title": f"{t} (MedlinePlus drug information)", "slug": "medlineplus drug " + t,
                 "category": "medicine-pharmacology", "paths": [p], "source_url": "https://" + p,
                 "extra": {"license": LIC_DRUG, "content_type": "drug monograph"}})

for i in range(z.entry_count):
    e = z._get_entry_by_id(i)
    if not e.is_redirect and e.path.startswith("medlineplus.gov/druginfo/natural/") and e.path.endswith(".html"):
        t = e.title.replace(": MedlinePlus Supplements", "").strip()
        docs.append({"key": e.path, "title": f"{t} (herb/supplement - MedlinePlus)", "slug": "medlineplus herb " + t,
                     "category": "medicine-pharmacology", "paths": [e.path], "source_url": "https://" + e.path,
                     "extra": {"license": LIC_HERB, "content_type": "herb and supplement monograph"}})

FIRST_AID = re.compile(r"poison|overdose|bite|sting|first aid|injur|burn|wound|fractur|broken|dislocat|CPR|chok|shock|emergenc|"
                       r"heat|frostbite|hypotherm|drown|foreign|bleed|sprain|strain|splint|sling|unconscious|trauma|amputation|"
                       r"cuts|scrape|splinter|fishhook|tick removal|smashed|heimlich|abdominal thrusts|breathing|cardiac arrest|"
                       r"heart attack|seizure|fainting|dehydration|mountain sickness|altitude|barotrauma|electrical|radiation sickness|"
                       r"spider|scorpion|snake|jellyfish|stingray|stonefish|scorpion fish|marine animal|centipede|caterpillar|"
                       r"fire ants|kit|recogniz|anaphylaxis|nosebleed|sunburn|swallow|drug use first aid|jimsonweed|oleander|"
                       r"hemlock|mistletoe|yew|foxglove|pokeweed|nightshade|lily|dieffenbachia|philodendron|caladium|poinsettia|"
                       r"rhubarb|potato plant|jack-in-the-pulpit|jerusalem cherry|elephant ear|splint|intoxication|withdrawal", re.I)
DIET = re.compile(r"in diet|food safety|food poisoning prevention|preventing food poisoning|fresh vs|water in diet|infant formulas", re.I)
E = json.load(open(os.path.join(W, "mplus_ency.json")))
for i in ints("mplus_ency_keep_*.txt"):
    p, t = E[i]
    cat = "medical-first-aid" if FIRST_AID.search(t) else "food-storage-preservation" if DIET.search(t) else "medical-conditions"
    docs.append({"key": p, "title": f"{t} (MedlinePlus encyclopedia)", "slug": "medlineplus ency " + t,
                 "category": cat, "paths": [p], "source_url": "https://" + p,
                 "extra": {"license": LIC_ENCY, "content_type": "medical encyclopedia article"}})

# same drug title on two monographs (e.g. oral vs topical): add the MedlinePlus id to the file name
from collections import Counter as _C
_n = _C(x["slug"] for x in docs)
for x in docs:
    if _n[x["slug"]] > 1:
        x["slug"] += " " + x["key"].rsplit("/", 1)[-1].split(".")[0]
seen, out = set(), []
for dd in docs:
    if dd["key"] not in seen:
        seen.add(dd["key"]); out.append(dd)
json.dump(out, open(os.path.join(W, "zimsel_medlineplus.json"), "w", encoding="utf-8"), indent=0)
from collections import Counter
print(len(out), Counter(x["category"] for x in out), Counter(x["extra"]["content_type"] for x in out))
