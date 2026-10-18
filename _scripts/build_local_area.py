"""Build Local Area - make the library's Local Area section for where YOU live.

Asks where you are (a town or address, or a position) and how far around it to look, then builds:
  * Start Here - frost dates, growing season, monthly weather and the hardiness zone for that spot
    (from 30 years of weather records, Open-Meteo; the official USDA zone too when a US ZIP code is known)
  * species pages - the plants, birds, mammals, fish, reptiles & amphibians, insects, spiders and fungi actually
    seen near you (iNaturalist research-grade sightings), with photos, the months they are seen, and the
    Wikipedia article
  * US only: USGS topographic maps (GeoPDFs - the maps Waypoints opens)
  * AIPortable (if it sits next to the library): a 'My area' region in its offline map download list
Everything goes into <library>\\local-area. Safe to stop and run again: finished pages are skipped.

  Build Local Area.bat                         asks the questions
  build_local_area.py --place "Asheville, NC" --radius 50 --per-group 100 [--maps 15] [--no-maps] [--yes]
"""
import argparse, datetime, json, math, os, re, statistics, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import requests
from common import RESEARCH, TODAY, front_matter, slugify, SlugRegistry
import local_area as la
import zimlib

LA = os.path.join(RESEARCH, "local-area")
CONF = os.path.join(LA, "local-area.json")   # where the section was built for; Library Manager uses its tiles when present
UA = {"User-Agent": "ResearchLibrary-LocalArea/1.0 (personal offline library; python-requests)"}
INAT = "https://api.inaturalist.org/v1/"
GROUPS = [   # (group, folder, page type, iNaturalist taxa by scientific name (rank), taxa left out)
    ("Plants - Flowering plants", "plants", "local-profile", [("Angiospermae", "subphylum")],
     [("Poaceae", "family"), ("Cyperaceae", "family"), ("Juncaceae", "family")]),
    ("Plants - Conifers", "plants", "local-profile", [("Pinopsida", "class")], []),
    ("Plants - Grasses, sedges & rushes", "plants", "local-profile",
     [("Poaceae", "family"), ("Cyperaceae", "family"), ("Juncaceae", "family")], []),
    ("Plants - Ferns & mosses", "plants", "local-profile", [("Polypodiopsida", "class"), ("Bryophyta", "phylum")], []),
    ("Wildlife - Birds", "wildlife", "local-wildlife", [("Aves", "class")], []),
    ("Wildlife - Mammals", "wildlife", "local-wildlife", [("Mammalia", "class")], []),
    ("Wildlife - Fish", "wildlife", "local-wildlife", [("Actinopterygii", "class")], []),
    ("Wildlife - Reptiles & amphibians", "wildlife", "local-wildlife", [("Reptilia", "class"), ("Amphibia", "class")], []),
    ("Insects", "insects", "local-wildlife", [("Insecta", "class")], []),
    ("Spiders, ticks & mites", "insects", "local-wildlife", [("Arachnida", "class")], []),
    ("Fungi & lichens", "fungi", "local-wildlife", [("Fungi", "kingdom")], []),
]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
FUNGI_WARN = "⚠ Never eat a wild mushroom identified from a description or photo - deadly and edible species can look alike."
PLANT_WARN = "⚠ Never eat a wild plant identified only from a description or photo - some edible plants have poisonous look-alikes."


