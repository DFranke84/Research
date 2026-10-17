"""Waypoints for the Local Area topo maps: your own named places (lat / long) that open the right map, zoomed to the spot.

  - saved in _work/waypoints.json (like favorites); the tablet viewer gets a copy when its data is rebuilt
  - which map holds a point: the 'bounds' line in each map page (local-area/maps/*.md, maps/regional/*.md)
  - where on the PDF page: the map's own GeoPDF georeferencing
      * 2024 US Topo (1:24,000): /VP viewport + /Measure GPTS (lat/long of the corners, NAD83)  -> projective fit
      * regional 1:100,000 (Avenza/TerraGo): /LGIDict CTM + Transverse Mercator projection (NAD27)  -> exact maths
    (NAD27 vs GPS is ~80 m in Montana - under 1 mm on a 1:100,000 sheet, so it is ignored)
"""
import datetime, glob, json, math, os, re, uuid

RESEARCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPS = os.path.join(RESEARCH, "local-area", "maps")
FILE = os.path.join(RESEARCH, "_work", "waypoints.json")


# ======================================================================= the saved waypoints
def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f).get("waypoints", [])
    except (OSError, ValueError):
        return []


def save(wps):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"waypoints": wps}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, FILE)


def new(name, lat, lon, notes=""):
    return {"id": uuid.uuid4().hex[:10], "name": name.strip() or "Waypoint", "lat": round(lat, 6), "lon": round(lon, 6),
            "notes": notes.strip(), "added": datetime.date.today().isoformat()}


# ======================================================================= reading coordinates people type or paste
def _dms(deg, mins, secs):
    return float(deg) + float(mins or 0) / 60 + float(secs or 0) / 3600


def parse(text):
    """'48.1958, -114.3129' / '48.1958 N 114.3129 W' / 48°11'45"N 114°18'46"W / 48 11.75, -114 18.77 /
    a Google Maps link (…/@48.19,-114.31,15z or ?q=48.19,-114.31).  Returns (lat, lon) or raises ValueError.
    A longitude typed without a minus or W is taken as West (every map here is in the western hemisphere)."""
    s = (text or "").strip()
    if not s:
        raise ValueError("Type or paste a position, e.g. 48.1958, -114.3129")
    m = re.search(r"[@=/](-?\d{1,2}\.\d+),\s*(-?\d{1,3}\.\d+)", s)   # map links
    if m and ("http" in s or "maps" in s):
        return _check(float(m[1]), float(m[2]))
    s = s.replace("º", "°").replace("’", "'").replace("′", "'").replace("”", '"').replace("″", '"').replace("''", '"')
    s = re.sub(r"(?i)\b(lat(itude)?|lon(g(itude)?)?)\b[:=]?", " ", s)
    s = re.sub(r"(?<![A-Za-z])([NSEWnsew])\s*(?=-?\d)", r"\1 ", s)     # 'N48 11.7' -> 'N 48 11.7' (hemisphere letter first)
    # halves: split on a comma / semicolon, else after a trailing hemisphere letter, else between leading ones
    halves = [h for h in re.split(r"[,;]", s) if h.strip()]
    if len(halves) != 2:   # '48°12'N 114°19'48"W': after the trailing N / S
        halves = [h for h in re.split(r"(?:(?<=[\d°'\"][NSns])|(?<=[\d°'\"] [NSns]))\s+(?=[-\d])", s) if h.strip()]
    if len(halves) != 2:   # 'N 48 11.7 W 114 18.8': before the leading E / W
        halves = [h for h in re.split(r"(?<=\d[\s°'\"])\s*(?=[NSEWnsew]\s*\d)", s) if h.strip()]
    if len(halves) != 2:
        nums = re.findall(r"-?\d+(?:\.\d+)?", s)
        if len(nums) in (2, 4, 6):   # no separator: split the numbers evenly
            k = len(nums) // 2
            hemis = re.findall(r"[NSEWnsew]", s)
            halves = [" ".join(nums[:k]) + (" " + hemis[0] if len(hemis) == 2 else ""),
                      " ".join(nums[k:]) + (" " + hemis[1] if len(hemis) == 2 else "")]
    if len(halves) != 2:
        raise ValueError("Couldn't read that - use latitude, longitude, e.g. 48.1958, -114.3129 or 48°11'45\"N 114°18'46\"W")
    vals = []
    for h in halves:
        nums = re.findall(r"-?\d+(?:\.\d+)?", h)
        hemi = (re.findall(r"[NSEWnsew]", h) or [""])[0].upper()
        if not 1 <= len(nums) <= 3:
            raise ValueError("Couldn't read that - use latitude, longitude, e.g. 48.1958, -114.3129")
        v = _dms(nums[0].lstrip("-"), *(nums[1:] + [0, 0])[:2])
        vals.append((-v if nums[0].startswith("-") or hemi in ("S", "W") else v, hemi))
    (a, ha), (b, hb) = vals
    if ha in ("E", "W") or hb in ("N", "S"):   # given as long, lat
        a, b = b, a
    if b > 0:
        b = -b
    return _check(a, b)


