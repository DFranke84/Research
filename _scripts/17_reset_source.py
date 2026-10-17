"""Delete the files built for one archive source so 15_build_zim_docs.py can rebuild them.
Filename claims in the slug registry are kept (a rebuild reuses the same names).
Usage: 17_reset_source.py <source>"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH

src = sys.argv[1]
bf = os.path.join(RESEARCH, "_work", f"built_zim_{src}.json")
built = json.load(open(bf, encoding="utf-8")) if os.path.exists(bf) else []
for b in built:
    base = os.path.join(RESEARCH, b["category"], b["slug"])
    if os.path.exists(base + ".md"):
        os.remove(base + ".md")
    if os.path.isdir(base + "_images"):
        shutil.rmtree(base + "_images")
if os.path.exists(bf):
    os.remove(bf)
print("reset", src, len(built), "files")
