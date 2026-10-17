"""Build one field-guide file per species, merging every species source:
  - tempDocsInstalled/inaturalist (original library's iNaturalist set, re-pulled with photo attribution)
  - tempDocs/visual-id (newer research-grade iNaturalist pull, 2 passes)
  - tempDocsInstalled/team-species (original library write-ups; images from data/library/images)
  - tempDocsInstalled/usda-plants (USDA PLANTS profiles; images from data/library/images)
Duplicates are merged when they resolve to the same Wikipedia article (or same iNaturalist taxon id).
Text = full Wikipedia article from the offline ZIM (fallback: the iNaturalist/Wikipedia summary).
Writes _work/species_paths.json so the Wikipedia builder skips these articles.
"""
import glob, json, os, re, shutil, sqlite3, sys
from urllib.parse import unquote
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry
from zimlib import resolve, article_md, save_article_images, taxonomy, page_meta, ZIM_DATE

AIP = r"E:\AIPortable"
TI = os.path.join(AIP, "tempDocsInstalled")
TD = os.path.join(AIP, "tempDocs")
LIBIMG = os.path.join(AIP, "data", "library", "images")
W = os.path.join(RESEARCH, "_work")

GROUP_CAT = {"plants-general": "GP", "edible-plants": "GP", "trees": "GP", "medicinal-plants": "GP",
             "fungi-general": "GF", "mammals-general": "GM", "insects-general": "GI", "insects-beneficial": "GI",
             "insects-pest": "GI", "insects-stinging": "GI", "insects-medical": "GI", "arachnids-general": "GI",
             "reptiles-general": "GR", "reptiles-nonvenomous": "GR", "reptiles-turtles": "GR", "reptiles-lizards": "GR",
             "amphibians-general": "GR", "amphibians": "GR"}


def cat_from_tax(tax):
    k, c, p = tax.get("Kingdom", ""), tax.get("Class", ""), tax.get("Phylum", "") or tax.get("Division", "")
    clades = " ".join(tax.get("Clades", []))
    if "Plantae" in k or "Angiosperms" in clades or "Tracheophytes" in clades:
        return "GP"
    if "Fungi" in k or "Amoebozoa" in k or "Myxo" in c:
        return "GF"
    if c.startswith("Mammalia"):
        return "GM"
    if c.startswith("Aves"):
        return "GB"
    if c in ("Reptilia", "Amphibia", "Testudines", "Squamata", "Crocodilia", "Lepidosauria") or "Reptilia" in clades or "Testudines" in clades:
        return "GR"
    if c in ("Insecta", "Arachnida", "Chilopoda", "Diplopoda", "Entognatha", "Collembola"):
        return "GI"
    if c in ("Actinopterygii", "Chondrichthyes", "Malacostraca", "Gastropoda", "Bivalvia", "Cephalopoda", "Scyphozoa",
             "Hydrozoa", "Cubozoa", "Echinoidea", "Anthozoa", "Polychaeta") or "Actinopterygii" in clades or "Mollusca" in p or "Cnidaria" in p:
        return "GA"
    if "Arthropoda" in p:
        return "GI"
    if "Chordata" in p:
        return "GA"
    return None


TEAM_MAP = json.load(open(os.path.join(RESEARCH, "_work", "team_species_map.json"), encoding="utf-8"))


def norm_sci(s):
    t = s.replace("×", "x").split()
    if len(t) >= 4 and t[2] in ("var.", "subsp.", "ssp."):
        return " ".join(t[:4])
    return " ".join(t[:2])


def cat_from_wikicats(meta):
    cats = " | ".join(meta.get("wgCategories", []))
    for pat, code in [(r"Flora of|plants|trees of|Trees of|shrubs|Medicinal plants|Edible plants|herbs", "GP"),
                      (r"Fungi of|fungi|mushrooms|Lichens", "GF"), (r"Mammals of|mammals", "GM"), (r"Birds of|birds", "GB"),
                      (r"Reptiles of|Amphibians of|snakes|turtles|lizards|frogs|salamanders", "GR"),
                      (r"Fish of|fish|Crustaceans|Molluscs|jellyfish", "GA"),
                      (r"Insects of|Arachnids of|Spiders of|insects|spiders|beetles|moths|butterflies|Hemiptera|Hymenoptera|Diptera", "GI")]:
        if re.search(pat, cats):
            return code
    return None


