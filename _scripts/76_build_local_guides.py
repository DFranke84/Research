"""Kalispell topic guides for Local Area (user request 2026-10-12): Food preservation at our altitude, Living with
wildlife, Heating with wood, Livestock & bees. Each page sums up what the downloaded sources say (cited) and links the
sources (local-area/references, built by 69 from local_area_specs.REFS with the same 'group') and the library's own books.

  76_build_local_guides.py          build/refresh the pages in local-area/topics/, then 20_catalog + 21_readme

Pages carry source_type 'local-guide' and group = the Local Area tile they belong to.
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter

D = os.path.join(RESEARCH, "local-area")
OUT = os.path.join(D, "topics")


def lib(path, text=None):
    """Link to a library file from local-area/topics/ - only if it exists."""
    p = os.path.join(RESEARCH, path)
    if not os.path.exists(p):
        print("  missing:", path)
        return None
    if text is None:
        m = re.search(r'^title: "(.*)"', open(p, encoding="utf-8").read(2000), re.M)
        text = m.group(1) if m else os.path.basename(path)
    return f"[{text}](../../{path})"


def ref(key, text=None):
    return lib(f"local-area/references/{key}.md", text)


def wild(slug):
    return lib(f"local-area/wildlife/{slug}.md")


def bullets(items):
    return "\n".join(f"- {x}" for x in items if x)


def page(slug, title, group, intro, body):
    meta = {"title": title, "category": "local-area", "source_type": "local-guide", "group": group,
            "license": "Compiled from the linked public agency and university publications",
            "provenance": "Compiled for this library from the linked Local Area and library documents", "compiled": TODAY,
            "date_added": TODAY, "date_source": "added to the library"}
    os.makedirs(OUT, exist_ok=True)
    text = front_matter(meta) + f"\n# {title}\n\nType: {group}  \n{intro}\n\n{body}\n"
    open(os.path.join(OUT, slug + ".md"), "w", encoding="utf-8").write(text)
    print("  page: topics/" + slug + ".md")


FS = "food-storage-preservation/"


def food():
    body = f"""## Your altitude: about 2,984 feet

MSU lists **Kalispell at 2,984 feet** in its table of Montana county-seat altitudes ({lib(FS + 'home-canning-using-boiling-water-canners-and-pressure-canners-montguide-mt200905hr.md')}).
Water boils at a lower temperature the higher you are, so home-canned food needs **more pressure or more time** than a sea-level recipe says.
Much of the Flathead Valley outside town is higher than 3,000 feet - check your own elevation (any topo map in the **Maps** topic, or your GPS) and use the row for it.

| Canning method | Setting for Kalispell (2,001-4,000 ft) | Source |
|---|---|---|
| **Dial-gauge pressure canner** | **12 lb** pressure (11 lb is only for 0-2,000 ft; 13 lb for 4,001-6,000 ft) | MSU MT200905HR |
| **Weighted-gauge pressure canner** | **15 lb** - required at all altitudes above 1,000 ft | MSU MT200905HR |
| **Boiling-water canner** | Use the processing time in the **2,001-3,000 ft** column of MSU's tables; if your home is above 3,000 ft use the **3,001-4,000 ft** column | MSU MT200905HR / MT200906HR |
| **Jams and jellies** | Cook to the lower jelling temperature for your altitude | {lib(FS + 'boiling-points-of-typical-fruit-sugar-mixtures-at-various-altitudes.md', 'Boiling points at altitude')} |

**Have a dial gauge tested every year** - MSU says dial-gauge canners must be tested yearly for accurate readings; ask the county Extension office (Flathead County Extension, Kalispell) or a hardware store.
Low-acid foods (vegetables, meat, fish) **must** be pressure canned: botulism toxin from under-processed jars can kill.

## Montana canning guides in your library (MSU Extension)

{bullets([lib(FS + 'home-canning-using-boiling-water-canners-and-pressure-canners-montguide-mt200905hr.md'),
          lib(FS + 'processing-fruit-and-tomato-products-times-and-pressures-montguide-mt200906hr.md'),
          lib(FS + 'pressure-canning-meat-poultry-and-fish-in-montana-montguide-mt200903hr.md'),
          lib(FS + 'canning-pickles-and-sauerkraut-montguide-mt200902hr.md'),
          lib(FS + 'making-jams-jellies-and-syrups-montguide-mt200904hr.md'),
          lib(FS + 'home-canning-using-an-atmospheric-steam-canner.md', 'Home-canning Using an Atmospheric Steam Canner (MSU MT202006HR)')])}

