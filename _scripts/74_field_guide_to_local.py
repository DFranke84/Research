"""Move the Field Guide pages that live in Montana into Local Area, and remove the ones that are not local
(user request 2026-10-12, using the verdicts in _work/field_guide_locality.json from 73_field_guide_locality.py).

  74_field_guide_to_local.py --check     show what would happen (nothing changes)
  74_field_guide_to_local.py             do it

Montana pages:
  * species the Montana Field Guide lists  -> a new Local Area page built like the others (71.build: Field Guide text, maps,
    photos, Wikipedia), then the Field Guide page is removed (Recycle Bin)
  * anything else (group articles 'Oak', books, species the Field Guide does not list) -> the page itself moves into
    local-area/<plants|wildlife|insects|fungi|references>/ (library_move rules: own files move, links fixed) and gets a type
  * already in Local Area (same Field Guide code, or same title) -> the Field Guide copy is just removed
'not local' pages -> Recycle Bin (library_delete). Garden/crop, general and nearby pages stay in the Field Guides.
Log: _work/field_guide_to_local.log. Then 20_catalog + 21_readme.
"""
import glob, importlib.util, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, slugify
import local_area as L
import library_delete as LD
import library_move as LM

spec = importlib.util.spec_from_file_location("w71", os.path.join(os.path.dirname(__file__), "71_build_local_wildlife.py"))
W = importlib.util.module_from_spec(spec); spec.loader.exec_module(W)

LOC = os.path.join(RESEARCH, "_work", "field_guide_locality.json")
LA = os.path.join(RESEARCH, "local-area")

GUIDE_GROUP = {"birds": "Wildlife - Birds", "fish-aquatic": "Wildlife - Fish", "mammals": "Wildlife - Mammals",
               "reptiles-amphibians": "Wildlife - Reptiles & amphibians", "fungi": "Fungi"}
OTHER_BUGS = "Insects - Other insects & bugs"
WEEDS = "Common weeds"


def _m(spec_):
    return {t.strip(): g for g, ts in spec_.items() for t in ts.split(";") if t.strip()}


INSECT_GROUP = _m({
    "Insects - Bees & wasps": "Bumblebee;Carpenter Ant;Common Blue Mud-dauber Wasp (Chalybion californicum);Eastern Carpenter Bee (Xylocopa virginica);"
        "Eastern Cicada-killer Wasp (Sphecius speciosus);Common Eastern Velvet Ant (Dasymutilla occidentalis);Hornet;Honey bee;"
        "Ligated Furrow Bee (Halictus ligatus);Yellow-legged Mud-dauber Wasp (Sceliphron caementarium);Yellowjacket",
    "Insects - Biting & stinging": "Anopheles;Botfly;Deer Fly;Horse Fly;Mosquito",
    "Spiders, ticks & mites": "Black widow;Bronze Jumping Spider (Eris militaris);Golden Jumping Spider (Paraphidippus aurantius);"
        "Marbled Orbweaver (Araneus marmoreus);Northern Yellow Sac Spider (Cheiracanthium mildei);Redlined Wolf Spider (Arctosa rubicunda);"
        "Spider;Wolf Spider;Tick;Ixodes;Mite;Poison Ivy Leaf Mite (Aculops rhois);Scorpion",
    "Insects - Butterflies": "Eastern Tiger Swallowtail (Papilio glaucus);Western Tiger Swallowtail (Papilio rutulus);Peck's Skipper (Polites peckius)",
    "Insects - Dragonflies & damselflies": "Dragonfly",
    "Insects - Garden & orchard pests": "Armyworm Moth (Pseudaletia unipuncta);Black Cherry Aphid (Myzus cerasi);Green Cloverworm Moth (Hypena scabra);"
        "Green Stink Bug (Chinavia hilaris);Grasshopper;Oleander Aphid (Aphis nerii);Spotted Cucumber Beetle (Diabrotica undecimpunctata);"
        "Large Yellow Underwing (Noctua pronuba);Spotted Lanternfly (Lycorma delicatula)",
    "Insects - Forest & tree pests": "Jack Pine Budworm Moth (Choristoneura pinus);Large Maple Spanworm Moth (Prochoerodes lineola);"
        "Yellow Birch Leaffolder Moth (Ancylis discigerana)",
    "Insects - Helpful insects": "Praying Mantis;Chinese Mantis (Tenodera sinensis);Pale Green Assassin Bug (Zelus luridus);"
        "Masked Hunter (Reduvius personatus);Poison hemlock moth (Agonopterix alstroemeriana)",
    "Insects - House & pantry pests": "Termite;Shiny Blue Bottle Fly (Cynomya cadaverina)",
    "Fungi": "Salmon-eggs (Hemitrichia decipiens)",   # a slime mold
})

