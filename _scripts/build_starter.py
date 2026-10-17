"""Build Starter Library - turn the starter packs (<library>\\starter) into library pages.

Pick the packs you want; each one adds the listed articles (with their pictures) to the library's categories.
Packs built from an archive need it in _sources\\zim first (Get Archives.bat). The Wikipedia pack is fetched from
wikipedia.org unless you have a Wikipedia archive. Safe to stop and run again: finished items are skipped.

  Build Starter Library.bat                pick from a list
  build_starter.py --list                  just show the packs
  build_starter.py ifixit se-ham ...       build these packs (all = every pack whose archive is here)
"""
import importlib, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from archives import local_path
from common import CODES, RESEARCH

STARTER = os.path.join(RESEARCH, "starter")
HERE = os.path.dirname(os.path.abspath(__file__))
CODE_OF = {v: k for k, v in CODES.items()}


def item_url(pack, d):
    if pack["kind"] == "wikipedia":
        return "https://en.wikipedia.org/wiki/" + d["path"]
    if pack["kind"] == "stackexchange":
        return f"https://{pack['archive'][3:]}.stackexchange.com/{d['path']}"
    return d.get("source_url") or d.get("url")


def in_library():
    f = os.path.join(RESEARCH, "CATALOG.json")
    return {r.get("source_url") for r in json.load(open(f, encoding="utf-8"))} if os.path.exists(f) else set()


def load_packs():
    meta = json.load(open(os.path.join(STARTER, "packs.json"), encoding="utf-8"))["packs"]
    return [json.load(open(os.path.join(STARTER, m["pack"] + ".json"), encoding="utf-8")) for m in meta]


def build(pack):
    items = pack["items"]
    if pack["kind"] == "wikipedia":
        todo = [d for d in items if d["category"] in CODE_OF]
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n".join(f"{d['path']}:{CODE_OF[d['category']]}" for d in todo))
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "67_add_wiki_articles.py"), "--file", f.name])
        finally:
            os.remove(f.name)
    elif pack["kind"] == "zim":
        importlib.import_module("15_build_zim_docs").build(pack["archive"], docs=items)
    elif pack["kind"] == "stackexchange":
        importlib.import_module("18_stackexchange").build(pack["archive"][3:], sel=items)
    elif pack["kind"] == "web":
        importlib.import_module("68_add_web_page").add_pages([d for d in items if d["kind"] == "page"])
        importlib.import_module("69_add_pdf_link").add_pdfs([d for d in items if d["kind"] == "pdf"])


def main():
    args = sys.argv[1:]
    packs = load_packs()
    have = in_library()
    print("Starter packs - the choices another library was built from. Pick the ones you want.\n")
    rows = []
    for i, p in enumerate(packs, 1):
        done = sum(1 for d in p["items"] if item_url(p, d) in have)
        ready = p["kind"] in ("wikipedia", "web") or bool(local_path(p["archive"]))
        state = ("all built" if done == len(p["items"]) else f"{done:,} built" if done else "") or ("ready" if ready else "")
        if not ready:
            state = "needs its archive (Get Archives)"
        rows.append((i, p, ready, done))
        print(f"{i:3}. {p['title']:46} {len(p['items']):6,} items   {state}")
        if p.get("about") and "--list" not in args:
            print(f"       {p['about']}")
    if "--list" in args:
        return
    if not args:
        ans = input("\nType the numbers to build (e.g. 1 3), 'all' for every ready pack, or Enter to stop: ").strip()
        if not ans:
            return
        args = ["all"] if ans.lower() == "all" else [r[1]["pack"] for r in rows for a in ans.replace(",", " ").split() if a == str(r[0])]
    chosen = [r for r in rows if (args == ["all"] and r[2]) or r[1]["pack"] in args]
    for i, p, ready, done in chosen:
        if not ready:
            print(f"\nSkipping {p['title']}: download its archive first with Get Archives.bat")
            continue
        print(f"\n=== {p['title']}: {len(p['items']) - done:,} to build ===", flush=True)
        build(p)
    if chosen:
        print("\nUpdating the catalog...", flush=True)
        for script in ("20_catalog.py", "21_readme.py"):
            subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True)
        print("Done. Open Library Manager to browse what was added.")


if __name__ == "__main__":
    main()
