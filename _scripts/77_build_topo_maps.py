"""Topographic maps for Local Area -> local-area/maps/ (user requests 2026-10-12).

  77_build_topo_maps.py            download / copy what is missing, then (re)write every map page, the index and the help page

Detailed maps: USGS US Topo 7.5-minute GeoPDFs (1:24,000, current editions) for all of northwest Montana - centre within
112.5-116.1 W, 46.75-49.0 N (Idaho border to the Rocky Mountain Front, Canada to Missoula, incl. Glacier NP and the Bob
Marshall) and a Montana sheet: ~425 sheets, ~18 GB (user choice 2026-10-12: 'all current 2024'). The 16 around Kalispell
form the 'Flathead Valley' grid on the index page.
Regional maps: the user's own 1:100,000 (30 x 60 minute) GeoPDFs, copied read-only from NAS_30X60 into
local-area/maps/regional/ (user choice: 'add regional + keep the 2024 valley maps'). Their bounds come from The National
Map's 'Historical Topographic Maps' records (cached in _work/local_area/regional_bounds.json).

Every map page has a 'Neighbouring maps' compass (N, NE, E, SE, S, SW, W, NW): links to the neighbour when it is in the
library, otherwise its USGS name (and whether the user's NAS collection has it). Valley maps link up to the regional map
that contains them; regional maps list the valley maps inside them. Help page: moving-between-maps.md.
Pages: source_type 'local-map', group 'Maps'. Then 20_catalog + 21_readme.
"""
import json, os, re, shutil, subprocess, sys
import requests
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter, slugify

OUT = os.path.join(RESEARCH, "local-area", "maps")
REG = os.path.join(OUT, "regional")
API = "https://tnmaccess.nationalmap.gov/api/v1/products"
BOX = (-116.10, 46.75, -112.50, 49.00)          # northwest Montana
VALLEY = (-114.50, 48.00, -114.00, 48.50)       # Flathead Valley grid on the index page
# official boundaries (NPS Land Resources Division; USFS EDW wilderness layer), cached for offline rebuilds
AREA_SRC = [("Glacier National Park", "https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/NPS_Land_Resources_Division_Boundary_and_Tract_Data_Service/FeatureServer/2/query",
             "UNIT_CODE='GLAC'"),
            ("Bob Marshall Wilderness Complex (Bob Marshall, Great Bear and Scapegoat)",
             "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_Wilderness_01/MapServer/0/query",
             "WILDERNESSNAME IN ('Bob Marshall Wilderness','Great Bear Wilderness','Scapegoat Wilderness')")]
AREA_CACHE = os.path.join(RESEARCH, "_work", "local_area", "map_area_boundaries.json")
AREAS = None


def areas():
    """{name: [rings]} - polygon rings [(lon, lat)...] of each area."""
    global AREAS
    if AREAS is not None:
        return AREAS
    cache = json.load(open(AREA_CACHE, encoding="utf-8")) if os.path.exists(AREA_CACHE) else {}
    for name, url, where in AREA_SRC:
        if name in cache:
            continue
        try:
            g = requests.get(url, params={"where": where, "outFields": "*", "f": "geojson", "outSR": 4326}, timeout=180).json()
            rings = []
            for f in g.get("features", []):
                geo = f["geometry"]
                polys = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
                for poly in polys:
                    rings.append(poly[0])   # outer ring
            if rings:
                cache[name] = rings
        except Exception as e:
            print("  boundary download failed:", name, e, flush=True)
    os.makedirs(os.path.dirname(AREA_CACHE), exist_ok=True)
    json.dump(cache, open(AREA_CACHE, "w", encoding="utf-8"))
    AREAS = cache
    return AREAS


def _inside(x, y, ring):
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi:
            c = not c
        j = i
    return c


def area_share(s, name):
    """Rough share (0-1) of the sheet inside an area: a 20 x 20 grid of points."""
    rings = areas().get(name, [])
    pts = [(s["minx"] + (s["maxx"] - s["minx"]) * (a + .5) / 20, s["miny"] + (s["maxy"] - s["miny"]) * (b + .5) / 20)
           for a in range(20) for b in range(20)]
    return sum(1 for x, y in pts if any(_inside(x, y, r) for r in rings)) / len(pts)


