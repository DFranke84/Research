"""Scan a folder of your own documents and add the relevant, non-duplicate ones to the library.

Supported: .pdf .docx .doc .odt .rtf .txt .md .html/.htm .epub .pptx  (scanned PDFs are OCR'd)

TWO-STEP WORKFLOW (nothing is added until step 2):

  1) Review (dry run) - writes a report you can open in Excel:
       _scripts\\.venv\\Scripts\\python _scripts\\50_ingest_folder.py "D:\\My Docs"
     -> _work\\ingest\\ingest_<date-time>.csv   one row per file with:
        decision  add | duplicate | near-duplicate | not-relevant | unreadable | unsupported
        category  best-matching library folder, score, title, reason, matching library file

  2) Optionally edit the CSV (change `decision` to add/skip, fix `category` or `title`), then apply:
       _scripts\\.venv\\Scripts\\python _scripts\\50_ingest_folder.py --apply _work\\ingest\\ingest_<date-time>.csv
     Rows marked `add` are written into the library: the original file is copied next to a Markdown
     sidecar (front-matter + full text). CATALOG.csv/.json and README.md are then regenerated.

Duplicates are detected three ways: identical file (SHA-256) against the library and within the folder,
and near-identical text (shared-passage fingerprint, e.g. the same manual in another format or edition).
Relevance is a keyword score against the 29 library categories; low-scoring files are marked not-relevant.

Options:  --min-score N   relevance threshold (default 8)   --no-ocr   skip OCR of scanned PDFs
          --rebuild-index  rebuild the library text-fingerprint index (_work/ingest/fingerprints.json)
"""
import argparse, csv, datetime, hashlib, html, json, os, re, shutil, subprocess, sys, zipfile
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, cat_dir, front_matter, slugify, SlugRegistry, find_antiword
from categories import CATEGORIES

W = os.path.join(RESEARCH, "_work", "ingest")
os.makedirs(W, exist_ok=True)
FORCE_OCR = os.environ.get("INGEST_FORCE_OCR", "")   # regex of file paths whose PDF text layer is garbage
EXT = {".pdf", ".docx", ".doc", ".odt", ".rtf", ".txt", ".md", ".markdown", ".html", ".htm", ".epub", ".pptx"}

# ---------------------------------------------------------------- relevance vocabulary (per category)
KW = {   # plain word = whole word (+ plural/-ed/-ing); "stem*" = prefix match; "_" joins a phrase
 "water": "water well rainwater cistern purif* filter boil chlorin* bleach disinfect* distill* sodis potable drinking_water spring aquifer "
          "pipe valve faucet plumbing drain pump leak",
 "food-storage-preservation": "canning canner mason_jar preserv* dehydrat* drying dried smoke smoking cure curing brine pickl* ferment* "
                              "root_cellar food_storage shelf_life botulism freezer spoilage food_safety mylar oxygen_absorber jerky",
 "food-production": "garden* seed seedling soil compost* crop harvest orchard irrigat* greenhouse livestock chicken poultry goat rabbit "
                    "cattle pig sheep beekeep* hive honey fertiliz* manure pest weed tillage permaculture aquaculture",
 "foraging-wild-food": "forag* wild_edible edible_plant wild_food berries acorn nuts",
 "hunting-fishing-trapping": "hunting hunter trap trapping snare fishing fishhook fishing_net game_animal deer butcher* field_dress bait",
 "cooking-fire": "firewood tinder kindling stove cooking cook oven charcoal campfire dutch_oven rocket_stove",
 "recipes": "recipe ingredient* tablespoon* teaspoon* tbsp tsp cup preheat serves servings stir whisk bake baking flour sugar butter "
            "dough knead batter simmer saute* sourdough casserole frosting cookie seasoning",
 "medical-first-aid": "first_aid wound bleeding tourniquet bandage splint fracture cpr airway burn shock trauma triage hypotherm* "
                      "heat_stroke frostbite snakebite sting casualty suture laceration dressing",
 "medical-conditions": "disease infection fever diarrhea dehydration diabetes asthma pneumonia malaria cholera symptom diagnos* "
                       "dental tooth pregnan* childbirth infant mental_health",
 "medicine-pharmacology": "medicine medication drug dose dosage antibiotic tablet mg analgesic herbal remedy pharmac* vaccin* prescription",
 "sanitation-hygiene": "latrine toilet sanitation hygiene handwashing soap sewage waste_disposal mosquito rodent disinfect* laundry",
 "shelter-construction": "shelter construction roof insulation timber brick adobe cob concrete foundation framing cabin tent",
 "energy-power": "solar_panel solar battery generator inverter wind_turbine hydro* electrical wiring voltage watt charge_controller propane "
                 "circuit breaker fuse outlet receptacle switch ground neutral heater furnace thermostat",
 "tools-crafts-skills": "axe knife saw blacksmith* forge metalwork* weld* woodwork* carpentry rope knot sewing textile leather tanning "
                        "candle pottery whittl*",
 "mechanical-vehicles": "engine vehicle car truck motor carburetor mechanic repair maintenance bicycle bike tire brake diesel gasoline "
                        "chainsaw oil_filter spark_plug gear chain bearing lawn_mower tractor replac* install* disassembl* reassembl* "
                        "screw bolt nut wrench screwdriver",
 "communications-radio": "radio antenna ham_radio amateur_radio frequency transceiver shortwave morse repeater cb_radio gmrs frs",
 "navigation-mapping": "map compass navigat* bearing azimuth latitude longitude topographic orienteering gps",
 "wilderness-survival": "survival wilderness bushcraft outdoor camping backpack* lost rescue signal_mirror whistle",
 "emergency-preparedness": "emergency disaster prepar* evacuat* emergency_kit go_bag bug_out hurricane flood earthquake tornado wildfire "
                           "blackout power_outage supplies stockpil*",
 "cbrn-hazmat": "nuclear radiation fallout radiological chemical_weapon biological hazmat decontamin* gas_mask respirator potassium_iodide",
 "security-defense": "self-defense firearm weapon ammunition tactical patrol perimeter burglar home_security",
 "weather": "weather forecast storm cloud barometer rainfall snow lightning frost",
 "legal-financial": "insurance deed barter currency financial legal_document fraud scam",
}


