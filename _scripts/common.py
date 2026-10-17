"""Shared helpers for writing E:\\Research source files."""
import datetime, json, os, re

RESEARCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the library folder = the folder this _scripts folder is in (copy it anywhere)
TODAY = datetime.date.today().isoformat()

CODES = {
    "W": "water", "FS": "food-storage-preservation", "FP": "food-production",
    "FW": "foraging-wild-food", "HF": "hunting-fishing-trapping", "CF": "cooking-fire", "RC": "recipes",
    "MA": "medical-first-aid", "MC": "medical-conditions", "MP": "medicine-pharmacology",
    "SH": "sanitation-hygiene", "SC": "shelter-construction", "EP": "energy-power",
    "TC": "tools-crafts-skills", "MV": "mechanical-vehicles", "CR": "communications-radio",
    "NM": "navigation-mapping", "WS": "wilderness-survival", "EM": "emergency-preparedness",
    "CB": "cbrn-hazmat", "SD": "security-defense", "WX": "weather", "LF": "legal-financial",
    # GP/GF/GM/GR/GI/GB/GA field guides retired 2026-10-12 - species pages live in Local Area
}


def note_path(item_file, original=None):
    """An item's note: a .txt with the item's name, beside it (bread.md -> bread.txt, Apple Pie.mp4 -> Apple Pie.txt).
    If that name is taken by the item's own original file, the note is '<name> (note).txt'."""
    p = os.path.splitext(item_file)[0] + ".txt"
    if original and os.path.normcase(os.path.abspath(original)) == os.path.normcase(os.path.abspath(p)):
        p = os.path.splitext(item_file)[0] + " (note).txt"
    return p


def find_browser():
    """Google Chrome wherever it is installed, else Microsoft Edge (built into Windows). Both make the recipe PDFs."""
    import shutil
    bases = [os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
    for rel in (r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"):
        for b in filter(None, bases):
            if os.path.exists(os.path.join(b, rel)):
                return os.path.join(b, rel)
    return shutil.which("chrome") or shutil.which("msedge") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def find_antiword():
    """antiword (reads old Word .doc files): on PATH, or the copy that comes with Git for Windows."""
    import shutil
    for b in filter(None, [os.environ.get(k) for k in ("ProgramFiles", "LOCALAPPDATA")]):
        for rel in (r"Git\mingw64\bin\antiword.exe", r"Programs\Git\mingw64\bin\antiword.exe"):
            if os.path.exists(os.path.join(b, rel)):
                return shutil.which("antiword") or os.path.join(b, rel)
    return shutil.which("antiword")


def slugify(s, maxlen=110):
    s = s.lower().replace("&", " and ").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen].rstrip("-")


def yaml_val(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        if not v:
            return "[]"
        out = []
        for x in v:
            if isinstance(x, dict) and x:
                items = [f"{k}: {yaml_val(y)}" for k, y in x.items()]
                out.append("  - " + items[0] + "".join("\n    " + i for i in items[1:]))
            else:
                out.append("  - " + yaml_val(x))
        return "\n" + "\n".join(out)
    if isinstance(v, dict):
        if not v:
            return "{}"
        return "\n" + "\n".join(f"  {k}: {yaml_val(x)}" for k, x in v.items())
    return json.dumps(str(v), ensure_ascii=False)


def front_matter(meta):
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {yaml_val(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def cat_dir(category):
    d = os.path.join(RESEARCH, category)
    os.makedirs(d, exist_ok=True)
    return d


class SlugRegistry:
    """Guarantees unique file slugs across the whole E:\\Research tree."""
    def __init__(self, path=os.path.join(RESEARCH, "_work", "slug_registry.json")):
        self.path = path
        self.map = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}

    def claim(self, slug, owner):
        base, n = slug, 2
        while slug in self.map and self.map[slug] != owner:
            slug = f"{base}-{n}"; n += 1
        self.map[slug] = owner
        return slug

    def save(self):
        json.dump(self.map, open(self.path, "w", encoding="utf-8"), indent=0, ensure_ascii=False)
