"""Build the Wardee Harmon / GNOWFGLINS "Traditional Cooking School" eCourse as one course folder in the library:

  recipes/wardee-traditional-cooking-school.md            course index
  recipes/wardee-traditional-cooking-school/<module>/     videos, audio, ebook PDFs + their .md, <module>.md lesson list

Moves (same drive, instant) the course files from E:\\Homesteading\\Wardee and the Wardee ebooks already in the
library into their module folders. Certificates and the duplicate Herbs & Essential Oils zip stay behind.

  _scripts\\.venv\\Scripts\\python _scripts\\55_build_wardee_course.py [--apply]
"""
import os, re, shutil, sys
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter, slugify
from categories import CATEGORIES

SRC = r"E:\Homesteading\Wardee"
SLUG = "wardee-traditional-cooking-school"
CAT = "recipes"
COURSE = os.path.join(RESEARCH, CAT, SLUG)
TITLE = "Traditional Cooking School by GNOWFGLINS (Wardee Harmon) - eCourse Collection"
MEDIA = {".mp4": "Video", ".m4v": "Video", ".mp3": "Audio"}
LEAVE = re.compile(r"completion_certificate|superbundle2017\.zip$|^wardee\.docx$", re.I)


def module_of(rel):
    """rel = path relative to the Wardee folder -> (folder slug, display name, order)."""
    top = rel.split(os.sep)[0] if os.sep in rel else ""
    m = re.match(r"(\d+)\s*-\s*(.+)", top)
    if m:
        return f"{int(m.group(1)):02d}-{slugify(m.group(2).strip())}", f"Module {int(m.group(1))}: {m.group(2).strip()}", int(m.group(1))
    if top.lower() == "cultures for health":
        return "cultures-for-health", "Cultures for Health eBooks", 90
    if top.lower() == "menu plans":
        return "menu-plans", "Menu Plans", 91
    return "extras", "Extras: Roundtables, Q&A and eBooklets", 99


def link(rel):
    return quote(rel.replace(os.sep, "/"), safe="/")


def plan():
    moves, lib_moves = [], []
    for root, _, fs in os.walk(SRC):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, SRC)
            if LEAVE.search(f) and (f.lower() != "wardee.docx" or root != SRC):
                continue
            if LEAVE.search(f):
                continue
            mod = module_of(rel)
            moves.append((p, os.path.join(COURSE, mod[0], f), mod))
    for c in CATEGORIES:
        d = os.path.join(RESEARCH, c)
        for f in os.listdir(d):
            if not f.endswith(".md"):
                continue
            head = open(os.path.join(d, f), encoding="utf-8").read(4000).partition("\n---\n")[0]
            pv = re.search(r'^provenance: "User-provided file: (.*) \(added', head, re.M)
            if not pv:
                continue
            src = pv.group(1).replace("\\\\", "\\")
            if not (src.lower().startswith(SRC.lower() + "\\") or src.lower() == r"e:\homesteading\wardee.docx"):
                continue
            rel = os.path.relpath(src, SRC) if src.lower().startswith(SRC.lower() + "\\") else "Wardee.docx"
            orig = re.search(r'^file: "(.*)"$', head, re.M)
            lib_moves.append((c, f, orig.group(1) if orig else None, module_of(rel)))
    return moves, lib_moves