def _term(w):
    w = re.escape(w).replace("_", r"[\s-]+")
    return w[:-2] + r"\w*" if w.endswith(r"\*") else w + r"(?:s|es|ed|ing)?"


KWRE = {c: re.compile(r"\b(" + "|".join(_term(w) for w in ws.split()) + r")\b", re.I) for c, ws in KW.items()}
MIN_DISTINCT = 3   # a relevant file must use at least this many different topic terms (all categories together)


def relevance(text, title):
    """Keyword hits per 1,000 words over the top 3 categories (title words count 20x).
    Returns (best category, score, runner-up, distinct terms matched in best category)."""
    body = text[:400000]
    n = max(len(body.split()), 300)
    scores, terms = {}, set()
    for c, rx in KWRE.items():
        found = rx.findall(body) + rx.findall(title) * 20
        scores[c] = len(found) * 1000.0 / n
        terms |= {f.lower() for f in found}
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    total = sum(v for _, v in ranked[:3])
    return ranked[0][0], round(total, 1), ranked[1][0], len(terms)


# ---------------------------------------------------------------- text extraction
def strip_html(s):
    from bs4 import BeautifulSoup
    from markdownify import markdownify
    soup = BeautifulSoup(s, "lxml")
    for t in soup(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    body = soup.body or soup
    return title, re.sub(r"\n{3,}", "\n\n", markdownify(str(body), heading_style="ATX", strip=["a", "img"])).strip()


def xml_text(xml, para_tag, text_tag):
    xml = re.sub(r"<%s[ >]" % para_tag, "\n<%s " % para_tag, xml)
    txt = re.sub(r"<[^>]+>", "", re.sub(r"<%s[^>]*/>" % "w:tab", "\t", xml))
    return html.unescape(re.sub(r"\n{3,}", "\n\n", txt)).strip()


def extract(path, ocr=True):
    """Return (title, text, info dict) or raise. Results are cached by file hash (OCR is slow)."""
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    cache = os.path.join(W, "textcache", sha + ("" if ocr else "-noocr") + ".json")
    if os.path.exists(cache):
        return tuple(json.load(open(cache, encoding="utf-8")))
    out = _extract(path, ocr)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(list(out), open(cache, "w", encoding="utf-8"))
    return out


def _extract(path, ocr=True):
    ext = os.path.splitext(path)[1].lower()
    info = {}
    if ext == ".pdf":
        import pymupdf
        doc = pymupdf.open(path)
        info["pages"] = doc.page_count
        title = (doc.metadata or {}).get("title") or ""
        info["author"] = (doc.metadata or {}).get("author") or ""
        parts, scanned = [], []
        force = bool(FORCE_OCR and re.search(FORCE_OCR, path, re.I))   # garbled text layer: OCR every page
        for i, pg in enumerate(doc):
            t = "" if force else pg.get_text().strip()
            if force or (len(t) < 40 and pg.get_images()):
                scanned.append(i)
            if t:
                parts.append(f"[Page {i + 1}]\n\n{t}")
        if scanned and ocr:
            import importlib
            o = importlib.import_module("31_ocr_pdfs")
            for i in scanned:
                t = o.page_text(o.ocr_page(doc[i]))
                if t:
                    parts.append(f"[Page {i + 1} - OCR]\n\n{t}")
            parts.sort(key=lambda p: int(re.match(r"\[Page (\d+)", p).group(1)))
            info["ocr_pages"] = len(scanned)
        elif scanned:
            info["scanned_pages_not_ocrd"] = len(scanned)
        return title, "\n\n".join(parts), info
    if ext == ".docx":
        z = zipfile.ZipFile(path)
        xml = z.read("word/document.xml").decode("utf-8", "replace")
        core = z.read("docProps/core.xml").decode("utf-8", "replace") if "docProps/core.xml" in z.namelist() else ""
        m = re.search(r"<dc:title>([^<]*)</dc:title>", core)
        return (html.unescape(m.group(1)) if m else ""), xml_text(xml, "w:p", "w:t"), info
    if ext == ".pptx":
        z = zipfile.ZipFile(path)
        slides = sorted((n for n in z.namelist() if re.match(r"ppt/(slides|notesSlides)/\w+?\d+\.xml$", n)),
                        key=lambda n: (n.startswith("ppt/notes"), int(re.search(r"(\d+)\.xml$", n).group(1))))
        return "", "\n\n".join(xml_text(z.read(n).decode("utf-8", "replace"), "a:p", "a:t") for n in slides), info
    if ext == ".odt":
        z = zipfile.ZipFile(path)
        return "", xml_text(z.read("content.xml").decode("utf-8", "replace"), "text:p", ""), info
    if ext == ".epub":
        z = zipfile.ZipFile(path)
        pages = sorted(n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        texts, title = [], ""
        for n in pages:
            t, md = strip_html(z.read(n).decode("utf-8", "replace"))
            title = title or t
            texts.append(md)
        return title, "\n\n".join(texts), info
    if ext == ".doc":
        aw = find_antiword()
        if not aw:
            raise RuntimeError("old Word .doc files need antiword - run Setup (it comes with Git for Windows)")
        r = subprocess.run([aw, "-w", "0", path], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError("antiword failed: " + r.stderr.decode("utf-8", "replace")[:200])
        return "", r.stdout.decode("utf-8", "replace"), info
    raw = open(path, "rb").read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            s = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    if ext in (".html", ".htm"):
        return (*strip_html(s), info)
    if ext == ".rtf":
        s = re.sub(r"\\par[d]?", "\n", s)
        s = re.sub(r"\{\\\*[^{}]*\}|\\[a-z]+-?\d* ?|[{}]", "", s)
        return "", s.strip(), info
    return "", s, info   # .txt / .md


def guess_title(title, text, path):
    t = (title or "").strip()
    if len(t) < 4 or re.match(r"(untitled|microsoft word|document\d*|slide \d+)", t, re.I):
        for line in text.splitlines():
            line = re.sub(r"^\[Page \d+.*\]$|^#+\s*", "", line.strip()).strip()
            if 6 <= len(line) <= 120 and re.search(r"[A-Za-z]{3}", line):
                t = line; break
    if len(t) < 4:
        t = os.path.splitext(os.path.basename(path))[0].replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", t)[:150]


# ---------------------------------------------------------------- duplicate detection
def norm_words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def fingerprint(text, k=8, mod=16, cap=400):
    """Sampled hashed k-word shingles (kept when hash % mod == 0): a compact, order-free text signature."""
    w = norm_words(text)
    fp = set()
    for i in range(max(len(w) - k + 1, 0)):
        h = int(hashlib.md5(" ".join(w[i:i + k]).encode()).hexdigest()[:12], 16)
        if h % mod == 0:
            fp.add(h)
            if len(fp) >= cap:
                break
    return fp


def library_files():
    for c in CATEGORIES:
        d = os.path.join(RESEARCH, c)
        for root, _, fs in os.walk(d):   # includes course folders such as recipes/<course>/<module>/
            for f in fs:
                if f.endswith(".md"):
                    yield os.path.join(root, f)


def load_index(rebuild=False):
    """Fingerprints + sha256 of every library file, cached and updated incrementally by file mtime."""
    path = os.path.join(W, "fingerprints.json")
    idx = {} if rebuild or not os.path.exists(path) else json.load(open(path, encoding="utf-8"))
    seen, changed = set(), 0
    for f in library_files():
        rel = os.path.relpath(f, RESEARCH)
        seen.add(rel)
        mt = int(os.path.getmtime(f))
        if rel in idx and idx[rel]["mtime"] == mt:
            continue
        txt = open(f, encoding="utf-8", errors="replace").read()
        head, _, body = txt.partition("\n---\n")
        shas = re.findall(r"^(?:sha256|sha256_before_ocr|original_sha256): \"?([0-9a-f]{64})", head, re.M)
        idx[rel] = {"mtime": mt, "sha": shas, "fp": sorted(fingerprint(body))}
        changed += 1
        if changed % 2000 == 0:
            print(f"  indexing library... {changed}", flush=True)
    for rel in set(idx) - seen:
        del idx[rel]
    if changed:
        json.dump(idx, open(path, "w", encoding="utf-8"))
    return idx


# ---------------------------------------------------------------- review (dry run)
def review(folder, min_score, ocr, rebuild):
    print("Loading library index (first run takes a few minutes)...", flush=True)
    idx = load_index(rebuild)
    sha_to = {s: rel for rel, v in idx.items() for s in v["sha"]}
    inv = defaultdict(set)
    for rel, v in idx.items():
        for h in v["fp"]:
            inv[h].add(rel)
    rows, batch_sha, batch_fp = [], {}, {}
    files = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs]
    print(f"Scanning {len(files)} files in {folder}", flush=True)
    for n, path in enumerate(sorted(files), 1):
        ext = os.path.splitext(path)[1].lower()
        row = {"file": path, "decision": "", "category": "", "score": "", "title": "", "words": "", "reason": "", "matches": "", "sha256": ""}
        if ext not in EXT:
            row.update(decision="unsupported", reason=f"file type {ext or '(none)'} not handled"); rows.append(row); continue
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        row["sha256"] = sha
        if sha in sha_to:
            row.update(decision="duplicate", reason="identical file already in library", matches=sha_to[sha]); rows.append(row); continue
        if sha in batch_sha:
            row.update(decision="duplicate", reason="identical to another file in this folder", matches=batch_sha[sha]); rows.append(row); continue
        batch_sha[sha] = path
        try:
            title, text, info = extract(path, ocr)
        except Exception as e:
            row.update(decision="unreadable", reason=f"{type(e).__name__}: {e}"[:200]); rows.append(row); continue
        words = len(text.split())
        title = guess_title(title, text, path)
        row.update(title=title, words=words)
        if words < 80:
            row.update(decision="unreadable", reason="little or no extractable text"
                       + (" (scanned PDF - rerun without --no-ocr)" if info.get("scanned_pages_not_ocrd") else "")); rows.append(row); continue
        fp = fingerprint(text)
        # near-duplicate: share of this file's fingerprint found in one library file / earlier batch file
        hits = Counter(rel for h in fp for rel in inv.get(h, ()))
        best = hits.most_common(1)
        if fp and best and best[0][1] / len(fp) >= 0.6:
            row.update(decision="near-duplicate", reason=f"{best[0][1] * 100 // len(fp)}% of its text is already in the library",
                       matches=best[0][0]); rows.append(row); continue
        dup_b = next((p for p, f2 in batch_fp.items() if fp and len(fp & f2) / len(fp) >= 0.6), None)
        if dup_b:
            row.update(decision="near-duplicate", reason="same text as another file in this folder", matches=dup_b); rows.append(row); continue
        batch_fp[path] = fp
        cat, score, second, nd = relevance(text, title)
        row.update(category=cat, score=score)
        if score < min_score or nd < MIN_DISTINCT:
            row.update(decision="not-relevant", reason=f"relevance score {score} (min {min_score}), {nd} distinct topic terms (min {MIN_DISTINCT})")
        else:
            row.update(decision="add", reason=f"relevant ({cat}; also {second})" + (f"; OCR'd {info['ocr_pages']} pages" if info.get("ocr_pages") else ""))
        rows.append(row)
        print(f"  [{n}/{len(files)}] {row['decision']:13} {os.path.basename(path)[:60]}", flush=True)
    out = os.path.join(W, "ingest_" + datetime.datetime.now().strftime("%Y%m%d-%H%M") + ".csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["file"])
        w.writeheader(); w.writerows(rows)
    c = Counter(r["decision"] for r in rows)
    print("\nSummary:", dict(c))
    print("Review report:", out)
    print("Edit decision/category/title if you like, then run:\n  _scripts\\.venv\\Scripts\\python _scripts\\50_ingest_folder.py --apply \"" + out + "\"")


# ---------------------------------------------------------------- apply
def apply(report, ocr):
    rows = list(csv.DictReader(open(report, encoding="utf-8-sig")))
    reg = SlugRegistry()
    added = 0
    for r in rows:
        if r["decision"].strip().lower() != "add":
            continue
        cat = r["category"].strip()
        if cat not in CATEGORIES:
            print("  skipped (unknown category):", r["file"], cat); continue
        path = r["file"]
        try:
            title, text, info = extract(path, ocr)
        except Exception as e:
            print(f"  FAILED (not added): {path}: {type(e).__name__}: {e}"[:300], flush=True); continue
        title = r["title"].strip() or guess_title(title, text, path)
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        ext = os.path.splitext(path)[1].lower()
        slug = reg.claim(slugify(title)[:100], "user:" + sha)
        d = cat_dir(cat)
        keep_original = ext not in (".txt", ".md", ".markdown")
        if keep_original:
            dst = os.path.join(d, slug + ext)
            if os.path.exists(dst):
                os.chmod(dst, 0o666); os.remove(dst)
            shutil.copy2(path, dst)
            os.chmod(dst, 0o666)   # don't carry a read-only attribute into the library
        meta = {"title": title, "category": cat, "source_type": "pdf" if ext == ".pdf" else "document",
                "file": (slug + ext) if keep_original else None,
                "publisher": info.get("author") or "User-provided document",
                "source_url": None, "provenance": f"User-provided file: {path} (added {TODAY})",
                "license": "Unknown - user-provided document; verify before redistribution",
                "pages": info.get("pages"), "sha256": sha, "words": len(text.split()),
                "ocr": {"pages_ocrd": info["ocr_pages"], "engine": "RapidOCR"} if info.get("ocr_pages") else None,
                "compiled": TODAY}
        body = [front_matter(meta), f"# {title}\n",
                f"**Source:** user-provided file `{os.path.basename(path)}`  ",
                f"**License:** {meta['license']}  "]
        if keep_original:
            body.append(f"**Original file:** [{slug + ext}]({slug + ext})")
        body += ["", "## Full text\n", text.strip()]
        open(os.path.join(d, slug + ".md"), "w", encoding="utf-8").write("\n".join(body) + "\n")
        added += 1
        print(f"  added  {cat}/{slug}.md", flush=True)
        if added % 25 == 0:
            reg.save()
    reg.save()
    print(f"\n{added} files added. Updating catalog and README...", flush=True)
    py = sys.executable
    subprocess.run([py, os.path.join(os.path.dirname(__file__), "20_catalog.py")])
    subprocess.run([py, os.path.join(os.path.dirname(__file__), "21_readme.py")])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", help="folder to scan (review step)")
    ap.add_argument("--apply", metavar="REPORT_CSV", help="add the rows marked 'add' in a review report")
    ap.add_argument("--min-score", type=float, default=8)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--rebuild-index", action="store_true")
    a = ap.parse_args()
    if a.apply:
        apply(a.apply, not a.no_ocr)
    elif a.folder and os.path.isdir(a.folder):
        review(a.folder, a.min_score, not a.no_ocr, a.rebuild_index)
    else:
        ap.print_help()
