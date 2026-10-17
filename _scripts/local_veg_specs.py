"""Home-garden vegetables for the Local Area section (user request 2026-10-12: crop pages + a Kalispell planting
calendar; varieties as lists; season extension included; the user has an UNHEATED greenhouse; home garden only).

VEG rows become '## Vegetables' plants in local_area_specs.PLANT_TABLE (kind 'vegetable'), built by 69_build_local_area.py.

Per crop (key = page slug):
  title, sci, wiki       page title, scientific name, Wikipedia article
  msu                    MSU Extension MontGuide MT199308AG 'Can I Grow That Here?' (read from the PDF's table):
                         dtm (days to maturity), spring / fall planting window, weeks to transplant size ('direct' =
                         direct seed), sun, frost tolerance, gh ('Greenhouse grown?'), soil (germination °F), notes,
                         cont (container varieties), ghv (greenhouse varieties)
                         Windows use L = average last spring frost, F = average first fall frost, offsets in weeks:
                         'L-1' = 1 week before last frost, 'F-12' = 12 weeks before first frost, 'L-6/L-4' = a range,
                         'mid' = mid-summer.
  nmsu                   NMSU Guide H-252 'Hoop House Vegetable Production' tables 1-2: (best growing temperature °F,
                         lethal minimum °F, days to maturity in a hoop house, special consideration)
  idaho                  table title in University of Idaho BUL 863 (veg_varieties.py) [+ ':' sub-type filter]
  pests                  local-area/insects page slugs
  season                 'cool' or 'warm'
"""

_BRASSICA = ["crucifer-flea-beetle", "cabbage-white", "cabbage-looper-moth", "diamondback-moth", "cabbage-aphid", "seedcorn-maggot"]
_CUCURBIT = ["spotted-cucumber-beetle", "twospotted-spider-mite", "green-peach-aphid"]
_SOLANUM = ["colorado-potato-beetle", "green-peach-aphid", "twospotted-spider-mite", "tarnished-plant-bug"]
_ALL = ["variegated-cutworm-moth", "army-cutworm-moth", "migratory-grasshopper", "two-striped-grasshopper", "european-earwig"]

_POLL = "Pollinating insects usually required."