def load_units():
    db = sqlite3.connect(f"file:{AIP}\\data\\library.db?mode=ro", uri=True)
    asset = {r[0]: (r[1], r[2]) for r in db.execute("select id, asset_dir, license from library_docs where asset_dir is not null")}
    units = []
    # A: original iNaturalist set
    for m in json.load(open(os.path.join(TI, "inaturalist", "manifest.json"), encoding="utf-8")):
        photos = []
        for p in m.get("photos", []):
            f = os.path.join(TI, "inaturalist", p["file"].replace("/", os.sep))
            if os.path.exists(f):
                photos.append({"path": f, "observation_url": p.get("observation_url"), "license": p.get("photo_license"),
                               "attribution": p.get("attribution"), "source": "iNaturalist"})
        if not photos and m["id"] in asset and asset[m["id"]][0]:
            d = os.path.join(LIBIMG, asset[m["id"]][0])
            for f in sorted(glob.glob(os.path.join(d, "*"))):
                photos.append({"path": f, "observation_url": None, "license": asset[m["id"]][1],
                               "attribution": "iNaturalist observer (per original library; individual attribution not recorded)",
                               "source": "iNaturalist"})
        desc = ""
        df = os.path.join(TI, "inaturalist", (m.get("description_file") or "").replace("/", os.sep))
        wiki_title = None
        if m.get("description_file") and os.path.exists(df):
            desc = open(df, encoding="utf-8", errors="replace").read()
            mm = re.search(r"Wikipedia:\s*https?://en\.wikipedia\.org/wiki/(.+)", desc)
            wiki_title = mm.group(1).strip() if mm else None
        units.append({"kind": "inat", "ids": [m["id"]], "common": m.get("common_name") or m["title"],
                      "sci": m.get("scientific_name"), "taxon_id": m.get("taxon_id"), "photos": photos, "desc": desc,
                      "wiki_title": wiki_title, "group": None})
    # B: visual-id
    for m in json.load(open(os.path.join(TD, "visual-id", "manifest.json"), encoding="utf-8")):
        photos = []
        for p in m.get("photos", []):
            f = os.path.join(TD, "visual-id", p["file"].replace("/", os.sep))
            if os.path.exists(f):
                photos.append({"path": f, "observation_url": p.get("observation_url"), "license": p.get("photo_license"),
                               "attribution": p.get("attribution"), "source": "iNaturalist"})
        desc = ""
        df = os.path.join(TD, "visual-id", (m.get("description_file") or "").replace("/", os.sep))
        if m.get("description_file") and os.path.exists(df):
            desc = open(df, encoding="utf-8", errors="replace").read()
        wt = (m.get("wikipedia_url") or "").split("/wiki/")[-1] or None
        units.append({"kind": "inat", "ids": [], "common": m.get("common_name"), "sci": m.get("scientific_name"),
                      "taxon_id": m.get("taxon_id"), "photos": photos, "desc": desc,
                      "wiki_title": unquote(wt) if wt else None, "group": m.get("group")})
    # C: team-species
    for m in json.load(open(os.path.join(TI, "team-species", "manifest.json"), encoding="utf-8")):
        photos = []
        if m["id"] in asset and asset[m["id"]][0]:
            for f in sorted(glob.glob(os.path.join(LIBIMG, asset[m["id"]][0], "*"))):
                photos.append({"path": f, "observation_url": None, "license": m.get("license"),
                               "attribution": "Image from the original library's team-species write-up (license as recorded: "
                                              + (m.get("license") or "unknown") + "; not independently verified)",
                               "source": "original library (team-species)"})
        tgt, tcode = TEAM_MAP.get(m["title"], [m["title"], None])
        units.append({"kind": "team", "ids": [m["id"]], "common": m["title"], "sci": None, "taxon_id": None,
                      "photos": photos, "desc": "", "wiki_title": tgt, "group": None, "code": tcode})
    # D: USDA PLANTS
    for m in json.load(open(os.path.join(TI, "usda-plants", "manifest.json"), encoding="utf-8")):
        txt = open(os.path.join(TI, "usda-plants", m["file"]), encoding="utf-8").read()
        first = txt.splitlines()[0]
        mm = re.match(r"#\s*(.+?)\s*\((.+)\)\s*$", first)
        sci = norm_sci(mm.group(2)) if mm else None
        body = "\n".join(l for l in txt.splitlines()[1:] if not l.startswith("Source:")).strip()
        photos = []
        if m["id"] in asset and asset[m["id"]][0]:
            for f in sorted(glob.glob(os.path.join(LIBIMG, asset[m["id"]][0], "*"))):
                photos.append({"path": f, "observation_url": None, "license": m.get("license"),
                               "attribution": "USDA NRCS PLANTS Database image (Public Domain as recorded by the original library)",
                               "source": "USDA PLANTS"})
        units.append({"kind": "usda", "ids": [m["id"]], "common": m["title"], "sci": sci, "taxon_id": None,
                      "photos": photos, "desc": "", "wiki_title": sci, "group": None,
                      "usda": {"symbol": m.get("symbol"), "url": m.get("source_url"), "text": body}})
    return units