ARTICLE = {"Glacier National Park": "Glacier National Park"}


def area_phrase(s, names):
    parts = []
    for n in names:
        share = area_share(s, n)
        label = ARTICLE.get(n, "the " + n)
        parts.append(("a small corner of this map is" if share < 0.05 else "part of this map is" if share < 0.75
                      else "most of this map is" if share < 0.98 else "this whole map is") + " inside " + label)
    t = "; ".join(parts)
    return t[0].upper() + t[1:] + "."


def area_hits(s):
    """Names of the areas whose official boundary reaches into this map sheet."""
    out = []
    for name, rings in areas().items():
        hit = False
        for ring in rings:
            xs, ys = [p[0] for p in ring], [p[1] for p in ring]
            if max(xs) < s["minx"] or min(xs) > s["maxx"] or max(ys) < s["miny"] or min(ys) > s["maxy"]:
                continue
            if any(s["minx"] <= p[0] <= s["maxx"] and s["miny"] <= p[1] <= s["maxy"] for p in ring[::3]):
                hit = True
            else:   # the area may surround the whole sheet: test a 5 x 5 grid of points
                hit = any(_inside(s["minx"] + (s["maxx"] - s["minx"]) * a / 4, s["miny"] + (s["maxy"] - s["miny"]) * b / 4, ring)
                          for a in range(5) for b in range(5))
            if hit:
                break
        if hit:
            out.append(name)
    return out
NAS = r"\\192.168.1.35\Business\Garmin\Avenza PDF Maps"
NAS_30X60 = os.path.join(NAS, "30x60")
NAS_75 = os.path.join(NAS, "7.5x7.5")
CACHE = os.path.join(RESEARCH, "_work", "local_area", "regional_bounds.json")
CODE_NAMES = {"F47114A1": ("MT", "Plains"), "F48113E1": ("MT", "Saint Mary")}   # files named by USGS map code
DIRS = [("N", 0, 1), ("NE", 1, 1), ("E", 1, 0), ("SE", 1, -1), ("S", 0, -1), ("SW", -1, -1), ("W", -1, 0), ("NW", -1, 1)]
WORD = {"N": "North", "NE": "Northeast", "E": "East", "SE": "Southeast", "S": "South", "SW": "Southwest", "W": "West", "NW": "Northwest"}


def tnm(params):
    return requests.get(API, params=params, timeout=120).json().get("items", [])


# ---------------------------------------------------------------- valley maps (current US Topo)
def valley_sheets():
    out, items, off = [], [], 0
    while True:   # the API pages its results
        j = requests.get(API, params={"datasets": "US Topo Current", "bbox": ",".join(map(str, BOX)), "max": 500, "offset": off},
                         timeout=180).json()
        it = j.get("items", [])
        items += it
        off += len(it)
        if not it or off >= j.get("total", 0):
            break
    for i in items:
        b = i["boundingBox"]
        cx, cy = (b["minX"] + b["maxX"]) / 2, (b["minY"] + b["maxY"]) / 2
        # states = everything after the place name: 'Kalispell, MT' / 'Adair, ID, MT' / 'Eureka North, MT,BC' (Canada border).
        # (Until 2026-10-13 only the LAST one was checked, so the MT,BC border row was skipped.)  Idaho sheets inside the box
        # are wanted too (user 2026-10-13: fill the gaps along the Idaho line - the border runs diagonally there).
        states = {x.strip() for x in i["title"].replace("US Topo 7.5-minute map for ", "").split(",")[1:]}
        if BOX[0] < cx < BOX[2] and BOX[1] < cy < BOX[3] and states & {"MT", "ID"}:
            name = i["title"].replace("US Topo 7.5-minute map for ", "").rsplit(",", 1)[0]
            if "MT" not in states and "," not in name:
                name += ", ID"   # Idaho-only sheet: 'Three Sisters, ID' (Montana has a Three Sisters too)
            out.append(dict(kind="valley", name=name, st="MT" if "MT" in states else "ID", date=i.get("publicationDate", ""), url=i["downloadURL"],
                            minx=b["minX"], maxx=b["maxX"], miny=b["minY"], maxy=b["maxY"], slug="usgs-topo-" + slugify(name)))
    return out