def main():
    apply = "--apply" in sys.argv or "--pages" in sys.argv
    moves, lib_moves = plan()
    modules = {}
    if "--pages" in sys.argv:   # rebuild module/index pages only, from the existing course folders
        moves, lib_moves = [], []
        for sub in os.listdir(COURSE):
            page = os.path.join(COURSE, sub, sub + ".md")
            if os.path.exists(page):
                name = re.search(r'^course_module: "(.*)"$', open(page, encoding="utf-8").read(3000), re.M).group(1)
                order = int(sub[:2]) if sub[:2].isdigit() else {"cultures-for-health": 90, "menu-plans": 91}.get(sub, 99)
                modules[(sub, name, order)] = {"files": [], "docs": []}
    for _, dst, mod in moves:
        modules.setdefault(mod, {"files": [], "docs": []})["files"].append(os.path.basename(dst))
    for c, f, orig, mod in lib_moves:
        modules.setdefault(mod, {"files": [], "docs": []})["docs"].append((c, f, orig))
    for mod in sorted(modules, key=lambda m: m[2]):
        v = modules[mod]
        kinds = {}
        for fn in v["files"]:
            k = MEDIA.get(os.path.splitext(fn)[1].lower(), "Other")
            kinds[k] = kinds.get(k, 0) + 1
        print(f"{mod[0]:32} {kinds}  library docs: {len(v['docs'])}")
    print(f"{len(moves)} course files to move from Homesteading, {len(lib_moves)} library entries to move into the course")
    if not apply:
        return

    # 1) move course files out of Homesteading
    for src, dst, _ in moves:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.chmod(src, 0o666)
        shutil.move(src, dst)
    # 2) move the library entries (md + original) into their module and re-home them in `recipes`
    for c, f, orig, mod in lib_moves:
        dst_dir = os.path.join(COURSE, mod[0])
        os.makedirs(dst_dir, exist_ok=True)
        txt = open(os.path.join(RESEARCH, c, f), encoding="utf-8").read()
        head, sep, body = txt.partition("\n---\n")
        head = re.sub(r'^category: ".*"$', f'category: "{CAT}"', head, flags=re.M)
        head += f'\ncourse: "{SLUG}"\ncourse_module: "{mod[1]}"\ntopic_category: "{c}"'
        open(os.path.join(dst_dir, f), "w", encoding="utf-8").write(head + sep + body)
        os.remove(os.path.join(RESEARCH, c, f))
        if orig:
            shutil.move(os.path.join(RESEARCH, c, orig), os.path.join(dst_dir, orig))
    # 3) module pages
    index_rows = []
    for mod in sorted(modules, key=lambda m: m[2]):
        d = os.path.join(COURSE, mod[0])
        files = sorted(os.listdir(d), key=str.lower)
        docs = [f for f in files if f.endswith(".md") and f != mod[0] + ".md"]
        vids = [f for f in files if MEDIA.get(os.path.splitext(f)[1].lower()) == "Video"]
        auds = [f for f in files if MEDIA.get(os.path.splitext(f)[1].lower()) == "Audio"]
        lessons = [f for f in vids if not re.search(r"#askwar|roundtable", f, re.I)]
        qa = [f for f in vids if f not in lessons]
        linked = set()
        for m in docs:
            h = open(os.path.join(d, m), encoding="utf-8").read(4000)
            o = re.search(r'^file: "(.*)"$', h, re.M)
            if o: linked.add(o.group(1))
        other = [f for f in files if f not in docs and f not in vids and f not in auds and f not in linked and f != mod[0] + ".md"]
        doc_lines = []
        for m in docs:
            h = open(os.path.join(d, m), encoding="utf-8").read(4000)
            t = re.search(r'^title: "(.*)"$', h, re.M).group(1)
            o = re.search(r'^file: "(.*)"$', h, re.M)
            doc_lines.append(f"- [{t}]({link(m)})" + (f" - original: [{o.group(1)}]({link(o.group(1))})" if o else ""))
        sec = lambda name, lst: ([f"## {name} ({len(lst)})", ""] + [f"- [{os.path.splitext(x)[0]}]({link(x)})" for x in lst] + [""]) if lst else []
        meta = {"title": f"{mod[1]} - Traditional Cooking School (Wardee Harmon)", "category": CAT,
                "source_type": "course-module", "publisher": "GNOWFGLINS / Traditional Cooking School (Wardee Harmon)",
                "source_url": None, "course": SLUG, "course_module": mod[1],
                "provenance": f"User-provided eCourse files from E:\\Homesteading\\Wardee (organised {TODAY})",
                "license": "Commercial course material purchased by the owner - personal use only, do not redistribute",
                "videos": len(vids), "audio": len(auds), "documents": len(docs), "compiled": TODAY}
        body = [front_matter(meta), f"# {mod[1]}\n", f"Part of [{TITLE}](../../{SLUG}.md).  ",
                "Video and audio links open in your default player.\n"]
        if doc_lines:
            body += [f"## eBooks and handouts ({len(doc_lines)})", ""] + doc_lines + [""]
        body += sec("Lesson videos", lessons) + sec("Q&A and bonus videos", qa) + sec("Audio lessons", auds) + sec("Other files", other)
        open(os.path.join(d, mod[0] + ".md"), "w", encoding="utf-8").write("\n".join(body) + "\n")
        index_rows.append(f"| [{mod[1]}]({SLUG}/{mod[0]}/{mod[0]}.md) | {len(vids)} | {len(auds)} | {len(docs)} |")
    # 4) course index
    meta = {"title": TITLE, "category": CAT, "source_type": "course",
            "publisher": "GNOWFGLINS / Traditional Cooking School (Wardee Harmon)", "source_url": "https://traditionalcookingschool.com",
            "provenance": f"User-provided eCourse files from E:\\Homesteading\\Wardee (organised {TODAY})",
            "license": "Commercial course material purchased by the owner - personal use only, do not redistribute",
            "compiled": TODAY}
    body = [front_matter(meta), f"# {TITLE}\n",
            "Wardee Harmon's traditional-foods eCourses: soaking and sprouting, sourdough, einkorn, cultured dairy, "
            "lacto-fermentation, dehydration, pressure cooking, allergy-free and outdoor cooking. Each module page lists its "
            "lesson videos (playable from the library folder), audio lessons and the course eBook PDFs with extracted text.\n",
            "| Module | Videos | Audio | Documents |", "|---|---|---|---|"] + index_rows
    open(os.path.join(RESEARCH, CAT, SLUG + ".md"), "w", encoding="utf-8").write("\n".join(body) + "\n")
    print("course built:", COURSE)


if __name__ == "__main__":
    main()
