"""List everything in E:\\AIPortable that was NOT carried into E:\\Research, with the reason.

Writes:
  E:\\Research\\EXCLUDED.csv                  one row per excluded file (PDFs, web pages, Kiwix docs, WikEM,
                                              Wikipedia export files, library image folders)
  E:\\Research\\EXCLUDED_wikipedia_titles.csv  the original library's Wikipedia title list items not included
Columns: collection, file, title, pages, size_mb, reason, reason_basis, same_as
  reason_basis = recorded       (identical-file match, rule filter, drop list or removal log)
                 content-check  (text compared with the library just now: same content already included)
                 reconstructed  (manual-review drop; reason inferred from the title and opening text)
Any excluded file can be added back with 50_ingest_folder.py."""
import ast, csv, glob, importlib, json, os, re, sys
from collections import Counter
from difflib import SequenceMatcher
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

W = os.path.join(RESEARCH, "_work")
TI, TD = r"E:\AIPortable\tempDocsInstalled", r"E:\AIPortable\tempDocs"
ing = importlib.import_module("50_ingest_folder")
rows = []


def add(collection, file, title, reason, basis, same_as="", pages="", size=None):
    rows.append({"collection": collection, "file": file, "title": title, "pages": pages,
                 "size_mb": round(size / 1e6, 1) if size else "", "reason": reason, "reason_basis": basis, "same_as": same_as})


