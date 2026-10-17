"""Select Stack Exchange questions per site by tag rules + score, and assign categories.
Writes _work/se_<site>_select.json. Only answered questions are considered (accepted answer or >=1 answer)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")

# site: (min_score, cap, include tags, exclude tags, default category, [(tags, category), ...] first match wins)
RULES = {
 "outdoors": (5, 500,
   "survival safety camping backpacking knots ropes winter cold-weather food cooking fire stoves water-purification drinking-water water "
   "first-aid health emergencies navigation maps compasses gps animals bears bugs hunting fishing tents sleeping-bags clothing footwear "
   "gear-care repairs waterproofing weather rain snow plants trees knives hygiene rivers wilderness backcountry preparation wild-camping "
   "shelter boats canoes kayaks sea swimming high-altitude trekking hiking diy",
   "rock-climbing bouldering skiing scuba-diving geocaching bird-watching bird-behaviour birds legality belaying rappelling climbing",
   "wilderness-survival",
   [("knots ropes", "tools-crafts-skills"), ("navigation maps compasses gps", "navigation-mapping"),
    ("first-aid health high-altitude", "medical-first-aid"), ("water-purification drinking-water", "water"),
    ("food cooking stoves fire", "cooking-fire"), ("hunting fishing", "hunting-fishing-trapping"), ("weather rain snow", "weather")]),
 "ham": (4, 300,
   "antenna antenna-theory antenna-construction antenna-system wire-antenna dipole vertical-antenna yagi emergency hf vhf uhf propagation "
   "cw morse-code repeater digital-modes packet aprs license procedure jargon baofeng uv-5r ht mobile receiver transceiver rf-power "
   "grounding lightning band-plan coaxial-cable feed-line swr-meter balun impedance-matching frequency modes ssb fm equipment-operation "
   "equipment-protection etiquette callsign fcc noise rfi batteries power-supply solar",
   "contest satellites microwave gnuradio phased-array math history software-defined-radio rtl-sdr",
   "communications-radio", []),
 "cooking": (8, 500,
   "food-safety storage-method storage-lifetime food-preservation canning fermentation bread dough sourdough yeast rice beans flour meat "
   "fish eggs milk cheese butter fat oil salt sugar substitutions boiling cast-iron water stock soup measurements drying smoking curing "
   "pickling jerky dehydrating grains vegetables potatoes onions garlic freezing refrigerator temperature cooking-time equipment knives "
   "baking frying roasting grilling barbecue stews slow-cooking pressure-cooker",
   "cake cookies dessert chocolate candy ice-cream sous-vide language pizza pie cocktails alcohol italian-cuisine asian-cuisine "
   "chinese-cuisine japanese-cuisine indian-cuisine vegan molecular-gastronomy coffee tea",
   "cooking-fire",
   [("food-safety storage-method storage-lifetime food-preservation canning fermentation drying smoking curing pickling jerky "
     "dehydrating freezing refrigerator", "food-storage-preservation")]),
 "mechanics": (8, 400,
   "engine battery starting tires brakes fuel-system oil oil-change maintenance troubleshooting cooling-system coolant diesel sparkplugs "
   "alternator ignition starter carburetor jump-start overheating winter radiator electrical wiring gasoline fuel-tank fuel-injection "
   "fuel-consumption motorcycle repair tools leak oil-leak rust lights headlight timing-belt diagnostics small-engine generator "
   "clutch manual-transmission transmission suspension steering exhaust wheels",
   "audio performance turbocharger obd-ii electronic-control-module cel",
   "mechanical-vehicles", []),
 "bicycles": (8, 350,
   "maintenance repair tire innertube puncture chain brakes wheels spokes wheel-building derailleur derailleur-rear gears shifting cable "
   "bearings hub lubricant tools cleaning trailer cargo touring winter frugal pump tubeless rim-brake disc-brake storage lighting rack "
   "bottom-bracket headset pedals crankset freewheel cassette chainring brake-pads rims damage mechanical",
   "racing training bike-fit fitness legal product-rec identify-this-bike vintage carbon clothes traffic",
   "mechanical-vehicles", []),
 "gardening": (6, 500,
   "vegetables fruit-trees soil compost pest-control pests diseases seeds germination seedlings seed-saving propagation cuttings grafting "
   "harvesting watering fertilizer soil-amendment raised-beds tomatoes potatoes root-vegetables herbs pruning weeds weed-control mulch "
   "organic insects fungus container-gardening hydroponic pollination overwintering strawberries apples peppers cucumbers tree-care "
   "trees planting transplanting fruits drainage nutrients variety-selection plant-health diagnosis",
   "houseplants succulents cactus bonsai lawn lawn-repair grass flowers roses office-gardening landscaping aloe indoors",
   "food-production", []),
 "diy": (10, 700,
   "plumbing water pipe leak drain water-heater toilet electrical wiring circuit-breaker electrical-panel receptacle switch "
   "electrical-grounding safety roof insulation heating furnace framing concrete foundation structural tools repair pest-control mold "
   "waterproofing drainage windows doors energy-efficiency gas wood screws deck fence exterior outdoor well septic generator solar "
   "wood-stove chimney fireplace attic basement vent joists studs gfci sink faucet shower drain-waste-vent",
   "drywall painting paint flooring tile cabinets trim kitchens code-compliance nec data-wiring ceiling-fan light-fixture "
   "hardwood-floor bathtub furniture countertops carpet",
   "shelter-construction",
   [("plumbing water pipe leak drain water-heater sink faucet shower drain-waste-vent well septic", "water"),
    ("toilet pest-control mold", "sanitation-hygiene"),
    ("electrical wiring circuit-breaker electrical-panel receptacle switch electrical-grounding gfci generator solar", "energy-power"),
    ("wood-stove chimney fireplace", "cooking-fire"), ("tools screws", "tools-crafts-skills")]),
 "woodworking": (5, 250,
   "hand-tools joinery sharpening plane hand-planing chisel hand-saw green-wood wood-drying making-lumber traditional-techniques "
   "wood-selection glue finishing tool-maintenance tool-repair drilling clamps lumber workbench turning lathe safety outdoor "
   "water-protection wood-movement technique wood-repair mortise-and-tenon dowel strength fasteners screws wood",
   "table-saw router router-bit router-table cnc dust-collection mdf miter-saw band-saw thickness-planer jointer",
   "tools-crafts-skills", []),
 "pets": (5, 150,
   "health diseases injury poison parasites fleas medicines feeding diet rabbits breeding horses veterinarian infections dental-care "
   "skin-condition allergies senior-pet death eating drinking hygiene grooming temperature outdoor feral strays containment",
   "aquarium fish betta reptiles lizards leopard-geckos hamsters toys play vocalizations snakes turtles tortoises saltwater "
   "freshwater community-aquarium aquatic-plants water-parameters pond filters",
   "food-production", []),
 "homebrew": (5, 200,
   "fermentation yeast sanitation cider wine mead bottling storage techniques equipment first-time-brewer water beer carbonation "
   "cleaning contamination bottle-conditioning priming priming-sugar fruit sugar alcohol-content temperature airlock hydrometer "
   "specific-gravity reusing-yeast yeast-starters ginger-beer brewing process troubleshooting aging",
   "kegging kegerator keg corny-keg beer-styles ipa lager stout dry-hop contest",
   "food-storage-preservation", []),
 "sustainability": (5, 200,
   "composting solar-power water heating energy-efficiency insulation gardening permaculture firewood vermicomposting aquaponics toilet "
   "cooking batteries wind-power water-heating cooling reuse waste farming husbandry food cleaning hygiene photovoltaics "
   "electricity-generation energy-storage water-management solar-thermal biodegradable-waste waste-water building-materials home "
   "personal-hygiene plastic-alternatives",
   "carbon-footprint economy green-it computing defining-sustainability carbon-offsetting decarbonisation transport cars "
   "electric-vehicles life-cycle-analysis greenhouse-gas-emissions",
   "energy-power",
   [("composting gardening permaculture farming husbandry aquaponics vermicomposting food", "food-production"),
    ("water water-management waste-water", "water"), ("toilet waste cleaning hygiene personal-hygiene biodegradable-waste", "sanitation-hygiene"),
    ("cooking firewood", "cooking-fire")]),
 "crafts": (5, 120,
   "sewing knitting crocheting fabric leather adhesives metalworking wood dye weaving pottery clay ceramics clothing repair restoration "
   "sewing-machine casting mold-making wax metal cutting tool-selection material-selection preservation yarn fiber-crafts felt carving "
   "embroidery upcycling plaster",
   "drawing painting oil-paint watercolor pencils colored-pencils acrylic-paint origami sketching portrait-drawing calligraphy "
   "airbrush markers illustration pencil-shading erasers pens paint-brushes kids-crafts canvas oil-pastels",
   "tools-crafts-skills", []),
 "lifehacks": (8, 100,
   "cleaning food substitute-tool water winter comfort temperature clothing shoes pest-control laundry repair camping fire batteries "
   "electricity health safety container storage food-safety hardware adhesive smell air weather sleeping kitchen home",
   "technology phone headphones office-supplies stationery photography music shopping books",
   "tools-crafts-skills",
   [("cleaning laundry pest-control smell", "sanitation-hygiene"), ("food food-safety kitchen", "food-storage-preservation")]),
}


def select(site):
    mn, cap, inc, exc, default, cats = RULES[site]
    inc, exc = set(inc.split()), set(exc.split())
    L = json.load(open(os.path.join(W, f"se_{site}_index.json"), encoding="utf-8"))
    out = []
    for path, title, score, tags, n_ans, acc in L:
        tags = set(tags)
        if score < mn or not (acc or n_ans) or not (tags & inc) or (tags & exc and not tags & inc - exc):
            continue
        cat = next((c for tl, c in cats if tags & set(tl.split())), default)
        out.append({"path": path, "title": title, "score": score, "tags": sorted(tags), "category": cat})
    out.sort(key=lambda x: -x["score"])
    out = out[:cap]
    json.dump(out, open(os.path.join(W, f"se_{site}_select.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    return out


if __name__ == "__main__":
    from collections import Counter
    tot = 0
    for site in (sys.argv[1:] or RULES):
        o = select(site); tot += len(o)
        print(f"{site:15} {len(o):4}  min score {o[-1]['score'] if o else '-':>4}  {dict(Counter(x['category'] for x in o))}")
    print("total", tot)
