"""What goes into the Local Area (Montana - Kalispell / Flathead County) section. 69_build_local_area.py reads this.

PLANT_TABLE: one profile page per line:
    title | scientific name | kind | extra keys (k=v; ...)
  kind: cultivar | native | introduced | noxious | poisonous
  extra keys (all optional):
    stark=<Stark Bro's product path after /products/>     op=<Orange Pippin path after /varieties/>
    wiki=<Wikipedia title (offline ZIM)>                  commons=<Wikimedia Commons category>
    kw=<extra search words, comma separated>              note=<one line shown at the top>
  Group = the '## ' heading above the lines (it is also the "type" button in Library Manager's Local Area page).
  Montana Field Guide code, iNaturalist photos, Stark growing guide, MSU documents and MSU pest pages are found
  automatically (GENUS_GUIDE / GROUP_GUIDE / MSU_PUBS / REFS below; 'for' = group names, genus/species prefixes or '*').
"""

REGION = {"town": "Kalispell", "county": "Flathead County", "zip": "59901", "zone": "5b",
          "zone_range": "-15 to -10 F", "zone_source": "USDA Plant Hardiness Zone Map 2023 (phzmapi.org lookup for 59901)"}

PLANT_TABLE = """
## Fruit trees - Apples
Honeycrisp Apple | Malus domestica 'Honeycrisp' | cultivar | stark=fruit-trees/apple-trees/honeycrisp-apple; op=apples/honeycrisp; wiki=Honeycrisp; commons=Honeycrisp
McIntosh Apple | Malus domestica 'McIntosh' | cultivar | stark=fruit-trees/apple-trees/mcintosh-apple; op=apples/mcintosh; wiki=McIntosh (apple); commons=McIntosh (apple)
Cortland Apple | Malus domestica 'Cortland' | cultivar | stark=fruit-trees/apple-trees/cortland-apple; op=apples/cortland; wiki=Cortland (apple); commons=Cortland (apple); kw=Cortland
Sweet Sixteen Apple | Malus domestica 'Sweet Sixteen' | cultivar | stark=fruit-trees/apple-trees/sweet-sixteen-apple; op=apples/sweet-sixteen; kw=Sweet 16
Wealthy Apple | Malus domestica 'Wealthy' | cultivar | stark=fruit-trees/apple-trees/wealthy-apple; op=apples/wealthy; wiki=Wealthy (apple); commons=Wealthy (apple)
Gala Apple | Malus domestica 'Gala' | cultivar | stark=fruit-trees/apple-trees/gala-apple; op=apples/gala; wiki=Gala (apple); commons=Gala (apple); note=MSU rates Gala for zones 5-8 - Kalispell is zone 5b, so it is at the cold edge: plant in a sheltered spot.
Zestar! Apple | Malus domestica 'Zestar' | cultivar | stark=fruit-trees/apple-trees/zestar-apple; op=apples/zestar; wiki=Zestar; kw=Zestar
Haralson Apple | Malus domestica 'Haralson' | cultivar | op=apples/haralson; wiki=Haralson (apple)
Honeygold Apple | Malus domestica 'Honeygold' | cultivar | stark=fruit-trees/apple-trees/honeygold-apple; op=apples/honeygold
State Fair Apple | Malus domestica 'State Fair' | cultivar | stark=fruit-trees/apple-trees/state-fair-apple; op=apples/state-fair
Goodland Apple | Malus domestica 'Goodland' | cultivar | op=apples/goodland
Wolf River Apple | Malus domestica 'Wolf River' | cultivar | stark=fruit-trees/apple-trees/wolf-river-apple; op=apples/wolf-river; wiki=Wolf River (apple)
Yellow Transparent Apple | Malus domestica 'Yellow Transparent' | cultivar | stark=fruit-trees/apple-trees/yellow-transparent-apple; op=apples/yellow-transparent; wiki=Yellow Transparent
Duchess of Oldenburg Apple | Malus domestica 'Duchess of Oldenburg' | cultivar | op=apples/duchess-of-oldenburg; wiki=Duchess of Oldenburg; kw=Duchess
Northern Spy Apple | Malus domestica 'Northern Spy' | cultivar | stark=fruit-trees/apple-trees/northern-spy-apple; op=apples/northern-spy; wiki=Northern Spy
Dolgo Crabapple | Malus 'Dolgo' | cultivar | op=apples/dolgo; kw=Dolgo; note=Crabapples bloom over a long period and are excellent pollinizers for other apples.
Chestnut Crabapple | Malus 'Chestnut' | cultivar | op=apples/chestnut-crab; kw=Chestnut crab
Ranetka Crabapple | Malus 'Ranetka' | cultivar | kw=Ranetka; note=Ranetka is a very hardy Siberian-type crabapple (Malus baccata / prunifolia background) - small fruit for jelly and juice, and a good pollinizer for other apples.
Selkirk Crabapple | Malus 'Selkirk' | cultivar | kw=Selkirk; note=Selkirk is a hardy Canadian (Morden) flowering crabapple with rose-red blossoms and small red fruit; a good pollinizer for other apples.

## Fruit trees - Pears
Pears (growing pears in Montana) | Pyrus communis | introduced | wiki=Pyrus communis; kw=pear; note=General page for pears - see the variety pages for Parker, Patten, Summercrisp, Ure and Golden Spice.
Parker Pear | Pyrus 'Parker' | cultivar | op=pears/parker; kw=Parker
Patten Pear | Pyrus 'Patten' | cultivar | op=pears/patten; kw=Patten
Summercrisp Pear | Pyrus 'Summercrisp' | cultivar | op=pears/summercrisp; kw=Summercrisp
Ure Pear | Pyrus ussuriensis 'Ure' | cultivar | op=pears/ure; kw=Ure
Golden Spice Pear | Pyrus 'Golden Spice' | cultivar | op=pears/golden-spice; kw=Golden Spice
Bartlett Pear | Pyrus communis 'Bartlett' | cultivar | stark=fruit-trees/pear-trees/bartlett-pear; op=pears/bartlett-williams; wiki=Williams pear; commons=Williams pear; kw=Bartlett
D'Anjou Pear | Pyrus communis 'Anjou' | cultivar | op=pears/beurre-d-anjou; wiki=D'Anjou; kw=Anjou

## Fruit trees - Plums & apricots
Italian Plum (Italian Prune) | Prunus domestica 'Italian' | cultivar | op=plums/italian-prune; wiki=Prunus domestica; kw=Italian
Mount Royal Plum | Prunus domestica 'Mount Royal' | cultivar | op=plums/mount-royal; kw=Mount Royal
Toka Plum | Prunus 'Toka' | cultivar | op=plums/toka; kw=Toka
Pembina Plum | Prunus 'Pembina' | cultivar | op=plums/pembina; kw=Pembina
Superior Plum | Prunus 'Superior' | cultivar | op=plums/superior; kw=Superior
Waneta Plum | Prunus 'Waneta' | cultivar | op=plums/waneta; kw=Waneta
American Plum (wild plum) | Prunus americana | native | wiki=Prunus americana
Westcot Apricot | Prunus armeniaca 'Westcot' | cultivar | kw=Westcot
Manchurian Apricot | Prunus mandshurica | introduced | wiki=Prunus mandshurica

## Fruit trees - Cherries
Lapins Cherry | Prunus avium 'Lapins' | cultivar | stark=fruit-trees/cherry-trees/lapins-sweet-cherry; op=cherries/lapins; kw=Lapins
Rainier Cherry | Prunus avium 'Rainier' | cultivar | op=cherries/rainier; wiki=Rainier cherry; kw=Rainier
Lambert Cherry | Prunus avium 'Lambert' | cultivar | op=cherries/lambert; kw=Lambert
Stella Cherry | Prunus avium 'Stella' | cultivar | op=cherries/stella; wiki=Stella (cherry); kw=Stella
Evans Cherry (Bali) | Prunus cerasus 'Evans' | cultivar | op=cherries/evans; kw=Evans, Bali
Carmine Jewel Cherry | Prunus x kerrasis 'Carmine Jewel' | cultivar | kw=Carmine Jewel
Romeo Cherry | Prunus x kerrasis 'Romeo' | cultivar | kw=Romeo
Juliet Cherry | Prunus x kerrasis 'Juliet' | cultivar | kw=Juliet
Crimson Passion Cherry | Prunus x kerrasis 'Crimson Passion' | cultivar | kw=Crimson Passion
Meteor Cherry | Prunus cerasus 'Meteor' | cultivar | stark=fruit-trees/cherry-trees/meteor-sour-cherry; op=cherries/meteor; kw=Meteor
Pie Cherry (Sour Cherry, Montmorency) | Prunus cerasus 'Montmorency' | cultivar | op=cherries/montmorency; wiki=Montmorency cherry; commons=Montmorency (cherry); kw=pie cherr, sour cherr, tart cherr, Montmorency; note=Pie (sour/tart) cherry - Montmorency is the classic variety; if yours is a different pie cherry the growing advice is the same.
North Star Cherry | Prunus cerasus 'North Star' | cultivar | op=cherries/north-star; kw=North Star
Nanking Cherry | Prunus tomentosa | introduced | wiki=Prunus tomentosa
Common Chokecherry | Prunus virginiana | native | wiki=Prunus virginiana
Canada Red Chokecherry (Schubert) | Prunus virginiana 'Canada Red' | cultivar | kw=Canada Red, Schubert

## Berries & small fruit
American Elderberry (native American elderberry) | Sambucus canadensis | native | wiki=Sambucus canadensis; kw=elderberr
Adams Elderberry | Sambucus canadensis 'Adams' | cultivar | stark=berry-plants/elderberry-plants/adams-elderberry; kw=Adams
Bob Gordon Elderberry | Sambucus canadensis 'Bob Gordon' | cultivar | stark=berry-plants/elderberry-plants/bob-gordon-elderberry; kw=Bob Gordon
Blue Elderberry | Sambucus cerulea | native | wiki=Sambucus cerulea; kw=blue elder
Red Elderberry | Sambucus racemosa | native | wiki=Sambucus racemosa; note=Raw red elderberries, seeds, leaves and stems are toxic - see Edibility.
Gooseberries | Ribes uva-crispa | introduced | stark=berry-plants/gooseberry-plants/invicta-gooseberry; wiki=Ribes uva-crispa; kw=gooseberr
Red Currant (Red Lake) | Ribes rubrum | introduced | stark=berry-plants/currant-plants/red-lake-currant; wiki=Redcurrant; kw=currant
Black Currant | Ribes nigrum | introduced | wiki=Blackcurrant; kw=currant
Golden Currant | Ribes aureum | native | wiki=Ribes aureum
Haskap (Honeyberry) | Lonicera caerulea | introduced | stark=berry-plants/honeyberry-plants/aurora-honeyberry; wiki=Lonicera caerulea; kw=haskap, honeyberr
Saskatoon Serviceberry | Amelanchier alnifolia | native | wiki=Amelanchier alnifolia; kw=serviceberr, saskatoon
Aronia (Black Chokeberry) | Aronia melanocarpa | introduced | stark=berry-plants/aronia-berry-plants/viking-aronia-berry; wiki=Aronia melanocarpa; kw=aronia
Sea Buckthorn | Hippophae rhamnoides | introduced | wiki=Hippophae rhamnoides
Silver Buffaloberry | Shepherdia argentea | native | wiki=Shepherdia argentea; kw=buffaloberr
Russet Buffaloberry (Soapberry) | Shepherdia canadensis | native | wiki=Shepherdia canadensis; kw=buffaloberr, soapberr
Raspberries (growing raspberries in Kalispell) | Rubus idaeus | introduced | stark=berry-plants/raspberry-plants/nova-red-raspberry; wiki=Rubus idaeus; kw=raspberr
Boyne Raspberry | Rubus idaeus 'Boyne' | cultivar | kw=Boyne
Killarney Raspberry | Rubus idaeus 'Killarney' | cultivar | kw=Killarney
Strawberries (Fort Laramie, everbearing) | Fragaria x ananassa | introduced | stark=berry-plants/strawberry-plants/honeoye-strawberry; wiki=Garden strawberry; kw=strawberr, Fort Laramie
Wild Strawberry | Fragaria virginiana | native | wiki=Fragaria virginiana
Blackberries (growing blackberries in Kalispell) | Rubus (blackberries) | introduced | wiki=Blackberry; kw=blackberr; note=Choose cold-hardy types: primocane (fall-bearing) blackberries fruit on new canes the same year, so they still crop when winter kills the canes back - the usual choice for cold areas (general horticultural guidance).
Prime-Ark Freedom Blackberry | Rubus 'Prime-Ark Freedom' | cultivar | stark=berry-plants/blackberry-plants/prime-ark-freedom-primocane-blackberry; kw=Prime-Ark, blackberr
Himalayan Blackberry | Rubus armeniacus | introduced | mt=Rubus discolor; wiki=Rubus armeniacus; kw=Himalayan blackberr; note=Introduced; edible berries, but it spreads aggressively by canes and seed - control it rather than plant it.
Rhubarb | Rheum rhabarbarum | introduced | stark=garden-plants/rhubarb-plants/starkrimson-rhubarb; wiki=Rhubarb
Valiant Grape | Vitis 'Valiant' | cultivar | kw=Valiant, grape
Frontenac Grape | Vitis 'Frontenac' | cultivar | stark=berry-plants/grape-vines/frontenac-grape; wiki=Frontenac (grape); kw=Frontenac, grape
Huckleberry (Big Huckleberry) | Vaccinium membranaceum | native | wiki=Vaccinium membranaceum; kw=huckleberr
Thimbleberry | Rubus parviflorus | native | wiki=Rubus parviflorus
Oregon Grape (Creeping Oregon-grape) | Berberis repens | native | wiki=Mahonia repens; kw=Oregon grape, Mahonia
Kinnikinnick (Bearberry) | Arctostaphylos uva-ursi | native | wiki=Arctostaphylos uva-ursi; kw=kinnikinnick, bearberry

## Nut trees
Hazelnuts (Filbert) | Corylus avellana | introduced | stark=nut-trees/filbert-hazelnut-trees/halls-giant-filbert-hazelnut; wiki=Corylus avellana; kw=hazelnut, filbert
American Hazelnut | Corylus americana | introduced | wiki=Corylus americana; kw=hazelnut
Beaked Hazelnut | Corylus cornuta | native | wiki=Corylus cornuta; kw=hazelnut

## Trees - Shade & ornamental
Sugar Maple | Acer saccharum | introduced | wiki=Acer saccharum
Norway Maple | Acer platanoides | introduced | wiki=Acer platanoides
Autumn Blaze Red Maple | Acer x freemanii 'Autumn Blaze' | cultivar | wiki=Acer × freemanii; kw=Autumn Blaze, Freeman
Rocky Mountain Maple | Acer glabrum | native | wiki=Acer glabrum
Amur Maple | Acer ginnala | introduced | wiki=Acer ginnala
Boxelder | Acer negundo | native | wiki=Acer negundo
Weeping Willow | Salix babylonica | introduced | wiki=Salix babylonica; kw=willow
Peachleaf Willow | Salix amygdaloides | native | wiki=Salix amygdaloides; kw=willow
American Mountain-ash | Sorbus americana | introduced | wiki=Sorbus americana; kw=mountain-ash, mountain ash; note=Telling the three mountain-ash apart (rough guide): European - orange to orange-red berries, fuzzy white-hairy winter buds; American - smaller red-orange berries, long narrow sharply pointed leaflets, sticky smooth buds; Showy - larger bright red berries in big clusters, shorter blunter leaflets.
European Mountain-ash | Sorbus aucuparia | introduced | wiki=Sorbus aucuparia; kw=mountain-ash, mountain ash; note=Telling the three mountain-ash apart (rough guide): European - orange to orange-red berries, fuzzy white-hairy winter buds; American - smaller red-orange berries, long narrow sharply pointed leaflets, sticky smooth buds; Showy - larger bright red berries in big clusters, shorter blunter leaflets.
Showy Mountain-ash | Sorbus decora | introduced | wiki=Sorbus decora; kw=mountain-ash, mountain ash; note=Telling the three mountain-ash apart (rough guide): European - orange to orange-red berries, fuzzy white-hairy winter buds; American - smaller red-orange berries, long narrow sharply pointed leaflets, sticky smooth buds; Showy - larger bright red berries in big clusters, shorter blunter leaflets.
Quaking Aspen | Populus tremuloides | native | wiki=Populus tremuloides; kw=aspen
Lombardy Poplar | Populus nigra 'Italica' | cultivar | wiki=Lombardy poplar; kw=poplar
Theves Poplar | Populus nigra 'Thevestina' | cultivar | wiki=Populus nigra; kw=Theves, Thevestina, poplar; note=Theves poplar is a narrow, column-shaped black poplar with pale, almost white bark - planted like Lombardy poplar for screens and windbreaks.
Hybrid Poplar | Populus x canadensis | introduced | wiki=Populus × canadensis; kw=poplar
Cottonless Cottonwood | Populus deltoides 'Siouxland' | cultivar | kw=cottonless, cottonwood; note='Cottonless' cottonwoods are male clones (e.g. Siouxland, Robusta) that do not shed seed fluff.
Plains Cottonwood | Populus deltoides | native | wiki=Populus deltoides; kw=cottonwood
Black Cottonwood | Populus trichocarpa | native | wiki=Populus trichocarpa; kw=cottonwood
Narrowleaf Cottonwood | Populus angustifolia | native | wiki=Populus angustifolia; kw=cottonwood
Paper Birch | Betula papyrifera | native | wiki=Betula papyrifera; kw=birch
Water Birch | Betula occidentalis | native | wiki=Betula occidentalis; kw=birch
European White Birch | Betula pendula | introduced | wiki=Betula pendula; kw=birch
Purple Ash (Autumn Purple White Ash) | Fraxinus americana 'Autumn Purple' | cultivar | wiki=Fraxinus americana; kw=ash
Green Ash | Fraxinus pennsylvanica | native | wiki=Fraxinus pennsylvanica; kw=ash
American Linden (Basswood) | Tilia americana | introduced | wiki=Tilia americana; kw=linden, basswood
Redmond Linden | Tilia americana 'Redmond' | cultivar | wiki=Tilia americana; kw=Redmond, linden; note=Redmond is a selection of American linden (basswood) with a dense, pyramid-shaped crown and large glossy leaves; care is the same as American linden.
Bur Oak | Quercus macrocarpa | introduced | wiki=Quercus macrocarpa
Common Hackberry | Celtis occidentalis | introduced | wiki=Celtis occidentalis
American Elm | Ulmus americana | introduced | wiki=Ulmus americana; kw=elm
Siberian Elm | Ulmus pumila | introduced | wiki=Ulmus pumila; kw=elm; note=Weedy and short-lived; spreads by seed. Not recommended for planting.
Russian Olive | Elaeagnus angustifolia | noxious | wiki=Elaeagnus angustifolia; note=Listed as a noxious weed in Montana - do not plant.
Japanese Tree Lilac | Syringa reticulata | introduced | wiki=Syringa reticulata
Black Hawthorn | Crataegus douglasii | native | wiki=Crataegus douglasii; kw=hawthorn

## Trees - Conifers
Ponderosa Pine | Pinus ponderosa | native | wiki=Pinus ponderosa; kw=ponderosa
Douglas-fir | Pseudotsuga menziesii | native | wiki=Pseudotsuga menziesii; kw=Douglas-fir, Douglas fir
Western Larch | Larix occidentalis | native | wiki=Larix occidentalis; kw=larch
Lodgepole Pine | Pinus contorta | native | wiki=Pinus contorta; kw=lodgepole
Colorado Blue Spruce | Picea pungens | introduced | wiki=Picea pungens; kw=blue spruce, Colorado spruce
Subalpine Fir | Abies lasiocarpa | native | wiki=Abies lasiocarpa; kw=subalpine fir
Engelmann Spruce | Picea engelmannii | native | wiki=Picea engelmannii; kw=Engelmann
Grand Fir | Abies grandis | native | wiki=Abies grandis; kw=grand fir
Western Redcedar | Thuja plicata | native | wiki=Thuja plicata; kw=redcedar, red cedar
Rocky Mountain Juniper | Juniperus scopulorum | native | wiki=Juniperus scopulorum; kw=juniper
Limber Pine | Pinus flexilis | native | wiki=Pinus flexilis; kw=limber pine
Whitebark Pine | Pinus albicaulis | native | wiki=Pinus albicaulis; kw=whitebark

## Shrubs & hedges
Common Lilac | Syringa vulgaris | introduced | wiki=Syringa vulgaris; kw=lilac
Caragana (Siberian Peashrub) | Caragana arborescens | introduced | wiki=Caragana arborescens; kw=caragana, peashrub, pea shrub
Spirea | Spiraea x vanhouttei | introduced | wiki=Spiraea; kw=spirea, spiraea
Birchleaf Spirea (native) | Spiraea betulifolia | native | wiki=Spiraea betulifolia; kw=spirea, spiraea
Red-osier Dogwood | Cornus sericea | native | wiki=Cornus sericea; kw=dogwood
Shrubby Cinquefoil (Potentilla) | Dasiphora fruticosa | native | wiki=Dasiphora fruticosa; kw=potentilla, cinquefoil
Lewis' Mock Orange | Philadelphus lewisii | native | wiki=Philadelphus lewisii; kw=mock orange, mockorange
Mallow Ninebark | Physocarpus malvaceus | native | wiki=Physocarpus malvaceus; kw=ninebark
Common Snowberry | Symphoricarpos albus | native | wiki=Symphoricarpos albus; kw=snowberr
Smooth Sumac | Rhus glabra | native | wiki=Rhus glabra; kw=sumac
Skunkbush Sumac | Rhus trilobata | native | wiki=Rhus trilobata; kw=sumac, skunkbush
Highbush Cranberry (American Cranberrybush) | Viburnum opulus var. americanum | native | wiki=Viburnum opulus; kw=cranberr, viburnum
Hedge Cotoneaster | Cotoneaster lucidus | introduced | wiki=Cotoneaster lucidus; kw=cotoneaster
Big Sagebrush | Artemisia tridentata | native | wiki=Artemisia tridentata; kw=sagebrush
Rubber Rabbitbrush | Ericameria nauseosa | native | wiki=Ericameria nauseosa; kw=rabbitbrush

## Roses
Roses (shrub roses for Montana) | Rosa | introduced | stark=garden-plants/roses/double-knock-out-rose; wiki=Rose; kw=rose; note=General page for growing roses in the Flathead - see the variety and native rose pages too.
John Cabot Rose | Rosa 'John Cabot' | cultivar | kw=John Cabot, Explorer
William Baffin Rose | Rosa 'William Baffin' | cultivar | kw=William Baffin, Explorer
Morden Blush Rose | Rosa 'Morden Blush' | cultivar | kw=Morden Blush, Parkland
Rugosa Rose | Rosa rugosa | introduced | wiki=Rosa rugosa; kw=rugosa
Harison's Yellow Rose | Rosa x harisonii | cultivar | wiki=Rosa × harisonii; kw=Harison
Austrian Copper Rose | Rosa foetida 'Bicolor' | cultivar | wiki=Rosa foetida; kw=Austrian Copper, foetida
Woods' Rose (wild rose, rose hips) | Rosa woodsii | native | wiki=Rosa woodsii; kw=Woods, rose hip
Prickly Rose | Rosa acicularis | native | wiki=Rosa acicularis; kw=prickly rose

## Herbs
Herbs for Montana Gardens | Lamiaceae and others | introduced | kw=herb; note=Overview page - see each herb below.
Chives | Allium schoenoprasum | introduced | wiki=Chives
Garlic | Allium sativum | introduced | wiki=Garlic
Thyme | Thymus vulgaris | introduced | wiki=Thymus vulgaris; kw=thyme
Oregano | Origanum vulgare | introduced | wiki=Oregano
Sage | Salvia officinalis | introduced | wiki=Salvia officinalis; kw=sage
Peppermint | Mentha x piperita | introduced | wiki=Peppermint; kw=mint
Spearmint | Mentha spicata | introduced | wiki=Spearmint; kw=mint
Lovage | Levisticum officinale | introduced | wiki=Lovage
Dill | Anethum graveolens | introduced | wiki=Dill
Parsley | Petroselinum crispum | introduced | wiki=Parsley
Cilantro (Coriander) | Coriandrum sativum | introduced | wiki=Coriander; kw=cilantro, coriander
Basil | Ocimum basilicum | introduced | wiki=Basil
Tarragon | Artemisia dracunculus | introduced | wiki=Tarragon
Horseradish | Armoracia rusticana | introduced | stark=garden-plants/horseradish-plants/horseradish; wiki=Horseradish
Lemon Balm | Melissa officinalis | introduced | wiki=Lemon balm
Hyssop | Hyssopus officinalis | introduced | wiki=Hyssopus officinalis; kw=hyssop
Comfrey | Symphytum officinale | introduced | wiki=Symphytum officinale; kw=comfrey; note=Comfrey contains liver-toxic alkaloids - not for internal use.
Lavender | Lavandula angustifolia | introduced | stark=garden-plants/herbs/munstead-certified-organic-lavender; wiki=Lavandula angustifolia; kw=lavender
Purple Coneflower (Echinacea) | Echinacea purpurea | introduced | wiki=Echinacea purpurea; kw=echinacea, coneflower
Common Yarrow | Achillea millefolium | native | wiki=Achillea millefolium; kw=yarrow
Catnip | Nepeta cataria | introduced | wiki=Catnip

## Native wildflowers & wild foods
Bitterroot (Montana state flower) | Lewisia rediviva | native | wiki=Lewisia rediviva; kw=bitterroot
Common Camas | Camassia quamash | native | wiki=Camassia quamash; kw=camas; note=Easily confused with deadly death camas when not in flower - see Death Camas.
Arrowleaf Balsamroot | Balsamorhiza sagittata | native | wiki=Balsamorhiza sagittata; kw=balsamroot
Fireweed | Chamaenerion angustifolium | native | wiki=Chamerion angustifolium; kw=fireweed
Common Cattail | Typha latifolia | native | wiki=Typha latifolia; kw=cattail
Stinging Nettle | Urtica dioica | native | wiki=Urtica dioica; kw=nettle

## Poisonous plants
Western Water Hemlock | Cicuta douglasii | poisonous | wiki=Cicuta douglasii; kw=water hemlock, Cicuta
Poison Hemlock | Conium maculatum | poisonous | wiki=Conium maculatum; kw=poison hemlock, Conium
Death Camas | Toxicoscordion venenosum | poisonous | wiki=Toxicoscordion venenosum; kw=death camas, Zigadenus
Red Baneberry | Actaea rubra | poisonous | wiki=Actaea rubra; kw=baneberry
Tall Larkspur | Delphinium occidentale | poisonous | wiki=Delphinium occidentale; kw=larkspur
False Hellebore (Corn Lily) | Veratrum viride | poisonous | wiki=Veratrum viride; kw=hellebore, Veratrum

## Noxious weeds
Spotted Knapweed | Centaurea stoebe | noxious | wiki=Centaurea stoebe; kw=knapweed
Leafy Spurge | Euphorbia virgata | noxious | wiki=Euphorbia virgata; kw=leafy spurge
Canada Thistle | Cirsium arvense | noxious | wiki=Cirsium arvense; kw=Canada thistle
Houndstongue | Cynoglossum officinale | noxious | wiki=Cynoglossum officinale; kw=houndstongue
Cheatgrass (Downy Brome) | Bromus tectorum | noxious | wiki=Bromus tectorum; kw=cheatgrass, downy brome
Dalmatian Toadflax | Linaria dalmatica | noxious | wiki=Linaria dalmatica; kw=toadflax
Field Bindweed | Convolvulus arvensis | noxious | wiki=Convolvulus arvensis; kw=bindweed
Oxeye Daisy | Leucanthemum vulgare | noxious | wiki=Leucanthemum vulgare; kw=oxeye daisy
White Bryony | Bryonia alba | noxious | wiki=Bryonia alba; kw=bryony
Orange Hawkweed | Pilosella aurantiaca | noxious | wiki=Pilosella aurantiaca; kw=hawkweed
"""