def norm(t):
    t = re.sub(r"\(.*?\)|\b(19|20)\d\d\b|\bedition\b|\bed\.?\b|\brev(ision)?\b|\bvolume\b|\bvol\b|\.pdf$", " ", (t or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


print("Loading library text index...", flush=True)
idx = ing.load_index()
inv_fp = {}
for rel, v in idx.items():
    for h in v["fp"]:
        inv_fp.setdefault(h, set()).add(rel)


def content_match(text):
    fp = ing.fingerprint(text)
    if len(fp) < 5:
        return None
    hits = Counter(r for h in fp for r in inv_fp.get(h, ()))
    if hits:
        rel, n = hits.most_common(1)[0]
        if n / len(fp) >= 0.5:
            return rel.replace("\\", "/"), int(100 * n / len(fp))
    return None


# ------------------------------------------------------------------ PDFs
units = json.load(open(os.path.join(W, "pdf_unique.json"), encoding="utf-8"))
inv = json.load(open(os.path.join(W, "pdf_inventory.json"), encoding="utf-8"))
dec = {}
for f in sorted(glob.glob(os.path.join(W, "pdf_decisions_*.txt"))):
    for l in open(f, encoding="utf-8"):
        if l.startswith("#") or "|" not in l:
            continue
        p = [x.strip() for x in l.rstrip("\n").split("|")]
        dec[p[0]] = p[1:]
built = {b["key"]: b for b in json.load(open(os.path.join(W, "built_pdfs.json"), encoding="utf-8"))}
kept_titles = {k: norm(b["title"]) for k, b in built.items()}

# 1) byte-identical copies: every inventory file beyond the first path of its unit
by_sha = {u["sha256"]: u for u in units}
for it in inv:
    u = by_sha.get(it["sha256"])
    if not u or os.path.normcase(it["path"]) == os.path.normcase(u["paths"][0]):
        continue
    if u["key"] in built:
        b = built[u["key"]]
        add("PDF", it["path"], it["file"], "identical copy of a PDF that is in the library", "recorded",
            f"{b['category']}/{b['slug']}.pdf", it.get("pages", ""), it.get("size"))
    else:
        add("PDF", it["path"], it["file"], "identical copy of another excluded PDF (see its row)", "recorded",
            u["paths"][0], it.get("pages", ""), it.get("size"))

# 2) unique PDFs dropped in review
BUCKETS = [
    (r"magazine|newsletter|\bissue\b|\bquarterly\b|monthly|bulletin no", "periodical issue (magazine/newsletter), not a reference work"),
    (r"thesis|dissertation|\bjournal\b|proceedings|scopus|\bdoi\b|international research|et al\b|abstract", "academic paper or thesis (research, not practical instructions)"),
    (r"\b(gun|rifle|pistol|carbine|howitzer|mortar|cannon|machine gun|grenade|launcher|missile|ammunition|artillery|tank)\b",
     "weapon- or ordnance-specific technical manual"),
    (r"\b(mep|tqg|tm \d|technical manual|parts list|rpstl|lubrication order)\b", "equipment-specific military technical manual (model/parts detail)"),
    (r"hack|penetration testing|malware|linux|windows|software|programming|python|network security|cyber", "computing / IT topic"),
    (r"novel|fiction|steampunk|story|stories|poem|memoir", "fiction or general reading"),
    (r"missouri|county|state of|veterans|benefits|grant|policy|annual report|strategic plan|legislat|regulation", "regional, administrative or policy document"),
    (r"history of|historical|world war|civil war|campaign|biography", "history rather than practical guidance"),
]
TOL = re.compile(r"\b(the|and|of|to|in|is|for|with|that|on)\b", re.I)
done = 0
for u in units:
    d = dec.get(u["key"])
    if u["key"] in built or not d or d[0] not in ("X", "CHECK"):
        continue
    title = u.get("title") or u.get("pdf_title") or os.path.basename(u["paths"][0])
    path, head = u["paths"][0], (u.get("head") or "")
    reason, basis, same = "", "reconstructed", ""
    nt = norm(title)
    best = max(((SequenceMatcher(None, nt, kt).ratio(), k) for k, kt in kept_titles.items() if kt), default=(0, None))
    if best[0] >= 0.8:
        b = built[best[1]]
        reason, basis, same = "another edition/copy of the same document is in the library", "recorded", f"{b['category']}/{b['slug']}.md"
    if not reason and os.path.exists(path):
        try:
            import pymupdf
            doc = pymupdf.open(path)
            text = " ".join(doc[i].get_text() for i in range(min(doc.page_count, 40)))
            m = content_match(text)
            if m:
                reason, basis, same = f"same content already in the library ({m[1]}% shared text)", "content-check", m[0]
            elif len(text.split()) > 200 and len(TOL.findall(text)) / max(len(text.split()), 1) < 0.02:
                reason = "not in English"
        except Exception:
            pass
    if not reason and d[0] == "CHECK":
        reason = "file content does not match its title (mislabelled/garbled scan)"
    if not reason:
        blob = f"{title} {head[:400]}".lower()
        reason = next((r for rx, r in BUCKETS if re.search(rx, blob)), "")
    if not reason and not u.get("has_text"):
        reason = "scanned without text layer and judged not relevant from its title"
    if not reason:
        reason = "judged not relevant to practical survival / self-reliance in manual review"
    add("PDF", path, title, reason, basis, same, u.get("pages", ""), u.get("size"))
    done += 1
    if done % 100 == 0:
        print(f"  PDFs checked: {done}", flush=True)

# ------------------------------------------------------------------ government / web exports
src11 = open(os.path.join(os.path.dirname(__file__), "11_build_web.py"), encoding="utf-8").read()
tree = ast.parse(src11)
consts = {t.targets[0].id: ast.literal_eval(t.value) for t in tree.body
          if isinstance(t, ast.Assign) and isinstance(t.targets[0], ast.Name) and t.targets[0].id in ("DROP", "PUBLISHERS")}
SPANISH_RE = re.compile(r"(-spanish$|^el-secado|^la-congelacion|^congelacion|^papas-y-batatas)")
removed = {}
if os.path.exists(os.path.join(W, "removed_duplicates.txt")):
    for l in open(os.path.join(W, "removed_duplicates.txt"), encoding="utf-8"):
        if "\t" in l:
            f, why = l.rstrip("\n").split("\t", 1)
            removed[os.path.basename(f)] = why
from common import slugify
built_web = {(b["src"], b["slug"]) for b in json.load(open(os.path.join(W, "built_web.json"), encoding="utf-8"))}
PFX = {"medlineplus": "medlineplus", "cdc": "cdc", "cisa": "cisa", "epa": "epa", "ftc": "ftc", "nih": "nih-medlineplus", "nws": "nws",
       "readygov": "ready-gov", "usfa": "usfa", "energystar": "energy-star", "nchfp": "nchfp"}
for src in consts["PUBLISHERS"]:
    mf = os.path.join(TI, src, "manifest.json")
    if not os.path.exists(mf):
        continue
    for m in json.load(open(mf, encoding="utf-8")):
        stem = os.path.splitext(m["file"])[0]
        short = stem[len("nchfp-"):] if src == "nchfp" else stem
        path = os.path.join(TI, src, m["file"])
        title = m.get("title") or stem
        slug = slugify(f"{PFX[src]}-{short.replace(PFX[src] + '-', '')}")
        was_built = any((src, s2) in built_web for s2 in (slug, slug + "-2", slug + "-3"))
        if was_built:
            why = removed.get(slug + ".md")
            if why:
                add(f"web: {src}", path, title, why, "recorded")
            continue
        if not os.path.exists(path):
            add(f"web: {src}", path, title, "file missing in export (fetch failed)", "recorded")
        elif short in consts["DROP"].get(src, ()):
            add(f"web: {src}", path, title, "judged off-topic (drop list)", "recorded")
        elif src == "nchfp" and SPANISH_RE.search(short):
            add(f"web: {src}", path, title, "Spanish-language duplicate of an English page that is included", "recorded")
        else:
            add(f"web: {src}", path, title, "empty or near-empty page (under 40 words of text)", "recorded")

# ------------------------------------------------------------------ Kiwix field-guide docs
man = {os.path.splitext(m["file"])[0].replace("-field-guide", ""): m
       for m in json.load(open(os.path.join(TI, "kiwix", "manifest.json"), encoding="utf-8"))}
for l in open(os.path.join(W, "kiwix_decisions.txt"), encoding="utf-8"):
    if l.startswith("#") or "|" not in l:
        continue
    p = l.rstrip("\n").split("|")
    if p[1] != "X" or p[0] not in man:
        continue
    m = man[p[0]]
    path = os.path.join(TI, "kiwix", m["file"])
    txt = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else ""
    first = next((x.strip("# ").strip() for x in txt.splitlines()[1:40] if len(x.strip()) > 15), "")
    cm = content_match(txt)
    if cm:
        add("Kiwix field guide", path, f"{m['title']} - {first[:90]}", f"same content already in the library ({cm[1]}% shared text)",
            "content-check", cm[0])
    else:
        add("Kiwix field guide", path, f"{m['title']} - {first[:90]}",
            "judged not relevant or a duplicate of a kept PDF in manual review", "reconstructed")

# ------------------------------------------------------------------ WikEM export
for stem in ("massive-transfusion-protocol",):
    add("WikEM export", os.path.join(TD, "wikem-emergency-medicine", stem + ".html"), stem.replace("-", " "),
        "hospital-only procedure (blood bank protocol)", "recorded")

# ------------------------------------------------------------------ Wikipedia (export files + original title list)
wr = importlib.import_module("wiki_rules")
feats = [json.loads(l) for l in open(os.path.join(W, "wiki_features.jsonl"), encoding="utf-8")]
built_wiki = {b["path"] for b in json.load(open(os.path.join(W, "built_wiki.json"), encoding="utf-8"))}
species = set(json.load(open(os.path.join(W, "species_paths.json"), encoding="utf-8")))
reviewed = {r["path"] for r in json.load(open(os.path.join(W, "wiki_review.json"), encoding="utf-8"))}
wrows = []
for rec in feats:
    p = rec.get("path")
    if p in built_wiki or p in species:
        continue
    why = wr.rule_drop(rec)
    if why:
        reason, basis = f"rule filter: {why}", "recorded"
    elif p in reviewed:
        reason, basis = "not selected in manual review (not practical survival content)", "recorded"
    elif (rec.get("words") or 0) < 60:
        reason, basis = "stub article (under 60 words)", "recorded"
    else:
        reason, basis = "not selected", "recorded"
    wrows.append({"title": rec.get("title") or rec.get("seed"), "wikipedia_path": p, "reason": reason, "reason_basis": basis})
wp_by_title = {norm(r["title"]): r for r in wrows}
lib_titles = {norm((r["title"] or "").split(" (")[0]) for r in json.load(open(os.path.join(RESEARCH, "CATALOG.json"), encoding="utf-8"))}
for f in glob.glob(os.path.join(TI, "wikipedia", "*.md")):
    first = open(f, encoding="utf-8", errors="replace").readline().lstrip("# ").strip()
    r = wp_by_title.get(norm(first))
    if r:
        add("Wikipedia export", f, first, r["reason"], r["reason_basis"])
    elif norm(first) not in lib_titles:
        add("Wikipedia export", f, first, "title not found in the current Wikipedia (renamed or merged); may be included under "
            "another name (e.g. a species profile) - check manually", "reconstructed")

# ------------------------------------------------------------------ library image folders
R = json.load(open(os.path.join(RESEARCH, "CATALOG.json"), encoding="utf-8"))
titles = {norm(r["title"].split(" (")[0]) for r in R if r["title"]}
libimg = r"E:\AIPortable\data\library\images"
for d in sorted(os.listdir(libimg)):
    nd = norm(re.sub(r"\s*\(\d+\)$", "", d))
    if nd in titles:
        continue
    n = len(os.listdir(os.path.join(libimg, d)))
    if re.search(r"\(\d+\)$", d):
        reason = "second image set for a topic/species that is included under its main name"
    else:
        reason = "topic not included in the library (images belonged to a dropped article, or the species is included under another name)"
    add("library images", os.path.join(libimg, d), f"{d} ({n} images)", reason, "reconstructed")

# ------------------------------------------------------------------ write
out = os.path.join(RESEARCH, "EXCLUDED.csv")
with open(out, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(sorted(rows, key=lambda r: (r["collection"], r["reason"], r["title"].lower())))
with open(os.path.join(RESEARCH, "EXCLUDED_wikipedia_titles.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(wrows[0].keys()))
    w.writeheader(); w.writerows(sorted(wrows, key=lambda r: (r["reason"], r["title"].lower())))
print(f"\nEXCLUDED.csv: {len(rows)} rows")
for (c, why), n in sorted(Counter((r["collection"], r["reason"]) for r in rows).items(), key=lambda x: (x[0][0], -x[1])):
    print(f"  {n:5}  {c:18} {why[:95]}")
print(f"EXCLUDED_wikipedia_titles.csv: {len(wrows)} titles;", dict(Counter(r["reason"].split(':')[0] for r in wrows)))
