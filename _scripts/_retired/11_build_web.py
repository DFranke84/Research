"""Build source files for the web-page / text sources:
  - US gov web pages (MedlinePlus, CDC, CISA, EPA, FTC, NIH, NWS, Ready.gov, USFA, Energy Star)
  - NCHFP (National Center for Home Food Preservation) pages
  - Kiwix "Field Guide" documents (each a separate publication; see kiwix_decisions.txt)
  - WikEM emergency-medicine articles (HTML + images)
  - FEMA/Ready.gov Emergency Supply Kit Checklist (PDF)
Relevance/category decisions are encoded below and in _work/kiwix_decisions.txt.
"""
import json, os, re, shutil, sys
from bs4 import BeautifulSoup
from markdownify import markdownify
sys.path.insert(0, os.path.dirname(__file__))
from common import CODES, RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry

TI = r"E:\AIPortable\tempDocsInstalled"
TD = r"E:\AIPortable\tempDocs"
W = os.path.join(RESEARCH, "_work")

PUBLISHERS = {
    "medlineplus": "MedlinePlus - US National Library of Medicine (NIH)",
    "cdc": "US Centers for Disease Control and Prevention (CDC)",
    "cisa": "US Cybersecurity and Infrastructure Security Agency (CISA)",
    "epa": "US Environmental Protection Agency (EPA)",
    "ftc": "US Federal Trade Commission (FTC)",
    "nih": "US National Institutes of Health / MedlinePlus Medical Encyclopedia",
    "nws": "US National Weather Service (NOAA)",
    "readygov": "Ready.gov - US Federal Emergency Management Agency (FEMA)",
    "usfa": "US Fire Administration (FEMA)",
    "energystar": "ENERGY STAR (US EPA / DOE)",
    "nchfp": "National Center for Home Food Preservation (University of Georgia / USDA NIFA)",
}
DEFAULT_CAT = {"medlineplus": "MC", "cdc": "MC", "cisa": "SD", "epa": "EM", "ftc": "LF", "nih": "MA",
               "nws": "EM", "readygov": "EM", "usfa": "EM", "energystar": "EP", "nchfp": "FS"}

