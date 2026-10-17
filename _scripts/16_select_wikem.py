"""Select WikEM articles from the reviewed candidate list (_work/wikem_candidates.json + wikem_keep_*.txt)
and assign a category by topic."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
L = json.load(open(os.path.join(W, "wikem_candidates.json"), encoding="utf-8"))
idx = [int(t) for f in sorted(glob.glob(os.path.join(W, "wikem_keep_*.txt"))) for t in open(f).read().split()]

CBRN = re.compile(r"radiation|dirty bomb|chemical weapon|blister chemical|nerve|phosgene|lewisite|sulfur mustard|mass destruction|"
                  r"bioterror|anthrax|hazmat|pulmonary chemical|ricin|smallpox|plague|chlorine gas|chloramine|arsine|phosphine|"
                  r"white phosphorus|explosi|blast|toxic inhalation|smoke inhalation|pepper spray", re.I)
EMERG = re.compile(r"mass casualty|pandemic|nine line|field trauma triage|first responder|isolation precautions|prisoners of war|combat stress", re.I)
FIRST = re.compile(r"toxic|poison|envenomation|bite|sting|jellyfish|urchin|anemone|coral|stonefish|stingray|octopus|lionfish|"
                   r"cone shell|irukandji|nematocyst|spider|snake|crotaline|elapidae|scorpion|tick|mushroom|amanita|gyromitra|"
                   r"inocybe|clitocybe|crotinarius|jimson|aconitum|strychnine|shellfish|ciguatera|scombroid|tetrodotoxin|"
                   r"trauma|fracture|dislocat|splint|sprain|laceration|wound|injur|amputation|avulsion|burn|escharotomy|"
                   r"hypotherm|cold|chilblain|frostbite|trench foot|heat|hyperthermia|altitude|decompression|diving|scuba|"
                   r"barotrauma|squeeze|submersion|drowning|lightning|electrical|shock|hemorrhage|hemothorax|pneumothorax|"
                   r"thoracostomy|flail|tourniquet|combat|tactical|care under fire|resuscitation|BLS|airway|cricothyrotomy|"
                   r"foreign bod|fishhook|ring removal|hair tourniquet|subungual|nail|felon|paronychia|incision and drainage|"
                   r"abscess|kg \(|epistaxis|dental|delivery|emergent delivery|episiotomy|postpartum|preterm labor|cord prolapse|"
                   r"strangulation|gun shot|ballistic|shark|alligator|mammalian|lizard|ingestion|activated charcoal|antidote|"
                   r"antivenin|toxidrome|pressure immobilization|hematoma block|LET|compartment|crush|rhabdomyolysis|"
                   r"salt|dehydration|oral rehydration|acid|alkali|caustic|cement|tar burn|hydrocarbon|hydrofluoric|"
                   r"hydrogen sulfide|cyanide|carbon monoxide|methemoglobin|organophosphate|carbamate|paraquat|lead|mercury|"
                   r"arsenic|heavy metal|metal fume|methanol|ethylene glycol|isopropyl|toxic alcohol|salicylate|NSAID|opioid|"
                   r"withdrawal|delirium tremens|poison control|intraosseous|nasopharyngeal|oropharyngeal|bag valve|"
                   r"improvised|ultraviolet keratitis|globe rupture|hyphema|ocular foreign|eyelid|ear foreign|nasal", re.I)
WATER = re.compile(r"water purification", re.I)
WILD = re.compile(r"wilderness|safety at sea|rucksack|water-related injuries|travel medicine|traveler", re.I)
FOOD = re.compile(r"nutrition|nutritional needs|starvation|refeeding|scurvy|pellagra|thiamine|vitamin|beriberi|rickets", re.I)


def category(t):
    if WATER.search(t): return "water"
    if CBRN.search(t): return "cbrn-hazmat"
    if EMERG.search(t): return "emergency-preparedness"
    if WILD.search(t): return "wilderness-survival"
    if FOOD.search(t): return "medical-conditions"
    if FIRST.search(t): return "medical-first-aid"
    return "medical-conditions"


docs = []
for i in sorted(set(idx)):
    p, t = L[i]
    title = f"Pediatric dosing weight: {t}" if re.match(r"^\d+(\.\d+)?kg \(", t) else t
    docs.append({"key": p, "title": f"{title} (WikEM)", "slug": "wikem " + title, "category": category(t),
                 "paths": [p], "source_url": "https://www.wikem.org/wiki/" + p})
json.dump(docs, open(os.path.join(W, "zimsel_wikem.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
from collections import Counter
print(len(docs), Counter(d["category"] for d in docs))
