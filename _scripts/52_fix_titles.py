"""Re-title user-ingested library files whose title came from junk PDF metadata ("Page 1 of 4", "MontGuide",
"Layout 1", "BurnInjuryFinal", "xyz.indd" ...). The new title is the original filename when that is descriptive,
otherwise the first sensible line of the document text. Renames the .md and its original file, fixes the links
and front matter, and updates slug_registry.json.

  _scripts\\.venv\\Scripts\\python _scripts\\52_fix_titles.py "E:\\Homesteading" [--apply]
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, slugify, SlugRegistry, yaml_val
from categories import CATEGORIES

JUNK = re.compile(
    r"^(page \d+( of \d+)?|montguide|for more online montguides.*|layout \d+|powerpoint presentation|untitled.*|contents|"
    r"c0\d\d.*|\d+ n havana|burninjuryfinal|microsoft (word|powerpoint).*|table of contents|of the|natural|infused|rg anic|"
    r"chapter \d+ mark [ivx\d]+.*|\d+[a-z/&]+|[\w\- .]*\.(pdf|pub|indd|pmd|pages|ppt|vp|max|jpg|doc)x?\b.*|"
    r"a proj?ect ?of.*|m?i+c?r?o?f?b?i?c?h?e?|microfiche|iuiicrofiche|ivIicrofiche|images|edition|pnwjoke|master1|"
    r"www\..*|https?://.*|.*@.*|\d[\d\-/ .]*|figuring stand space.*|top of form|by the way.*|week \d+:?|"
    r"[a-z]*_kindle|cover|welcome.*|caution|improved|a look|annual report|home gardens|training and|in this issue)$", re.I)
CODE = re.compile(r"^(mt\d{6}[a-z]{2}|eb\d+\w*|em\d+\w*|pnw\d+\w*|bul\d+|az\d+|\d+|document|doc\d*|viewpdf.*|health\d|"
                  r"misc\d+\w*|nrcs.*|scan\d+|emags? ?\d*|delon|handhold|innercover|facilities|nutrition|parasites|"
                  r"reproduction|advrepro|ships|[a-z]*\d{4,}\w*)$", re.I)


MANUAL = {   # source filename (lower-case) -> title, for code-named files whose text has no clean first line
    "az1144.pdf": "Arizona Cooperative Extension AZ1144 (1999)",
    "eb0719.pdf": "General Winemaking Procedure (WSU EB0719)",
    "mt200902hr.pdf": "Canning Pickles and Sauerkraut (MontGuide MT200902HR)",
    "mt200903hr.pdf": "Pressure Canning Meat, Poultry and Fish in Montana (MontGuide MT200903HR)",
    "mt200904hr.pdf": "Making Jams, Jellies and Syrups (MontGuide MT200904HR)",
    "mt200905hr.pdf": "Home-canning Using Boiling Water Canners and Pressure Canners (MontGuide MT200905HR)",
    "mt200906hr.pdf": "Processing Fruit and Tomato Products - Times and Pressures (MontGuide MT200906HR)",
    "mt200907hr.pdf": "Drying Vegetables (MontGuide MT200907HR)",
    "mt200910hr.pdf": "Freezing Fruit (MontGuide MT200910HR)",
    "mt199310ag.pdf": "Lawn Establishment and Care in Montana (MontGuide MT199310AG)",
    "mt199604ag.pdf": "Collecting and Handling Seeds of Montana Native Species (MontGuide MT199604AG)",
    "mt200303hr.pdf": "Tracking Progress Toward Family Savings Goals (MontGuide MT200303HR)",
    "mt200707hr.pdf": "Beneficiary Deeds in Montana (MontGuide MT200707HR)",
    "c046 fuchsias 05.pdf": "Fuchsias (WSU Spokane Master Gardener C046)",
    "c026 dahlias 05.pdf": "Dahlias (WSU Spokane Master Gardener C026)",
    "c018 clematis 05.pdf": "Clematis (WSU Spokane Master Gardener C018)",
    "c048 geranium 05.pdf": "Zonal Geraniums (WSU Spokane Master Gardener C048)",
    "c049 gladiolus 05.pdf": "Gladiolus (WSU Spokane Master Gardener C049)",
    "c072 manure on vegetable gardens 05.pdf": "Manure on Vegetable Gardens (WSU Spokane Master Gardener C072)",
    "c123 rose culture 09.pdf": "Rose Culture (WSU Spokane Master Gardener C123)",
    "c100 planting trees & shrubs 05.pdf": "Planting Trees and Shrubs (WSU Spokane Master Gardener C100)",
    "c118 tree care  05.pdf": "Tree Care (WSU Spokane Master Gardener C118)",
    "c146 vegetable gardening 09.pdf": "Vegetable Gardening (WSU Spokane Master Gardener C146)",
    "952840lo.pdf": "Gravel Bags for Packstock (USDA Forest Service)",
    "eb1128e.pdf": "Critical Temperatures for Blossom Buds - Cherries (WSU EB1128)",
    "eb0422.pdf": "Home Gardens (WSU EB0422)",
    "eb0637.pdf": "Training and Trellising Grapes for Production in Washington (WSU EB0637)",
    "eb2005.pdf": "Growing and Marketing Lavender (WSU EB2005)",
    "pnw0525.pdf": "Edamame - Growing and Marketing (PNW0525)",
    "pnw603-e.pdf": "Protecting Grapevines from Winter Injury (PNW 603)",
    "delon.pdf": "Stable-Climate Hive - Roger Delon's version of Warre's People's Hive",
    "2006 04.pdf": "WSU Equine News - Spring 2006",
    "viewpdf_2605_48932.pdf": "Biosecurity for Livestock Herds and Flocks",
    "donut.pdf": "Pumpkin Recipes (Daily Inter Lake, Oct 2013)",
    "infused.pdf": "Infused - Lisa Barthuly (Homestead Originals)",
    "treatment chart (excel).pdf": "Goat Treatment Chart",
    "the handbook of clinically tested herbal remedies [2 vols] - m. barrett (haworth, 2004) ww.pdf":
        "The Handbook of Clinically Tested Herbal Remedies (Barrett, 2004)",
    "eliot wigginton - the foxfire book - volume 04 (pdf).pdf": "The Foxfire Book - Volume 4 (Eliot Wigginton)",
    "2007 04.pdf": "WSU Equine News - Spring 2007",
}


def is_junk(t):
    t = t.strip(" .:-*#")
    return (len(t) < 4 or (len(t) > 90 and ":" not in t) or bool(JUNK.match(t))
            or bool(re.match(r"(hi folks|welcome to|this is the time|baking soda|gordon ramsay)\b", t, re.I))) or not re.search(r"[A-Za-z]{3}", t)


def clean_name(fn):
    s = os.path.splitext(os.path.basename(fn))[0]
    s = re.sub(r"\[\d\]|\(\d\)|%20|_(FINAL|final|opt|new|web|update[d]?)\b.*", " ", s)
    s = re.sub(r"[_+]+", " ", s)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return re.sub(r"\s+", " ", s).strip(" -")


def text_title(body):
    for line in body.split("## Full text", 1)[-1].splitlines():
        line = re.sub(r"^\[Page \d+.*\]$|^#+\s*", "", line.strip()).strip()
        if (8 <= len(line) <= 70 and not is_junk(line) and len(re.findall(r"[A-Za-z]{3,}", line)) >= 2
                and line[0].isupper() and not re.match(r"(by|this|these|the following|page|photo|source)\b", line, re.I)
                and not re.search(r"(,|\b(and|or|the|of|to|for|in|a|an|with|will|are|is))$", line, re.I)
                and not re.search(r"universit|extension|inter lake|zealand|copyright|©|\d{3}-\d{4}", line, re.I)):
            return line.rstrip(".")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    reg = SlugRegistry()
    n = 0
    for c in CATEGORIES:
        d = os.path.join(RESEARCH, c)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".md"):
                continue
            p = os.path.join(d, f)
            txt = open(p, encoding="utf-8").read()
            head, sep, body = txt.partition("\n---\n")
            m = re.search(r'^provenance: "User-provided file: (.*) \(added', head, re.M)
            if not m or not m.group(1).replace("\\\\", "\\").lower().startswith(a.folder.lower()):
                continue
            src = m.group(1).replace("\\\\", "\\")
            title = re.search(r'^title: (".*")$', head, re.M)
            old = eval(title.group(1)) if title else ""
            manual = MANUAL.get(os.path.basename(src).lower())
            if not manual and not is_junk(old):
                continue
            name = clean_name(src)
            new = manual or (name if (not CODE.match(name) and len(re.findall(r"[A-Za-z]{3,}", name)) >= 2)
                             else (text_title(body) or name))
            if new == old:
                continue
            new = new[:150]
            oslug = f[:-3]
            nslug = reg.claim(slugify(new)[:100], reg.map.get(oslug, "user:" + oslug))
            print(f"{c}/{oslug}  <-  {old!r}\n    -> {nslug}   ({new})")
            n += 1
            if not a.apply:
                continue
            ofile = re.search(r'^file: "(.*)"$', head, re.M)
            head = head.replace(title.group(0), "title: " + yaml_val(new))
            body = body.replace(f"# {old}\n", f"# {new}\n", 1)
            if ofile:
                ext = os.path.splitext(ofile.group(1))[1]
                os.rename(os.path.join(d, ofile.group(1)), os.path.join(d, nslug + ext))
                head = head.replace(ofile.group(0), f'file: "{nslug + ext}"')
                body = body.replace(f"[{ofile.group(1)}]({ofile.group(1)})", f"[{nslug + ext}]({nslug + ext})")
            open(os.path.join(d, nslug + ".md"), "w", encoding="utf-8").write(head + sep + body)
            if nslug != oslug:
                os.remove(p)
                reg.map.pop(oslug, None)
    if a.apply:
        reg.save()
    print(n, "titles", "fixed" if a.apply else "would be fixed (dry run)")


if __name__ == "__main__":
    main()