DROP = {
    "medlineplus": {"cosmetics", "tanning", "nuclear-scans", "neuroblastoma", "oral-cancer", "throat-cancer",
                    "mesothelioma", "health-checkup", "kidney-cysts", "dialysis", "veterans-and-military-health",
                    "occupational-health", "hiv-in-women", "heart-disease-in-women", "juvenile-arthritis",
                    "interstitial-lung-diseases", "pneumocystis-infections", "diabetic-kidney-problems"},
    "cdc": {"cdc-covid-19", "cdc-rsv"},
    "cisa": {"cisa-election-security", "cisa-critical-infrastructure-security"},
    "epa": {"epa-safer-chemical-choice", "epa-epa-emergency-response"},
    "nws": {"nws-events-calendar", "nws-lightning-espanol"},
    "readygov": {"mass-gathering-incidents"},
    "usfa": {"usfa-hotel-fires", "usfa-houses-of-worship", "usfa-college-students", "usfa-construction-sites",
             "usfa-prevent-youth-firesetting", "usfa-fief", "usfa-holiday", "usfa-boats-and-marinas",
             "usfa-vacant-abandoned-buildings", "usfa-hoarding"},
}
CAT = {
    "medlineplus": {
        **{k: "MA" for k in ["animal-bites", "bleeding", "blisters", "burns", "choking", "cpr", "dislocations", "drowning",
                             "electrical-injuries", "eye-injuries", "fainting", "first-aid", "fractures", "frostbite",
                             "head-injuries", "heat-illness", "hypothermia", "insect-bites-and-stings", "poisoning", "shock",
                             "spider-bites", "sprains-and-strains", "tick-bites", "wounds-and-injuries", "concussion",
                             "ankle-injuries-and-disorders", "nose-injuries-and-disorders", "spinal-cord-injuries",
                             "sports-injuries", "sun-exposure", "carbon-monoxide-poisoning", "dehydration", "seizures",
                             "heart-attack", "sudden-cardiac-arrest", "anaphylaxis", "opioid-overdose", "mosquito-bites",
                             "chest-pain", "breathing-problems", "traumatic-brain-injury", "after-surgery", "pressure-sores"]},
        **{k: "MP" for k in ["antibiotics", "antibiotic-resistance", "medicines", "drug-reactions", "vaccines",
                             "tetanus-diphtheria-and-pertussis-vaccines", "oxygen-therapy"]},
        "germs-and-hygiene": "SH", "drinking-water": "W", "water-pollution": "W", "food-safety": "FS",
        "disaster-preparation-and-recovery": "EM", "winter-weather-emergencies": "EM", "tsunamis": "EM",
        "radiation-exposure": "CB", "biodefense-and-bioterrorism": "CB", "arsenic": "CB", "asbestos": "CB", "molds": "SH",
    },
    "cdc": {"cdc-carbon-monoxide-poisoning": "MA", "cdc-chemical-emergencies": "CB", "cdc-drinking-water-safety": "W",
            "cdc-emergency-preparedness-and-response": "EM", "cdc-handwashing": "SH", "cdc-heat-and-your-health": "MA",
            "cdc-mosquito-bites-and-prevention": "SH", "cdc-radiation-health": "CB", "cdc-ticks-and-tick-borne-diseases": "MC",
            "cdc-healthy-pets-healthy-people": "SH"},
    "cisa": {"cisa-emergency-communications": "CR"},
    "epa": {"epa-drinking-water": "W", "epa-private-wells": "W", "epa-water-emergencies-resilience": "W",
            "epa-household-hazardous-waste": "CB", "epa-radon": "CB", "epa-lead": "SH", "epa-lead-exposure-reduction": "SH",
            "epa-carbon-monoxide-indoor-air": "MA", "epa-air-quality": "WX", "epa-airnow-air-quality-index": "WX"},
    "nws": {"nws-airquality": "WX", "nws-heat-index": "WX", "nws-space": "WX", "nws-drought": "WX", "nws-heat-illness": "MA",
            "nws-beach-ripcurrents-hazards": "WS", "nws-ripcurrent-toolkit": "WS", "nws-beach": "WS", "nws-lightning-struck": "MA"},
    "readygov": {"food-storage": "FS", "water-storage": "W", "storing-water-in-plastic-soda-bottles": "W",
                 "cybersecurity": "SD", "financial-preparedness": "LF", "radiation-emergencies": "CB",
                 "biological-hazards": "CB", "hazardous-materials-incidents": "CB", "household-chemical-emergencies": "CB",
                 "explosions": "CB", "safety-skills": "MA", "coping-with-disaster": "MC", "space-weather": "WX",
                 "emergency-alerts": "CR"},
    "usfa": {"usfa-burns-first-aid-911": "MA", "usfa-home-hazardous-materials": "CB", "usfa-electric-vehicles": "MV",
             "usfa-recreational-vehicles": "MV", "usfa-vehicle-fires": "MV", "usfa-road-safety": "MV"},
}
NAV_JUNK = {"Learn More", "See, Play and Learn", "Resources", "For You", "Start Here", "Diagnosis and Tests",
            "Prevention and Risk Factors", "Treatments and Therapies", "Related Issues", "Specifics", "Genetics",
            "Images", "Videos and Tutorials", "Test Your Knowledge", "Statistics and Research", "Clinical Trials",
            "Journal Articles", "Find an Expert", "Children", "Teenagers", "Men", "Women", "Seniors", "Patient Handouts",
            "Skip navigation", "Summary", "Living With"}
SPANISH_RE = re.compile(r"(-spanish$|^el-secado|^la-congelacion|^congelacion|^papas-y-batatas)")


def read_md(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    lines = txt.splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else None
    body = "\n".join(l for l in lines[1:] if not l.startswith("Source: ") and l.strip() not in NAV_JUNK).strip()
    return title, body


def write_doc(reg, category, slug_base, owner, meta, body_md, assets=None):
    slug = reg.claim(slug_base, owner)
    d = cat_dir(category)
    if assets:
        adir = os.path.join(d, slug + "_images")
        os.makedirs(adir, exist_ok=True)
        for src, name in assets:
            dst = os.path.join(adir, name)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
        body_md = body_md.replace("__IMGDIR__", slug + "_images")
    meta = {"title": meta["title"], "category": category, **{k: v for k, v in meta.items() if k != "title"}, "compiled": TODAY}
    head = f"# {meta['title']}\n\n**Source:** {meta.get('publisher') or ''}" + (f" - <{meta['source_url']}>" if meta.get("source_url") else "") + \
           f"  \n**License:** {meta.get('license')}\n"
    open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + head + "\n" + body_md.strip() + "\n")
    return slug


