"""Extract classification features for Wikipedia titles from the ZIM.

Input: a newline list of titles (default: every wikipedia doc in AIPortable's library.db).
Output: <library>/_work/wiki_features.jsonl  (title, path, cats, first sentence, words, images, infobox)
Resumable: skips titles already in the output.
"""
import json, os, re, sqlite3, sys
from urllib.parse import unquote
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(__file__))
from zimlib import resolve, page_meta, content_cats, first_para

OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_work", "wiki_features.jsonl")


def seed_titles():
    if len(sys.argv) > 1 and sys.argv[1] != "db":
        return [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    # AIPortable sits next to the Research folder (both inside AI-Research)
    aip_db = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "AIPortable", "data", "library.db")
    db = sqlite3.connect("file:" + aip_db + "?mode=ro", uri=True)
    out = []
    for title, url in db.execute("select title,source_url from library_docs where source='wikipedia'"):
        if url and "/wiki/" in url:
            out.append(unquote(url.split("/wiki/", 1)[1]))
        else:
            out.append(title)
    return out


def main():
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            done.add(json.loads(l)["seed"])
    f = open(OUT, "a", encoding="utf-8")
    titles = [t for t in dict.fromkeys(seed_titles()) if t not in done]
    print("todo", len(titles), flush=True)
    for i, t in enumerate(titles):
        rec = {"seed": t}
        e = resolve(t)
        if e is None:
            rec["missing"] = True
        else:
            html = bytes(e.get_item().content).decode("utf-8", "replace")
            meta = page_meta(html)
            soup = BeautifulSoup(html, "lxml")
            body = soup.find(id="mw-content-text") or soup
            ib = body.find("table", class_=re.compile("infobox"))
            ibtxt = ""
            if ib:
                cap = ib.find(["caption", "th"])
                ibtxt = " ".join((ib.get("class") or [])) + " | " + (cap.get_text(" ", strip=True)[:80] if cap else "")
            words = len(body.get_text(" ").split())
            rec.update(path=e.path, title=e.title, cats=content_cats(meta),
                       first=first_para(soup)[:400], words=words,
                       imgs=len(body.find_all("img")), infobox=ibtxt,
                       assess=list((meta.get("wgPageAssessments") or {}).keys()))
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if i % 50 == 0:
            f.flush(); print(i, flush=True)
    f.close()
    print("done")


main()
