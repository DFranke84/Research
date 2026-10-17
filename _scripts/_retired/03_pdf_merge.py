"""Collapse the PDF inventory to unique files (by sha256) and attach the best
available metadata from every manifest. Output: _work/pdf_unique.json + a
compact review listing _work/pdf_review.txt."""
import json, os, collections

W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work")
TI = r"E:\AIPortable\tempDocsInstalled"
TD = r"E:\AIPortable\tempDocs"

inv = json.load(open(os.path.join(W, "pdf_inventory.json"), encoding="utf-8"))

# filename -> manifest record, per folder label
man = {}
for label in ["archive-org", "team-archive", "local-pdf", "unattributed"]:
    for m in json.load(open(os.path.join(TI, label, "manifest.json"), encoding="utf-8")):
        man[(label, m["file"])] = m
for label in ["defense-field-manuals", "animal-tracks"]:
    for m in json.load(open(os.path.join(TD, label, "manifest.json"), encoding="utf-8")):
        man[(label, m["file"])] = m
# unattributed titles/urls from the normalized DB export
unat = {m["id"]: m for m in json.load(open(os.path.join(TI, "manifests", "unattributed.json"), encoding="utf-8"))}

groups = collections.defaultdict(list)
for r in inv:
    groups[r["sha256"]].append(r)

out = []
for sha, rs in groups.items():
    u = {"key": sha[:12], "sha256": sha, "size": rs[0]["size"], "pages": rs[0].get("pages"),
         "has_text": rs[0].get("has_text"), "head": rs[0].get("head", "")[:400],
         "pdf_title": rs[0].get("pdf_title", ""), "paths": [r["path"] for r in rs],
         "folders": sorted({r["folder"] for r in rs}), "files": sorted({r["file"] for r in rs})}
    titles, urls, lic, ids, cats, notes, ia = [], [], [], [], [], [], []
    for r in rs:
        if r.get("db_title"): titles.append(r["db_title"])
        if r.get("source_url"): urls.append(r["source_url"])
        if r.get("license"): lic.append(r["license"])
        if r.get("db_id"): ids.append(r["db_id"])
        if r.get("db_category"): cats.append(r["db_category"])
        m = man.get((r["folder"], r["file"]))
        if m:
            titles.append(m.get("title") or m.get("queried_as") or "")
            if m.get("source_url"): urls.append(m["source_url"])
            if m.get("license"): lic.append(m["license"])
            if m.get("id"): ids.append(m["id"])
            if m.get("archive_org_identifier"): ia.append(m["archive_org_identifier"])
            if m.get("note"): notes.append(m["note"])
            if m.get("id") in unat:
                titles.append(unat[m["id"]]["title"])
                if unat[m["id"]].get("source_url"): urls.append(unat[m["id"]]["source_url"])
    titles = [t for t in titles if t]
    u["title"] = max(titles, key=len) if titles else os.path.splitext(rs[0]["file"])[0]
    u["source_url"] = next(iter(dict.fromkeys(urls)), None)
    u["alt_urls"] = list(dict.fromkeys(urls))[1:]
    u["license"] = next(iter(dict.fromkeys(lic)), None)
    u["library_ids"] = sorted(set(ids))
    u["old_category"] = cats[0] if cats else None
    u["ia_identifier"] = ia[0] if ia else None
    u["notes"] = list(dict.fromkeys(notes))
    out.append(u)

out.sort(key=lambda u: u["title"].lower())
json.dump(out, open(os.path.join(W, "pdf_unique.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
with open(os.path.join(W, "pdf_review.txt"), "w", encoding="utf-8") as f:
    for u in out:
        t = u["title"].split(" | FAQ:")[0][:150]
        f.write(f"{u['key']} | {t} | p{u['pages']} | {'' if u['has_text'] else 'NOTEXT | '}{u['head'][:110]}\n")
print(len(out))
