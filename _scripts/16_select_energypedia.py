"""Select energypedia technical pages (_work/energypedia_candidates.json + energypedia_keep_*.txt)."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
C = json.load(open(os.path.join(W, "energypedia_candidates.json"), encoding="utf-8"))
idx = [int(x) for f in sorted(glob.glob(os.path.join(W, "energypedia_keep_*.txt"))) for x in open(f).read().split()]


def category(t):
    if re.search(r"dryer|drying|cooling|refrigerat|milk|meat|vegetable|fruit|cereal|pre-cooling|river ice", t, re.I):
        return "food-storage-preservation"
    if re.search(r"irrigation|SPIS|pump|reservoir|water heat|water purif|water storage", t, re.I):
        return "water" if re.search(r"purif|water storage|pump", t, re.I) and not re.search(r"irrigation|SPIS", t, re.I) else "food-production"
    if re.search(r"stove|cook|kitchen|oven|charcoal|firewood|woodfuel|fuel|briquet|heat retainer|fireless|pressure cooker|gasifier stove|kerosene|LPG|plant oil|vegetable oil", t, re.I):
        return "cooking-fire"
    return "energy-power"


docs = []
for i in sorted(set(idx)):
    p, t, w, s, fp = C[i]
    t2 = re.sub(r"\s*\(PA Technology\)", " (Powering Agriculture technology sheet)", t)
    docs.append({"key": p, "title": t2, "category": category(t), "paths": [p],
                 "source_url": "https://energypedia.info/wiki/" + p})
json.dump(docs, open(os.path.join(W, "zimsel_energypedia.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
from collections import Counter
print(len(docs), Counter(d["category"] for d in docs))
