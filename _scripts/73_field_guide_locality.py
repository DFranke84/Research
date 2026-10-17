"""Which Field Guide species live near Montana? (user question 2026-10-12)

For every field-guide-*/*.md species page: wild iNaturalist observations (verifiable, not captive/cultivated) in Montana and
in the region around it (Montana, Idaho, Washington, Oregon, Wyoming, British Columbia, Alberta), plus whether the
Montana Field Guide lists it. Writes _work/field_guide_locality.csv + .md. Read-only - changes nothing in the library.

  73_field_guide_locality.py
"""
import csv, glob, hashlib, json, os, re, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
import local_area as L

REGION = {"Montana": 16, "Idaho": 22, "Washington": 46, "Oregon": 10, "Wyoming": 15, "British Columbia": 7085, "Alberta": 6834}
MIN_OBS = 3   # fewer wild records than this in the whole region = a stray / escaped garden plant, not local
OUT = os.path.join(RESEARCH, "_work", "field_guide_locality")


def head(f):
    t = open(f, encoding="utf-8").read(4000)
    g = lambda k: (re.search(rf'^{k}: "?(.*?)"?\s*$', t, re.M) or [None, ""])[1]
    v = [g(k) for k in ("title", "common_name", "scientific_name", "inaturalist_taxon_id")]
    return [x if x.lower() not in ("null", "none") else "" for x in v]


def cached(u):
    return os.path.exists(os.path.join(L.CACHE, hashlib.md5((u + json.dumps(None, sort_keys=True)).encode()).hexdigest() + ".html"))


def get(u):
    """iNaturalist JSON through the disk cache, ~1 request a second for new lookups."""
    for i in range(4):
        try:
            new = not cached(u)
            r = json.loads(L.fetch(u))
            if new:
                time.sleep(1.1)
            return r
        except Exception as e:
            print("  retry", u, e, flush=True)
            L.HOST_FAILS.clear()
            time.sleep(10 * (i + 1))
    return None


LATIN = re.compile(r"[A-Z][a-z]+( [a-z-]+){1,3}$")


def resolve(title, common, sci, taxon):
    """(taxon id, scientific name): pages with no id, or a common name in the scientific_name field, are looked up."""
    if taxon:
        return taxon, sci
    for q in [sci if LATIN.match(sci or "") else None, common, re.sub(r"\s*\(.*", "", title)]:
        if not q:
            continue
        r = get("https://api.inaturalist.org/v1/taxa?per_page=1&q=" + urllib.parse.quote(q))
        if r and r.get("results"):
            t = r["results"][0]
            return str(t["id"]), t["name"]
    return "", sci


def count(taxon, places):
    r = get(f"https://api.inaturalist.org/v1/observations?taxon_id={taxon}&place_id={','.join(map(str, places))}"
            "&verifiable=true&captive=false&per_page=0")
    return r["total_results"] if r else None


def mtfg_names():
    names = set()
    for f in ("mtfg_animalia.json", "mtfg_plants.json", "mtfg_fungi.json"):
        p = os.path.join(L.W, f)
        if os.path.exists(p):
            names |= {v[1].lower() for v in json.load(open(p, encoding="utf-8")).values()}
    return names


def main():
    mt_names = mtfg_names()
    rows = []
    files = sorted(glob.glob(os.path.join(RESEARCH, "field-guide-*", "*.md")))
    for n, f in enumerate(files, 1):
        title, common, sci, taxon = head(f)
        cat = os.path.basename(os.path.dirname(f))[len("field-guide-"):]
        r = {"guide": cat, "title": title, "scientific_name": sci, "file": os.path.relpath(f, RESEARCH)}
        taxon, sci2 = resolve(title, common, sci, taxon) if (sci or common) else ("", "")
        if not taxon:
            r["verdict"] = "not a species page" if not sci else "unknown (not found on iNaturalist)"
        else:
            sci = sci2 or sci
            r["scientific_name"] = sci
            region = count(taxon, REGION.values())
            mt = (count(taxon, [16]) or 0) if region else 0
            in_mtfg = sci.lower() in mt_names
            r.update(region_obs=region, montana_obs=mt, montana_field_guide="yes" if in_mtfg else "")
            if region is None:
                r["verdict"] = "unknown (lookup failed)"
            elif in_mtfg or mt >= MIN_OBS:
                r["verdict"] = "Montana"
            elif region >= MIN_OBS:
                r["verdict"] = "nearby (PNW region, not Montana)"
            else:
                r["verdict"] = "not local"
        rows.append(r)
        if n % 50 == 0:
            print(n, "/", len(files), flush=True)
    keys = ["guide", "verdict", "title", "scientific_name", "montana_obs", "region_obs", "montana_field_guide", "file"]
    with open(OUT + ".csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, keys); w.writeheader(); w.writerows(rows)
    json.dump(rows, open(OUT + ".json", "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    print("done", len(rows))


if __name__ == "__main__":
    main()