PLANT_GROUP = _m({
    "Poisonous plants": "Cicuta;Digitalis;European lily of the valley (Convallaria majalis);Meadow deathcamas (Zigadenus venenosus);"
        "Mountain Deathcamas (Anticlea elegans);Poison ivy;Columbian Monkshood (Aconitum columbianum);Jimsonweed (Datura stramonium);"
        "Water hemlock (Cicuta maculata);Western poison ivy (Toxicodendron rydbergii);Upland larkspur (Delphinium nuttallianum);"
        "Purple foxglove (Digitalis purpurea);Bittersweet nightshade (Solanum dulcamara);Black nightshade (Solanum nigrum);"
        "Hemp dogbane (Apocynum cannabinum)",
    "Noxious weeds": "Japanese knotweed (Reynoutria japonica);Ragwort (Jacobaea vulgaris)",
    "Herbs": "Echinacea;German chamomile (Matricaria recutita);Mentha;Water mint (Mentha aquatica);Absinthe wormwood (Artemisia absinthium);"
        "Common mugwort (Artemisia vulgaris);Common motherwort (Leonurus cardiaca);Common selfheal (Prunella vulgaris);Wild bergamot (Monarda fistulosa)",
    "Berries & small fruit": "Blackberry;Cranberry;Gooseberry;Grape;Lonicera caerulea;Raspberry;Ribes;Sambucus;Strawberry;Viburnum trilobum;"
        "Canadian gooseberry (Ribes oxyacanthoides);Ribes americanum;Huckleberry;Vaccinium myrtilloides;Fragaria virginiana;"
        "Woodland strawberry (Fragaria vesca);Trailing blackberry (Rubus ursinus);Shepherdia argentea;Shepherdia canadensis;Wild Grape (Vitis riparia)",
    "Fruit trees - Cherries": "Cherry",
    "Roses": "Rose hip",
    "Nut trees": "Acorn;Eastern black walnut (Juglans nigra);Hazelnut",
    "Trees - Shade & ornamental": "Birch;Honey locust (Gleditsia triacanthos);Horse-chestnut (Aesculus hippocastanum);Maple;Oak;Willow;"
        "Black locust (Robinia pseudoacacia);Common hawthorn (Crataegus monogyna)",
    "Trees - Conifers": "Juniper;Pine;Spruce;Taxus;Western white pine (Pinus monticola);Lodgepole Pine Dwarf-Mistletoe (Arceuthobium americanum)",
    "Shrubs & hedges": "Berberis;Japanese barberry (Berberis thunbergii);Staghorn sumac (Rhus typhina);Sumac;Common buckthorn (Rhamnus cathartica);"
        "Virginia creeper (Parthenocissus quinquefolia)",
    "Native wildflowers & wild foods": "Common cowparsnip (Heracleum maximum);Common jewelweed (Impatiens capensis);Firewheel (Gaillardia pulchella);"
        "Goldenrod;Physalis;Prickly Pear;Slender stinging nettle (Urtica gracilis);Solomon's plume (Maianthemum racemosum);Sphagnum;"
        "Star-flowered lily-of-the-valley (Maianthemum stellatum);Stinging nettle;Typha;Viola (plant);Watercress;Wild rice",
    WEEDS: "Amaranth;Arctium;California poppy (Eschscholzia californica);Clover;False Cleavers (Galium spurium);Horseweed (Erigeron canadensis);"
        "Purple crownvetch (Securigera varia);Purslane;Taraxacum;Verbascum",
    "": "Conservation Trees and Shrubs for Montana;MONTANA NATIVE PLANT SOCIETY",   # documents -> references (no type)
})

