"""Montana Field Guide animals, fungi and grasses for the Local Area section (user request 2026-10-11:
vertebrates only, all grasses, named fungi only - no lichens).

  71_build_local_wildlife.py                    build everything (resumes: plants already downloaded are reused)
  71_build_local_wildlife.py --only grasses     one group: mammals | birds | fish | herps | fungi | grasses | insects
  71_build_local_wildlife.py --limit 5          first N of each group (testing)

Pages: local-area/wildlife/<slug>.md (animals, source_type local-wildlife), local-area/fungi/<slug>.md (local-wildlife),
local-area/plants/<slug>.md (grasses, local-profile, group 'Grasses'). Each page: Key facts for Kalispell (Montana status,
conservation rank, habitat, range), photos (Field Guide + iNaturalist exact-name), the Field Guide account
(description, habitat, food, reproduction, management...), range maps, the Field Guide PDF report, Wikipedia (offline
ZIM, checked to be about the species), links to the same species elsewhere in the library. Fungi pages carry an
edibility warning. Indexes: _work/local_area/mtfg_{animalia,fungi,plants}.json (from _mtfg_index.py / _mtfg_index_k.py).
Then runs 20_catalog.py + 21_readme.py.
"""
import glob, importlib.util, json, os, re, subprocess, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, slugify
import local_area as L

spec = importlib.util.spec_from_file_location("lab", os.path.join(os.path.dirname(__file__), "69_build_local_area.py"))
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)   # shared helpers (write_doc, wiki_section, ...)

D = B.D
GROUPS = {   # key -> (group name, folder, source_type)
    "mammals": ("Wildlife - Mammals", "wildlife", "local-wildlife"),
    "birds": ("Wildlife - Birds", "wildlife", "local-wildlife"),
    "fish": ("Wildlife - Fish", "wildlife", "local-wildlife"),
    "herps": ("Wildlife - Reptiles & amphibians", "wildlife", "local-wildlife"),
    "fungi": ("Fungi", "fungi", "local-wildlife"),
    "grasses": ("Grasses", "plants", "local-profile"),
}
import local_insects_specs as IS   # insects/spiders/ticks (user choice 2026-10-11: the 'useful set', ~830 species)
for _g in list(IS.PICKED) + [w[0] for w in IS.WHOLE]:
    GROUPS.setdefault(_g, (_g, "insects", "local-wildlife"))
INSECT = {g for g in GROUPS if g.startswith(("Insects", "Spiders"))}
PREFIX = {"AM": "mammals", "AB": "birds", "AF": "fish", "AR": "herps", "AA": "herps"}
FUNGI_WARNING = ("⚠ Never eat a wild mushroom identified from a description or photo. Several deadly Montana "
                 "species (e.g. Amanita, Galerina, false morels) look like edible ones. Have an expert check it in person.")
RANKS = {"1": "critically imperiled", "2": "imperiled", "3": "vulnerable", "4": "apparently secure", "5": "secure",
         "H": "possibly extirpated", "X": "presumed extirpated", "NA": "not applicable (introduced or accidental)",
         "U": "unrankable", "NR": "not ranked"}


def entries():
    """[(group key, elcode, common, scientific)] - species-level entries first, one page per common name."""
    W = L.W
    out = []
    a = json.load(open(os.path.join(W, "mtfg_animalia.json"), encoding="utf-8"))
    for code, (common, sci, fam) in a.items():
        g = PREFIX.get(code[:2])
        if g:
            out.append((g, code, common, sci))
    f = os.path.join(W, "mtfg_fungi.json")
    if os.path.exists(f):
        for code, (common, sci, fam) in json.load(open(f, encoding="utf-8")).items():
            # user choice: NAMED fungi only - no lichens (NL...), no "A Fungus" / "An Earth Star" placeholder names
            if code.startswith("NF") and not re.match(r"(A|An)\s", common):
                out.append(("fungi", code, common, sci))
    for code, (g, common, sci, fam) in insect_select(a).items():
        out.append((g, code, common, sci))
    for code, (common, sci, fam) in json.load(open(os.path.join(W, "mtfg_plants.json"), encoding="utf-8")).items():
        if fam == "Poaceae":
            out.append(("grasses", code, common, sci))
    out.sort(key=lambda e: (e[0], len(e[3].split()), e[2]))   # species before subspecies/varieties
    seen, res = set(), []
    for e in out:
        k = (e[0], e[2].lower())
        if k in seen or not e[3]:
            continue
        seen.add(k); res.append(e)
    return res