# Stark Bro's growing-guide series: by scientific-name prefix (longest match wins), else by group
GENUS_GUIDE = {"Malus": "fruit-trees/apple-trees", "Pyrus": "fruit-trees/pear-trees", "Prunus avium": "fruit-trees/cherry-trees",
               "Prunus cerasus": "fruit-trees/cherry-trees", "Prunus x kerrasis": "fruit-trees/cherry-trees",
               "Prunus tomentosa": "fruit-trees/cherry-trees", "Prunus domestica": "fruit-trees/plum-trees",
               "Prunus 'T": "fruit-trees/plum-trees", "Prunus 'P": "fruit-trees/plum-trees", "Prunus 'S": "fruit-trees/plum-trees",
               "Prunus 'W": "fruit-trees/plum-trees", "Prunus americana": "fruit-trees/plum-trees",
               "Prunus armeniaca": "fruit-trees/apricot-trees", "Prunus mandshurica": "fruit-trees/apricot-trees",
               "Sambucus canadensis": "berry-plants/elderberry-plants", "Ribes": "berry-plants/gooseberry-plants",
               "Lonicera caerulea": "berry-plants/honeyberry-plants", "Aronia": "berry-plants/aronia-berry-plants",
               "Rubus idaeus": "berry-plants/raspberry-plants", "Rubus (": "berry-plants/blackberry-plants",
               "Rubus 'P": "berry-plants/blackberry-plants", "Rubus armeniacus": "berry-plants/blackberry-plants", "Fragaria x": "berry-plants/strawberry-plants",
               "Vitis": "berry-plants/grape-vines", "Rheum": "garden-plants/rhubarb-plants", "Corylus": "nut-trees/filbert-hazelnut-trees",
               "Syringa vulgaris": "garden-plants/lilacs", "Rosa '": "garden-plants/roses", "Rosa rugosa": "garden-plants/roses",
               "Rosa x": "garden-plants/roses", "Rosa foetida": "garden-plants/roses", "Rosa": "garden-plants/roses",
               "Armoracia": "garden-plants/horseradish-plants"}