VEG = {
    "snap-bean": dict(title="Snap Bean (Green Bean)", sci="Phaseolus vulgaris", wiki="Green bean", kw="bean", season="warm",
        msu=dict(dtm="52-70", spring="L-1/F-12", trans="direct", sun="Needs full sun", frost="None", gh="No", soil="60-85",
                 notes="Pole beans tend to mature later than most varieties of bush bean. Succession plant bush types once a week, up to the last planting date.",
                 cont="Bush Romano, Contender, Provider, Tendercrop Stringless"),
        nmsu=("60-70", "32", "48-60", ""), idaho="Garden Beans", pests=["seedcorn-maggot", "black-bean-aphid", "twospotted-spider-mite", "tarnished-plant-bug"]),
    "lima-bean": dict(title="Lima Bean", sci="Phaseolus lunatus", wiki="Lima bean", kw="lima", season="warm",
        msu=dict(dtm="Bush 75-80, Pole 85-90", spring="L-1/F-12", trans="direct", sun="Needs full sun", frost="None", gh="No", soil="65-85",
                 notes="Succession plant bush varieties every week or two, up to the last planting date.",
                 cont="Bush Baby, Fordhook Bush Lima, Fordhook 242, Henderson"),
        nmsu=None, idaho=None, pests=["seedcorn-maggot", "black-bean-aphid", "twospotted-spider-mite"]),
    "beet": dict(title="Beet", sci="Beta vulgaris", wiki="Beetroot", kw="beet", season="cool",
        msu=dict(dtm="50-80", spring="L-4/F-10..F-8", trans="direct", sun="Needs full sun", frost="Hardy", gh="No", soil="50-75",
                 notes="Succession plant every 2-3 weeks, up to the last planting date.", cont="Baby Canning, Spinel Baby Beets"),
        nmsu=("60-65", "15-20", "56-70", ""), idaho="Beets", pests=["beet-leafminer", "green-peach-aphid"]),
    "broccoli": dict(title="Broccoli", sci="Brassica oleracea (Italica group)", wiki="Broccoli", kw="broccoli", season="cool",
        msu=dict(dtm="60-80 after transplanting", spring="L-6/F-14", trans="6-8", sun="At least 5 hours daily", frost="Hardy", gh="No", soil="50-65",
                 notes="Succession planting: if summers are not too hot, plant more broccoli one month after the first planting, up to the last planting date.",
                 cont="Any will work; Crusader Hybrid is smaller and more compact"),
        nmsu=("60-65", "25", "55-78 from transplanting", ""), idaho="Broccoli", pests=_BRASSICA),
    "brussels-sprouts": dict(title="Brussels Sprouts", sci="Brassica oleracea (Gemmifera group)", wiki="Brussels sprout", kw="Brussels", season="cool",
        msu=dict(dtm="80-90 after transplanting", spring="L-6/L+3", trans="6-8", sun="At least 6 hours daily", frost="Hardy", gh="No", soil="65-75",
                 notes="Sprouts harvested after moderate freezes are much sweeter in taste."),
        nmsu=None, idaho="Brussels Sprouts", pests=_BRASSICA),
    "cabbage": dict(title="Cabbage", sci="Brassica oleracea (Capitata group)", wiki="Cabbage", kw="cabbage", season="cool",
        msu=dict(dtm="60-90 after transplanting", spring="L-6/F-13", trans="6-8", sun="At least 5 hours daily", frost="Hardy", gh="No", soil="50-75",
                 notes="Over-fertilization or cold weather in the five- to eight-leaf stage will cause poor or misshapen heading.",
                 cont="Baby Head, Dwarf Morden"),
        nmsu=("60-65", "10-15", "62-120", ""), idaho="Cabbage", pests=_BRASSICA),
    "carrot": dict(title="Carrot", sci="Daucus carota subsp. sativus", wiki="Carrot", kw="carrot", season="cool",
        msu=dict(dtm="60-80 after direct seeding", spring="L-4/F-13", trans="direct", sun="At least 5 hours daily", frost="Hardy", gh="No", soil="55-75",
                 notes="Succession plant every 2-3 weeks up to the last planting date.",
                 cont="short-rooted kinds such as Baby Finger Nantes, Gold Nugget, Oxheart, Short 'n' Sweet, Tiny Sweet"),
        nmsu=("60-65", "12", "50-95", "Temperatures below 50°F result in poor color; high temperatures decrease quality."), idaho="Carrots",
        pests=["green-peach-aphid"]),
    "cauliflower": dict(title="Cauliflower", sci="Brassica oleracea (Botrytis group)", wiki="Cauliflower", kw="cauliflower", season="cool",
        msu=dict(dtm="50-95 after transplanting", spring="L-3/F-14", trans="4-5", sun="At least 6 hours daily", frost="Hardy", gh="No", soil="50-75",
                 notes="Weather conditions influence the growth of cauliflower more than any other vegetable. Extreme heat or cold can cause serious crop reductions."),
        nmsu=("60-65", "25", "50-125", "The developing curd must be protected from light to prevent off color and flavor."), idaho="Cauliflower", pests=_BRASSICA),
    "celery": dict(title="Celery", sci="Apium graveolens", wiki="Celery", kw="celery", season="cool",
        msu=dict(dtm="125 after direct seeding", spring="L-3/F-19", trans="10", sun="At least 5 hours daily", frost="Hardy", gh="No", soil="50-70",
                 notes="Celery likes some shading in the heat of summer. Cold nights in early season will cause bolting."),
        nmsu=None, idaho=None, pests=["tarnished-plant-bug"]),
    "swiss-chard": dict(title="Swiss Chard", sci="Beta vulgaris (Cicla group)", wiki="Chard", kw="chard", season="cool",
        msu=dict(dtm="55-60 after direct seeding", spring="L-4/F-6", trans="direct", sun="At least 5 hours daily", frost="Hardy", gh="No", soil="40-70",
                 notes="", cont="any variety"),
        nmsu=("60-65", "10", "50-60", ""), idaho="Swiss chard", pests=["beet-leafminer"]),
    "chinese-cabbage-and-bok-choy": dict(title="Chinese Cabbage and Bok Choy", sci="Brassica rapa (Pekinensis & Chinensis groups)", wiki="Napa cabbage",
        kw="Chinese cabbage, bok choy", season="cool",
        msu=dict(dtm="45-60 after direct seeding, 40-50 after transplanting", spring="L-6/L0", fall="F-11", trans="4", sun="At least 6 hours daily",
                 frost="Hardy", gh="Yes", soil="50-75",
                 notes="Most varieties will bolt with the first hot days of summer, so they are best planted in summer for fall cropping. Some varieties dislike transplanting.",
                 cont="most varieties, especially Bok Choy, Michihli, Wong Bok", ghv="any variety can be grown in a cool greenhouse"),
        nmsu=None, idaho=None, pests=_BRASSICA),
    "collards": dict(title="Collards", sci="Brassica oleracea (Viridis group)", wiki="Collard (plant)", kw="collard", season="cool",
        msu=dict(dtm="60-80 after direct seeding", spring="L-4/L+2", fall="F-10/F-8", trans="direct", sun="Needs full sun", frost="Hardy", gh="No", soil="40-70",
                 notes="", cont="any variety"),
        nmsu=("60-65", "12", "70-85", ""), idaho="Collards and Kale", pests=_BRASSICA),
    "sweet-corn": dict(title="Sweet Corn", sci="Zea mays (sweet corn)", wiki="Sweet corn", kw="corn", season="warm",
        msu=dict(dtm="70-90+", spring="L0/L+3", trans="4", sun="Needs full sun", frost="None", gh="No", soil="55-85",
                 notes="Succession plant a second crop 3 weeks after the first.", cont="any space-saving variety"),
        nmsu=None, idaho="Sweet Corn", pests=["corn-earworm-moth", "seedcorn-maggot", "european-earwig"]),
    "cucumber": dict(title="Cucumber", sci="Cucumis sativus", wiki="Cucumber", kw="cucumber", season="warm",
        msu=dict(dtm="50-70", spring="L-1/F-12", trans="4", sun="At least 5 hours daily", frost="None", gh="Yes", soil="65-85",
                 notes="", cont="space-saving kinds such as Bush Crop, Patio Pic, Pot Luck, Space Master",
                 ghv="special greenhouse varieties including Burpless Early Pik, Crispy Salty, Pot Luck, Patio Pik, Tiny Dill Cuke"),
        nmsu=("65-75", "32", "48-72", _POLL), idaho="Cucumber", pests=_CUCURBIT),
    "eggplant": dict(title="Eggplant", sci="Solanum melongena", wiki="Eggplant", kw="eggplant", season="warm",
        msu=dict(dtm="100-120", spring="L-1/F-14", trans="6-10", sun="Needs full sun", frost="None", gh="No", soil="65-85",
                 notes="", cont="space-saving kinds such as Dusky, Baby Bell, Morden Midget"),
        nmsu=("70-85", "32", "50-80 from transplanting", ""), idaho=None, pests=_SOLANUM),
    "kale": dict(title="Kale", sci="Brassica oleracea (Acephala group)", wiki="Kale", kw="kale", season="cool",
        msu=dict(dtm="55-75 after direct seeding", spring="L-5/L+2", fall="F-8/F-6", trans="direct", sun="At least 5 hours daily", frost="Hardy", gh="No",
                 soil="40-70", notes="", cont="any variety"),
        nmsu=None, idaho="Collards and Kale", pests=_BRASSICA),
    "kohlrabi": dict(title="Kohlrabi", sci="Brassica oleracea (Gongylodes group)", wiki="Kohlrabi", kw="kohlrabi", season="cool",
        msu=dict(dtm="45-60 after direct seeding, 25-35 after transplanting", spring="L-5/L+2", fall="F-10", trans="6-8", sun="At least 5 hours daily",
                 frost="Hardy", gh="No", soil="50-75", notes="Kohlrabi does not grow well in containers or in the greenhouse."),
        nmsu=None, idaho="Kohlrabi", pests=_BRASSICA),
    "leek": dict(title="Leek", sci="Allium ampeloprasum (leek)", wiki="Leek", kw="leek", season="cool", msu=None, nmsu=None, idaho="Leeks",
        pests=["onion-maggot", "onion-thrips"]),
    "lettuce": dict(title="Lettuce", sci="Lactuca sativa", wiki="Lettuce", kw="lettuce", season="cool",
        msu=dict(dtm="40-60 after direct seeding, 25-35 after transplanting", spring="L-4/F-6", trans="4-6", sun="At least 5 hours daily", frost="Hardy",
                 gh="Yes", soil="45-75",
                 notes="Succession plant lettuce every 2 weeks up to the last planting date, shifting to warm-weather varieties for the summer months. Oak Leaf lettuce is heat resistant.",
                 cont="any variety grows well, with partial shade", ghv="loose-leaf varieties such as Arctic King, North Pole and Parris Cos perform best"),
        nmsu=("60-65", "15-25", "40-50", "High temperatures may cause bitterness and bolting."), idaho="Lettuce", pests=["green-peach-aphid", "tarnished-plant-bug"]),
    "muskmelon": dict(title="Muskmelon (Cantaloupe)", sci="Cucumis melo", wiki="Cantaloupe", kw="melon", season="warm",
        msu=dict(dtm="80-100 after transplanting", spring="L-1/F-16", trans="3-4", sun="Needs full sun", frost="None", gh="Yes", soil="65-85", notes="",
                 cont="Burpee's Sugar Bush, New Hampshire Midget, Yellow Baby Hybrid, Musketeer, Bush Star",
                 ghv="New Hampshire Granite and Minnesota Midget"),
        nmsu=("65-75", "32", "85-110", _POLL), idaho=None, pests=_CUCURBIT),
    "okra": dict(title="Okra", sci="Abelmoschus esculentus", wiki="Okra", kw="okra", season="warm",
        msu=dict(dtm="55-65 after direct seeding", spring="L-1/F-16", trans="6-8", sun="Needs full sun", frost="None", gh="No", soil="70-95",
                 notes="Okra does not grow well in containers or in the greenhouse. Okra responds well when grown with black plastic mulch."),
        nmsu=("70-85", "32", "50-60", ""), idaho=None, pests=["green-peach-aphid"]),
    "onion": dict(title="Onion", sci="Allium cepa", wiki="Onion", kw="onion", season="cool",
        msu=dict(dtm="40-70 from sets", spring="L-3/L+2", trans="4-8", sun="At least 5 hours daily", frost="Hardy", gh="Yes", soil="50-80",
                 notes="For fall scallions, plant a second crop 8 weeks after the spring planting. Keep seedling tops trimmed to 1/2 inch until a week before planting outdoors.",
                 cont="any variety, but bunching onions are more productive in small spaces - try Beltsville Bunching and White Pearl",
                 ghv="try any variety"),
        nmsu=None, idaho="Onions", pests=["onion-maggot", "onion-thrips"]),
    "parsnip": dict(title="Parsnip", sci="Pastinaca sativa", wiki="Parsnip", kw="parsnip", season="cool",
        msu=dict(dtm="100-120 after direct seeding", spring="L-4..L-2/L+4", trans="direct", sun="At least 5 hours daily", frost="Hardy", gh="No", soil="50-70",
                 notes="Parsnips do not grow well in the greenhouse or in containers."),
        nmsu=None, idaho=None, pests=[]),
    "peas": dict(title="Peas", sci="Pisum sativum", wiki="Pea", kw="pea", season="cool",
        msu=dict(dtm="55-90 after direct seeding", spring="L-6..L-4/L+2..L+3", fall="F-12", trans="direct", sun="Needs full sun", frost="Very hardy",
                 gh="No", soil="40-70",
                 notes="Dwarf peas still require a low trellis to keep air circulating through the vines. Keep plants picked to encourage production, and keep soil moist once flowers appear.",
                 cont="space-saving kinds such as Laxton's Progress, Little Marvel, SugarBon, SugarMel, Sugar Rae"),
        nmsu=None, idaho="Garden Peas", pests=["pea-leaf-weevil", "green-peach-aphid"]),
    "peppers": dict(title="Peppers (Sweet and Hot)", sci="Capsicum annuum", wiki="Bell pepper", kw="pepper", season="warm",
        msu=dict(dtm="50-75 after transplanting", spring="L-1/F-17", trans="6-8", sun="At least 6 hours daily", frost="None", gh="No", soil="65-85", notes="",
                 cont="space-saving kinds such as Canape, Gypsy Hybrid, Italian Sweet, Pepper Pot, or any hot pepper variety"),
        nmsu=("70-75 (bell), 70-85 (chile)", "32", "65-80 from transplanting", ""), idaho="Peppers", pests=_SOLANUM),
    "potato": dict(title="Potato", sci="Solanum tuberosum", wiki="Potato", kw="potato", season="cool",
        msu=dict(dtm="80-140", spring="L-1/F-17", trans="direct plant (seed pieces)", sun="Needs full sun", frost="Vegetation tender, potato tubers hardy",
                 gh="No", soil="60-65", notes="Potatoes cannot be grown in the greenhouse or in containers."),
        nmsu=None, idaho="Potatoes", pests=["colorado-potato-beetle", "green-peach-aphid", "analagous-click-beetle"]),
    "pumpkin": dict(title="Pumpkin", sci="Cucurbita pepo (pumpkin)", wiki="Pumpkin", kw="pumpkin", season="warm",
        msu=dict(dtm="100-120 after transplanting", spring="L0/F-15", trans="4", sun="Needs full sun",
                 frost="Foliage tender, pumpkins take a light frost or two", gh="No", soil="65-85",
                 notes="Harvest before a heavy freeze. Pumpkins cannot be grown in the greenhouse or in containers."),
        nmsu=("65-75", "32", "85-120", _POLL), idaho="Pumpkins", pests=_CUCURBIT),
    "radish": dict(title="Radish", sci="Raphanus sativus", wiki="Radish", kw="radish", season="cool",
        msu=dict(dtm="20-49 after direct seeding", spring="L-6", fall="F-7", trans="direct", sun="At least 6 hours daily", frost="Hardy", gh="Yes",
                 soil="40-85",
                 notes="Succession plant radishes every 10 days until warm weather arrives (day temperatures of 70). For fall successions, plant every 10 days, up to the last fall planting date.",
                 cont="Cherry Belle, Early Scarlet Globe, French Breakfast, Sparkler - round red and white-tipped kinds do best; stay away from large winter radishes",
                 ghv="French Breakfast and Sparkler"),
        nmsu=None, idaho="Radish", pests=["crucifer-flea-beetle", "seedcorn-maggot"]),
    "rutabaga": dict(title="Rutabaga", sci="Brassica napus (Napobrassica group)", wiki="Rutabaga", kw="rutabaga", season="cool",
        msu=dict(dtm="90-100 after direct seeding", spring="L-6/F-16", trans="direct", sun="At least 6 hours daily", frost="Hardy", gh="No", soil="65-75",
                 notes="Rutabagas cannot be grown in the greenhouse or in containers."),
        nmsu=None, idaho="Rutabaga", pests=_BRASSICA),
    "spinach": dict(title="Spinach", sci="Spinacia oleracea", wiki="Spinach", kw="spinach", season="cool",
        msu=dict(dtm="40-60 after direct seeding", spring="L-6/mid-7", fall="F-8/F-6", trans="direct", sun="At least 5 hours daily", frost="Hardy", gh="No",
                 soil="40-75", notes="A good hot-weather substitute is New Zealand spinach.", cont="any variety"),
        nmsu=("60-65", "0-5", "37-45", ""), idaho="Spinach", pests=["beet-leafminer", "green-peach-aphid"]),
    "summer-squash-and-zucchini": dict(title="Summer Squash and Zucchini", sci="Cucurbita pepo (summer squash)", wiki="Zucchini", kw="squash, zucchini",
        season="warm",
        msu=dict(dtm="45-60 after transplanting", spring="L0/F-10", trans="4", sun="Needs full sun", frost="None", gh="No", soil="65-85", notes="",
                 cont="Early Yellow Summer Crookneck, Goldbar Straightneck, Park's Creamy, Scallopine"),
        nmsu=("65-75", "32", "40-50", _POLL), idaho="Squash:Summer", pests=_CUCURBIT),
    "winter-squash": dict(title="Winter Squash", sci="Cucurbita maxima / moschata / pepo", wiki="Winter squash", kw="squash", season="warm",
        msu=dict(dtm="85-100 after direct seeding, 60-80 after transplanting", spring="L-1/F-13", trans="3-4", sun="Needs full sun", frost="None", gh="No",
                 soil="65-85", notes="", cont="space-saving bush kinds such as Butterbush"),
        nmsu=("65-75", "32", "85-120", _POLL), idaho="Squash:Winter", pests=_CUCURBIT),
    "tomato": dict(title="Tomato", sci="Solanum lycopersicum", wiki="Tomato", kw="tomato", season="warm",
        msu=dict(dtm="70 after transplanting", spring="L-1/F-17", trans="6-10", sun="Needs at least 8 hours or more full sun daily", frost="None", gh="Yes",
                 soil="65-85", notes="",
                 cont="Patio VF, Pixie, Small Fry VFN, Sweet 100, Toy Boy, Tumblin' Tom, Yellow Pear, and others designed for containers",
                 ghv="Patio, Small Fry and Tiny Tim"),
        nmsu=("70-75", "32", "60-90 from transplanting", "Vibrating or shaking plants will enhance pollination and aid in fruit set."), idaho="Tomatoes",
        pests=_SOLANUM),
    "turnip": dict(title="Turnip", sci="Brassica rapa (Rapifera group)", wiki="Turnip", kw="turnip", season="cool",
        msu=dict(dtm="Greens 30-75, roots 60-75 after direct seeding", spring="L-6/mid", fall="F-8/F-6", trans="direct", sun="At least 5 hours daily",
                 frost="Hardy", gh="No", soil="60-75", notes="Succession plant every 3 weeks till midsummer.", cont="any variety"),
        nmsu=None, idaho="Turnip", pests=_BRASSICA),
    "watermelon": dict(title="Watermelon", sci="Citrullus lanatus", wiki="Watermelon", kw="watermelon", season="warm",
        msu=dict(dtm="30-100 warm days after transplanting", spring="L-1/F-16", trans="3-4", sun="Needs full sun", frost="None", gh="No", soil="65-75",
                 notes="", cont="special varieties such as Sugar Baby"),
        nmsu=("70-85", "32", "75-95", _POLL), idaho=None, pests=_CUCURBIT),
    "asparagus": dict(title="Asparagus", sci="Asparagus officinalis (garden)", wiki="Asparagus", kw="asparagus", season="cool", msu=None, nmsu=None,
        idaho="Asparagus", pests=[]),
    "sweet-potato": dict(title="Sweet Potato", sci="Ipomoea batatas", wiki="Sweet potato", kw="sweet potato", season="warm", msu=None, nmsu=None,
        idaho=None, pests=[]),
    "tomatillo": dict(title="Tomatillo", sci="Physalis philadelphica", wiki="Tomatillo", kw="tomatillo", season="warm", msu=None, nmsu=None,
        idaho=None, pests=_SOLANUM),
    "ground-cherry": dict(title="Ground Cherry", sci="Physalis pruinosa", wiki="Physalis pruinosa", kw="ground cherr", season="warm", msu=None,
        nmsu=None, idaho=None, pests=_SOLANUM),
    "shallot": dict(title="Shallot", sci="Allium cepa (Aggregatum group)", wiki="Shallot", kw="shallot", season="cool", msu=None, nmsu=None,
        idaho=None, pests=["onion-maggot", "onion-thrips"]),
    "scallions": dict(title="Scallions (Green Onions)", sci="Allium fistulosum", wiki="Scallion", kw="scallion, green onion, bunching onion",
        season="cool", msu=None, nmsu=None, idaho=None, pests=["onion-maggot", "onion-thrips"]),
    "arugula": dict(title="Arugula", sci="Eruca vesicaria", wiki="Eruca vesicaria", kw="arugula, rocket", season="cool", msu=None, nmsu=None,
        idaho=None, pests=["crucifer-flea-beetle", "cabbage-aphid"]),
    "endive": dict(title="Endive and Escarole", sci="Cichorium endivia", wiki="Endive", kw="endive, escarole", season="cool", msu=None,
        nmsu=None, idaho=None, pests=["green-peach-aphid", "tarnished-plant-bug"]),
}