def inat_mt_counts(genus):
    """{scientific name: research-grade iNaturalist observations in Montana (place 16)} for one genus."""
    u = ("https://api.inaturalist.org/v1/observations/species_counts?place_id=16&quality_grade=research&per_page=200&taxon_name="
         + urllib.parse.quote(genus))
    try:
        return {x["taxon"]["name"].lower(): x["count"] for x in json.loads(L.fetch(u))["results"]}
    except Exception as e:
        print("  inat counts failed", genus, e)
        return {}


def insect_select(a):
    """{elcode: (group, common, scientific, family)} from local_insects_specs: whole groups (butterflies, dragonflies, big
    moths) + the hand-picked list. A genus pick takes every species only for IS.WHOLE_GENERA; otherwise the 3 (fly-fishing
    2) most-observed in Montana."""
    named = {k: v for k, v in a.items() if k[0] == "I" and not re.match(r"(A|An) ", v[0])}
    out = {}
    for g, pre, fam in IS.WHOLE:
        for k, v in named.items():
            if (pre and k.startswith(pre)) or (fam and v[2] == fam):
                out.setdefault(k, g)
    for g, picks in IS.PICKED.items():
        for p in picks:
            hits = [k for k, v in named.items() if v[1] == p or v[2] == p or (" " not in p and v[1].split()[0] == p)]
            if " " in p or p in IS.WHOLE_GENERA or len(hits) <= 1:
                take = hits
            else:
                c = inat_mt_counts(p)
                hits.sort(key=lambda k: -c.get(named[k][1].lower(), 0))
                take = [k for i, k in enumerate(hits[:IS.TOP_N.get(g, 3)]) if i == 0 or c.get(named[k][1].lower(), 0) > 0]
            for k in take:
                out.setdefault(k, g)
    return {k: (g,) + tuple(named[k]) for k, g in out.items()}


def pest_link(sci, fdir):
    """The MSU pest-guide page in pests-problems/ covering this species, if any."""
    for pre, slug in sorted(IS.PEST_LINKS.items(), key=lambda x: -len(x[0])):
        if sci == pre or sci.startswith(pre + " "):
            f = os.path.join(D, "pests-problems", slug + ".md")
            if os.path.exists(f):
                return f"[{slug[len('insects-'):].replace('-', ' ').capitalize()} (MSU pest guide)]({B.rel(f, fdir)})"
    return None


def library_twins():
    """scientific name -> library .md path for species already in the field guides (to link them)."""
    out = {}
    for f in glob.glob(os.path.join(RESEARCH, "field-guide-*", "*.md")):
        head = open(f, encoding="utf-8").read(3000)
        m = re.search(r'^scientific_name: "(.*)"', head, re.M)
        if m:
            out.setdefault(m.group(1).lower(), f)
    return out


def rank_text(r):
    m = re.match(r"([GS])(\w+)", r or "")
    if not m:
        return r or ""
    core = m.group(2)
    key = next((k for k in ("NA", "NR", "X", "H", "U") if core.startswith(k)), core[:1])
    return f"{r} ({RANKS.get(key, '')})"