GROUP_GUIDE = {"Trees - Shade & ornamental": "landscape-trees/shade-trees", "Trees - Conifers": "landscape-trees/evergreens",
               "Herbs": "garden-plants/herbs"}
NO_GUIDE_KINDS = ("noxious", "poisonous")

# MSU Extension publications (extension-store.montana.edu product slugs) -> groups / scientific-name prefixes ('*' = every page)
MSU_PUBS = {
    "growing-fruit-trees-in-montana-download-only": ["Fruit trees - Apples", "Fruit trees - Pears", "Fruit trees - Plums & apricots", "Fruit trees - Cherries"],
    "pruning-fruit-trees-in-montana": ["Fruit trees - Apples", "Fruit trees - Pears", "Fruit trees - Plums & apricots", "Fruit trees - Cherries"],
    "backyard-guide-to-codling-moth-management": ["Fruit trees - Apples", "Fruit trees - Pears"],
    "growing-minor-stone-fruit-in-montana": ["Fruit trees - Plums & apricots", "Fruit trees - Cherries"],
    "growing-cold-hardy-berries-and-small-fruits-in-montana": ["Berries & small fruit"],
    "growing-currants-and-gooseberries-in-montana": ["Ribes"],
    "growing-raspberries-in-montana-gardens": ["Rubus idaeus"],
    "strawberries-in-the-home-garden": ["Fragaria"],
    "growing-rhubarb-in-montana": ["Rheum"],
    "growing-serviceberries": ["Amelanchier"],
    "growing-lilacs-in-montana": ["Syringa"],
    "growing-shrub-roses-in-montana": ["Roses"],
    "herbs-for-montana-gardens": ["Herbs"],
    "growing-garlic-in-montana": ["Allium sativum"],
    "native-plants-for-montanas-home-gardens-mt202503ag": ["Native wildflowers & wild foods", "Shrubs & hedges"],
    "perennials-and-biennials-for-montana-gardens": ["Native wildflowers & wild foods"],
    "poisonous-plants-in-the-home-landscape": ["Poisonous plants"],
    "fire-resistant-plants-for-montana-landscapes": ["Trees - Shade & ornamental", "Trees - Conifers", "Shrubs & hedges"],
    "fire-resistant-landscaping-considerations-for-montanas-wildland-urban-interface-wui": ["Trees - Conifers", "Shrubs & hedges"],
    "minimizing-deer-damage-in-residential-settings": ["Trees - Shade & ornamental", "Shrubs & hedges", "Roses", "Fruit trees - Apples"],
    "whats-wrong-with-this-tree": ["Trees - Shade & ornamental", "Trees - Conifers"],
    "home-garden-soil-testing-and-fertilizer-guidelines": ["*"],
    "yard-and-garden-water-management": ["*"],
    "home-composting": [],
    "creating-native-bee-habitat-for-gardens-in-montana-and-the-rocky-mountain-region": [],
    "bumble-bees-in-montana": [],
    # vegetables (home garden) - added 2026-10-12
    "can-i-grow-that-here-vegetable-seed-and-transplant-schedules-for-garden-or-container": ["Vegetables"],
    "successful-home-vegetable-gardening": ["Vegetables"],
    "hotbeds-cold-frames-and-low-tunnels-for-montana-gardeners": ["Vegetables"],
    "heirloom-vegetables-for-montana-gardens": ["Vegetables"],
    "growing-tomatoes-in-montana": ["Solanum lycopersicum"],
    "asparagus-in-the-home-garden": ["Asparagus"],
    "late-blight-in-garden-potatoes": ["Solanum tuberosum", "Solanum lycopersicum"],
}