# MSU MontGuide MT199217AG 'Growing Tomatoes in Montana' (rev. 2019): "A Partial List of Recommended Tomato Cultivars for
# Montana" - D determinate (no staking), I indeterminate (needs support), H heirloom
MSU_LISTS = {
    "tomato": ("Growing Tomatoes in Montana (MSU MontGuide MT199217AG) - \"select very early to early mid-season cultivars that ripen "
               "their fruit in 60 to 70 days for a sure crop\". D = determinate (no staking), I = indeterminate (needs support), H = heirloom",
               "msu-growing-tomatoes-in-montana.md", [
        ("Very early to early salad types", "Bloody Butcher (I/H), Early Girl Hybrid (D), Early Pick Hybrid (D), Fourth of July (I), Gem State (D), "
         "Northern Exposure (D), Oregon Spring (D), Prairie Fire (D), Siberian (D/H), Stupice (I/H), Sub Arctic Plenty (D)"),
        ("Early to mid-season salad types", "Black Sea Man (D/H), Celebrity (D), Coldset (D), Fantastic (D), New Yorker (D), "
         "Patio Princess Hybrid (D), Springset (D), SteakHouse (I), Whopper Improved (I)"),
        ("Very early small-fruited", "Early Sub Arctic Plenty (D), Gold Nugget (D), Juliet Hybrid (I), Orange Pixie Hybrid (D), Sugary (I), Tumbler Hybrid (D)"),
        ("Early to mid-season small-fruited", "Sungold (I), Super Sweet 100 (I), Sweet Baby Girl (I), Yellow Pear (I/H)"),
    ]),
}