The **Food Storage & Preservation** category also holds over 400 tested recipes from the National Center for Home Food Preservation (search "NCHFP") - always switch their times to the Kalispell column above.

## Freezing and drying

{bullets([lib(FS + 'safety-is-the-top-priority.md'), lib(FS + 'freezing-fruit-montguide-mt200910hr.md'),
          lib(FS + 'drying-vegetables-montguide-mt200907hr.md'), lib(FS + 'drying-fruits.md', 'Drying Fruits (MSU MT200909HR)'),
          lib(FS + 'nchfp-drying-fruits-and-vegetables.md')])}

## Storing the harvest - root cellars and cold storage

Cool, cold-storage crops (potatoes, carrots, beets, cabbage, winter squash, onions) can keep for months without canning. These guides give the temperature and humidity each crop wants and how to build or improvise a root cellar; the Alaska guide is written for a climate colder than ours.

{bullets([lib(FS + 'storing-vegetables-at-home.md'), lib(FS + 'storing-vegetables.md'), lib(FS + 'uaf-root-cellars-for-alaska-hga-00331.md'),
          lib(FS + 'handbook-for-building-a-root-cellar-novia-2016.md'),
          lib(FS + 'storing-vegetables-fruits-in-basements-cellars-outbuildings-pits-no-119-1978.md'),
          lib(FS + 'cold-storage-of-fruits-and-vegetables-practical-action.md')])}

Each vegetable page in **Vegetables** also quotes what these guides say about storing that crop.
"""
    page("kalispell-food-preservation", "Food Preservation in Kalispell - Canning at Our Altitude", "Food preservation",
         "Canning pressures and times for Kalispell's elevation, freezing, drying and root-cellar storage - from MSU Extension and the library's food-storage guides.",
         body)


def wildlife():
    lww = ["tips", "deer", "voles", "pocket-gophers", "rabbits", "ground-squirrels", "tree-squirrels", "skunks", "raccoons", "porcupines",
           "woodpeckers", "woodrats", "bats", "snakes", "magpies", "starlings", "turkeys", "beavers", "injured-orphaned-wildlife",
           "subdivision-recommendations"]
    body = f"""## Bears - grizzly and black bears both live around the Flathead Valley

Montana FWP: bears are curious and food driven, and **securing attractants greatly reduces the chance of a conflict** ({ref('fwp-living-in-bear-country')}).

**Keep attractants away from bears (FWP):**
- **Garbage:** an IGBC-certified bear-resistant bin in a secure spot, or keep garbage and recycling in a secured building; put it out only on collection day.
- **Pet food, bird feeders, barbecues:** feed pets outside only by day and clean up; skip bird feeding during the active bear season (use bird baths and native plants instead); clean the grill after use.
- **Fruit trees, gardens, compost:** pick fruit as soon as it is ripe, store picked fruit and vegetables inside a secure building, and consider an electric fence around fruit trees and the garden.
- **Livestock:** store feed in a secure building; secure chickens, goats and sheep with an electric fence.
- **How to secure things:** a hard-sided building with a securable door (a hasp and carabiner is enough), a steel drum with a locking lid or another bear-resistant container, or an effective, maintained electric fence. Motion-activated sirens or lights, loud noises and an electrified "unwelcome mat" also deter bears.

## Electric fencing for bears (FWP guide, April 2025)

From {ref('fwp-electric-fencing-guide')}:
- Bears need a shock of **at least 5,000-7,000 volts** to be deterred.
- Use **at least 5 electrified wires** (or a mix of hot and ground-return wires), the **lowest about 8-12 inches** above the ground and the **top at least 36-42 inches** high.
- The energizer should pulse **45-60 times a minute**; use a **low-impedance** energizer (high-impedance "weed burner" types can start fires). Plug-in 110-volt AC energizers are the cheapest to run and recommended where possible; battery and solar units work for remote spots.
- Ground rods: galvanized steel at least 1/2 inch thick, 6-8 feet long, driven almost all the way in - and **3-6 feet of ground rod per joule** of stored energy. In dry or rocky soil use several rods 10 feet apart, or a ground-return design.
- Never electrify barbed wire; hang warning signs; check the fence with a fence voltage meter.
- Fences protect gardens, fruit trees, chicken coops, beehives, compost, garbage, sheds and more.