def _check(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("That isn't a valid position (latitude -90..90, longitude -180..180)")
    return lat, lon


def fmt(lat, lon):
    return f"{lat:.5f}, {lon:.5f}"


def fmt_dms(lat, lon):
    def one(v, pos, neg):
        h = pos if v >= 0 else neg
        v = abs(v); d = int(v); m = int((v - d) * 60); s = (v - d - m / 60) * 3600
        return f"{d}°{m:02d}'{s:04.1f}\"{h}"
    return f"{one(lat, 'N', 'S')} {one(lon, 'E', 'W')}"


# ======================================================================= which map holds a point
_INDEX = None


def index(refresh=False):
    """Every map page: [{md, pdf, title, set ('detail'/'regional'), s, n, w, e}] - west longitudes negative."""
    global _INDEX
    if _INDEX is not None and not refresh:
        return _INDEX
    out = []
    for md in glob.glob(os.path.join(MAPS, "*.md")) + glob.glob(os.path.join(MAPS, "regional", "*.md")):
        try:
            with open(md, encoding="utf-8") as f:
                head = f.read(2000)
        except OSError:
            continue
        b = re.search(r'^bounds: "([\d.]+)-([\d.]+) N, ([\d.]+)-([\d.]+) W"', head, re.M)
        fn = re.search(r'^file: "([^"]+\.pdf)"', head, re.M)
        if not (b and fn):
            continue
        s, n, e, w = (float(x) for x in b.groups())
        t = re.search(r'^title: "(.*)"', head, re.M)
        out.append({"md": md, "pdf": os.path.join(os.path.dirname(md), fn[1]), "title": t[1] if t else os.path.basename(md),
                    "set": "regional" if os.sep + "regional" + os.sep in md else "detail", "s": s, "n": n, "w": -w, "e": -e})
    _INDEX = out
    return out


def maps_at(lat, lon):
    """(detailed map, regional map) holding the point - either may be None.  On a shared edge the map whose
    centre is nearest wins."""
    best = {}
    for m in index():
        if m["s"] <= lat <= m["n"] and m["w"] <= lon <= m["e"]:
            d = abs(lat - (m["s"] + m["n"]) / 2) / (m["n"] - m["s"]) + abs(lon - (m["w"] + m["e"]) / 2) / (m["e"] - m["w"])
            if m["set"] not in best or d < best[m["set"]][0]:
                best[m["set"]] = (d, m)
    return tuple(best[k][1] if k in best else None for k in ("detail", "regional"))


def map_for_pdf(pdf):
    p = os.path.normcase(os.path.abspath(pdf))
    for m in index():
        if os.path.normcase(os.path.abspath(m["pdf"])) == p:
            return m
    return None


# ======================================================================= lat / long <-> point on the PDF page
class Georef:
    """forward(lat, lon) -> (x, y) and inverse(x, y) -> (lat, lon), in PDF points with y DOWN (as PyMuPDF and the
    rendered picture use), page 1."""

    def __init__(self, fwd, width, height):
        self.fwd, self.width, self.height = fwd, width, height

    def forward(self, lat, lon):
        return self.fwd(lat, lon)

    def inverse(self, x, y, guess=None):
        lat, lon = guess or self._centre
        for _ in range(30):   # Newton steps on the forward mapping
            fx, fy = self.fwd(lat, lon)
            h = 1e-5
            ax, ay = self.fwd(lat + h, lon); bx, by = self.fwd(lat, lon + h)
            j11, j21, j12, j22 = (ax - fx) / h, (ay - fy) / h, (bx - fx) / h, (by - fy) / h
            det = j11 * j22 - j12 * j21
            if not det:
                break
            dx, dy = x - fx, y - fy
            dlat, dlon = (j22 * dx - j12 * dy) / det, (-j21 * dx + j11 * dy) / det
            lat, lon = lat + dlat, lon + dlon
            if abs(dlat) + abs(dlon) < 1e-9:
                break
        return lat, lon

    def on_page(self, lat, lon):
        x, y = self.forward(lat, lon)
        return 0 <= x <= self.width and 0 <= y <= self.height


def _homography(src, dst):
    """3x3 projective transform taking the 4 src points onto the 4 dst points (plain Gaussian elimination).
    The src points are centred first so the equations stay well-conditioned."""
    cx, cy = sum(p[0] for p in src) / 4, sum(p[1] for p in src) / 4
    src = [(x - cx, y - cy) for x, y in src]
    A, B = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    n = 8
    M = [row[:] + [b] for row, b in zip(A, B)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    h = [M[i][n] / M[i][i] for i in range(n)] + [1.0]

    def f(x, y):
        x, y = x - cx, y - cy
        w = h[6] * x + h[7] * y + 1
        return (h[0] * x + h[1] * y + h[2]) / w, (h[3] * x + h[4] * y + h[5]) / w
    return f


def _nums(s):
    return [float(x) for x in re.findall(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", s)]   # PDF numbers can be '.5' or '-.04'


ELLIPSOIDS = {"NAS": (6378206.4, 1 / 294.9786982), "NAR": (6378137.0, 1 / 298.257222101), "WGE": (6378137.0, 1 / 298.257223563)}


def _tmerc(lat, lon, lon0, lat0, k0, fe, fn, a, f):
    """Transverse Mercator forward (Snyder, Map Projections - A Working Manual, eq. 8-9 .. 8-10)."""
    e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    phi, lam = math.radians(lat), math.radians(lon - lon0)
    N = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    T, Cc, A = math.tan(phi) ** 2, ep2 * math.cos(phi) ** 2, lam * math.cos(phi)

    def merid(phi):   # distance along the meridian from the equator
        return a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
                    + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi) - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    M = merid(phi) - merid(math.radians(lat0))   # some sheets put the origin at the map's own latitude
    x = k0 * N * (A + (1 - T + Cc) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * Cc - 58 * ep2) * A ** 5 / 120)
    y = k0 * (M + N * math.tan(phi) * (A ** 2 / 2 + (5 - T + 9 * Cc + 4 * Cc ** 2) * A ** 4 / 24
                                       + (61 - 58 * T + T ** 2 + 600 * Cc - 330 * ep2) * A ** 6 / 720))
    return x + fe, y + fn


_GEO = {}


def georef(pdf):
    """Georef for a map PDF, or None if the PDF has no georeferencing this understands."""
    key = os.path.normcase(os.path.abspath(pdf))
    if key not in _GEO:
        try:
            _GEO[key] = _read_georef(pdf)
        except Exception:
            _GEO[key] = None
    return _GEO[key]


def _read_georef(pdf):
    import pymupdf
    with pymupdf.open(pdf) as d:
        p = d[0]
        H, W = p.mediabox.height, p.mediabox.width
        oy = p.mediabox.y0
        vp = d.xref_get_key(p.xref, "VP")
        if vp[0] == "array":   # US Topo: the largest viewport with a GEO measure
            best = None
            for bbox, mref in re.findall(r"/BBox\s*\[([^\]]+)\][^>]*?/Measure\s+(\d+)\s+0\s+R", vp[1]):
                x0, y0, x1, y1 = _nums(bbox)
                area = abs(x1 - x0) * abs(y1 - y0)
                if not best or area > best[0]:
                    best = (area, (x0, y0, x1, y1), int(mref))
            if best:
                _, (x0, y0, x1, y1), mref = best
                ms = d.xref_object(mref)
                g = _nums(re.search(r"/GPTS\s*\[([^\]]+)\]", ms)[1])
                l = _nums(re.search(r"/LPTS\s*\[([^\]]+)\]", ms)[1])
                geo = [(g[i], g[i + 1]) for i in range(0, 8, 2)]                       # (lat, lon)
                page = [(x0 + l[i] * (x1 - x0), H - (y0 + l[i + 1] * (y1 - y0) - oy)) for i in range(0, 8, 2)]
                return Georef(_homography(geo, page), W, H)
        lgi = d.xref_get_key(p.xref, "LGIDict")
        if lgi[0] in ("array", "dict"):
            s = lgi[1]
            ctm = _nums(re.search(r"/CTM\s*\[([^\]]+)\]", s)[1])
            pj = re.search(r"/Projection\s*<<(.*?)>>", s, re.S)[1]

            def val(k, default=None):
                m = re.search(r"/" + k + r"\s*\(([^)]*)\)", pj)
                return m[1].strip() if m else default
            if val("ProjectionType") not in ("TC", "UT"):
                return None
            if val("ProjectionType") == "UT":
                zone = int(_nums(val("Zone", "0"))[0])
                lon0, lat0, k0, fe, fn = -183 + 6 * zone, 0.0, 0.9996, 500000.0, 0.0
            else:
                lon0, k0 = float(val("CentralMeridian")), float(val("ScaleFactor", "1"))
                lat0 = float(val("OriginLatitude", "0"))
                fe, fn = float(val("FalseEasting", "0")), float(val("FalseNorthing", "0"))
            a_, b_, c_, d_, e_, f_ = ctm
            ell = ELLIPSOIDS.get((val("Datum") or "NAS")[:3], ELLIPSOIDS["NAS"])
            det = a_ * d_ - b_ * c_

            def fwd(lat, lon):
                X, Y = _tmerc(lat, lon, lon0, lat0, k0, fe, fn, *ell)
                X, Y = X - e_, Y - f_                       # metres -> PDF user space (inverse of the CTM)
                ux, uy = (d_ * X - c_ * Y) / det, (-b_ * X + a_ * Y) / det
                return ux, H - (uy - oy)
            return Georef(fwd, W, H)
    return None


def _centre_for(g, m):
    g._centre = ((m["s"] + m["n"]) / 2, (m["w"] + m["e"]) / 2) if m else (48.2, -114.3)
    return g


def georef_for_map(m):
    g = georef(m["pdf"])
    return _centre_for(g, m) if g else None


def georef_for_pdf(pdf):
    g = georef(pdf)
    return _centre_for(g, map_for_pdf(pdf)) if g else None


def page_box(m):
    """Where the map's own corners fall on the page, for the tablet viewer: a 4-point lat/long -> page fit."""
    g = georef_for_map(m)
    if not g:
        return None
    pts = [(m["s"], m["w"]), (m["n"], m["w"]), (m["n"], m["e"]), (m["s"], m["e"])]
    return {"geo": [[round(a, 6), round(b, 6)] for a, b in pts],
            "page": [[round(v, 2) for v in g.forward(a, b)] for a, b in pts], "w": round(g.width, 2), "h": round(g.height, 2)}


# ======================================================================= distances (the 📏 Measure tool)
def distance_km(a, b):
    """Great-circle distance between two (lat, lon) points, km (mean earth radius - within ~0.5% of the true ellipsoid)."""
    r = math.pi / 180
    h = math.sin((b[0] - a[0]) * r / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin((b[1] - a[1]) * r / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def dist_text(km):
    """'3.42 mi (5.50 km)', or feet / metres for short distances."""
    mi = km * 0.621371
    if mi < 0.2:
        return f"{round(mi * 5280):,} ft ({round(km * 1000):,} m)"
    return f"{mi:.2f} mi ({km:.2f} km)" if mi < 10 else f"{mi:.1f} mi ({km:.1f} km)"