def api(path, **params):
    """iNaturalist API through the library's cache (and politely: about one request a second)."""
    url = INAT + path + ("?" + "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()) if params else "")
    j = json.loads(la.fetch(url))
    time.sleep(0.4)
    return j


def download(url, dest):
    """Straight to the file (photos, maps) - not through the cache, so nothing is stored twice."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    for attempt in range(3):
        try:
            with requests.get(url, headers=UA, timeout=(15, 120), stream=True) as r:
                r.raise_for_status()
                with open(dest + ".part", "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            os.replace(dest + ".part", dest)
            return dest
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"could not download {url}")


def taxon_id(name, rank):
    """iNaturalist's id for a group; matched by name (and rank when it agrees - ranks get reclassified now and then)."""
    hits = [t for t in api("taxa", q=name, per_page=10)["results"] if t["name"].lower() == name.lower()]
    best = next((t for t in hits if t["rank"] == rank), hits[0] if hits else None)
    if not best:
        raise SystemExit(f"iNaturalist does not know the taxon {name} ({rank})")
    return best["id"]


# ------------------------------------------------------------------------------------------------ where
def geocode(text):
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$", text)
    if m:
        lat, lon = float(m[1]), float(m[2])
        r = requests.get("https://nominatim.openstreetmap.org/reverse", params={"lat": lat, "lon": lon, "format": "jsonv2",
                         "addressdetails": 1, "zoom": 12}, headers=UA, timeout=60).json()
        return [{"name": r.get("display_name") or f"{lat}, {lon}", "lat": lat, "lon": lon, "address": r.get("address", {})}]
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": text, "format": "jsonv2", "addressdetails": 1,
                     "limit": 5}, headers=UA, timeout=60).json()
    return [{"name": p["display_name"], "lat": float(p["lat"]), "lon": float(p["lon"]), "address": p.get("address", {})} for p in r]


def short_name(place):
    a = place["address"]
    town = a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or a.get("municipality") or a.get("county") or ""
    region = a.get("state") or a.get("region") or a.get("country") or ""
    return ", ".join(x for x in (town, region) if x) or place["name"].split(",")[0]


def bbox(lat, lon, km):
    dlat = km / 111.0
    dlon = km / (111.0 * max(math.cos(math.radians(lat)), 0.05))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon


# ------------------------------------------------------------------------------------------------ Start Here (climate)
def climate(lat, lon):
    j = requests.get("https://archive-api.open-meteo.com/v1/archive", params={"latitude": lat, "longitude": lon,
                     "start_date": "1991-01-01", "end_date": "2020-12-31", "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum",
                     "timezone": "auto"}, timeout=180).json()
    d = j["daily"]
    days = [(datetime.date.fromisoformat(t), lo, hi, p) for t, lo, hi, p in
            zip(d["time"], d["temperature_2m_min"], d["temperature_2m_max"], d["precipitation_sum"]) if lo is not None]
    mon = {m: {"lo": [], "hi": [], "p": {}} for m in range(1, 13)}
    for day, lo, hi, p in days:
        mon[day.month]["lo"].append(lo); mon[day.month]["hi"].append(hi)
        mon[day.month]["p"][day.year] = mon[day.month]["p"].get(day.year, 0) + (p or 0)
    months = [(MONTHS[m - 1], statistics.mean(mon[m]["hi"]), statistics.mean(mon[m]["lo"]), statistics.mean(mon[m]["p"].values()))
              for m in range(1, 13)]
    # frost season: the half of the year around midwinter (northern: Jul-Jun, southern: Jan-Dec)
    south = lat < 0
    last, first, mins = [], [], []
    for y in range(1991, 2021):
        if south:
            spring = [x for x in days if x[0].year == y and x[0].month >= 7]       # late winter -> spring
            fall = [x for x in days if x[0].year == y and x[0].month < 7]
        else:
            spring = [x for x in days if x[0].year == y and x[0].month < 7]
            fall = [x for x in days if x[0].year == y and x[0].month >= 7]
        sf = [x[0] for x in spring if x[1] <= 0]
        ff = [x[0] for x in fall if x[1] <= 0]
        if sf:
            last.append(max(sf).timetuple().tm_yday if not south else max(sf).timetuple().tm_yday)
        if ff:
            first.append(min(ff).timetuple().tm_yday)
        mins.append(min(x[1] for x in days if x[0].year == y))
    tmin_f = statistics.mean(mins) * 9 / 5 + 32
    zone = math.floor((tmin_f + 60) / 10) + 1
    half = "a" if (tmin_f + 60) % 10 < 5 else "b"
    out = {"elevation": j.get("elevation"), "months": months, "zone": f"{zone}{half}" if 1 <= zone <= 13 else None,
           "tmin_f": tmin_f, "frost_years": len(last)}
    if last and first and len(last) >= 15:
        q = lambda xs, f: sorted(xs)[min(int(len(xs) * f), len(xs) - 1)]
        out["last_frost"], out["last_frost_late"] = statistics.median(last), q(last, 0.9)
        out["first_frost"], out["first_frost_early"] = statistics.median(first), q(first, 0.1)
        out["season"] = (out["first_frost"] - out["last_frost"]) % 366
    return out