**Help with the cost:** FWP can help design and install a fence, and Defenders of Wildlife reimburses **50 percent of the cost, up to $500 per project** in eligible counties - you must contact them **before** buying materials ({ref('defenders-electric-fence-brochure')}).

More: {ref('fwp-be-bear-aware')} · {ref('fwp-bear-aware-flyer-homes')} · {ref('defenders-got-bears-mt')}

## Mountain lions, wolves and moose

FWP's pages on these animals are about the species and their management in Montana; they include where to report problems - for a suspected **livestock loss to wolves**, call USDA Wildlife Services (West District (406) 459-5943) ({ref('fwp-wolf')}).
{bullets([ref('fwp-mountain-lion'), ref('fwp-wolf'), ref('fwp-moose')])}

Species pages in Local Area: {", ".join(x for x in [wild('grizzly-bear'), wild('american-black-bear'), wild('mountain-lion'), wild('gray-wolf'), wild('moose'), wild('coyote'), wild('bobcat')] if x)}

## Deer in the garden

FWP: the most common deer complaint is damage to **vegetable gardens, fruit trees and ornamentals**, and no single trick works for long. **Fencing is the most effective deterrent** - deer easily jump a 5-foot fence and many clear 6 feet, so a single fence needs to be **7-8 feet** high; a cheaper option is **two 5-foot fences 4-5 feet apart** (deer cannot do the high jump and the broad jump together), or a 5-foot fence with an extra wire slanting out at 30 degrees for 4-5 feet. A free-roaming dog in a fenced yard is a strong deterrent; repellents only help with light pressure ({ref('fwp-lww-deer')}).
Species pages: {", ".join(x for x in [wild('white-tailed-deer'), wild('mule-deer'), wild('elk')] if x)}

## Smaller animals around the house and garden (FWP Living with Wildlife)

{bullets([ref('fwp-lww-' + s) for s in lww])}

Related: the **Pests & Problems** topic has MSU's pages on vole, deer and woodpecker damage to trees.
"""
    page("living-with-wildlife-kalispell", "Living with Wildlife Around Kalispell - Bears, Deer and Garden Pests", "Living with wildlife",
         "Keeping bears, lions, deer and smaller animals out of trouble - and out of the garden, chicken coop and garbage - from Montana FWP and partners.",
         body)


def wood():
    body = f"""## Cutting your own firewood - Flathead National Forest (2025 guide)

