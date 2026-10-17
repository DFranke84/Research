"""Which Montana Field Guide insects / spiders / ticks get a Local Area page (user choice 2026-10-11: the 'useful set').

Whole families/orders by elcode prefix or family, plus a hand-picked practical list (matched by scientific name;
genus-only entries take every named species of that genus). Used by 71_build_local_wildlife.py.
"""

# group name -> rule
WHOLE = [   # (group, elcode prefix or None, family or None)
    ("Insects - Butterflies", "IILEP", None),
    ("Insects - Dragonflies & damselflies", "IIODO", None),
    ("Insects - Big moths", None, "Sphingidae"),
    ("Insects - Big moths", None, "Saturniidae"),
]

PICKED = {
    "Insects - Bees & wasps": [
        "Bombus", "Apis mellifera", "Osmia lignaria", "Megachile rotundata", "Nomia melanderi",
        "Vespula", "Dolichovespula", "Polistes dominula", "Polistes fuscatus", "Sceliphron caementarium",
        "Camponotus modoc", "Camponotus herculeanus", "Camponotus pennsylvanicus",
        "Tetramorium immigrans", "Tetramorium caespitum", "Formica obscuripes", "Pogonomyrmex occidentalis",
        "Sirex", "Urocerus", "Tremex columba", "Cimbex americana",
    ],
    "Insects - Biting & stinging": [
        "Culex tarsalis", "Culex pipiens", "Aedes vexans", "Aedes", "Culiseta inornata", "Anopheles freeborni",
        "Tabanus", "Chrysops", "Hybomitra", "Simulium", "Culicoides", "Stomoxys calcitrans", "Haematobia irritans",
        "Hypoderma", "Cuterebra", "Ctenocephalides felis", "Ctenocephalides canis", "Pulex irritans",
        "Oropsylla montana", "Cimex lectularius", "Pediculus humanus", "Triatoma",
    ],
    "Spiders, ticks & mites": [
        "Dermacentor andersoni", "Dermacentor variabilis", "Dermacentor albipictus", "Ixodes", "Rhipicephalus sanguineus",
        "Argas", "Ornithodoros hermsi", "Otobius megnini",
        "Latrodectus hesperus", "Latrodectus", "Eratigena agrestis", "Tegenaria domestica", "Eratigena atrica",
        "Loxosceles", "Cheiracanthium", "Araneus diadematus", "Araneus gemmoides", "Argiope aurantia", "Argiope trifasciata",
        "Misumena vatia", "Phidippus audax", "Phidippus", "Salticus scenicus", "Dolomedes", "Tigrosa", "Hogna",
        "Pholcus phalangioides", "Parasteatoda tepidariorum", "Steatoda", "Dysdera crocata", "Trombicula",
        "Tetranychus urticae", "Oligonychus ununguis", "Varroa destructor",
    ],
    "Insects - Garden & orchard pests": [
        "Pieris rapae", "Trichoplusia ni", "Plutella xylostella", "Delia radicum", "Delia antiqua", "Delia platura",
        "Phyllotreta", "Epitrix", "Psylliodes", "Leptinotarsa decemlineata", "Acalymma", "Diabrotica",
        "Anasa tristis", "Lygus", "Lygus lineolaris", "Lygus hesperus", "Murgantia histrionica", "Halyomorpha halys",
        "Euschistus", "Chlorochroa", "Leptoglossus occidentalis", "Boisea trivittata", "Blissus",
        "Cydia pomonella", "Rhagoletis pomonella", "Rhagoletis indifferens", "Rhagoletis cingulata", "Rhagoletis zephyria",
        "Drosophila suzukii", "Grapholita molesta", "Archips argyrospila", "Choristoneura rosaceana", "Malacosoma",
        "Hyphantria cunea", "Operophtera", "Alsophila pometaria", "Synanthedon", "Caliroa cerasi", "Tetralopha",
        "Popillia japonica", "Macrodactylus", "Otiorhynchus sulcatus", "Otiorhynchus ovatus", "Otiorhynchus rugosostriatus",
        "Agrotis", "Euxoa", "Peridroma saucia", "Mamestra configurata", "Spodoptera", "Helicoverpa zea", "Ostrinia nubilalis",
        "Limonius", "Ctenicera", "Agriotes", "Tipula", "Phyllophaga", "Hylemya", "Contarinia",
        "Forficula auricularia", "Melanoplus sanguinipes", "Melanoplus bivittatus", "Melanoplus differentialis",
        "Melanoplus femurrubrum", "Camnula pellucida", "Anabrus simplex", "Gryllus",
        "Frankliniella occidentalis", "Thrips tabaci", "Trialeurodes vaporariorum", "Bemisia",
        "Myzus persicae", "Brevicoryne brassicae", "Macrosiphum euphorbiae", "Aphis", "Eriosoma lanigerum",
        "Psila rosae", "Liriomyza", "Pegomya", "Cephus cinctus", "Oulema melanopus", "Mayetiola destructor",
        "Hypera postica", "Sitona", "Ceutorhynchus", "Phyllobius", "Popilius", "Tetranychus",
    ],
    "Insects - Forest & tree pests": [
        "Dendroctonus ponderosae", "Dendroctonus pseudotsugae", "Dendroctonus rufipennis", "Dendroctonus brevicomis",
        "Dendroctonus valens", "Ips pini", "Ips", "Scolytus", "Dryocoetes confusus", "Pityogenes",
        "Choristoneura freemani", "Choristoneura occidentalis", "Choristoneura fumiferana", "Orgyia pseudotsugata",
        "Lambdina fiscellaria", "Malacosoma disstria", "Malacosoma californicum", "Neodiprion", "Pikonema",
        "Pissodes strobi", "Pissodes", "Agrilus anxius", "Agrilus planipennis", "Agrilus", "Chrysobothris",
        "Saperda calcarata", "Monochamus", "Melanophila", "Phloeosinus", "Adelges cooleyi", "Adelges piceae",
        "Pineus", "Cinara", "Chionaspis pinifoliae", "Lepidosaphes ulmi", "Pulvinaria", "Physokermes",
        "Lymantria dispar", "Euproctis", "Nymphalis antiopa", "Corythucha", "Rhyacionia", "Eucosma",
        "Coleotechnites", "Zeiraphera", "Acleris gloverana", "Archips cerasivorana", "Phyllonorycter", "Dioryctria",
        "Xylotrechus", "Trichodes", "Enaphalodes",
    ],
    "Insects - House & pantry pests": [
        "Blattella germanica", "Periplaneta americana", "Blatta orientalis", "Lepisma saccharinum", "Thermobia domestica",
        "Plodia interpunctella", "Tineola bisselliella", "Tinea pellionella", "Sitotroga cerealella",
        "Tribolium", "Oryzaephilus surinamensis", "Stegobium paniceum", "Lasioderma serricorne", "Sitophilus",
        "Rhyzopertha dominica", "Dermestes", "Anthrenus", "Attagenus", "Trogoderma", "Tenebrio molitor",
        "Musca domestica", "Pollenia", "Fannia canicularis", "Calliphora", "Lucilia", "Phormia regina",
        "Drosophila melanogaster", "Megaselia", "Psychoda", "Sciaridae", "Liposcelis", "Reticulitermes", "Zootermopsis",
        "Leptoglossus", "Harmonia axyridis", "Hylotrupes bajulus", "Anobium punctatum", "Lyctus", "Ptinus",
        "Acheta domesticus", "Ceuthophilus", "Scutigera coleoptrata", "Armadillidium vulgare", "Porcellio scaber",
        "Monomorium pharaonis", "Lasius", "Tapinoma sessile",
    ],
    "Insects - Helpful insects": [
        "Coccinella septempunctata", "Coccinella", "Hippodamia convergens", "Hippodamia", "Harmonia axyridis",
        "Adalia bipunctata", "Cycloneda", "Stethorus", "Chilocorus", "Psyllobora",
        "Chrysoperla", "Chrysopa", "Hemerobius", "Micromus", "Syrphus", "Eupeodes", "Toxomerus", "Allograpta",
        "Eristalis tenax", "Sphaerophoria", "Aphidoletes aphidimyza", "Calosoma", "Carabus nemoralis", "Pterostichus melanarius",
        "Harpalus", "Cicindela", "Podisus maculiventris", "Perillus bioculatus", "Nabis", "Orius", "Geocoris", "Zelus",
        "Phymata", "Sinea", "Mantis religiosa", "Litaneutria minor", "Tenodera sinensis",
        "Bombylius major", "Promachus", "Efferia", "Tachina", "Trichogramma", "Aphidius", "Ichneumon",
        "Ophion", "Megarhyssa", "Bembix", "Sphex", "Ammophila", "Podalonia", "Philanthus",
        "Larinioides", "Pisaurina", "Pardosa",
        "Larinus minutus", "Larinus obtusus", "Cyphocleonus achates", "Aphthona", "Galerucella", "Mecinus janthinus",
        "Mecinus janthiniformis", "Rhinocyllus conicus", "Trichosirocalus", "Urophora", "Chrysolina", "Hylobius transversovittatus",
        "Agapeta zoegana", "Oberea erythrocephala", "Spurgia esulae", "Hyles euphorbiae",
    ],
    "Insects - Fly-fishing hatches": [
        "Pteronarcys californica", "Pteronarcys", "Hesperoperla pacifica", "Calineuria californica", "Claassenia sabulosa",
        "Isoperla", "Skwala", "Sweltsa", "Suwallia", "Malenka", "Zapada", "Capnia", "Taenionema", "Brachyptera",
        "Drunella grandis", "Drunella flavilinea", "Drunella doddsii", "Drunella coloradensis", "Ephemerella excrucians",
        "Ephemerella dorothea", "Ephemerella", "Baetis tricaudatus", "Baetis", "Callibaetis", "Tricorythodes",
        "Hexagenia limbata", "Ephemera simulans", "Epeorus", "Rhithrogena", "Heptagenia", "Cinygmula", "Paraleptophlebia",
        "Siphlonurus", "Isonychia", "Ameletus", "Timpanoga",
        "Dicosmoecus", "Hydropsyche", "Cheumatopsyche", "Arctopsyche", "Brachycentrus", "Rhyacophila", "Glossosoma",
        "Hesperophylax", "Limnephilus", "Lepidostoma", "Oecetis", "Helicopsyche", "Psychoglypha", "Onocosmoecus",
        "Chironomus", "Tipula", "Corydalus", "Sialis", "Anax junius", "Aeshna", "Hyalella", "Gammarus",
    ],
}