def gather(g, code, common, sci, slug, img_dir):
    cache = os.path.join(L.W, "wild", slug + ".json")
    if os.path.exists(cache):
        return json.load(open(cache, encoding="utf-8"))
    os.makedirs(img_dir, exist_ok=True)
    d = {"photos": [], "sources": [], "lic": []}
    try:
        mt = L.mtfg_species(code, img_dir, "")
        d["mtfg"] = mt
        d["sources"].append(("Montana Field Guide", mt["url"]))
        d["photos"] += [{"file": x["file"], "credit": f"Montana Field Guide - {x['photographer'] or x['copyright']}"} for x in mt["photos"][:8]]
        d["lic"].append("Montana Field Guide: " + B.MTFG_LICENSE)
        for f_ in ("mtfg_annualchart.png", "mtfg_elevchart_fs.png"):   # charts the page does not show
            if os.path.exists(os.path.join(img_dir, f_)):
                os.remove(os.path.join(img_dir, f_))
        mt["maps"] = [m for m in mt["maps"] if "chart" not in m["file"]]
        for x in mt["photos"][8:]:   # keep only what the page shows
            p = os.path.join(img_dir, x["file"])
            if os.path.exists(p):
                os.remove(p)
    except Exception as e:
        print("  mtfg failed", common, e)
    base = re.sub(r"\s+(ssp\.|var\.|subsp\.).*", "", sci)
    if len(d["photos"]) < 4 and " " in base:
        try:
            t, ph = L.inat_photos(base, img_dir)
            if t:
                d["sources"].append(("iNaturalist", f"https://www.inaturalist.org/taxa/{t['id']}"))
                d["photos"] += [{"file": x["file"], "credit": f"iNaturalist: {x['attribution']} ({x['license']})"} for x in ph]
                d["lic"].append("iNaturalist photos: per photo (CC licenses as noted)")
        except Exception as e:
            print("  inat failed", common, e)
    try:
        p = {"base": base, "sci": sci}
        md, w = B.wiki_section(base, img_dir, slug + "_images", p)
        if w:
            d["wiki_md"], d["wiki"] = md, w
            d["sources"].append(("Wikipedia", w["url"]))
            d["lic"].append("Wikipedia text: CC BY-SA 4.0 (offline Kiwix archive)")
    except Exception as e:
        print("  wiki failed", common, e)
    if "wiki_md" not in d and g in INSECT:   # many small insects have no article - use the genus article instead
        try:
            e_ = genus_article(base.split()[0])
            if e_ is not None:
                md, w = B.wiki_section(e_.path.replace("_", " "), img_dir, slug + "_images")
                if w:
                    d["wiki_md"], d["wiki"], d["wiki_genus"] = md, w, True
                    d["sources"].append(("Wikipedia (genus)", w["url"]))
                    d["lic"].append("Wikipedia text: CC BY-SA 4.0 (offline Kiwix archive)")
        except Exception as e:
            print("  genus wiki failed", common, e)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return d


BUGWORDS = re.compile(r"\b(insects?|beetles?|flies|fly|moths?|butterfl\w+|spiders?|ticks?|mites?|bees?|wasps?|ants?|bugs?|aphids?|"
                      r"mayfl\w+|stonefl\w+|caddisfl\w+|dragonfl\w+|damselfl\w+|weevils?|crickets?|grasshoppers?|arachnids?|sawfl\w+|midges?|lacewings?)\b")


def genus_article(genus):
    """Wikipedia article for an insect/arachnid genus - only if its taxobox says Arthropoda (not e.g. 'Ips' the unit) and it is
    not a disambiguation page."""
    from zimlib import resolve
    for t in (genus, f"{genus} (genus)", f"{genus} (insect)", f"{genus} (beetle)", f"{genus} (fly)", f"{genus} (moth)", f"{genus} (spider)"):
        e = resolve(t)
        if e is None:
            continue
        raw = bytes(e.get_item().content)[:80000].decode("utf-8", "replace").lower()
        if "disambiguation" in raw[:6000]:   # e.g. Tribolium (the beetle genus and a plant genus)
            continue
        head = re.sub(r"<[^>]+>", " ", raw)
        if "arthropoda" in head and genus.lower() in head and (BUGWORDS.search(head) or "genus" in head):
            return e
    return None


EMPTY = re.compile(r"^(We do not yet have descriptive information|Shropshire and Tallamy \(20\d\d\) provide a link)", re.I)


def short(text, n):
    """Up to n characters, ending at a sentence (or word) boundary."""
    text = tidy(text)
    if len(text) <= n:
        return text
    cut = text[:n]
    i = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:i + 1] if i > n * 0.4 else cut.rsplit(" ", 1)[0] + " …")