From {ref('flathead-nf-firewood-guide')}:
- A **personal-use firewood permit** is needed to cut and take firewood home (wood you burn at your campsite needs none). The permit season is **January 1 to December 31**; the permit is good across the Forest Service Northern Region, but check local rules with the ranger district.
- **4-cord minimum, 12-cord maximum per adult per year.** Check the Forest Products web page or a ranger district for current cost (the 2025 guide points there for fees).
- You may cut **dead down trees and standing dead trees** in the permitted area. **Do not** cut standing cedar or Pacific yew, anything with signs, tags or paint marks, or within **150 feet** of streams, ponds or wet areas.
- **Six feet** is the longest piece you may haul; winch cables no longer than 100 feet. Fill in the removal record on the permit before you leave the site.
- Get permits at any ranger district (Supervisor's Office in Kalispell, Tally Lake, Swan Lake, Hungry Horse/Glacier View, Spotted Bear). Use the free Motor Vehicle Use Map for open roads.

## Which local wood gives the most heat

From Utah State University Extension's firewood table ({ref('usu-wood-heating')}) - heat per **cord of air-dried wood**:

| Wood (common here) | Heat per cord (million BTU) | Dry weight per cord (lb) | Notes (USU) |
|---|---|---|---|
| Western larch (tamarack) | 21.8 | 3,330 | easy-medium to split, many sparks |
| Lodgepole pine | 21.1 | 2,610 | easy to split, many sparks, good fragrance |
| Birch | 20.8 | 2,992 | good coals, few sparks |
| Douglas-fir | 20.7 | 2,970 | easy to split, smoky, good overall |
| Aspen (quaking) | 18.2 | 2,160 | easy to split, few sparks |
| Ponderosa pine | 16.2 | 2,336 | many sparks |
| Cottonwood | 15.8 | 2,272 | easy to split |
| Spruce / Engelmann spruce | 15.5 / 15.0 | 2,240 / 2,070 | poor coals, many sparks |

The University of Idaho also recommends **Douglas-fir or western larch** when you want the most heat ({ref('uidaho-cis472-fuelwood')}).
A full cord is 128 cubic feet (4 x 4 x 8 ft); a face cord is only 32-48 cubic feet; a full-size pickup level with the bed holds about half a cord (USU).

## Burning it safely and efficiently (EPA Burn Wise)

From {ref('epa-best-wood-burning-practices')}:
- **Season wood at least six months**, stacked outdoors, off the ground, with **only the top covered**. It burns best below **20 percent moisture** - check with a moisture meter.
- Never start a fire with gasoline, kerosene or charcoal starter; never burn wet or green wood.
- Build hot fires - a smoldering fire is neither safe nor efficient. Keep stove doors closed except when loading.
- Put ashes in a **covered metal container outdoors** on a non-flammable surface; keep a fire extinguisher handy; keep curtains, furniture and paper away from the stove.
- Check your local air-quality forecast before you burn.

Choosing a stove: {ref('epa-choosing-wood-stove')}

## In your library
{bullets([lib('cooking-fire/firewood-2.md'), lib('cooking-fire/firewood-cookstoves.md'), lib('cooking-fire/cooking-with-firewood.md')])}
"""
    page("heating-with-wood-kalispell", "Heating with Wood in the Flathead - Permits, Local Firewood and Safe Burning", "Heating with wood",
         "Flathead National Forest firewood permits, the heat value of local woods (larch, lodgepole, Douglas-fir, birch...) and safe, efficient burning.",
         body)


def livestock():
    body = f"""## Bees - every apiary in Montana must be registered

The Montana Department of Agriculture registers **all apiary sites in the state** ({ref('mda-honeybees')}). There are four kinds of registration:
- **Hobbyist:** not more than **5 hives per individual or 10 per household**; no minimum distance between hobbyist apiaries.
- **Landowner:** registered to the owner of the land the hives are on; no buffer zone or hive limit.
- **General (commercial):** must be 3 miles from another beekeeper's general site.
- **Pollination:** temporary sites for crops in bloom.

Register with the {ref('mda-new-apiary-form', 'New Apiary and Landowner Registration Form')} (the landowner signs; GPS coordinates of the site are required). See also {ref('mda-montana-bee-guide-2007')} (2007 - check fees and limits against the department's current page).

**Bears love hives** - FWP lists beehives among the things an electric fence should protect (see **Living with Wildlife**).
In your library: {", ".join(x for x in [lib('food-production/beekeeping-basics-penn-state-maarec.md')] if x)}; Local Area also has every Montana bumble bee in **Insects & Spiders**.

## Backyard chickens and other poultry

- **Disease testing:** the Montana Department of Livestock runs the National Poultry Improvement Plan. Backyard flocks **enrolled in NPIP** test up to 300 birds 4 months or older for *Salmonella* Pullorum once every 1-3 years; flocks that choose avian-influenza certification have 30 birds swabbed every six months ({ref('mdol-npip-poultry')}).
- **Your family's health:** live poultry can carry *Salmonella* and *Campylobacter* - see the state health department's sheet ({ref('dphhs-backyard-poultry')}); wash hands after handling birds and keep poultry out of the house.
- **Predators:** FWP advises securing chickens with an electric fence in bear country, and the FWP fencing guide covers coops and poultry pens.

In your library: {", ".join(x for x in [lib('food-production/ndsu-beginners-guide-to-raising-chickens-as2045.md'), lib('food-production/raising-chickens-wikibooks.md')] if x)}

## Goats and small livestock

{ref('usu-goats')} - housing, fencing, feeding and health basics for small acreages (Utah State). FWP: store livestock feed in a secure building and protect goats and sheep with electric fencing in bear country.
In your library: {lib('food-production/electric-fence.md') or ''}
"""
    page("livestock-and-bees-kalispell", "Backyard Livestock and Bees in Montana - Rules, Health and Predators", "Livestock & bees",
         "Montana apiary registration, backyard poultry health and testing, goats, and protecting animals from bears.",
         body)


def main():
    food(); wildlife(); wood(); livestock()
    for s in ("20_catalog.py", "21_readme.py"):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), s)])


if __name__ == "__main__":
    main()