def main():
    reg = SlugRegistry()
    units = load_units()
    print("units", len(units), flush=True)
    merged = {}
    for u in units:
        e = None
        for cand in [u.get("wiki_title"), u.get("sci"), u.get("common")]:
            if cand:
                e = resolve(cand)
                if e is not None:
                    break
        key = ("wiki:" + e.path) if e is not None else ("taxon:%s" % u["taxon_id"] if u.get("taxon_id") else "name:" + (u.get("sci") or u["common"]).lower())
        u["entry"] = e
        if key in merged:
            g = merged[key]
            g["members"].append(u)
        else:
            merged[key] = {"key": key, "entry": e, "members": [u]}
    # second pass: merge taxon-id duplicates that resolved to different keys
    by_taxon = {}
    for k, g in list(merged.items()):
        for u in g["members"]:
            if u.get("taxon_id"):
                if u["taxon_id"] in by_taxon and by_taxon[u["taxon_id"]] != k and k in merged:
                    merged[by_taxon[u["taxon_id"]]]["members"].extend(merged.pop(k)["members"])
                    break
                by_taxon.setdefault(u["taxon_id"], k)
    print("merged species", len(merged), flush=True)
    species_paths, out = [], []
    for key, g in merged.items():
        mem = g["members"]
        e = g["entry"]
        inat = [u for u in mem if u["kind"] == "inat"]
        sci = next((u["sci"] for u in inat if u.get("sci")), None) or next((u["sci"] for u in mem if u.get("sci")), None)
        common = next((u["common"] for u in inat if u.get("common")), None) or mem[0]["common"]
        if sci and re.search(r"virus", sci, re.I):
            continue
        tax = taxonomy(e) if e is not None else {}
        code = (next((GROUP_CAT[u["group"]] for u in mem if u.get("group") in GROUP_CAT), None)
                or next((u["code"] for u in mem if u.get("code")), None) or cat_from_tax(tax))
        if code is None and e is not None:
            code = cat_from_wikicats(page_meta(bytes(e.get_item().content).decode("utf-8", "replace")))
        if code is None:
            code = "GP" if any(u["kind"] == "usda" for u in mem) else "GI"
        category = CODES[code]
        common_disp = common[:1].upper() + common[1:] if common else sci
        if not sci and e is not None and " " in e.title and e.title[0].isupper() and e.title.split()[0].istitle() and e.title.split()[1].islower():
            sci = e.title
        title = f"{common_disp} ({sci})" if sci and sci.lower() != (common or "").lower() else common_disp
        slug = reg.claim(slugify(f"{common_disp} {sci or ''}"), key)
        d = cat_dir(category)
        img_dir = os.path.join(d, slug + "_images")
        # photos (dedupe by observation url / file)
        photos, seen = [], set()
        for u in mem:
            for p in u["photos"]:
                k2 = p.get("observation_url") or p["path"]
                if k2 in seen:
                    continue
                seen.add(k2)
                photos.append(p)
        photos = photos[:12]
        body = [f"# {title}\n"]
        photo_meta = []
        if photos:
            os.makedirs(img_dir, exist_ok=True)
            body.append("## Identification photos\n")
            for i, p in enumerate(photos):
                ext = os.path.splitext(p["path"])[1].lower() or ".jpg"
                fn = f"photo_{i + 1:02d}{ext}"
                dst = os.path.join(img_dir, fn)
                if not os.path.exists(dst):
                    shutil.copy2(p["path"], dst)
                cap = f"{title} - {p.get('attribution') or 'unknown photographer'}" + (f" ({p['license']})" if p.get("license") else "")
                body.append(f"![{cap}]({slug}_images/{fn})  ")
                body.append(f"*{p.get('source')}: {p.get('attribution') or ''}; license {p.get('license') or 'unrecorded'}"
                            + (f"; observation <{p['observation_url']}>" if p.get("observation_url") else "") + "*\n")
                photo_meta.append({"file": fn, "source": p.get("source"), "attribution": p.get("attribution"),
                                   "license": p.get("license"), "observation_url": p.get("observation_url")})
        wiki_meta, wiki_imgs = None, []
        if e is not None:
            art = article_md(e, max_images=25)
            md, wiki_imgs = save_article_images(art, img_dir, slug + "_images")
            rev = art["meta"].get("wgCurRevisionId")
            wiki_meta = {"title": e.title, "url": "https://en.wikipedia.org/wiki/" + e.path,
                         "revision_url": f"https://en.wikipedia.org/w/index.php?oldid={rev}" if rev else None,
                         "snapshot": f"Kiwix ZIM wikipedia_en_all_maxi_2026-08 ({ZIM_DATE})"}
            body.append("## Wikipedia article\n")
            body.append(re.sub(r"^\s*#\s.*\n", "", md))
            species_paths.append(e.path)
        else:
            desc = next((u["desc"] for u in mem if u.get("desc")), "")
            if desc:
                body.append("## Description\n")
                body.append("\n".join(l for l in desc.splitlines()[3:]).strip() or desc)
        usda = next((u["usda"] for u in mem if u.get("usda")), None)
        if usda:
            body.append("\n## USDA PLANTS profile\n")
            body.append(f"Source: USDA NRCS PLANTS Database - <{usda['url']}>\n")
            body.append(usda["text"])
        taxon_id = next((u["taxon_id"] for u in mem if u.get("taxon_id")), None)
        sources = []
        if taxon_id:
            sources.append({"name": "iNaturalist taxon", "url": f"https://www.inaturalist.org/taxa/{taxon_id}"})
        if wiki_meta:
            sources.append({"name": "Wikipedia", "url": wiki_meta["url"], "revision": wiki_meta["revision_url"]})
        if usda:
            sources.append({"name": "USDA NRCS PLANTS Database", "url": usda["url"]})
        body.append("\n## Sources\n")
        for s in sources:
            body.append(f"- {s['name']}: <{s['url']}>" + (f" (revision <{s['revision']}>)" if s.get("revision") else ""))
        if wiki_meta:
            body.append("- Wikipedia text: CC BY-SA 4.0, Wikipedia contributors; retrieved from " + wiki_meta["snapshot"])
        body.append("- Photos: individual photographer and license listed under each photo")
        meta = {"title": title, "category": category, "source_type": "species-profile",
                "common_name": common_disp, "scientific_name": sci,
                "taxonomy": {k: v for k, v in tax.items() if k != "Clades"},
                "inaturalist_taxon_id": taxon_id,
                "source_url": sources[0]["url"] if sources else None,
                "sources": sources,
                "license": "Mixed: Wikipedia text CC BY-SA 4.0; photos per-image (CC0 / CC BY / CC BY-SA via iNaturalist, or as noted); USDA content public domain",
                "photos": photo_meta, "wikipedia_images": wiki_imgs,
                "original_library_ids": sorted({i for u in mem for i in u["ids"]}),
                "merged_from": sorted({u["kind"] for u in mem}),
                "compiled": TODAY}
        open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + "\n".join(body).strip() + "\n")
        out.append({"slug": slug, "category": category, "title": title, "key": key, "n_photos": len(photo_meta)})
        if len(out) % 50 == 0:
            print(len(out), flush=True)
            reg.save()
    reg.save()
    json.dump(species_paths, open(os.path.join(W, "species_paths.json"), "w", encoding="utf-8"))
    json.dump(out, open(os.path.join(W, "built_species.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    import collections
    print("built", len(out), collections.Counter(o["category"] for o in out))


main()