# other reference documents (PDF or web page) -> groups / scientific-name prefixes
_WARC = "Montana State University - Western Agricultural Research Center"
_FL = "MSU Extension - Flathead County"
_FLD = "https://www.montana.edu/extension/flathead/documents/ag/"
APPLE, PEAR, PLUM, CHERRY = "Fruit trees - Apples", "Fruit trees - Pears", "Fruit trees - Plums & apricots", "Fruit trees - Cherries"
FRUIT = [APPLE, PEAR, PLUM, CHERRY]
PLUMS = ["Prunus domestica", "Prunus 'T", "Prunus 'P", "Prunus 'S", "Prunus 'W", "Prunus americana"]
REFS = {
    "msu-apple-cultivars": {"title": "Apple Cultivars Recommended for Montana (MSU WARC)", "kind": "html", "for": [APPLE],
        "url": "https://agresearch.montana.edu/warc/guides/apples/apple_cultivars_grown_in_Montana.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-apple-rootstocks": {"title": "Selecting Rootstocks and Apple Cultivars for Montana (MSU WARC)", "kind": "html", "for": [APPLE],
        "url": "https://agresearch.montana.edu/warc/guides/apples/rootstocks_cultivars.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-apple-site": {"title": "Apple Orchard Site Selection (MSU WARC)", "kind": "html", "for": [APPLE, PEAR],
        "url": "https://agresearch.montana.edu/warc/guides/apples/apple_orchard_site_selection_.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-apple-planting": {"title": "Apple Orchard Site Preparation and Planting (MSU WARC)", "kind": "html", "for": [APPLE, PEAR],
        "url": "https://agresearch.montana.edu/warc/guides/apples/apple_site_prep_and_planting.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-apple-irrigation": {"title": "Apple Orchard Irrigation (MSU WARC)", "kind": "html", "for": [APPLE, PEAR],
        "url": "https://agresearch.montana.edu/warc/guides/apples/Apple_Irrigation.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-apple-nutrition": {"title": "Apple Orchard Nutrition (MSU WARC)", "kind": "html", "for": [APPLE, PEAR],
        "url": "https://agresearch.montana.edu/warc/guides/apples/apple_orchard_nutrition.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-fire-blight": {"title": "Fire Blight in Montana Apple Orchards (MSU WARC)", "kind": "html", "for": [APPLE, PEAR, "Sorbus", "Cotoneaster", "Crataegus"],
        "url": "https://agresearch.montana.edu/warc/guides/apples/fire_blight_in_montana_apple_orchards.html", "root": "#rightpane", "publisher": _WARC, "topic": "Pests & diseases"},
    "msu-codling-moth": {"title": "Managing Codling Moth in the Home Orchard (MSU WARC)", "kind": "html", "for": [APPLE, PEAR],
        "url": "https://agresearch.montana.edu/warc/guides/apples/managing_codling_moth_in_the_home_orchard.html", "root": "#rightpane", "publisher": _WARC, "topic": "Pests & diseases"},
    "msu-heritage-care": {"title": "Caring for Heritage Apple Trees (MSU WARC Heritage Orchard Guide)", "kind": "html", "for": [APPLE],
        "url": "https://agresearch.montana.edu/warc/guides/apples/heritage_orchard_management_guide/caring-for-heritage-trees/index.html", "root": "#rightpane", "publisher": _WARC, "topic": "Apples"},
    "msu-fire-blight-workshop": {"title": "Fire Blight - Montana IPM Workshop 2018 (MSU)", "kind": "pdf", "for": [APPLE, PEAR],
        "url": "https://agresearch.montana.edu/warc/guides/apples/Fire%20Blight%20Montana%20IPM%20workshop%202018.pdf", "publisher": "Montana State University", "topic": "Pests & diseases"},
    "msu-fruit-research-sites": {"title": "MSU Extension Fruit Research Sites - Bloom Dates, Frost Risk and Cultivar Survival", "kind": "pdf", "for": FRUIT,
        "url": "https://agresearch.montana.edu/warc/research_current/msu-ext-fruit-research-sites/docs/MSU_Extension_Research_webpage.pdf",
        "publisher": "Montana State University Extension", "topic": "Fruit trees"},
    "msu-growing-fruit-trees-maes": {"title": "Growing Fruit Trees in Montana (MSU Agricultural Experiment Station)", "kind": "pdf", "for": FRUIT,
        "url": "https://agresearch.montana.edu/warc/research_current/msu-ext-fruit-research-sites/Growing%20fruit%20trees%20in%20MT-%20MSU.pdf",
        "publisher": "Montana State University", "topic": "Fruit trees"},
    "flathead-frost-free-days": {"title": "Frost-Free Days Chart - MSU Northwestern Ag Research Center, Creston (Flathead Valley)", "kind": "pdf", "for": ["*"],
        "url": _FLD + "yard-garden/Frost%20Free%20Days%20Chart-MSU%20Creston%20Research%20Station.pdf", "publisher": _FL, "topic": "Kalispell climate"},
    "flathead-proper-watering": {"title": "Proper Watering (MSU Extension Flathead County)", "kind": "pdf", "for": ["*"],
        "url": _FLD + "yard-garden/Proper%20Watering.pdf", "publisher": _FL, "topic": "Care"},
    "flathead-composting": {"title": "Composting (MSU Extension Flathead County)", "kind": "pdf", "for": [],
        "url": _FLD + "yard-garden/Composting%20Article.pdf", "publisher": _FL, "topic": "Care"},
    "flathead-ground-squirrels": {"title": "Ground Squirrels (MSU Extension Flathead County)", "kind": "pdf", "for": [],
        "url": _FLD + "yard-garden/Ground%20Squirrels.pdf", "publisher": _FL, "topic": "Pests & diseases"},
    "wsu-spray-apple": {"title": "Spray Schedule for Apple Trees (WSU, via MSU Flathead County)", "kind": "pdf", "for": [APPLE],
        "url": _FLD + "yard-garden/Spray%20schedule%20for%20apple%20trees%20-%20WSU.pdf", "publisher": "Washington State University Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "wsu-spray-cherry": {"title": "Spray Schedule for Cherry Trees (WSU, via MSU Flathead County)", "kind": "pdf", "for": [CHERRY],
        "url": _FLD + "yard-garden/Spray%20schedule%20for%20Cherries%20-%20WSU.pdf", "publisher": "Washington State University Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "wsu-spray-apricot": {"title": "Spray Schedule for Peach and Apricot Trees (WSU, via MSU Flathead County)", "kind": "pdf", "for": ["Prunus armeniaca", "Prunus mandshurica"],
        "url": _FLD + "yard-garden/Spray%20schedule%20for%20peaches%20and%20apricots%20-%20WSU.pdf", "publisher": "Washington State University Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "wsu-spray-pear": {"title": "Spray Schedule for Pear Trees (WSU, via MSU Flathead County)", "kind": "pdf", "for": [PEAR],
        "url": _FLD + "yard-garden/Spray%20schedule%20for%20pears%20-%20WSU.pdf", "publisher": "Washington State University Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "wsu-spray-plum": {"title": "Spray Schedule for Plum and Prune Trees (via MSU Flathead County)", "kind": "pdf", "for": PLUMS,
        "url": _FLD + "yard-garden/Spray%20schedule%20for%20plums%20and%20prunes.pdf", "publisher": "Washington State University Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "flathead-needle-cast": {"title": "Needle Cast Diseases of Conifers (MSU Flathead County)", "kind": "pdf", "for": ["Trees - Conifers"],
        "url": _FLD + "plant-disease/Needle%20Cast%20Diseases%20of%20Conifers.pdf", "publisher": _FL, "topic": "Pests & diseases"},
    "flathead-powdery-mildew": {"title": "Powdery Mildew (Colorado State Extension, via MSU Flathead County)", "kind": "pdf", "for": ["Syringa", "Rosa", "Acer", "Ribes", "Vitis", "Malus"],
        "url": _FLD + "plant-disease/Powdery%20Mildew%20Colorado%20State%20Extension.pdf", "publisher": "Colorado State University Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "flathead-raspberry-cane-borer": {"title": "Raspberry Cane Borer (UNH, via MSU Flathead County)", "kind": "pdf", "for": ["Rubus idaeus", "Rosa"],
        "url": _FLD + "spiders-insects/Raspberry%20cane%20borer%20New%20Hampshire.pdf", "publisher": "University of New Hampshire Extension (via MSU Extension Flathead County)", "topic": "Pests & diseases"},
    "flathead-bark-beetle": {"title": "Bark Beetles (MSU Flathead County)", "kind": "pdf", "for": ["Trees - Conifers"],
        "url": _FLD + "spiders-insects/Bark%20Beetle%20PDF%202%20-better%20version.pdf", "publisher": _FL, "topic": "Pests & diseases"},
    "msu-mountain-pine-beetle": {"title": "Managing Mountain Pine Beetle in Urban and Shelterbelt Trees (MSU Extension)", "kind": "pdf", "for": ["Pinus"],
        "url": _FLD + "spiders-insects/Managing%20Mountain%20Pine%20Beetle.pdf", "publisher": "Montana State University Extension (Flathead County)", "topic": "Pests & diseases"},
    "flathead-tussock-moth": {"title": "Douglas-fir Tussock Moth (MSU Flathead County)", "kind": "pdf", "for": ["Pseudotsuga", "Abies", "Picea"],
        "url": _FLD + "spiders-insects/Douglas%20Fir%20Tussock%20Moth.pdf", "publisher": _FL, "topic": "Pests & diseases"},
    "flathead-spruce-budworm": {"title": "Western Spruce Budworm (MSU Flathead County)", "kind": "pdf", "for": ["Pseudotsuga", "Abies", "Picea", "Larix"],
        "url": _FLD + "spiders-insects/Western%20Spruce%20Budworms.pdf", "publisher": _FL, "topic": "Pests & diseases"},
    "flathead-bt-budworm": {"title": "Using Bt for Spruce Budworm (MSU Flathead County)", "kind": "pdf", "for": ["Pseudotsuga", "Abies", "Picea"],
        "url": _FLD + "spiders-insects/The%20use%20of%20BT%20for%20Spruce%20Bud%20Worm.pdf", "publisher": _FL, "topic": "Pests & diseases"},
    "flathead-biological-controls": {"title": "MSU IPM - Biological Controls", "kind": "pdf", "for": [],
        "url": _FLD + "spiders-insects/MSU%20IPM%20biological%20controls.pdf", "publisher": "MSU Extension", "topic": "Pests & diseases"},
    "flathead-bee-id": {"title": "Montana Bee Identification Guide (MSU)", "kind": "pdf", "for": [],
        "url": _FLD + "spiders-insects/Montana%20Bee%20Identification%20Guide.pdf", "publisher": "MSU Extension", "topic": "Pollinators"},
    "flathead-white-bryony": {"title": "White Bryony (MSU Flathead County)", "kind": "pdf", "for": ["Bryonia"],
        "url": _FLD + "weeds/White%20Bryony.pdf", "publisher": _FL, "topic": "Weeds"},
    "usda-ponderosa-plant-guide": {"title": "Ponderosa Pine - Plant Guide (USDA NRCS PLANTS)", "kind": "pdf", "for": ["Pinus ponderosa"],
        "url": "https://plants.usda.gov/DocumentLibrary/plantguide/pdf/pg_pipo.pdf",
        "publisher": "USDA NRCS PLANTS Database", "license": "Public domain (US government work)", "topic": "Trees"},
    "usda-ponderosa-fact-sheet": {"title": "Ponderosa Pine - Fact Sheet (USDA NRCS PLANTS)", "kind": "pdf", "for": ["Pinus ponderosa"],
        "url": "https://plants.usda.gov/DocumentLibrary/factsheet/pdf/fs_pipo.pdf",
        "publisher": "USDA NRCS PLANTS Database", "license": "Public domain (US government work)", "topic": "Trees"},
    "usfs-conifer-pests": {"title": "Field Guide to Diseases and Insect Pests of Northern and Central Rocky Mountain Conifers (USFS R1-03-08)", "kind": "pdf",
        "for": ["Trees - Conifers"],
        "url": "https://dnrc.mt.gov/_docs/forestry/Forestry_Assistance/Forest_Pests/2013-A-FIELD-GUIDE-TO-insect-and-disease-as-PDF.pdf",
        "publisher": "USDA Forest Service Northern Region (Hagle, Gibson & Tunnock; 2013 reprint)", "license": "Public domain (US government work)", "topic": "Pests & diseases"},
    "msu-sw-montana-forest": {"title": "Southwest Montana Forest Guide (MSU Extension Gallatin County)", "kind": "pdf", "for": ["Trees - Conifers"],
        "url": "https://www.montana.edu/extension/gallatin/documents/naturalresourcesdocuments/SWMontanaForestGuide.pdf",
        "publisher": "Montana State University Extension (Gallatin County)", "topic": "Trees"},
}
# documents already in the library elsewhere, linked (not copied) from matching pages
VEG = "Vegetables"
REFS.update({
    "uidaho-bul863-short-season-varieties": {"title": "Short-Season, High-Altitude Gardening: Choosing and Growing Adapted Vegetable Varieties (University of Idaho BUL 863)",
        "kind": "pdf", "for": [VEG], "publisher": "University of Idaho Extension", "topic": "Vegetable varieties",
        "url": "https://www.uidaho.edu/-/media/UIdaho-Responsive/Files/Extension/publications/bul/bul0863.pdf",
        "fetch_url": "http://web.archive.org/web/20250607033932id_/https://uidaho.edu/-/media/uidaho-responsive/files/extension/publications/bul/bul0863.pdf"},
    "pnw497-short-season-gardening": {"title": "Short Season Vegetable Gardening (PNW 497 - Idaho, Oregon State, Washington State)",
        "kind": "pdf", "for": [VEG], "publisher": "Pacific Northwest Extension (University of Idaho / OSU / WSU)", "topic": "Vegetables",
        "url": "https://www.uidaho.edu/-/media/UIdaho-Responsive/Files/Extension/publications/pnw/pnw0497.pdf",
        "fetch_url": "http://web.archive.org/web/20230314132031id_/https://www.uidaho.edu/-/media/UIdaho-Responsive/Files/Extension/publications/pnw/pnw0497.pdf"},
    "uwyo-b1148r-extending-season": {"title": "Extending the Vegetable Growing Season (University of Wyoming B-1148R)", "kind": "pdf", "for": [VEG],
        "url": "https://www.wyoextension.org/agpubs/pubs/B-1148R-extending-season_web.pdf", "publisher": "University of Wyoming Extension",
        "topic": "Season extension & greenhouse"},
    "nmsu-h252-hoop-house": {"title": "Hoop House Vegetable Production (New Mexico State University Guide H-252)", "kind": "pdf", "for": [VEG],
        "url": "https://pubs.nmsu.edu/_h/H252.pdf", "publisher": "New Mexico State University Cooperative Extension",
        "topic": "Season extension & greenhouse"},
})

REFS.update({
    "umn-tomatillos-ground-cherries": {"title": "Growing Tomatillos and Ground Cherries (University of Minnesota Extension)", "kind": "html",
        "for": ["Physalis"], "url": "https://extension.umn.edu/vegetables/growing-tomatillos-and-ground-cherries",
        "publisher": "University of Minnesota Extension", "topic": "Vegetables"},
    "usu-tomatillos": {"title": "Tomatillos in the Garden (Utah State University Extension)", "kind": "html", "for": ["Physalis philadelphica"],
        "url": "https://extension.usu.edu/yardandgarden/research/tomatillos-in-the-garden", "publisher": "Utah State University Extension",
        "topic": "Vegetables"},
    "usu-sweet-potatoes": {"title": "Sweet Potatoes in the Garden (Utah State University Extension)", "kind": "html", "for": ["Ipomoea"],
        "url": "https://extension.usu.edu/yardandgarden/research/sweet-potatoes-in-the-garden", "publisher": "Utah State University Extension",
        "topic": "Vegetables"},
})
REFS.update({
    "cornell-arugula": {"title": "Arugula Growing Guide (Cornell University Home Gardening)", "kind": "html", "for": ["Eruca"],
        "url": "https://gardening.cals.cornell.edu/garden-guidance/foodgarden/vegetable-growing-guides/arugula/",
        "publisher": "Cornell University - Cornell Garden-Based Learning", "topic": "Vegetables"},
    "umn-scallions": {"title": "Growing Scallions in Home Gardens (University of Minnesota Extension)", "kind": "html", "for": ["Allium fistulosum"],
        "url": "https://extension.umn.edu/vegetables/growing-scallions-home-gardens", "publisher": "University of Minnesota Extension", "topic": "Vegetables"},
    "usu-shallots": {"title": "Shallots in the Garden (Utah State University Extension)", "kind": "html", "for": ["Allium cepa (Aggregatum"],
        "url": "https://extension.usu.edu/yardandgarden/research/shallots-in-the-garden", "publisher": "Utah State University Extension",
        "topic": "Vegetables"},
    "mcgill-endive": {"title": "Endive - Ecological Agriculture Projects (McGill University)", "kind": "html", "for": ["Cichorium endivia"],
        "url": "https://eap.mcgill.ca/CPLV_2.htm", "publisher": "McGill University - Ecological Agriculture Projects", "topic": "Vegetables"},
})
WILD, WOOD, LIVE = "Living with wildlife", "Heating with wood", "Livestock & bees"
FWP = "Montana Fish, Wildlife & Parks"
REFS.update({
    "fwp-lww-tips": {"title": "Living with Wildlife - General Tips - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/tips", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-deer": {"title": "Deer - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/deer", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-voles": {"title": "Voles - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/voles", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-pocket-gophers": {"title": "Pocket Gophers - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/pocket-gophers", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-skunks": {"title": "Skunks - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/skunks", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-raccoons": {"title": "Raccoons - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/raccoons", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-rabbits": {"title": "Rabbits - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/rabbits", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-woodpeckers": {"title": "Woodpeckers - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/woodpeckers", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-bats": {"title": "Bats - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/bats", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-snakes": {"title": "Snakes - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/snakes", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-porcupines": {"title": "Porcupines - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/porcupines", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-ground-squirrels": {"title": "Ground Squirrels - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/ground-squirrels", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-tree-squirrels": {"title": "Tree Squirrels - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/tree-squirrels", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-woodrats": {"title": "Woodrats (Pack Rats) - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/woodrats", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-magpies": {"title": "Magpies - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/magpies", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-turkeys": {"title": "Wild Turkeys - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/turkeys", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-beavers": {"title": "Beavers - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/beavers", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-starlings": {"title": "Starlings - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/starlings", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-injured-orphaned-wildlife": {"title": "Injured or Orphaned Wildlife - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/injured-orphaned-wildlife", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-lww-subdivision-recommendations": {"title": "Wildlife Recommendations for Subdivisions - Living with Wildlife (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/living-with-wildlife/subdivision-recommendations", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-living-in-bear-country": {"title": "Living in Bear Country (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/wildlife-management/bear/be-bear-aware/living-bear-country", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-be-bear-aware": {"title": "Be Bear Aware (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/wildlife-management/bear/be-bear-aware", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-electric-fencing-guide": {"title": "Electric Fencing Guide for Bears (Montana FWP, v5.0)", "kind": "pdf", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/binaries/content/assets/fwp/conservation/wildlife-reports/bears/mfwp_electric-fencing-guide_v5.0.pdf",
        "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-bear-aware-flyer-homes": {"title": "Bear Aware Flyer for Homes (Montana FWP)", "kind": "pdf", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/binaries/content/assets/fwp/conservation/living-with-wildlife/bear-aware-flyer-for-homes.pdf",
        "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-mountain-lion": {"title": "Mountain Lion (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/wildlife-management/mountain-lion", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-moose": {"title": "Moose (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/wildlife-management/moose", "publisher": FWP, "topic": "Living with wildlife"},
    "fwp-wolf": {"title": "Wolf (Montana FWP)", "kind": "html", "for": [], "group": WILD,
        "url": "https://fwp.mt.gov/conservation/wildlife-management/wolf", "publisher": FWP, "topic": "Living with wildlife"},
    "defenders-got-bears-mt": {"title": "Got Bears? A Guide to Living with Bears in Montana (Defenders of Wildlife, 2023)", "kind": "pdf", "for": [],
        "group": WILD, "url": "https://defenders.org/sites/default/files/inline-files/got-bears-mt-brochure-2023-fin-web.pdf",
        "publisher": "Defenders of Wildlife", "topic": "Living with wildlife"},
    "defenders-electric-fence-brochure": {"title": "Electric Fencing for Bears (Defenders of Wildlife / IGBC brochure)", "kind": "pdf", "for": [],
        "group": WILD, "url": "https://igbconline.org/wp-content/uploads/2021/08/140529_DOW_EFence_Brochure.pdf",
        "publisher": "Defenders of Wildlife / Interagency Grizzly Bear Committee", "topic": "Living with wildlife"},
    # heating with wood
    "flathead-nf-firewood-guide": {"title": "Personal Use Firewood Guide (Flathead National Forest, 2025)", "kind": "pdf", "for": [], "group": WOOD,
        "url": "https://www.fs.usda.gov/media/221067", "publisher": "USDA Forest Service - Flathead National Forest", "topic": "Heating with wood"},
    "usu-wood-heating": {"title": "Wood Heating (Utah State University Forestry Extension)", "kind": "html", "for": [], "group": WOOD,
        "url": "https://extension.usu.edu/forestry/resources/forest-products/wood-heating", "publisher": "Utah State University Extension",
        "topic": "Heating with wood"},
    "uidaho-cis472-fuelwood": {"title": "Fuelwood - Selecting and Using Wood for Heat (University of Idaho CIS 472)", "kind": "pdf", "for": [],
        "group": WOOD, "url": "https://objects.lib.uidaho.edu/uiext/uiext28849.pdf", "publisher": "University of Idaho Extension", "topic": "Heating with wood"},
    "epa-best-wood-burning-practices": {"title": "Best Wood-Burning Practices (EPA Burn Wise)", "kind": "html", "for": [], "group": WOOD,
        "url": "https://www.epa.gov/burnwise/best-wood-burning-practices", "publisher": "US Environmental Protection Agency", "topic": "Heating with wood"},
    "epa-choosing-wood-stove": {"title": "Choosing the Right Wood-Burning Stove (EPA Burn Wise)", "kind": "html", "for": [], "group": WOOD,
        "url": "https://www.epa.gov/burnwise/choosing-right-wood-burning-stove", "publisher": "US Environmental Protection Agency", "topic": "Heating with wood"},
    # livestock & bees
    "mda-honeybees": {"title": "Honeybees and Apiary Registration (Montana Department of Agriculture)", "kind": "html", "for": [], "group": LIVE,
        "url": "https://agr.mt.gov/topics/a-d/Bees/Honeybees", "publisher": "Montana Department of Agriculture", "topic": "Livestock & bees"},
    "mda-new-apiary-form": {"title": "New Apiary and Landowner Registration Form (Montana Department of Agriculture)", "kind": "pdf", "for": [],
        "group": LIVE, "url": "https://agr.mt.gov/_docs/bees-docs/NewApiaryandLandownerForm.pdf", "publisher": "Montana Department of Agriculture",
        "topic": "Livestock & bees"},
    "mda-montana-bee-guide-2007": {"title": "Montana Bee Guide (Montana Department of Agriculture, 2007)", "kind": "pdf", "for": [], "group": LIVE,
        "url": "https://prod-agr.mt.gov/_docs/bees-docs/MDA_MontanaBeeGuide07.pdf", "publisher": "Montana Department of Agriculture", "topic": "Livestock & bees"},
    "mdol-npip-poultry": {"title": "National Poultry Improvement Plan - Backyard Flocks (Montana Department of Livestock)", "kind": "html", "for": [],
        "group": LIVE, "url": "https://liv.mt.gov/Animal-Health/National-Poultry-Improvement-Plan-NPIP", "publisher": "Montana Department of Livestock",
        "topic": "Livestock & bees"},
    "dphhs-backyard-poultry": {"title": "Live Poultry and Salmonella - Backyard Flock Health (Montana DPHHS)", "kind": "pdf", "for": [], "group": LIVE,
        "url": "https://prod-dphhs.mt.gov/assets/publichealth/CDEpi/Infographics/BackyardPoultry/LivePoultry2017.pdf",
        "publisher": "Montana Department of Public Health and Human Services", "topic": "Livestock & bees"},
    "usu-goats": {"title": "Goats - Small Farms (Utah State University Extension)", "kind": "html", "for": [], "group": LIVE,
        "url": "https://extension.usu.edu/smallfarms/animals/goats", "publisher": "Utah State University Extension", "topic": "Livestock & bees"},
    # vegetable garden gaps (shown on every vegetable page)
    "usu-vegetable-diseases": {"title": "Vegetable Diseases of Utah (Utah State University Extension, 2022)", "kind": "pdf", "for": ["Vegetables"],
        "url": "https://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=3183&context=extension_curall", "fetch_url": "http://web.archive.org/web/20240720104348id_/https://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=3183&context=extension_curall", "publisher": "Utah State University Extension",
        "topic": "Pests & diseases"},
    "arizona-seed-saving": {"title": "Seed Saving (University of Arizona Cooperative Extension)", "kind": "pdf", "for": ["Vegetables"],
        "url": "https://www.extension.arizona.edu/sites/extension.arizona.edu/files/attachment/SeedSaving.pdf",
        "publisher": "University of Arizona Cooperative Extension", "topic": "Vegetables"},
    "umd-seed-saving": {"title": "Seed Saving for Vegetables - Resources (University of Maryland Extension)", "kind": "pdf", "for": ["Vegetables"],
        "url": "https://extension.umd.edu/sites/extension.umd.edu/files/2021-02/Seed%20Saving%20Veggies%20Resources.pdf",
        "publisher": "University of Maryland Extension", "topic": "Vegetables"},
})
import local_veg_specs as _VS
PLANT_TABLE += "\n" + _VS.table_rows() + "\n"

LIBRARY_DOCS_VEG = ["food-storage-preservation/storing-vegetables-at-home.md", "food-storage-preservation/storing-vegetables.md",
                    "food-storage-preservation/uaf-root-cellars-for-alaska-hga-00331.md",
                    "food-storage-preservation/safety-is-the-top-priority.md",
                    "food-storage-preservation/drying-vegetables-montguide-mt200907hr.md",
                    "food-storage-preservation/home-canning-using-boiling-water-canners-and-pressure-canners-montguide-mt200905hr.md",
                    "food-storage-preservation/canning-pickles-and-sauerkraut-montguide-mt200902hr.md",
                    "food-production/backyard-composting.md", "food-production/complete-guide-to-home-composting-joe-lamp.md",
                    "food-production/seed-saving-guide-open-pollinated-varieties.md"]
LIBRARY_DOCS = {"local-area/references/conservation-trees-and-shrubs-for-montana.md": ["Trees - Shade & ornamental", "Trees - Conifers", "Shrubs & hedges"]}
LIBRARY_DOCS.update({p_: ["Vegetables"] for p_ in LIBRARY_DOCS_VEG})

# USDA PLANTS plant guides / fact sheets: symbol per scientific name (pg_<symbol>.pdf / fs_<symbol>.pdf), tried automatically

# Montana Field Guide lists some plants under another (older) scientific name, or not at all
MTFG_ALIAS = {"Populus trichocarpa": "Populus balsamifera", "Dasiphora fruticosa": "Potentilla fruticosa",
              "Viburnum opulus var. americanum": "Viburnum opulus", "Lonicera caerulea": "Lonicera caerulea var. cauriana",
              "Chamaenerion angustifolium": "Chamerion angustifolium", "Toxicoscordion venenosum": "Zigadenus venenosus",
              "Pilosella aurantiaca": "Hieracium aurantiacum", "Euphorbia virgata": "PDEUP0Q0L2"}

# Pollination needs where no variety database covers the plant. Source: general horticultural references
# (nursery catalogs, University of Saskatchewan fruit program, MSU small-fruit MontGuide) - shown on the page as such.
POLLINATION = {
    "Prunus x kerrasis": "Self-fertile (University of Saskatchewan dwarf sour cherries) - fruits without a partner; bees still needed.",
    "Prunus cerasus": "Sour (pie) cherries are self-fertile - one tree is enough.",
    "Prunus avium 'Lapins'": "Self-fertile sweet cherry, and a universal pollinizer for other sweet cherries (e.g. Rainier, Lambert).",
    "Prunus avium 'Rainier'": "Needs another sweet cherry blooming at the same time - Lapins is the usual partner.",
    "Prunus avium 'Stella'": "Self-fertile sweet cherry (one of the first self-fertile sweet cherries) - fruits alone and pollinates other sweet cherries such as Rainier and Lambert.",
    "Prunus avium 'Lambert'": "Not self-fertile - needs another sweet cherry such as Lapins (Bing, Rainier and Lambert do not pollinate each other).",
    "Prunus domestica": "European plums (Italian, Mount Royal) are self-fertile; a second European plum increases the crop. They do not pollinate the American-hybrid plums.",
    "Prunus 'Toka'": "American-hybrid plum. Toka is the classic pollinizer for the other hybrid plums (Pembina, Superior, Waneta); it needs another hybrid or a native American plum itself.",
    "Prunus 'Pembina'": "American-hybrid plum - not self-fertile. Plant Toka or a native American plum (Prunus americana / nigra) nearby.",
    "Prunus 'Superior'": "American-hybrid plum - not self-fertile. Toka or a native American plum is the recommended partner.",
    "Prunus 'Waneta'": "American-hybrid plum - not self-fertile. Toka or a native American plum is the recommended partner.",
    "Prunus americana": "Wild plums set more fruit with a second seedling or a hybrid plum nearby; they also pollinate Pembina, Superior and Waneta.",
    "Prunus armeniaca": "Apricots set more fruit with a second apricot variety (e.g. Westcot with Manchurian or another hardy apricot); they bloom very early - frost on the blossoms is the main risk.",
    "Prunus mandshurica": "Manchurian apricot seedlings are good pollinizers for Westcot and other hardy apricots.",
    "Pyrus": "Pears need a second pear variety that blooms at the same time: Parker and Patten pollinate each other; Ure is pollinated by Golden Spice (and vice versa); Summercrisp needs any other pear.",
    "Malus": "Apples need a different apple or crabapple blooming at the same time within about 100 ft. Crabapples such as Dolgo and Chestnut are long-blooming 'universal' pollinizers.",
    "Sambucus": "Elderberries fruit much better with two different varieties planted together (e.g. Adams + Bob Gordon, or a wild elderberry).",
    "Lonicera caerulea": "Haskap needs a second, different variety that blooms at the same time (check the nursery's pollinator chart).",
    "Hippophae": "Male and female plants are separate - plant at least one male for every 6-8 females.",
    "Shepherdia": "Male and female plants are separate - plant both to get berries.",
    "Corylus": "Hazelnuts are wind-pollinated and need two compatible varieties (or seedlings) within about 50 ft.",
    "Aronia": "Self-fertile.", "Ribes": "Mostly self-fertile; a second variety often increases the crop (black currants especially).",
    "Rubus idaeus": "Self-fertile.", "Rubus (": "Blackberries are self-fertile - one variety is enough.", "Rubus 'P": "Self-fertile.", "Fragaria": "Self-fertile.", "Vitis": "Hardy grapes such as Valiant and Frontenac are self-fertile.",
    "Amelanchier": "Self-fertile; more fruit with another serviceberry nearby.", "Vaccinium membranaceum": "Wild plant - pollinated by native bees; does not transplant easily.",
}

# groups built by 71_build_local_wildlife.py (Montana Field Guide) - also type buttons in Library Manager
WILD_GROUPS = ["Grasses", "Wildlife - Mammals", "Wildlife - Birds", "Wildlife - Fish", "Wildlife - Reptiles & amphibians",
               "Fungi"]
import local_insects_specs as _IS
WILD_GROUPS += list(dict.fromkeys(list(_IS.PICKED) + [w[0] for w in _IS.WHOLE] + _IS.EXTRA_GROUPS))
