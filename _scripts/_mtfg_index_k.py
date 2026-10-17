"""Walk the Montana Field Guide (Plantae) -> _work/local_area/mtfg_" + KING.lower() + ".json {elcode: [common, scientific, family]}."""
import json, os, re, html, sys
sys.path.insert(0, os.path.dirname(__file__))
import local_area as L
B = L.MTFG
KING = sys.argv[1]
LINK = re.compile(r"(display(?:Classes|Orders|Family|Species)\.aspx\?(?:phylum|class|order|family)=[^\"'&<> ]+)")
todo, seen, out = ["displayPhyDiv.aspx?Kingdom=" + KING + ""], set(), {}
while todo:
    page = todo.pop()
    if page in seen:
        continue
    seen.add(page)
    h = L.fetch(B + page)
    if page.startswith("displaySpecies"):
        fam = page.split("=", 1)[1]
        for m in re.finditer(r"elcode=(\w+)'>([^<]+)</a>.{0,300}?<i>([^<]+)</i>", h, re.S):
            out[m.group(1)] = [html.unescape(m.group(2)).strip(), html.unescape(m.group(3)).strip(), fam]
        continue
    for l in LINK.findall(h):
        if l not in seen and "Kingdom" not in l:
            todo.append(l)
    if len(seen) % 25 == 0:
        print(len(seen), len(out), flush=True)
json.dump(out, open(os.path.join(L.W, "mtfg_" + KING.lower() + ".json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
print("pages", len(seen), "species", len(out))