# shown in every insect page's Key facts when a library pest page covers it: scientific-name prefix -> pests-problems page slug
PEST_LINKS = {
    "Cydia pomonella": "insects-codling-moth",
    "Dendroctonus ponderosae": "insects-mountain-pine-beetle",
    "Orgyia pseudotsugata": "insects-douglas-fir-tussock-moth",
    "Choristoneura freemani": "insects-western-spruce-budworm",
    "Choristoneura occidentalis": "insects-western-spruce-budworm",
    "Malacosoma disstria": "insects-forest-tent-caterpillars",
    "Malacosoma": "insects-forest-tent-caterpillars",
    "Pissodes strobi": "insects-white-pine-weevil",
    "Agrilus anxius": "insects-bronze-birch-borer",
    "Saperda calcarata": "insects-poplar-borer",
    "Adelges cooleyi": "insects-cooley-spruce-gall-adelgid",
    "Chionaspis pinifoliae": "insects-pine-needle-scale",
    "Lepidosaphes ulmi": "insects-oystershell-scale",
    "Caliroa cerasi": "insects-pear-sawfly-or-pearslug",
    "Otiorhynchus": "insects-root-weevils",
    "Ips": "insects-engraver-beetles",
    "Tetranychus urticae": "insects-two-spotted-spider-mite",
    "Oligonychus ununguis": "insects-spruce-spider-mite",
    "Cinara": "insects-giant-conifer-aphids",
    "Pulvinaria": "insects-cottony-maple-scale",
    "Physokermes": "insects-spruce-bud-scale",
}

# genus entries normally take only the species most often seen in Montana (iNaturalist research-grade counts, place 16);
# these genera are taken whole (every named Montana species matters to people)
WHOLE_GENERA = {"Bombus", "Vespula", "Dolichovespula", "Latrodectus", "Dermacentor", "Ixodes", "Pteronarcys", "Malacosoma"}
TOP_N = {"Insects - Fly-fishing hatches": 2}   # per-genus cap by group (default 3)

# extra types used by 74_field_guide_to_local.py (pages moved in from the Field Guides)
EXTRA_GROUPS = ["Insects - Other insects & bugs", "Common weeds", "Vegetables", "Nearby - Plants", "Nearby - Fungi",
                "Nearby - Insects & spiders", "Nearby - Reptiles & amphibians", "Nearby - Mammals"]