INSECT_GROUPS = {g for g in INSECT_GROUP.values() if g != "Fungi"} | {OTHER_BUGS}


def nice_name(title):
    """'American yellow morel (Morchella americana)' -> 'American Yellow Morel'."""
    t = re.sub(r"\s*\(.*", "", title).strip()
    return " ".join(w[:1].upper() + w[1:] for w in t.split())


def folder_for(group):
    if not group:
        return "references"
    if group.startswith(("Insects", "Spiders")):
        return "insects"
    if group == "Fungi":
        return "fungi"
    if group.startswith("Wildlife"):
        return "wildlife"
    return "plants"


def mtfg_index():
    out = {}
    for f in ("mtfg_animalia.json", "mtfg_plants.json", "mtfg_fungi.json"):
        for code, (common, sci, fam) in json.load(open(os.path.join(L.W, f), encoding="utf-8")).items():
            out.setdefault(sci.lower(), (code, common, sci))
    return out


def local_pages():
    """elcode / title / scientific name (lower) -> Local Area page."""
    by = {}
    for f in glob.glob(os.path.join(LA, "**", "*.md"), recursive=True):
        t = open(f, encoding="utf-8").read(3000)
        for k in ("mtfg_elcode", "title", "scientific_name"):
            m = re.search(rf'^{k}: "?(.*?)"?\s*$', t, re.M)
            if m and m.group(1):
                by.setdefault((k, m.group(1).lower()), f)
    return by


def plant_group_by_status(code, common, sci, slug):
    """Montana Field Guide status: noxious -> Noxious weeds, introduced -> Common weeds, native -> wildflowers & wild foods."""
    d = W.gather("x", code, common, sci, slug, os.path.join(LA, "plants", slug + "_images"))
    st = (L.mtfg_status(code) if d.get("mtfg") else "").lower()
    if "noxious" in st:
        return "Noxious weeds"
    if "non-native" in st or "regulated weed" in st:
        return WEEDS
    return "Native wildflowers & wild foods"


def add_type(md, group):
    t = open(md, encoding="utf-8").read()
    head, sep, body = t.partition("\n---\n")
    if group:
        head = re.sub(r'^group:.*\n?', "", head, flags=re.M) + f'\ngroup: "{group}"'
        if not re.search(r"^Type: ", body, re.M):
            body = re.sub(r"^(# .*\n)", lambda m: m.group(1) + f"\nType: {group}\n", body, count=1, flags=re.M)
    open(md, "w", encoding="utf-8").write(head + sep + body)