def build_gov(reg, out):
    for src in list(PUBLISHERS):
        mf = os.path.join(TI, src, "manifest.json")
        if not os.path.exists(mf):
            continue
        for m in json.load(open(mf, encoding="utf-8")):
            stem = os.path.splitext(m["file"])[0]
            short = stem[len("nchfp-"):] if src == "nchfp" else stem
            path = os.path.join(TI, src, m["file"])
            if not os.path.exists(path) or short in DROP.get(src, ()) or (src == "nchfp" and SPANISH_RE.search(short)):
                continue
            title, body = read_md(path)
            if len(body.split()) < 40:
                continue
            title = re.sub(r"^(NCHFP|CDC|CISA|EPA|FTC|NIH|NWS|USFA|DOE)\s+", "", title or m["title"]).strip()
            if src == "nwd":
                pass
            code = CAT.get(src, {}).get(short, DEFAULT_CAT[src])
            category = CODES[code]
            prefix = {"medlineplus": "medlineplus", "cdc": "cdc", "cisa": "cisa", "epa": "epa", "ftc": "ftc", "nih": "nih-medlineplus",
                      "nws": "nws", "readygov": "ready-gov", "usfa": "usfa", "energystar": "energy-star", "nchfp": "nchfp"}[src]
            lic = m.get("license") or "Public Domain (US Government work)"
            if src == "nchfp":
                lic = "NCHFP content (University of Georgia / USDA-funded); educational use - verify before redistribution"
            meta = {"title": title if src != "nchfp" else f"{title} (NCHFP)",
                    "source_type": "web-page", "publisher": PUBLISHERS[src], "source_url": m.get("source_url"),
                    "license": lic, "original_library_ids": [m["id"]],
                    "provenance": f"AIPortable tempDocsInstalled/{src}/{m['file']} (re-fetched 2026-09-13 via trafilatura)"}
            slug = write_doc(reg, category, slugify(f"{prefix}-{short.replace(prefix + '-', '')}"), f"{src}:{m['id']}", meta, body)
            out.append({"src": src, "category": category, "slug": slug, "title": meta["title"]})


def build_kiwix(reg, out):
    dec = {}
    for l in open(os.path.join(W, "kiwix_decisions.txt"), encoding="utf-8"):
        if l.startswith("#") or not l.strip():
            continue
        p = l.rstrip("\n").split("|")
        dec[p[0]] = p[1:]
    man = {os.path.splitext(m["file"])[0].replace("-field-guide", ""): m for m in json.load(open(os.path.join(TI, "kiwix", "manifest.json"), encoding="utf-8"))}
    for stem, d in dec.items():
        if d[0] == "X":
            continue
        m = man[stem]
        _, body = read_md(os.path.join(TI, "kiwix", m["file"]))
        body = re.sub(r"\s*-- \d+ of \d+ --\s*", "\n\n", body)
        meta = {"title": d[2], "source_type": "document",
                "publisher": "Kiwix offline 'Field Guide' collection (original publisher named in title)",
                "source_url": None, "license": "Varies by document (not recorded); treat as all-rights-reserved unless the document states otherwise",
                "original_library_ids": [m["id"]], "original_library_title": m["title"],
                "provenance": "Text extracted from an offline Kiwix ZIM 'Field Guide' collection by the original library builder; "
                              f"exported from AIPortable library.db to tempDocsInstalled/kiwix/{m['file']}. Exact ZIM file not recorded."}
        slug = write_doc(reg, CODES[d[0]], d[1], f"kiwix:{m['id']}", meta, body)
        out.append({"src": "kiwix", "category": CODES[d[0]], "slug": slug, "title": d[2]})