def tidy(text):
    text = re.sub(r"\b(HGCN|HOPC|HOC)\b", "", text)
    text = re.sub(r"\s*\(Lesica et al\..*?\)\.?", ".", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def build(g, code, common, sci, slug, twins):
    group, folder, stype = GROUPS[g]
    kind = "fungi" if folder == "fungi" else "plants" if folder == "plants" else "animals"
    group = L.type_overrides().get(f"{B.CAT}/{folder}/{slug}.md", group)   # the user's own choice (Change type...)
    fdir = os.path.join(D, folder)
    img = slug + "_images"
    d = gather(g, code, common, sci, slug, os.path.join(fdir, img))
    mt = d.get("mtfg") or {}
    f = dict(mt.get("facts", {}))
    if mt:
        try:
            f["Status"] = L.mtfg_status(code)   # re-read: older caches hold a wrong 'Noxious Weed'
        except Exception as e:
            print("  status failed", common, e)
    s = {k: v for k, v in mt.get("sections", {}).items() if not EMPTY.match(tidy(v))}   # Field Guide placeholder text
    wiki = d.get("wiki_md") or ""
    rows = []
    status = f.get("Status") or ""
    rows.append(("In Montana", status or "listed in the Montana Field Guide"))
    if f.get("State Rank"):
        rows.append(("Montana conservation rank", rank_text(f["State Rank"]) + (f"; global {rank_text(f['Global Rank'])}" if f.get("Global Rank") else "")))
    if kind == "fungi":
        rows.insert(0, ("⚠ EDIBILITY", FUNGI_WARNING))
    if s.get("Habitat"):
        rows.append(("Montana habitat", short(s["Habitat"], 450)))
    if s.get("Range Comments"):
        rows.append(("Range", short(s["Range Comments"], 350)))
    if s.get("Migration"):
        rows.append(("Migration", short(s["Migration"], 350)))
    if s.get("Food Habits"):
        rows.append(("Food", short(s["Food Habits"], 350)))
    if kind != "animals":   # plants and fungi: can it be eaten / is it poisonous
        tox = L.sentences(wiki, r"\b(toxic|poison\w*|edible|deadly|inedible)\b", n=2, maxlen=300)
        label_ = "Edibility (Wikipedia)"
    else:   # animals: only real hazards to people (not 'lead poisoning kills eagles')
        pat = r"\b(venomous|venom\b|attacks? (on )?(humans|people)|dangerous to (humans|people)|fatal to humans|bites? (can|may) )"
        if g in INSECT:   # bugs: stings, disease carriers, allergic reactions
            pat = pat[:-1] + r"|stings? (can|may|are|is)|painful sting|allergic|anaphyla\w+|transmits?|vectors? of|carr(y|ies) (the )?(disease|bacteri\w+|virus)|West Nile|Lyme|spotted fever|tularemia)"
        tox = L.sentences(wiki, pat, n=6 if g in INSECT else 2, maxlen=300)
        if g in INSECT:   # not radio 'transmitters', plant-virus 'vectors', or 'not to be confused with venomous...'
            tox = [x for x in tox if not re.search(r"transmitters?|confused (with|for)|resembles", x, re.I)
                   and (re.search(r"\b(humans?|people|person|skin|allerg\w+|pain\w*|sting\w*|bites?|fever|tularemia|Lyme|West Nile|plague|encephalitis)\b", x, re.I)
                        or not re.search(r"\b(plants?|crops?|trees?|pepper|potato\w*|pests?|fruit)\b", x, re.I))][:2]
        label_ = "Danger to people (Wikipedia)"
    if tox:
        rows.append((label_, " ".join(f"“{x}”" for x in tox)))
    if g in INSECT:
        pl = pest_link(sci, fdir)
        if pl:
            rows.append(("Control & damage", pl))
    twin = twins.get(re.sub(r"\s+(ssp\.|var\.|subsp\.).*", "", sci).lower())
    if twin:
        rows.append(("Also in your library", f"[{os.path.splitext(os.path.basename(twin))[0].replace('-', ' ').title()}]({B.rel(twin, fdir)})"))
    out = [f"# {common}\n\n*{sci}*  \nType: {group}\n",
           B.facts_table(rows)]
    if kind == "fungi":
        out.append(f"> {FUNGI_WARNING}\n")
    if d["photos"]:
        out.append("## Photos\n\n" + "\n\n".join(f"![{common} - {x['credit']}]({img}/{x['file']})  \n*{x['credit']}*" for x in d["photos"][:12]) + "\n")
    if s or mt.get("maps"):
        order = ["General Description", "Species Description", "Diagnostic Characteristics", "Diagnostic Characteristics of Tracks",
                 "Similar Species", "Phenology", "Migration", "Habitat", "Food Habits", "Ecology", "Reproductive Characteristics",
                 "Management", "Ethnobotany", "Invasive Status", "Origin of this species in Montana", "Hunting", "Fishing"]
        part = [f"### {k}\n\n{tidy(s[k])}" for k in order if s.get(k)]
        maps = "\n\n".join(f"![{m['caption']}]({img}/{m['file']})  \n*{m['caption']} (Montana Field Guide)*" for m in mt.get("maps", [])[:3])
        reps = ([f"- [Montana Field Guide species report (PDF)]({img}/{mt['report']})"] if mt.get("report") else []) + \
               ([f"- [Montana conservation status report (PDF)]({img}/{mt['rank_report']})"] if mt.get("rank_report") else [])
        out.append("## Montana Field Guide\n\n" + "\n\n".join(part) + ("\n\n### Range maps\n\n" + maps if maps else "")
                   + ("\n\n" + "\n".join(reps) if reps else "") + f"\n\nSource: {mt.get('url', '')}\n")
    if wiki and d.get("wiki_genus"):
        out.append(f"## Wikipedia: {d['wiki']['title']} (the genus)\n\n*Wikipedia has no article on {common} itself - this is "
                   f"the article on its genus, which covers its close relatives too.*\n\n{wiki}\n")
    elif wiki:
        out.append(f"## Wikipedia: {d['wiki']['title']}\n\n{wiki}\n")
    out.append("## Sources\n\n" + "\n".join(f"- {n}: <{u}>" for n, u in d["sources"]) + "\n\nLicenses: " + "; ".join(dict.fromkeys(d["lic"])) + "\n")
    meta = {"title": common, "category": B.CAT, "source_type": stype, "group": group, "scientific_name": sci,
            "plant_type": ("noxious" if "Noxious" in status else "introduced" if "Non-native" in status else "native") if kind == "plants" else None,
            "mtfg_elcode": code, "source_url": mt.get("url") or f"{L.MTFG}speciesDetail.aspx?elcode={code}",
            "sources": [{"name": n, "url": u} for n, u in d["sources"]], "license": "Mixed - see Sources",
            "key_facts": {a: re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", b) for a, b in rows},
            "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    if mt.get("report"):
        meta["file"] = f"{img}/{mt['report']}"
    meta = {k: v for k, v in meta.items() if v is not None}
    B.write_doc(os.path.join(fdir, slug + ".md"), meta, "", "\n".join(out))


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1] if "--only" in a else None
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else None
    twins = library_twins()
    taken = {p["slug"] for p in B.parse_table()}   # pages from your plant list (e.g. Cheatgrass) - not built twice
    count = {}
    for g, code, common, sci in entries():
        if only and g != only and not (only == "insects" and g in INSECT):
            continue
        count[g] = count.get(g, 0) + 1
        if limit and count[g] > limit:
            continue
        slug = slugify(common)
        if g in INSECT and os.path.exists(os.path.join(D, "wildlife", slug + ".md")):   # same common name as a vertebrate
            slug += "-insect"
        if g == "grasses" and slug in taken:   # e.g. Cheatgrass already has a (noxious weed) page
            continue
        try:
            build(g, code, common, sci, slug, twins)
            print(f"  {GROUPS[g][1]}/{slug}.md", flush=True)
        except Exception as e:
            print(f"  FAILED {common}: {e}", flush=True)
    print("counts:", count)
    for s in ("20_catalog.py", "21_readme.py"):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), s)])


if __name__ == "__main__":
    main()
