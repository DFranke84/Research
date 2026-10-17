"""Select iFixit repair guides by device category (tree built from device pages: _work/ifixit_map.json).
Only categories relevant to self-reliance are kept (outdoor power equipment, home repair, key appliances, radios,
tools, vehicles, clothing/shoes, outdoor gear, sewing, clinical equipment, repair skills)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
M = json.load(open(os.path.join(W, "ifixit_map.json"), encoding="utf-8"))
parent = M["parent"]

# (device-path segment anywhere in the chain) -> category; first match (most specific listed first) wins
RULES = [
    ("Device/Water_Pump", "water"), ("Device/Plumbing", "water"),
    ("How_to_extend_the_life_of_your_Katadyn_Hiker_and_Hiker_Pro_Filter", "water"),
    ("Device/Weather_Station", "weather"),
    ("Device/Lawn_and_Garden", "mechanical-vehicles"),
    ("Device/Door_And_Window", "shelter-construction"), ("Device/Electrical", "energy-power"),
    ("Device/Space_Heater", "energy-power"), ("Device/Fan", "energy-power"), ("Device/Air_Conditioning", "energy-power"),
    ("Device/Heat_Pump", "energy-power"), ("Device/Furnace", "energy-power"), ("Device/Dehumidifier", "energy-power"),
    ("Device/Blower_Fan", "energy-power"), ("Device/Lighting", "energy-power"), ("Device/Solar_Lamp", "energy-power"),
    ("Device/Battery", "energy-power"), ("Device/FixHub_Portable_Power_Station", "energy-power"),
    ("Device/Refrigerator", "food-storage-preservation"), ("Device/Freezer", "food-storage-preservation"),
    ("Device/Stove", "cooking-fire"), ("Device/Barbecue_Grill", "cooking-fire"),
    ("Device/Radio", "communications-radio"), ("Device/Test_Equipment", "tools-crafts-skills"),
    ("Device/Firearm", "security-defense"), ("Device/Fishing_Tackle", "hunting-fishing-trapping"),
    ("Device/Camping_Equipment", "wilderness-survival"), ("Device/Binoculars", "wilderness-survival"),
    ("Device/Petzl_E03_050_Headlamp", "wilderness-survival"), ("Device/SolaDyne_LED_Lantern", "energy-power"),
    ("Device/Coleman_Rechargeable_Fluorescent_Twin_Tube", "energy-power"), ("Device/Kayak", "mechanical-vehicles"),
    ("Device/Arts_Crafts_and_Sewing", "tools-crafts-skills"),
    ("Device/Tool", "tools-crafts-skills"),
    ("Device/Car_and_Truck", "mechanical-vehicles"), ("Device/Motorcycle", "mechanical-vehicles"),
    ("Device/Tractor", "mechanical-vehicles"), ("Device/Boat", "mechanical-vehicles"), ("Device/Recreational_Vehicle", "mechanical-vehicles"),
    ("Device/Bicycle", "mechanical-vehicles"), ("Device/bicycle_manufacturer", "mechanical-vehicles"),
    ("Device/Clothing", "tools-crafts-skills"), ("Device/Shoe", "tools-crafts-skills"), ("Device/Eyeglasses", "medical-conditions"),
    ("Device/Hat", "tools-crafts-skills"), ("Device/Walking_Boots", "tools-crafts-skills"),
    ("Device/Electronics_Skills", "tools-crafts-skills"), ("Device/Blacksmithing", "tools-crafts-skills"),
    ("Device/Plastics", "tools-crafts-skills"), ("Device/Miscellaneous", "tools-crafts-skills"),
    ("Device/Clinical_Equipment", "medicine-pharmacology"),
]
EXCLUDE = {"Device/Power_Tool", "Device/Power_Tool_Accessory", "Device/Floor_Cleaner", "Device/Paint_Supply", "Device/Swimming_pool", "Device/Hot_Tub", "Device/Drywall",
           "Device/Aircraft", "Device/Personal_Electric_Vehicle"}


def chain(d):
    c, seen = [d], {d}
    while d in parent and parent[d] not in seen:
        d = parent[d]; c.append(d); seen.add(d)
    return c


docs = []
for g, (title, dev) in M["gdev"].items():
    ch = set(chain(dev))
    if ch & EXCLUDE:
        continue
    cat = next((c for key, c in RULES if key in ch or any(x.startswith(key + "#") for x in ch)), None)
    if not cat:
        continue
    docs.append({"key": g, "title": title, "category": cat, "paths": [g],
                 "source_url": "https://www.ifixit.com/" + g.replace(" ", "+"),
                 "extra": {"device": dev.replace("Device/", "").replace("_", " ")}})
docs.sort(key=lambda d: d["title"].lower())
json.dump(docs, open(os.path.join(W, "zimsel_ifixit.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
from collections import Counter
print(len(docs), Counter(d["category"] for d in docs).most_common())