def doy(n):
    return (datetime.date(2001, 1, 1) + datetime.timedelta(days=int(n) - 1)).strftime("%B %d").replace(" 0", " ")


def usda_zone(place):
    a = place["address"]
    if a.get("country_code") != "us":
        return None
    pc = a.get("postcode")
    if not pc:
        r = requests.get("https://nominatim.openstreetmap.org/reverse", params={"lat": place["lat"], "lon": place["lon"],
                         "format": "jsonv2", "addressdetails": 1, "zoom": 18}, headers=UA, timeout=60).json()
        pc = r.get("address", {}).get("postcode")
    m = re.match(r"\d{5}", pc or "")
    if not m:
        return None
    try:
        return requests.get(f"https://phzmapi.org/{m[0]}.json", timeout=30).json().get("zone")
    except Exception:
        return None


def start_here(conf, groups_built):
    c = climate(conf["lat"], conf["lon"])
    zone = usda_zone(conf["place"]) if conf["country"] == "us" else None
    name = conf["name"]
    f2 = lambda c_: f"{c_ * 9 / 5 + 32:.0f} °F ({c_:.0f} °C)"
    lines = [f"# Start Here - {name}", "",
             f"Your Local Area is built for **{name}** ({conf['lat']:.4f}, {conf['lon']:.4f}) and everything within "
             f"**{conf['radius']} km** ({conf['radius'] * 0.621:.0f} miles) of it." + (f" Elevation about {c['elevation']:.0f} m "
             f"({c['elevation'] * 3.281:,.0f} ft)." if c.get("elevation") is not None else ""), "",
             "## Growing season", "", "| | |", "|---|---|"]
    if zone:
        lines.append(f"| Hardiness zone (USDA, official) | **{zone}** |")
    if c["zone"]:
        lines.append(f"| Hardiness zone (estimated from local weather records) | {c['zone']} (average coldest night {c['tmin_f']:.0f} °F) |")
    if "last_frost" in c:
        lines += [f"| Average last spring frost | **{doy(c['last_frost'])}** (1 year in 10 it is later than {doy(c['last_frost_late'])}) |",
                  f"| Average first fall frost | **{doy(c['first_frost'])}** (1 year in 10 it is earlier than {doy(c['first_frost_early'])}) |",
                  f"| Frost-free season | about **{c['season']:.0f} days** |"]
    elif c["frost_years"] < 15:
        lines.append("| Frost | Frost is rare here (in fewer than half the years 1991-2020) |")
    lines += ["", "Frost here means a night at or below 0 °C (32 °F). These come from 30 years of weather records (1991-2020, "
              "Open-Meteo) for a grid square of about 10 km around the spot, so valley bottoms can be colder and slopes milder - "
              "by a week or more for frost dates.", "", "## Weather by month", "",
              "| Month | Average high | Average low | Rain & snow (water) |", "|---|---|---|---|"]
    lines += [f"| {m} | {f2(hi)} | {f2(lo)} | {p:.0f} mm ({p / 25.4:.1f} in) |" for m, hi, lo, p in c["months"]]
    lines += ["", "## What is in this section", ""]
    lines += [f"- **{g}**: {n} species seen near you" for g, n in groups_built if n]
    lines += ["- **Maps**: USGS topographic maps of the area (open them from Local Area › Maps or 📍 Waypoints)" if conf.get("maps") else "",
              "", "Species pages list what people have actually recorded within the area on iNaturalist (research-grade "
              "sightings only), most often seen first. Each page shows photos, the months it is seen here, and the Wikipedia "
              "article. Add your own local documents (extension guides, planting calendars) with **Add a Document** and pick "
              "the **Local Area** category.", "", "**Never eat a wild plant or mushroom identified only from a description or photo.**"]
    meta = {"title": f"Start Here - {name}", "category": "local-area", "source_type": "local-overview",
            "publisher": "Weather records and sightings",
            "source_url": f"https://www.openstreetmap.org/?mlat={conf['lat']}&mlon={conf['lon']}#map=11/{conf['lat']}/{conf['lon']}",
            "sources": [{"name": "Open-Meteo historical weather (ERA5)", "url": "https://open-meteo.com/"},
                        {"name": "iNaturalist", "url": "https://www.inaturalist.org/"}] +
                       ([{"name": "USDA Plant Hardiness Zone Map (phzmapi.org)", "url": "https://planthardiness.ars.usda.gov/"}] if zone else []),
            "license": "Compiled from the sources listed", "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    open(os.path.join(LA, "start-here.md"), "w", encoding="utf-8").write(front_matter(meta) + "\n".join(l for l in lines if l is not None) + "\n")
    print(f"  Start Here written (zone {zone or c['zone']}, frost-free about {c.get('season', 0):.0f} days)")


# ------------------------------------------------------------------------------------------------ species pages
def species_list(conf, include, exclude, n):
    params = {"lat": conf["lat"], "lng": conf["lon"], "radius": conf["radius"], "quality_grade": "research",
              "taxon_id": ",".join(str(i) for i in include), "per_page": 200, "locale": "en", "hrank": "species", "lrank": "species"}
    if exclude:
        params["without_taxon_id"] = ",".join(str(i) for i in exclude)
    out, page = [], 1
    while len(out) < n:
        r = api("observations/species_counts", page=page, **params)
        out += r["results"]
        if page * 200 >= r["total_results"] or not r["results"]:
            break
        page += 1
    return out[:n]


def months_seen(conf, tid):
    h = api("observations/histogram", taxon_id=tid, lat=conf["lat"], lng=conf["lon"], radius=conf["radius"],
            quality_grade="research", date_field="observed", interval="month_of_year")["results"]["month_of_year"]
    return [h.get(str(m), 0) for m in range(1, 13)]


def species_page(conf, group, folder, ptype, sc, reg):
    t, count = sc["taxon"], sc["count"]
    tid = t["id"]
    d = os.path.join(LA, folder)
    os.makedirs(d, exist_ok=True)
    common = (t.get("preferred_common_name") or "").strip()
    title = (common[:1].upper() + common[1:]) if common else t["name"]
    slug = reg.claim(slugify(title)[:90] or f"taxon-{tid}", f"local-inat:{tid}")
    md_path = os.path.join(d, slug + ".md")
    img_dir, img_rel = os.path.join(d, slug + "_images"), slug + "_images"
    full = api(f"taxa/{tid}")["results"][0]
    family = next((a["name"] for a in full.get("ancestors", []) if a.get("rank") == "family"), "")
    os.makedirs(img_dir, exist_ok=True)
    photos = []
    for p in full.get("taxon_photos", []):
        ph = p["photo"]
        if not ph.get("license_code"):   # all rights reserved -> not copied
            continue
        url = ph.get("large_url") or ph["url"].replace("square", "large")
        name = f"inat_{len(photos) + 1:02d}.jpg"
        try:
            download(url, os.path.join(img_dir, name))
        except Exception:
            continue
        credit = " ".join((ph.get("attribution") or "iNaturalist").split())   # credits can hold line breaks
        photos.append({"file": name, "caption": f"{title} - {credit}",
                       "source_file_page": f"https://www.inaturalist.org/photos/{ph['id']}", "license": ph["license_code"].upper()})
        if len(photos) >= 4:
            break
    seen = months_seen(conf, tid)
    top = max(seen) or 1
    when = [MONTHS[i] for i, v in enumerate(seen) if v >= top * 0.25]
    wiki_md, wiki_imgs, wiki_url = "", [], t.get("wikipedia_url") or ""
    if wiki_url and "/wiki/" in wiki_url:
        try:
            e = zimlib.resolve(requests.utils.unquote(wiki_url.split("/wiki/", 1)[1]))
            if e is not None:
                art = zimlib.article_md(e, max_images=6)
                wiki_md, wiki_imgs = zimlib.save_article_images(art, img_dir, img_rel, start=len(photos))
                wiki_md = re.sub(r"^\s*#\s.*\n", "", wiki_md).strip()
        except Exception as ex:
            print(f"    (no Wikipedia article: {type(ex).__name__})")
    if not wiki_md and full.get("wikipedia_summary"):
        wiki_md = re.sub(r"<[^>]+>", "", full["wikipedia_summary"]).strip()
    warn = FUNGI_WARN if folder == "fungi" else PLANT_WARN if folder == "plants" else ""
    status = full.get("conservation_status") or {}
    facts = [("Scientific name", f"*{t['name']}*"), ("Family", family),
             (f"Seen near {conf['name']}", f"{count:,} research-grade sightings within {conf['radius']} km"),
             ("Usually seen", ", ".join(when) if when else "-"),
             ("Conservation status", (status.get("status_name") or status.get("status") or "").title() if status else "")]
    body = [f"# {title}", "", f"*{t['name']}*  ", f"Type: {group.split(' - ')[-1]}", "",
            "## Key facts", "", "| | |", "|---|---|"] + [f"| {k} | {v} |" for k, v in facts if v]
    if warn:
        body += ["", f"> {warn}"]
    body += ["", "## Photos", ""] + [f"![{p['caption']}]({img_rel}/{p['file']})" for p in photos]
    body += ["", f"## When it is seen near {conf['name']}", "", "| " + " | ".join(MONTHS) + " |", "|" + "---|" * 12,
             "| " + " | ".join(str(v) if v else "-" for v in seen) + " |", "",
             "(research-grade iNaturalist sightings per month, all years)"]
    if wiki_md:
        body += ["", "## About", "", wiki_md]
    body += ["", "## Sources", "", f"- iNaturalist: <https://www.inaturalist.org/taxa/{tid}>"] + \
            ([f"- Wikipedia: <{wiki_url}>"] if wiki_url else [])
    meta = {"title": title, "category": "local-area", "source_type": ptype, "group": group, "scientific_name": t["name"],
            "family": family or None, "inat_taxon_id": tid, "source_url": f"https://www.inaturalist.org/taxa/{tid}",
            "sources": [{"name": "iNaturalist", "url": f"https://www.inaturalist.org/taxa/{tid}"}] +
                       ([{"name": "Wikipedia", "url": wiki_url}] if wiki_url else []),
            "license": "Mixed - see Sources (photos: each photographer's license; Wikipedia text CC BY-SA 4.0)",
            "seen_nearby": count, "images": (photos + wiki_imgs) or None, "words": len(" ".join(body).split()),
            "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    if not photos and not wiki_imgs:
        os.rmdir(img_dir) if os.path.isdir(img_dir) and not os.listdir(img_dir) else None
    open(md_path, "w", encoding="utf-8").write(front_matter(meta) + "\n".join(body) + "\n")
    return slug


# ------------------------------------------------------------------------------------------------ USGS topo maps (US)
def topo_maps(conf, km, yes):
    s, n, w, e = bbox(conf["lat"], conf["lon"], km)
    items, off = [], 0
    while True:
        j = requests.get("https://tnmaccess.nationalmap.gov/api/v1/products", params={"datasets": "US Topo Current",
                         "bbox": f"{w},{s},{e},{n}", "max": 100, "offset": off}, timeout=120).json()
        items += [i for i in j.get("items", []) if i.get("downloadURL", "").lower().endswith(".pdf")]
        off += 100
        if off >= j.get("total", 0):
            break
    if not items:
        print("  No USGS topo maps found for this area.")
        return 0
    gb = sum(i.get("sizeInBytes") or 0 for i in items) / 1e9
    print(f"  {len(items)} USGS topographic maps cover {km} km around you (about {gb:.1f} GB).")
    if not yes and input("  Download them? Type Y or N: ").strip().lower() != "y":
        return 0
    d = os.path.join(LA, "maps")
    os.makedirs(d, exist_ok=True)
    done = 0
    for i in sorted(items, key=lambda i: i["title"]):
        bb = i["boundingBox"]
        quad = re.sub(r"^US Topo 7\.5-minute map for ", "", i["title"]).strip()
        slug = "usgs-topo-" + slugify(quad)
        pdf, md = os.path.join(d, slug + ".pdf"), os.path.join(d, slug + ".md")
        if not os.path.exists(pdf):
            try:
                download(i["downloadURL"], pdf)
            except Exception as ex:
                print(f"    {quad}: download failed ({ex})"); continue
        pub = (i.get("publicationDate") or "")[:10]
        meta = {"title": f"{quad} - USGS 1:24,000 Topographic Map" + (f" ({pub[:4]})" if pub else ""), "category": "local-area",
                "source_type": "local-map", "group": "Maps", "file": slug + ".pdf",
                "publisher": "US Geological Survey - The National Map (US Topo)", "source_url": i["downloadURL"],
                "license": "US Government work - public domain", "map_scale": "1:24,000 (7.5-minute quadrangle)",
                "bounds": f"{bb['minY']:.3f}-{bb['maxY']:.3f} N, {-bb['maxX']:.3f}-{-bb['minX']:.3f} W",
                "published": pub or None, "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
        body = (f"# {meta['title']}\n\nType: Maps  \nDetailed map - USGS US Topo 7.5-minute quadrangle, scale 1:24,000"
                + (f", published {pub}" if pub else "") + f".\n\n**Open the map:** [{slug}.pdf]({slug}.pdf)\n\n"
                f"- Covers **{bb['minY']:.3f}° to {bb['maxY']:.3f}° N** and **{-bb['maxX']:.3f}° to {-bb['minX']:.3f}° W**.\n"
                "- Contour lines (elevation), roads, streams, lakes and place names. It is a **GeoPDF**: Library Manager's "
                "Waypoints place pins on it, and GPS map apps (e.g. Avenza Maps) can show your position on it offline.\n")
        open(md, "w", encoding="utf-8").write(front_matter(meta) + body)
        done += 1
        print(f"    map {done}/{len(items)}: {quad}", flush=True)
    return done


# ------------------------------------------------------------------------------------------------ AIPortable map region
def aiportable_region(conf, km):
    cat = os.path.join(os.path.dirname(RESEARCH), "AIPortable", "data", "maps-catalog.json")
    if not os.path.exists(cat):
        return False
    s, n, w, e = bbox(conf["lat"], conf["lon"], km)
    raw = json.load(open(cat, encoding="utf-8"))
    regions = raw.get("regions", raw)
    entry = {"name": f"My area ({conf['name']})", "group": "Local", "bbox": f"{w:.3f},{s:.3f},{e:.3f},{n:.3f}", "size": "",
             "description": f"Full street detail for {km} km around {conf['name']} - made by Build Local Area."}
    new = {"my-area": entry, **{k: v for k, v in regions.items() if k != "my-area"}}   # first in the list
    if "regions" in raw:
        raw["regions"] = new
    else:
        raw = {k: v for k, v in raw.items() if k.startswith("_")} | new
    json.dump(raw, open(cat, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return True


# ------------------------------------------------------------------------------------------------ main
def recycle(paths):
    """Send files / folders to the Windows Recycle Bin (never a permanent delete)."""
    import subprocess
    for p in paths:
        if not os.path.exists(p):
            continue
        kind = "DeleteDirectory" if os.path.isdir(p) else "DeleteFile"
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::"
                        f"{kind}('{p}', 'OnlyErrorDialogs', 'SendToRecycleBin')"], check=False)


def ask(prompt, default):
    a = input(f"{prompt} [{default}]: ").strip()
    return a or str(default)


def main():
    for stream in (sys.stdout, sys.stderr):   # a console that can't show a character must not stop the build
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place"); ap.add_argument("--radius", type=int); ap.add_argument("--per-group", type=int)
    ap.add_argument("--maps", type=int, help="topo maps within this many km (US only)"); ap.add_argument("--no-maps", action="store_true")
    ap.add_argument("--groups", help="only these groups (comma-separated words, e.g. birds,fungi)")
    ap.add_argument("--yes", action="store_true", help="answer yes to every question")
    a = ap.parse_args()
    os.makedirs(LA, exist_ok=True)
    old = json.load(open(CONF, encoding="utf-8")) if os.path.exists(CONF) else None
    if not old and any(f.endswith(".md") for _, _, fs in os.walk(LA) for f in fs):
        sys.exit("This library already has a Local Area that was made another way - Build Local Area leaves it alone.")
    print("Build Local Area - the plants, wildlife, weather and maps of where you live.\n")
    if old and not a.place:
        print(f"Already built for: {old['name']} ({old['radius']} km). Press Enter to continue it, or type another place.")
    place_text = a.place or ask("Where are you? A town or address, or a position like 35.59, -82.55", old["query"] if old else "")
    places = geocode(place_text)
    if not places:
        sys.exit("That place was not found - try a town and state/country, or a position.")
    place = places[0]
    if len(places) > 1 and not (a.place or a.yes):
        for i, p in enumerate(places, 1):
            print(f"  {i}. {p['name']}")
        place = places[int(ask("Which one?", 1)) - 1]
    radius = a.radius or int(ask("How far around it to look, in km (50 km = 31 miles)", old["radius"] if old else 50))
    per = a.per_group or int(ask("How many species per group (plants, birds, fungi...) - the most often seen first", 100))
    conf = {"query": place_text, "name": short_name(place), "lat": place["lat"], "lon": place["lon"], "radius": radius,
            "country": place["address"].get("country_code", ""), "place": place, "per_group": per, "made": TODAY}
    if old and (abs(old["lat"] - conf["lat"]) > 0.01 or abs(old["lon"] - conf["lon"]) > 0.01 or old["radius"] != radius):
        print(f"\nThis replaces the Local Area made for {old['name']} ({old['radius']} km): its species pages, maps and Start Here")
        print("go to the Recycle Bin. Documents you added to Local Area yourself stay.")
        if not a.yes and input("Continue? Type Y or N: ").strip().lower() != "y":
            sys.exit("Nothing changed.")
        recycle([os.path.join(LA, f) for f in ("plants", "wildlife", "insects", "fungi", "maps", "start-here.md")])
        reg0 = SlugRegistry()
        reg0.map = {k: v for k, v in reg0.map.items() if not v.startswith("local-inat:")}
        reg0.save()
    print(f"\nBuilding for {conf['name']} ({conf['lat']:.4f}, {conf['lon']:.4f}), {radius} km around, up to {per} species per group.\n")
    json.dump({k: v for k, v in conf.items() if k != "place"} | {"address": place["address"]}, open(CONF, "w", encoding="utf-8"), indent=1)

    reg = SlugRegistry()
    groups_built = []
    want = [w.strip().lower() for w in (a.groups or "").split(",") if w.strip()]
    for group, folder, ptype, inc, exc in GROUPS:
        if want and not any(w in group.lower() for w in want):
            continue
        include = [taxon_id(nm, rk) for nm, rk in inc]
        exclude = [taxon_id(nm, rk) for nm, rk in exc]
        found = species_list(conf, include, exclude, per)
        print(f"== {group}: {len(found)} species", flush=True)
        made = 0
        owners = {v: k for k, v in reg.map.items()}   # pages built on an earlier run are skipped
        for k, sc in enumerate(found, 1):
            tid = sc["taxon"]["id"]
            old_slug = owners.get(f"local-inat:{tid}")
            if old_slug and os.path.exists(os.path.join(LA, folder, old_slug + ".md")):
                made += 1; continue
            try:
                slug = species_page(conf, group, folder, ptype, sc, reg)
                made += 1
                if k % 10 == 0 or k == len(found):
                    print(f"   {k}/{len(found)}  {slug}", flush=True); reg.save()
            except Exception as ex:
                print(f"   skipped {sc['taxon'].get('name')}: {type(ex).__name__}: {ex}"[:200])
        groups_built.append((group, made))
        reg.save()
    print("\n== Start Here")
    conf["maps"] = False
    if conf["country"] == "us" and not a.no_maps:
        print("\n== Topographic maps (USGS)")
        mk = a.maps or (int(ask("  Topo maps for how many km around you (each map is about 13 x 14 km, ~50 MB)", min(radius, 15)))
                        if not a.yes else min(radius, 15))
        conf["maps"] = topo_maps(conf, mk, a.yes) > 0
    start_here(conf, groups_built)
    if aiportable_region(conf, radius):
        print(f"\nAdded 'My area ({conf['name']})' to AIPortable's map list (Tools/Settings > Maps > Download maps).")
    print("\nUpdating the catalog...", flush=True)
    import subprocess
    for script in ("20_catalog.py", "21_readme.py"):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), script)], capture_output=True)
    print("Done. Open Library Manager > Local Area.")


if __name__ == "__main__":
    main()