WIKEM_CAT = {"tick-borne-illnesses": "MC", "sepsis": "MC", "diabetic-ketoacidosis": "MC", "hypoglycemia": "MC", "rabies": "MC"}
WIKEM_DROP = {"massive-transfusion-protocol"}


def build_wikem(reg, out):
    base = os.path.join(TD, "wikem-emergency-medicine")
    for m in json.load(open(os.path.join(base, "manifest.json"), encoding="utf-8")):
        stem = os.path.splitext(m["file"])[0]
        if stem in WIKEM_DROP:
            continue
        html = open(os.path.join(base, m["file"]), encoding="utf-8").read()
        soup = BeautifulSoup(html, "lxml")
        for t in soup.select("#toc, .mw-editsection, script, style"):
            t.decompose()
        by_url = {i["source_url"]: i["file"] for i in m.get("images", []) if i.get("source_url")}
        assets, img_meta = [], []
        for img in soup.find_all("img"):
            rel = by_url.get(img.get("src", ""))
            local = os.path.join(base, rel.replace("/", os.sep)) if rel else None
            if local and os.path.exists(local):
                name = os.path.basename(local)
                assets.append((local, name))
                img_meta.append({"file": name, "source_url": img["src"], "license": "CC BY-SA 4.0 (WikEM) unless noted on source"})
                img["src"] = f"__IMGDIR__/{name}"
            else:
                img.decompose()
        md = markdownify(str(soup), heading_style="ATX")
        md = re.sub(r"\n{3,}", "\n\n", md)
        code = WIKEM_CAT.get(stem, "MA")
        meta = {"title": f"{m['title']} (WikEM)", "source_type": "wiki-article",
                "publisher": "WikEM - The Global Emergency Medicine Wiki (wikem.org)", "source_url": m["source_url"],
                "license": "CC BY-SA 4.0 (attribution: WikEM contributors; share-alike)",
                "images": img_meta,
                "provenance": f"AIPortable tempDocs/wikem-emergency-medicine/{m['file']} (MediaWiki API action=parse, fetched 2026-09-13)"}
        slug = write_doc(reg, CODES[code], slugify("wikem-" + stem), f"wikem:{stem}", meta, md, assets)
        out.append({"src": "wikem", "category": CODES[code], "slug": slug, "title": meta["title"]})


def build_fema_checklist(reg, out):
    src = os.path.join(TI, "fema", "emergency-supply-kit-checklist.pdf")
    import pymupdf
    text = "\n".join(p.get_text() for p in pymupdf.open(src))
    slug = reg.claim("ready-gov-emergency-supply-kit-checklist", "fema:libdb_2434")
    d = cat_dir("emergency-preparedness")
    shutil.copy2(src, os.path.join(d, slug + ".pdf"))
    meta = {"title": "Emergency Supply Kit Checklist (Ready.gov / FEMA)", "category": "emergency-preparedness", "source_type": "pdf",
            "file": slug + ".pdf", "publisher": PUBLISHERS["readygov"],
            "source_url": "https://www.ready.gov/sites/default/files/2021-02/ready_checklist.pdf",
            "license": "Public Domain (US Government work)", "original_library_ids": ["libdb_2434"],
            "text_layer": len(text.strip()) > 100,
            "provenance": "AIPortable tempDocsInstalled/fema/emergency-supply-kit-checklist.pdf", "compiled": TODAY}
    body = f"# {meta['title']}\n\n**Source:** {meta['publisher']} - <{meta['source_url']}>  \n**License:** {meta['license']}  \n" \
           f"**Original file:** [{slug}.pdf]({slug}.pdf)\n\n## Full text\n\n" + (text.strip() or "_No text layer (graphical checklist); see the PDF._")
    open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write(front_matter(meta) + body + "\n")
    out.append({"src": "fema", "category": "emergency-preparedness", "slug": slug, "title": meta["title"]})


def main():
    reg = SlugRegistry()
    out = []
    build_gov(reg, out)
    build_kiwix(reg, out)
    build_wikem(reg, out)
    build_fema_checklist(reg, out)
    reg.save()
    json.dump(out, open(os.path.join(W, "built_web.json"), "w", encoding="utf-8"), indent=1)
    import collections
    print(len(out), collections.Counter(o["src"] for o in out))


main()