# crops MSU's planting table does not cover: key facts and variety lists taken from the named documents
# (facts: (label, text) - '{last}' / '{first}' / '{last+N}' / '{last-N}' (days) are filled with Kalispell dates)
EXTRA = {
    "sweet-potato": dict(
        facts=[("Will it ripen in Kalispell?", "Only with help - the roots need 4 to 5 months (Utah State); our frost-free season is about {season} "
                "days. Grow the earliest varieties (Centennial, Georgia Jet: 90-100 days) in the greenhouse or on black plastic under row covers."),
               ("Cold damage", "Plants can be damaged by temperatures below 50°F (Utah State) - they need warm nights."),
               ("How to plant", "From slips (sprouts grown from a root); plant after the danger of frost is over (Utah State) - here about "
                "{last+14} or later (Wyoming advises 10-14 days after the last frost for sweet potatoes). Space slips 12 inches apart, rows 36-48 inches."),
               ("Head start", "Plant through black plastic mulch, up to ten days earlier than in uncovered soil; use floating row covers for "
                "frost protection (Utah State)."),
               ("Harvest", "When roots are 1 1/2-2 inches thick; most gardeners dig when the foliage yellows or after the first frost damages "
                "the leaves, but before the soil freezes (Utah State). Expect 1-2 lb of roots per plant.")],
        vars=("Utah State University Extension ([Sweet Potatoes in the Garden](../references/usu-sweet-potatoes.md)) - the shortest are best here",
              [("Centennial", "90-100", "Orange flesh, orange skin; clay tolerant"), ("Georgia Jet", "90-100", "Orange flesh, red or purple skin"),
               ("Beauregard", "105-110", "Dark orange flesh, light purple skin"), ("Bush Porto Rico", "110", "Orange flesh, copper skin"),
               ("Vardaman Bush", "110", "Orange flesh, gold skin"), ("Sumor", "110-120", "Light yellow flesh, tan skin"),
               ("Carolina Bunch", "110-120", "Deep orange flesh, copper skin"), ("Jewel", "120-135", "Orange flesh, copper skin")])),
    "tomatillo": dict(
        facts=[("Start indoors", "4-5 weeks before setting out - a week or two later than tomatoes (University of Minnesota): about "
                "{last-35} to {last-28} for planting out after the last frost."),
               ("Plant outdoors", "After all danger of frost has passed and the soil has warmed (University of Minnesota) - about {last} or "
                "later; bring transplants in if nights are below 55°F while hardening off."),
               ("Space", "As much as 3 feet - plants are bushy and bigger than tomatoes; trellis, cage or support them (University of Minnesota)."),
               ("Pollination", "Grow more than one plant for best fruit set - cross-pollination between two varieties is ideal (University of Minnesota)."),
               ("Harvest", "When the fruit fills the husk but is still green and firm (University of Minnesota).")],
        vars=("University of Minnesota Extension ([Growing Tomatillos and Ground Cherries](../references/umn-tomatillos-ground-cherries.md)) - "
              "there are few varieties and none bred for northern gardens",
              [("Purple", "", "1 1/2-inch fruit, sweeter flavor"), ("Green (Verde)", "", "2-inch fruit"), ("De Milpa", "", "1-inch fruit, tangier flavor"),
               ("Tamayo", "", "3-inch fruit")])),
    "ground-cherry": dict(
        facts=[("Start indoors", "6-7 weeks before planting outdoors - about two weeks before tomato seed (University of Minnesota): about "
                "{last-49} to {last-42} here."),
               ("Plant outdoors", "After all danger of frost has passed and the soil has warmed (University of Minnesota) - about {last} or later."),
               ("Space", "18-24 inches in all directions; plants stay under 30 inches and may sprawl (University of Minnesota)."),
               ("Harvest", "When the husks are dry and the fruit begins to drop from the plant (University of Minnesota)."),
               ("Drought and heat", "Tomatillo and ground cherry plants can stand drought and heat (University of Minnesota).")],
        vars=("University of Minnesota Extension ([Growing Tomatillos and Ground Cherries](../references/umn-tomatillos-ground-cherries.md)) - "
              "all good in Minnesota gardens",
              [("Goldie", "", "sweet and tangy"), ("Pineapple", "", "sweet and tangy"), ("Aunt Molly's", "", "sweet and tangy")])),
    "asparagus": dict(
        facts=[("Will it grow in Kalispell?", "Yes - a perennial; most cultivars are hardy to USDA zone 3, some to zone 2 (MSU MT198365AG). "
                "Kalispell is zone 5b."),
               ("Plant", "In spring, when the soil has reached at least 50°F, from 1- or 2-year-old dormant crowns, in a trench 10 inches deep "
                "with crowns 18 inches apart and 2 1/2-3 feet between rows (MSU)."),
               ("Harvest", "None the first season, lightly the second; the first full harvest is in the third season (MSU). Beds peak at about "
                "eight years and stay productive 12-15 years or more."),
               ("Site", "Moist soil and full sun; tolerates more soil salt than most garden plants (MSU)."),
               ("Pests", "Asparagus beetle and cutworms; asparagus rust occurs in Montana - plant resistant 'Mary Washington' or the 'Jersey' "
                "series (MSU).")]),
    "leek": dict(
        facts=[("Will it ripen in Kalispell?", "Yes - leeks do not need to reach full size to be eaten; harvest once the underground stem is "
                "1/2 inch thick (University of Idaho BUL 863)."),
               ("Plant outdoors", "Transplant about two weeks before the average last spring frost (Idaho) - about {last-14} here."),
               ("Frost", "Very tolerant of frost in spring, but hard frost in fall can damage them - harvest before the cold weather sets in (Idaho)."),
               ("Blanching", "For long, white stems keep a large part of the stem underground while it grows (Idaho).")]),
    "shallot": dict(
        facts=[("Will it ripen in Kalispell?", "Yes - a cool-season crop planted in early spring (Utah State); green tops can be cut about "
                "50-60 days after planting, dry bulbs when the tops fall over."),
               ("Plant outdoors", "Bulb sets or seed in early spring as soon as the ground can be worked (Utah State) - here usually April, "
                "well before the last frost (about {last}). Bulbs 1-2 inches deep and 3-6 inches apart in rows 12-18 inches apart; "
                "wide spacing gives clusters of 10-15 bulbs."),
               ("Feeding", "Nitrogen 30 and 60 days after planting; do not fertilize after mid-July - it reduces how well the bulbs store (Utah State)."),
               ("Water", "Keep evenly moist; drought cuts yield and overwatering rots the bulbs (Utah State)."),
               ("Overwintering", "Mulch helps overwintered shallots (Utah State) - a fall planting under mulch is worth trying here.")],
        vars=("Utah State University Extension ([Shallots in the Garden](../references/usu-shallots.md))",
              [("French Red", "", "the most common variety sold"), ("Gray Griselle", "", "best flavor"),
               ("Dutch Yellow", "", "stronger, more onion-like flavor")])),
    "scallions": dict(
        facts=[("Will it ripen in Kalispell?", "Yes - pull scallions whenever they reach usable size (University of Minnesota); bunching "
                "onions do not form bulbs."),
               ("Plant outdoors", "Direct seed as soon as the soil is workable (University of Minnesota) - usually April here. Sow in a "
                "2-inch band, 1/4-1/2 inch deep, rows 12-18 inches apart; thin to one plant per inch."),
               ("Start indoors", "Four weeks before planting out (University of Minnesota): about {last-42} for transplants set out around {last-14}."),
               ("Fall crop", "For fall scallions, plant a second crop 8 weeks after the spring planting (MSU MT199308AG)."),
               ("Perennial option", "Egyptian walking onions: plant topset bulbs in late summer 1-2 inches deep, 6 inches apart, cover "
                "lightly with straw for winter; cut greens from the second season (University of Minnesota).")],
        vars=("MSU ([Can I Grow That Here?](../references/msu-can-i-grow-that-here-vegetable-seed-and-transplant-schedules-for-garde.md)) - "
              "bunching onions are the most productive in small spaces",
              [("Beltsville Bunching", "", "bunching onion (MSU)"), ("White Pearl", "", "bunching onion (MSU)"),
               ("Egyptian walking onion", "", "perennial, from topsets (University of Minnesota)")])),
    "arugula": dict(
        facts=[("Will it ripen in Kalispell?", "Yes - often ready as early as 4 weeks after seeding (Cornell)."),
               ("Plant outdoors", "Seeds germinate quickly even in cold soil - plant as soon as the soil can be worked in spring (Cornell), "
                "usually April here."),
               ("Keep it coming", "New plantings every 2-3 weeks until about a month before the average first frost (Cornell) - "
                "last sowing about {first-30} here."),
               ("Bolting", "Slow bolting by reducing heat and moisture stress; give summer plantings some shade (Cornell). Long days and heat "
                "make it bolt, so spring and late-summer sowings do best."),
               ("Rotation", "Do not plant where cabbage-family crops grew (Cornell) - it shares their pests, especially flea beetles.")],
        vars=("Cornell University ([Arugula Growing Guide](../references/cornell-arugula.md))",
              [("Common arugula (Eruca vesicaria)", "about 28 (4 weeks)", "fast-growing, peppery"),
               ("Sylvetta (wild arugula, Diplotaxis tenuifolia)", "", "slower growing, half as tall and slower to bolt; smaller lobed leaves, more pungent")])),
    "endive": dict(
        facts=[("Will it ripen in Kalispell?", "Yes - a cool-season green that does best with mild days and cool nights (McGill)."),
               ("Start indoors", "Start spring seeds indoors and set out month-old seedlings 3-4 weeks before the last frost, under row covers "
                "(McGill): sow about {last-56}, plant out about {last-28} to {last-21}."),
               ("Plant outdoors", "Wyoming Extension lists endive among crops not hurt by light frost - plant 2-4 weeks before the last frost."),
               ("Fall crop", "Direct seed in late summer, at least three weeks after the summer solstice (after about July 12) (McGill); thin to "
                "8-12 inches, closer for blanching."),
               ("Temperatures", "Seeds germinate best at 70-75°F soil; best growth at 60-65°F days (McGill)."),
               ("Flavor", "Keep it evenly watered and mulched - drought makes it bitter; tie the heads to blanch them (McGill).")],
        vars=("McGill University ([Endive - Ecological Agriculture Projects](../references/mcgill-endive.md)) - two types",
              [("Curly endive (frisée)", "", "finely cut, curly leaves"), ("Escarole (broad-leaved)", "", "broad, lettuce-like leaves")])),
}

# crops Wyoming Extension (B-1148R) says should go in 10-14 days AFTER the last frost - they will not grow in cool soil
WYO_LATE = {"cucumber", "eggplant", "snap-bean", "lima-bean", "muskmelon", "peppers", "pumpkin", "sweet-potato", "watermelon"}

# old general pages (moved from the Field Guides) that these crop pages replace -> removed when the pages are built
REPLACES = ["bean", "beetroot", "carrot", "chili-pepper", "cucumber", "cucurbita", "kale", "onion", "pea", "spinach", "turnip",
            "buckwheat", "chickpea"]


def table_rows():
    """'## Vegetables' rows for local_area_specs.PLANT_TABLE."""
    out = ["## Vegetables"]
    for slug, v in VEG.items():
        out.append(f"{v['title']} | {v['sci']} | vegetable | wiki={v['wiki']}; kw={v['kw']}; veg={slug}")
    return "\n".join(out)
