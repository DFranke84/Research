"""Fold the last Field Guide pages into Local Area and retire the Field Guides section (user request 2026-10-12).

  75_retire_field_guides.py --check     show what would happen
  75_retire_field_guides.py             do it

Uses the verdicts in _work/field_guide_locality.json (73) and the per-state counts added for 'nearby' species:
  nearby (PNW, not Montana) -> local-area/nearby/<page> with type 'Nearby - <Plants|Fungi|...>' and a banner saying where
                               it has been seen (iNaturalist wild sightings per state/province)
  garden / crop             -> local-area/plants/<page> with a Local Area type (Vegetables & field crops, Herbs, ...);
                               pages Local Area already covers (Garlic, Lavender...) are removed instead
  general                   -> ordinary library categories (foraging-wild-food, wilderness-survival)
Removed pages go to the Recycle Bin (library_delete). Moves use library_move (own files move, links fixed).
Then 20_catalog + 21_readme.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
import library_delete as LD
import library_move as LM

LOC = os.path.join(RESEARCH, "_work", "field_guide_locality.json")
LA = os.path.join(RESEARCH, "local-area")
VEG = "Vegetables & field crops"
NEARBY = {"plants": "Nearby - Plants", "fungi": "Nearby - Fungi", "insects-arachnids": "Nearby - Insects & spiders",
          "reptiles-amphibians": "Nearby - Reptiles & amphibians", "mammals": "Nearby - Mammals"}
GARDEN = {"Apple": "Fruit trees - Apples", "Walnut": "Nut trees", "Calendula": "Herbs", "Rosemary": "Herbs",
          **{t: VEG for t in ("Bean", "Beetroot", "Buckwheat", "Carrot", "Chickpea", "Chili pepper", "Cucumber", "Cucurbita",
                              "Kale", "Onion", "Pea", "Spinach", "Turnip")}}
# already covered by a Local Area page (same plant), or not relevant here -> removed
DROP = {"Aronia": "aronia", "Garlic": "garlic", "Peppermint": "peppermint", "Sage": "sage", "Thyme": "thyme",
        "Lavandula": "lavender", "Symphytum": "comfrey", "Blackcurrant": "black-currant", "Wheat": "cultivated-wheat",
        "Chamomile": "german-chamomile-matricaria-recutita", "Bamboo": None}
GENERAL = {"Edible mushroom": "foraging-wild-food", "Mushroom": "foraging-wild-food",
           "List of poisonous plants": "foraging-wild-food", "Poisonous Plants in the Home Landscape": "foraging-wild-food",
           "Identification of Mammal Tracks from Sooted Track Stations": "wilderness-survival"}


def banner(r):
    pl = {k: v for k, v in (r.get("places") or {}).items() if v}
    where = " · ".join(f"{k} {v:,}" for k, v in sorted(pl.items(), key=lambda x: -x[1]))
    return ("> 📍 **Nearby, not Montana.** The Montana Field Guide does not list this species and it has fewer than 3 wild "
            "records in Montana" + (f" ({r['montana_obs']})" if r.get("montana_obs") else "") + ". Wild sightings close by "
            "(iNaturalist, checked 2026-10-12): " + (where or "a few records in the region") + ".\n")


def set_type(md, group, extra=""):
    t = open(md, encoding="utf-8").read()
    head, sep, body = t.partition("\n---\n")
    head = re.sub(r'^group:.*\n?', "", head, flags=re.M) + f'\ngroup: "{group}"'
    body = re.sub(r"^Type: .*\n", "", body, flags=re.M)
    body = re.sub(r"^(# .*\n)", lambda m: m.group(1) + f"\nType: {group}\n" + ("\n" + extra if extra else ""), body, count=1, flags=re.M)
    open(md, "w", encoding="utf-8").write(head + sep + body)


def move(rel_, dest_dir, check):
    """library_move to any folder (the category is set from the folder's first part)."""
    it = {"file": rel_, "path": rel_}
    cat = os.path.relpath(dest_dir, RESEARCH).replace(os.sep, "/").split("/")[0]
    p = LM.plan(it, cat)
    p["problems"] = [x for x in p["problems"] if "already has" not in x]
    for f in p["move"] + p["copy"]:
        to = os.path.join(dest_dir, os.path.relpath(f, os.path.dirname(LD.ab(rel_))))
        if os.path.exists(to):
            p["problems"].append(f"{os.path.relpath(dest_dir, RESEARCH)} already has {os.path.basename(to)}")
    p["dest"] = dest_dir
    if p["problems"] or check:
        return p["problems"], None
    errs = LM.execute(p)
    return errs, (LD.ab(p["new_path"]) if p.get("new_path") else None)


def main():
    check = "--check" in sys.argv
    rows = json.load(open(LOC, encoding="utf-8"))
    log, counts = [], {"nearby": 0, "garden": 0, "general": 0, "removed": 0, "problems": 0}
    say = lambda s: (print(s, flush=True), log.append(s))
    for r in rows:
        rel_ = r["file"].replace("\\", "/")
        if not os.path.exists(LD.ab(rel_)):
            continue
        v, title = r["verdict"], r["title"]
        if v.startswith("nearby"):
            group = NEARBY[r["guide"]]
            errs, new = move(rel_, os.path.join(LA, "nearby"), check)
            kind = "nearby"
        elif v.startswith("garden") and title in DROP:
            other = DROP[title]
            say(f"remove   {rel_}  " + (f"(Local Area already has plants/{other}.md)" if other else "(not relevant here)"))
            if other:
                assert os.path.exists(os.path.join(LA, "plants", other + ".md")), other
            counts["removed"] += 1
            if not check:
                LD.execute(LD.plan({"file": rel_, "path": rel_}))
            continue
        elif v.startswith("garden"):
            group = GARDEN[title]
            errs, new = move(rel_, os.path.join(LA, "plants"), check)
            kind = "garden"
        elif v.startswith("general"):
            group = None
            errs, new = move(rel_, os.path.join(RESEARCH, GENERAL[title]), check)
            kind = "general"
        else:
            say(f"?? left  {rel_}  ({v})")
            continue
        say(f"{kind:8} {rel_}  ->  " + (group or GENERAL[title]) + ("  PROBLEM: " + "; ".join(errs) if errs else ""))
        if errs:
            counts["problems"] += 1
            continue
        counts[kind] += 1
        if new and group:
            set_type(new, group, banner(r) if kind == "nearby" else "")
    say("counts: " + json.dumps(counts))
    if not check:
        open(os.path.join(RESEARCH, "_work", "retire_field_guides.log"), "w", encoding="utf-8").write("\n".join(log) + "\n")
        for s in ("20_catalog.py", "21_readme.py"):
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), s)])


if __name__ == "__main__":
    main()
