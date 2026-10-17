"""Photo candidates for Local Area plants that have no (or few) photos - for the user to REVIEW, never added automatically.

  70_photo_candidates.py collect [--max-photos 0] [--per 8] [slug ...]
        Bing image search "<plant> <fruit/plant word>" -> _work/local_area/photo_candidates/<slug>/NN.jpg + sources.json
        + a numbered contact sheet _work/local_area/photo_candidates/<slug>.jpg (and _all.jpg overview)
  70_photo_candidates.py keep <slug> 1 3 5
        copies the chosen candidates into local-area/plants/<slug>_images/my_web_NN.jpg (+ my_photo_sources.json with the
        page each came from); 69_build_local_area.py shows 'my_' photos first and never removes them.
Web photos belong to whoever posted them: fine for this personal offline library, not for sharing.
"""
import html, json, os, re, shutil, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
import local_area as L
from PIL import Image, ImageDraw, ImageFont, ImageOps

CAND = os.path.join(L.W, "photo_candidates")
PLANTS = os.path.join(L.RESEARCH, "local-area", "plants")
IMG = (".jpg", ".jpeg", ".png", ".webp")


def plant_info():
    out = {}
    for md in os.listdir(PLANTS):
        if not md.endswith(".md"):
            continue
        slug = md[:-3]
        head = open(os.path.join(PLANTS, md), encoding="utf-8").read(4000)
        g = lambda k: (re.search(rf'^{k}: "(.*)"', head, re.M) or [None, ""])[1]
        d = os.path.join(PLANTS, slug + "_images")
        photos = [f for f in os.listdir(d) if f.lower().endswith(IMG) and not re.search(r"map|chart|range", f, re.I)] if os.path.isdir(d) else []
        out[slug] = {"title": g("title"), "sci": g("scientific_name"), "group": g("group"), "photos": len(photos)}
    return out


# watermarked, paid stock-photo sites - never used
STOCK = re.compile(r"istockphoto|gettyimages|shutterstock|ftcdn|stock\.adobe|dreamstime|alamy|123rf|depositphotos|"
                   r"agefotostock|pond5|bigstock|canstockphoto|vecteezy|freepik", re.I)

WORD = {"Apples": "apple tree", "Pears": "pear tree", "Plums & apricots": "tree", "Cherries": "cherry tree",
        "Berries & small fruit": "plant", "Nut trees": "tree", "Shade & ornamental": "tree", "Conifers": "tree",
        "Shrubs & hedges": "shrub", "Roses": "rose", "Herbs": "herb plant"}


def bing(query, n):
    url = "https://www.bing.com/images/async?" + urllib.parse.urlencode({"q": query, "first": 0, "count": 35, "mmasync": 1})
    h = L.fetch(url)
    res = []
    for m in re.finditer(r'class="iusc"[^>]*\sm="([^"]+)"', h):
        try:
            j = json.loads(html.unescape(m.group(1)))
        except Exception:
            continue
        if j.get("murl") and not any(r["image"] == j["murl"] for r in res):
            res.append({"image": j["murl"], "page": j.get("purl"), "title": j.get("t", "")})
        if len(res) >= n:
            break
    return res


def sheet(slug, files, out):
    font = ImageFont.truetype("arial.ttf", 22)
    T = 260
    cols = 4
    rows = (len(files) + cols - 1) // cols or 1
    im = Image.new("RGB", (cols * (T + 10) + 10, rows * (T + 40) + 50), "white")
    dr = ImageDraw.Draw(im)
    dr.text((10, 10), slug, fill="black", font=font)
    for i, f in enumerate(files):
        x, y = 10 + (i % cols) * (T + 10), 50 + (i // cols) * (T + 40)
        try:
            p = Image.open(f); p.seek(0); p = ImageOps.exif_transpose(p).convert("RGB"); p.thumbnail((T, T))
            im.paste(p, (x, y))
        except Exception:
            dr.rectangle([x, y, x + T, y + T], outline="red")
        dr.text((x, y + T + 4), str(int(os.path.basename(f)[:2])), fill="black", font=font)
    im.save(out, quality=80)


def collect(args):
    maxp = int(args[args.index("--max-photos") + 1]) if "--max-photos" in args else 0
    per = int(args[args.index("--per") + 1]) if "--per" in args else 8
    only = [a for a in args if not a.startswith("--") and not a.isdigit()]
    info = plant_info()
    todo = [s for s in sorted(info) if s in only] if only else [s for s, i in sorted(info.items()) if i["photos"] <= maxp]
    os.makedirs(CAND, exist_ok=True)
    for slug in todo:
        i = info[slug]
        name = re.sub(r"\s*\(.*\)", "", i["title"])
        q = f"{name} {WORD.get(i['group'].split(' - ')[-1], '')}".strip()
        d = os.path.join(CAND, slug)
        os.makedirs(d, exist_ok=True)
        bj = os.path.join(d, "bing.json")   # results read from Bing in the built-in browser (same results the user sees)
        try:
            hits = json.load(open(bj, encoding="utf-8")) if os.path.exists(bj) else bing(q, per * 2)
        except Exception as e:
            print(f"{slug}: search failed {e}"); continue
        hits = [h_ for h_ in hits if not STOCK.search(h_["image"] + " " + (h_.get("page") or ""))]
        kept, files = [], []
        for h_ in hits:
            if len(kept) >= per:
                break
            n = len(kept) + 1
            f = os.path.join(d, f"{n:02d}.jpg")
            try:
                b = L.fetch(h_["image"], binary=True)
                tmp = f + ".tmp"
                open(tmp, "wb").write(b)
                p = Image.open(tmp); p.seek(0); p = ImageOps.exif_transpose(p).convert("RGB")
                if min(p.size) < 200:
                    os.remove(tmp); continue
                p.thumbnail((1400, 1400)); p.save(f, quality=88); os.remove(tmp)
            except Exception:
                if os.path.exists(f + ".tmp"):
                    os.remove(f + ".tmp")
                continue
            kept.append(dict(h_, file=os.path.basename(f), query=q)); files.append(f)
        json.dump(kept, open(os.path.join(d, "sources.json"), "w", encoding="utf-8"), indent=1)
        sheet(f"{i['title']}  (search: {q})", files, os.path.join(CAND, slug + ".jpg"))
        print(f"{slug}: {len(kept)} candidates", flush=True)
        time.sleep(2)


def keep(args):
    slug, nums = args[0], [int(x) for x in args[1:]]
    d = os.path.join(CAND, slug)
    src = json.load(open(os.path.join(d, "sources.json"), encoding="utf-8"))
    dest = os.path.join(PLANTS, slug + "_images")
    os.makedirs(dest, exist_ok=True)
    log_p = os.path.join(dest, "my_photo_sources.json")
    log = json.load(open(log_p, encoding="utf-8")) if os.path.exists(log_p) else []
    for n in nums:
        s = next((x for x in src if x["file"] == f"{n:02d}.jpg"), None)
        if not s:
            print("no candidate", n); continue
        name = f"my_web_{len([x for x in os.listdir(dest) if x.startswith('my_web_')]) + 1:02d}.jpg"
        shutil.copy2(os.path.join(d, s["file"]), os.path.join(dest, name))
        log.append({"file": name, "source_page": s.get("page"), "image_url": s["image"], "search": s.get("query"),
                    "note": "web photo chosen by the user - personal reference only, owned by its publisher"})
        print("kept", slug, n, "->", name)
    json.dump(log, open(log_p, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"collect": collect, "keep": keep}[a[0]](a[1:])