def main():
    check = "--check" in sys.argv
    rows = json.load(open(LOC, encoding="utf-8"))
    idx, have = mtfg_index(), local_pages()
    twins = W.library_twins()
    log, counts = [], {"built": 0, "moved": 0, "duplicate removed": 0, "not local removed": 0, "problems": 0}
    say = lambda s: (print(s, flush=True), log.append(s))
    for r in rows:
        if r["verdict"] != "Montana":
            continue
        rel_ = r["file"].replace("\\", "/")
        it = {"file": rel_, "path": rel_}
        title, sci = r["title"], r.get("scientific_name") or ""
        if r["guide"] == "insects-arachnids":
            group = INSECT_GROUP.get(title, OTHER_BUGS)
        elif r["guide"] == "plants":
            group = PLANT_GROUP.get(title)
        else:
            group = INSECT_GROUP.get(title) or GUIDE_GROUP[r["guide"]]
        hit = idx.get(sci.lower()) if r.get("montana_field_guide") and r.get("kind") == "species" else None
        if hit:
            code, common, msci = hit
            if re.match(r"(A|An) ", common):   # Field Guide placeholder ('A Fungus') - use the Field Guide page's own name
                common = nice_name(title)
            dup = (have.get(("mtfg_elcode", code.lower())) or have.get(("title", common.lower()))
                   or have.get(("scientific_name", msci.lower())))
            if dup:
                say(f"duplicate  {rel_}  (Local Area already has {LD.rel(dup)})")
                counts["duplicate removed"] += 1
                if not check:
                    LD.execute(LD.plan(it))
                continue
            slug = slugify(common)
            if r["guide"] == "plants" and group is None:
                group = plant_group_by_status(code, common, msci, slug) if not check else "(by Field Guide status)"
            folder = folder_for(group)
            if os.path.exists(os.path.join(LA, folder, slug + ".md")):
                slug += "-" + r["guide"].split("-")[0]
            say(f"build      {rel_}  ->  local-area/{folder}/{slug}.md  [{group}]")
            counts["built"] += 1
            if check:
                continue
            W.GROUPS[group] = (group, folder, "local-profile" if folder == "plants" else "local-wildlife")
            if group in INSECT_GROUPS:
                W.INSECT.add(group)
            try:
                W.build(group, code, common, msci, slug, twins)
                have[("mtfg_elcode", code.lower())] = os.path.join(LA, folder, slug + ".md")
                LD.execute(LD.plan(it))
            except Exception as e:
                say(f"  ! build failed: {e}")
                counts["problems"] += 1
            continue
        dup = have.get(("title", title.lower())) or (have.get(("scientific_name", sci.lower())) if r.get("kind") == "species" and sci else None)
        if dup:
            say(f"duplicate  {rel_}  (Local Area already has {LD.rel(dup)})")
            counts["duplicate removed"] += 1
            if not check:
                LD.execute(LD.plan(it))
            continue
        if group is None:
            group = WEEDS
        folder = folder_for(group)
        same = os.path.join(LA, folder, os.path.basename(rel_))
        if os.path.exists(same):   # e.g. Huckleberry: Local Area already has a page of that name
            say(f"duplicate  {rel_}  (Local Area already has {LD.rel(same)})")
            counts["duplicate removed"] += 1
            if not check:
                LD.execute(LD.plan(it))
            continue
        p = LM.plan(it, "local-area")
        dest = os.path.join(LA, folder)
        p["problems"] = [x for x in p["problems"] if not x.startswith("local-area/ already has")]
        for f in p["move"] + p["copy"]:
            to = os.path.join(dest, os.path.relpath(f, os.path.dirname(LD.ab(rel_))))
            if os.path.exists(to):
                p["problems"].append(f"local-area/{folder}/ already has {os.path.basename(to)}")
        p["dest"] = dest
        say(f"move       {rel_}  ->  local-area/{folder}/  [{group or 'reference'}]" + ("" if not p["problems"] else "  PROBLEM: " + "; ".join(p["problems"])))
        if p["problems"]:
            counts["problems"] += 1
            continue
        counts["moved"] += 1
        if check:
            continue
        errs = LM.execute(p)
        if errs:
            say("  ! " + "; ".join(errs))
        if p.get("new_path"):
            add_type(LD.ab(p["new_path"]), group)
    gone = [r for r in rows if r["verdict"] == "not local"]
    for r in gone:
        rel_ = r["file"].replace("\\", "/")
        if not os.path.exists(LD.ab(rel_)):
            continue
        say(f"remove     {rel_}  (not local)")
        counts["not local removed"] += 1
        if not check:
            LD.execute(LD.plan({"file": rel_, "path": rel_}))
    say("counts: " + json.dumps(counts))
    if not check:
        open(os.path.join(RESEARCH, "_work", "field_guide_to_local.log"), "w", encoding="utf-8").write("\n".join(log) + "\n")
        for s in ("20_catalog.py", "21_readme.py"):
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), s)])


if __name__ == "__main__":
    main()