def download(s, path, tries=4):
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return False
    import time
    for k in range(tries):
        tmp = path + ".part"
        try:
            with requests.get(s["url"], stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if open(tmp, "rb").read(4) != b"%PDF":
                raise RuntimeError("not a PDF: " + s["url"])
            os.replace(tmp, path)
            return True
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            if k == tries - 1:
                raise
            time.sleep(20 * (k + 1))


# ---------------------------------------------------------------- regional maps (user's 1:100,000 collection)
def regional_sheets():
    os.makedirs(REG, exist_ok=True)
    if os.path.isdir(NAS_30X60):
        for f in os.listdir(NAS_30X60):
            if f.lower().endswith(".pdf") and not os.path.exists(os.path.join(REG, f)):
                shutil.copy2(os.path.join(NAS_30X60, f), os.path.join(REG, f))
                print("  copied", f, flush=True)
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    out = []
    for f in sorted(os.listdir(REG)):
        if not f.lower().endswith(".pdf"):
            continue
        m = re.match(r"([A-Z]{2})_(.+?)_(\d+)_(\d{4})_100000_geo\.pdf$", f)
        code = None
        if m:
            st, name, year = m.group(1), m.group(2), m.group(4)
        else:
            code = re.match(r".*_(F\d{5}[A-Z]\d)_geo\.pdf$", f)
            code = code.group(1) if code else None
            st, name = CODE_NAMES.get(code or "", ("MT", f.split("_")[0].replace("-", " ")))
            year = ""
        name = name.replace("DAlene", "d'Alene")
        key = f"{name}, {st}"
        if key not in cache and code:   # USGS map code F<lat><lon><A|E>1: 1 x 2 degree cell, A = south half, E = north half
            lat, lon = int(code[1:3]), int(code[3:6])
            south = lat + (0.5 if code[6] == "E" else 0.0)
            cache[key] = {"minX": -(lon + 1.0), "maxX": -float(lon), "minY": south, "maxY": south + 0.5}
        if key not in cache:
            want = f"USGS 1:100000-scale Quadrangle for {name.replace(chr(39), '')}, {st}".lower()
            for i in tnm({"datasets": "Historical Topographic Maps", "q": name.split()[0].replace("'", ""), "max": 200}):
                t = i["title"].lower().replace("'", "")
                if t.startswith(want):
                    cache[key] = i["boundingBox"]
                    break
        b = cache.get(key)
        out.append(dict(kind="regional", name=name, st=st, date=year, file=f, slug="usgs-100k-" + slugify(f"{st} {name}"),
                        **({"minx": b["minX"], "maxx": b["maxX"], "miny": b["minY"], "maxy": b["maxY"]} if b else {})))
        if not b:
            print("  no bounds found for", key, flush=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1)
    return out


# ---------------------------------------------------------------- neighbours
def nas_quads():
    """Names of the 7.5-minute maps in the user's NAS collection (lower case), if the NAS is reachable."""
    try:
        out = set()
        for f in os.listdir(NAS_75):   # e.g. MT_Werner_Peak_20140529_TM_geo.pdf, MT_Kalispell_TM_geo.pdf
            m = re.match(r"^[A-Z]{2}_(.+?)(?:_\d{8})?(?:_TM)?_geo\.pdf$", f, re.I)
            if m:
                out.add(m.group(1).replace("_", " ").lower())
        return out
    except OSError:
        return set()


def find_at(sheets, x, y):
    return next((s for s in sheets if "minx" in s and s["minx"] < x < s["maxx"] and s["miny"] < y < s["maxy"]), None)


def outside_name(kind, x, y):
    """USGS name of the map sheet at a point outside the library's set."""
    try:
        if kind == "valley":
            items = tnm({"datasets": "US Topo Current", "bbox": f"{x - .001},{y - .001},{x + .001},{y + .001}", "max": 5})
            for i in items:
                b = i["boundingBox"]
                if b["minX"] < x < b["maxX"] and b["minY"] < y < b["maxY"]:
                    return i["title"].replace("US Topo 7.5-minute map for ", "")
        else:
            items = tnm({"datasets": "Historical Topographic Maps", "bbox": f"{x - .001},{y - .001},{x + .001},{y + .001}", "max": 100})
            for i in items:
                b = i["boundingBox"]
                if "1:100000-scale" in i["title"] and b["minX"] < x < b["maxX"] and b["minY"] < y < b["maxY"]:
                    return re.sub(r"^USGS 1:100000-scale Quadrangle for (.+?) \d{4}.*$", r"\1", i["title"])
    except Exception:
        pass
    return None


def neighbours(s, same, nas):
    """{dir: (text, link or None)} for the 8 neighbours of a sheet among sheets of the same kind."""
    if "minx" not in s:
        return {}
    w, hgt = s["maxx"] - s["minx"], s["maxy"] - s["miny"]
    cx, cy = (s["minx"] + s["maxx"]) / 2, (s["miny"] + s["maxy"]) / 2
    out = {}
    for d, dx, dy in DIRS:
        x, y = cx + dx * w, cy + dy * hgt
        n = find_at(same, x, y)
        if n:
            out[d] = (n["name"], n["slug"])
        else:
            nm = outside_name(s["kind"], x, y)
            if nm and s["kind"] == "valley":
                short = nm.split(",")[0]
                out[d] = (f"{nm} - not in the library" + (" (in your NAS collection)" if short.lower() in nas else ""), None)
            else:
                out[d] = ((f"{nm} - " if nm else "") + "not in the library", None)
    return out


def compass(s, nb, prefix=""):
    """3 x 3 Markdown table with this map in the middle. Table cells show plain names (the reader does not follow links in
    tables), so the clickable links follow as a list."""
    def cell(d):
        t, link = nb.get(d, ("-", None))
        return t
    rows = [["NW", "N", "NE"], ["W", None, "E"], ["SW", "S", "SE"]]
    lines = ["| | | |", "|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(f"**{s['name']}** (this map)" if d is None else f"{d}: {cell(d)}" for d in r) + " |")
    links = [f"- **{WORD[d]}:** [{nb[d][0]}]({prefix}{nb[d][1]}.md)" for d, _, _ in DIRS if d in nb and nb[d][1]]
    return "\n".join(lines) + ("\n\n**Go to the next map:**\n\n" + "\n".join(links) if links else "")


# ---------------------------------------------------------------- pages
def write(meta, body, path):
    open(path, "w", encoding="utf-8").write(front_matter({k: v for k, v in meta.items() if v not in (None, "")}) + "\n" + body)


HELP = "moving-between-maps.md"


def valley_page(s, nb, region):
    yr = s["date"][:4]
    # 'Kalispell, MT' / 'Adair, ID, MT' (both states) / 'Eureka North, MT' (name already has MT: Canada border) / 'Wallace, ID'
    place = s["name"] if s["st"] != "MT" or s["name"].endswith(", MT") else f"{s['name']}, MT"
    title = f"{place} - USGS 1:24,000 Topographic Map ({yr})"
    mine = area_hits(s)
    meta = {"title": title, "category": "local-area", "source_type": "local-map", "group": "Maps", "file": s["slug"] + ".pdf",
            "publisher": "US Geological Survey - The National Map (US Topo)", "source_url": s["url"],
            "license": "US Government work - public domain", "map_scale": "1:24,000 (7.5-minute quadrangle)", "map_set": "valley",
            "bounds": f"{s['miny']:.3f}-{s['maxy']:.3f} N, {abs(s['maxx']):.3f}-{abs(s['minx']):.3f} W",
            "published": s["date"], "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    up = f"[{region['name']}, {region['st']} (1:100,000)](regional/{region['slug']}.md)" if region else "none in the library"
    body = (f"# {title}\n\nType: Maps  \nDetailed map - USGS US Topo 7.5-minute quadrangle, scale 1:24,000, published {s['date']}."
            + (f"  \n{area_phrase(s, mine)}" if mine else "") + "\n\n"
            f"**Open the map:** [{s['slug']}.pdf]({s['slug']}.pdf)\n\n"
            f"- Covers **{s['miny']:.3f}° to {s['maxy']:.3f}° N** and **{abs(s['maxx']):.3f}° to {abs(s['minx']):.3f}° W** "
            "(about 8.6 miles north-south by 5.8 miles east-west).\n"
            f"- On the regional map: {up}.\n"
            "- Contour lines (elevation), roads, streams, lakes and place names; the PDF has layers (imagery, contours...) you can "
            "turn on or off. It is a **GeoPDF** - Avenza Maps and similar apps show your GPS position on it with no internet.\n\n"
            "## Neighbouring maps\n\n" + compass(s, nb) + "\n\n"
            f"How to carry on from one map to the next: [Moving between maps]({HELP}). All maps: "
            "[Northwest Montana topographic maps](flathead-valley-topo-maps.md).\n\n"
            f"Source: US Geological Survey, The National Map - <{s['url']}>\n")
    write(meta, body, os.path.join(OUT, s["slug"] + ".md"))


def regional_page(s, nb, inside):
    title = f"{s['name']}, {s['st']} - USGS 1:100,000 Topographic Map" + (f" ({s['date']})" if s["date"] else "")
    bounds = (f"{s['miny']:.2f}-{s['maxy']:.2f} N, {abs(s['maxx']):.2f}-{abs(s['minx']):.2f} W") if "minx" in s else None
    meta = {"title": title, "category": "local-area", "source_type": "local-map", "group": "Maps", "file": s["file"],
            "publisher": "US Geological Survey (from my own map collection)", "license": "US Government work - public domain",
            "map_scale": "1:100,000 (30 x 60 minute)", "map_set": "regional", "bounds": bounds, "published": s["date"] or None,
            "provenance": "Copied from my NAS map collection (Avenza PDF Maps)", "compiled": TODAY, "date_added": TODAY,
            "date_source": "added to the library"}
    body = (f"# {title}\n\nType: Maps  \nRegional map - USGS 30 x 60 minute sheet, scale 1:100,000"
            + (f", {s['date']} edition" if s["date"] else "") + " - from my own map collection.\n\n"
            f"**Open the map:** [{s['file']}]({s['file']})\n\n"
            + (f"- Covers **{s['miny']:.2f}° to {s['maxy']:.2f}° N** and **{abs(s['maxx']):.2f}° to {abs(s['minx']):.2f}° W** "
               "(30 minutes of latitude x 1 degree of longitude, about 35 x 45 miles).\n" if "minx" in s else "")
            + "- Good for trips, routes and evacuation planning; less detail than the 1:24,000 detailed maps. Older edition - roads "
              "and buildings may have changed.\n"
              "- It is a **GeoPDF**: Avenza Maps and similar apps show your GPS position on it with no internet.\n"
            + (("\n## Detailed maps inside this map (1:24,000)\n\n" + "\n".join(f"- [{v['name']}](../{v['slug']}.md)" for v in inside) + "\n")
               if inside else "")
            + ("\n## Neighbouring regional maps\n\n" + compass(s, nb) + "\n" if nb else "")
            + f"\nHow to carry on from one map to the next: [Moving between maps](../{HELP}). All maps: "
              "[Northwest Montana topographic maps](../flathead-valley-topo-maps.md).\n")
    write(meta, body, os.path.join(REG, s["slug"] + ".md"))


def grid(sheets, prefix=""):
    rows = {}
    for s in sheets:
        if "minx" in s:
            rows.setdefault(round(s["maxy"], 2), []).append(s)
    xs = sorted({round(s["minx"], 2) for s in sheets if "minx" in s})
    if not xs:
        return ""
    out = ["| " + " | ".join(f"{abs(x):.2f}° W" for x in xs) + " |", "|" + "---|" * len(xs)]
    for y in sorted(rows, reverse=True):
        by = {round(s["minx"], 2): s for s in rows[y]}
        out.append("| " + " | ".join(by[x]["name"] if x in by else "" for x in xs) + " |")
    return "\n".join(out)


def index_page(valley, regional):
    centre = lambda s: ((s["minx"] + s["maxx"]) / 2, (s["miny"] + s["maxy"]) / 2)
    inbox = lambda s, b: b[0] < centre(s)[0] < b[2] and b[1] < centre(s)[1] < b[3]
    core = [s for s in valley if inbox(s, VALLEY)]
    hits = {s["slug"]: area_hits(s) for s in valley}
    areas_md = "".join(f"### {name}\n\nMaps that include part of it (from the official boundary):\n\n"
                       + ", ".join(f"[{s['name']}]({s['slug']}.md)" for s in sorted(valley, key=lambda s: s["name"]) if name in hits[s["slug"]])
                       + "\n\n" for name in areas())
    groups = ""
    for r in sorted(regional, key=lambda r: (-r.get("maxy", 0), r.get("minx", 0))):
        if "minx" not in r:
            continue
        mine = [s for s in valley if inbox(s, (r["minx"], r["miny"], r["maxx"], r["maxy"]))]
        if mine:
            groups += (f"### On the [{r['name']}, {r['st']}](regional/{r['slug']}.md) regional map ({len(mine)})\n\n"
                       + ", ".join(f"[{s['name']}]({s['slug']}.md)" for s in sorted(mine, key=lambda s: s["name"])) + "\n\n")
    body = ("# Northwest Montana Topographic Maps\n\nType: Maps  \nTwo sets of USGS topographic maps for northwest Montana - from the "
            "Idaho border to the Rocky Mountain Front and from Canada down to Missoula, including **Glacier National Park** and the "
            f"**Bob Marshall Wilderness**: **{len(valley)} detailed maps** (1:24,000, current 2024 editions) and **{len(regional)} regional "
            "maps** (1:100,000, older editions from my own collection). Every map page has a **Neighbouring maps** compass with links "
            f"north, south, east and west - see [Moving between maps]({HELP}) for how to carry on from one sheet to the next.\n\n"
            "## Flathead Valley around Kalispell (1:24,000) - north at the top\n\nEach detailed sheet covers 7.5 minutes of latitude and "
            "longitude, about 8.6 miles north-south by 5.8 miles east-west.\n\n" + grid(core) + "\n\n"
            "## Glacier National Park and the Bob Marshall\n\n" + areas_md +
            "## All detailed maps, by regional map\n\nEach regional map holds up to 32 detailed maps (4 rows of 8).\n\n" + groups +
            "Alphabetical: " + ", ".join(f"[{s['name']}]({s['slug']}.md)" for s in sorted(valley, key=lambda s: s["name"])) + "\n\n"
            "## Regional maps (1:100,000) - north at the top\n\nEach sheet covers 30 minutes of latitude x 1 degree of longitude, "
            "about 35 x 45 miles.\n\n" + grid(regional) + "\n\n"
            + "\n".join(f"- [{s['name']}, {s['st']}](regional/{s['slug']}.md)" + (f" ({s['date']})" if s["date"] else "")
                        for s in sorted(regional, key=lambda s: (s["st"] != "MT", s["name"]))) + "\n\n"
            "Use them to find **your elevation** (for canning - see **Food Preservation**), plan routes, read terrain for wildfire or "
            "flood planning, and navigate with no internet. More on map reading is in the library's **Navigation & Mapping** category.\n")
    meta = {"title": "Northwest Montana Topographic Maps - Index", "category": "local-area", "source_type": "local-map", "group": "Maps",
            "map_set": "index", "publisher": "US Geological Survey - The National Map", "license": "US Government work - public domain",
            "provenance": "Index compiled for this library from the USGS map records",
            "compiled": TODAY, "date_added": TODAY, "date_source": "added to the library"}
    write(meta, body, os.path.join(OUT, "flathead-valley-topo-maps.md"))


def help_page():
    body = """# Moving Between Maps

Type: Maps
How the map sheets fit together, and how to carry on when you walk or drive off the edge of one.

## How the sheets fit together

- USGS maps are cut along lines of **latitude and longitude**, so neighbouring sheets meet exactly edge to edge: the north edge of
  one map is the south edge of the next.
- **Detailed maps (1:24,000)** are 7.5 minutes on each side - about 8.6 miles north-south and 5.8 miles east-west here. Four of
  them across and four down cover the Flathead Valley from Whitefish to Somers; the library has them for all of northwest Montana.
- **Regional maps (1:100,000)** are 30 minutes north-south and 1 degree east-west - each one holds 32 detailed maps (4 rows of 8).
- North is always at the top. Each corner of a map is printed with its latitude and longitude, and the same numbers appear on the
  corner of the neighbouring sheet - that is the easiest way to check you have the right one.

## Finding the next map

1. **Use the compass on the map's page** in this library: every map page has a *Neighbouring maps* table (N, NE, E, SE, S, SW,
   W, NW) with links straight to the next sheet. Where the neighbour is not in the library it still gives the USGS name, and
   says if it is in your NAS map collection.
2. **Use the map margin:** USGS topographic maps print the names of the **adjoining maps** in the margin (on US Topo maps, in a
   small diagram near the bottom of the sheet) - look for the name on the side you are heading towards.
3. **Use the index page:** [Northwest Montana topographic maps](flathead-valley-topo-maps.md) shows both sets laid out as grids,
   north at the top.
4. **Zoom out or in:** each detailed map page names the regional map that contains it, and each regional map lists the
   detailed maps inside it - go up a scale to see the bigger picture, down a scale for detail.

## Lining up two paper maps

- Lay them side by side so the shared edge touches; the contour lines, roads and streams should continue straight across.
- Match a feature that crosses the edge (a road, creek or section line) rather than the paper margins - the margins are trimmed
  differently on each sheet.
- Most older regional sheets use an older datum (NAD 27) than the current detailed maps (NAD 83), so the grid
  lines can sit a little apart - line up the features, not the grid.

## On a phone or tablet with GPS

- These maps are **GeoPDFs**: load them into a map app such as Avenza Maps and your GPS position shows on the map with no
  internet or phone signal.
- Load **all the sheets** you might need before you go, so the next map is ready when the blue dot reaches the edge.
- In the app, open the sheet named on the side you are heading towards (from the compass on this library's map page or the map
  margin).
- Keep a paper copy or a second device for the area you are travelling in - phones fail in the cold and batteries run down.

Related: the library's **Navigation & Mapping** category has more on map reading, compass use and coordinates.
"""
    meta = {"title": "Moving Between Maps - How the Map Sheets Fit Together", "category": "local-area", "source_type": "local-map",
            "group": "Maps", "map_set": "index", "license": "Written for this library",
            "provenance": "Written for this library (map facts from USGS map specifications)", "compiled": TODAY, "date_added": TODAY,
            "date_source": "added to the library"}
    write(meta, body, os.path.join(OUT, HELP))


def main():
    os.makedirs(OUT, exist_ok=True)
    valley = valley_sheets()
    print(len(valley), "detailed sheets", flush=True)
    for n_, s in enumerate(valley, 1):
        try:
            if download(s, os.path.join(OUT, s["slug"] + ".pdf")):
                print(f"  downloaded {n_}/{len(valley)}: {s['name']}", flush=True)
        except Exception as e:
            print("  FAILED", s["name"], e, flush=True)
            s["failed"] = True
    valley = [s for s in valley if not s.get("failed")]
    regional = regional_sheets()
    print(len(regional), "regional sheets", flush=True)
    nas = nas_quads()
    for s in valley:
        cx, cy = (s["minx"] + s["maxx"]) / 2, (s["miny"] + s["maxy"]) / 2
        valley_page(s, neighbours(s, valley, nas), find_at(regional, cx, cy))
        print("  valley:", s["name"], flush=True)
    for s in regional:
        inside = [v for v in valley if "minx" in s and s["minx"] < (v["minx"] + v["maxx"]) / 2 < s["maxx"]
                  and s["miny"] < (v["miny"] + v["maxy"]) / 2 < s["maxy"]]
        regional_page(s, neighbours(s, regional, nas), sorted(inside, key=lambda v: v["name"]))
        print("  regional:", s["name"], flush=True)
    index_page(valley, regional)
    help_page()
    print("done", flush=True)
    for s_ in ("20_catalog.py", "21_readme.py"):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), s_)])


if __name__ == "__main__":
    main()
