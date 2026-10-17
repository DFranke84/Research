"""Print the insect selection (testing helper for 71)."""
import json, os, re, sys, urllib.parse, collections
sys.path.insert(0, os.path.dirname(__file__))
import local_area as L, local_insects_specs as S

def mt_counts(genus):
    u = ("https://api.inaturalist.org/v1/observations/species_counts?place_id=16&quality_grade=research&per_page=200&taxon_name="
         + urllib.parse.quote(genus))
    try:
        r = json.loads(L.fetch(u))["results"]
    except Exception as e:
        print("  inat failed", genus, e); return {}
    return {x["taxon"]["name"].lower(): x["count"] for x in r}

def select():
    d = json.load(open(os.path.join(L.W, "mtfg_animalia.json"), encoding="utf-8"))
    named = {k: v for k, v in d.items() if k[0] == "I" and not re.match(r"(A|An) ", v[0])}
    out = {}
    for g, pre, fam in S.WHOLE:
        for k, v in named.items():
            if (pre and k.startswith(pre)) or (fam and v[2] == fam):
                out.setdefault(k, g)
    for g, picks in S.PICKED.items():
        for p in picks:
            hits = [k for k, v in named.items() if v[1] == p or v[2] == p or (" " not in p and v[1].split()[0] == p)]
            if " " in p or p in S.WHOLE_GENERA or len(hits) <= 1:
                take = hits
            else:
                c = mt_counts(p)
                hits.sort(key=lambda k: -c.get(named[k][1].lower(), 0))
                take = [k for i, k in enumerate(hits[:S.TOP_N.get(g, 3)]) if i == 0 or c.get(named[k][1].lower(), 0) > 0]
            for k in take:
                out.setdefault(k, g)
    return {k: (g,) + tuple(named[k]) for k, g in out.items()}

if __name__ == "__main__":
    s = select()
    print(collections.Counter(v[0] for v in s.values()), len(s))
