"""Read a browser bookmarks export (Netscape bookmark HTML) and return the links inside chosen folders.
The format leaves <DT> unclosed, so it is read line by line, tracking <DL> nesting."""
import html, re

H3 = re.compile(r"<DT><H3[^>]*>(.*?)</H3>", re.I)
A = re.compile(r'<DT><A HREF="([^"]*)"([^>]*)>(.*?)</A>', re.I)


def folder_links(path, names):
    """{folder name: [(subfolder path, title, url, add_date)]} for each folder whose name is in `names` (case-insensitive)."""
    want = {n.lower() for n in names}
    out, stack, pending = {}, [], None   # stack of folder names (one per open <DL>)
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        m = H3.search(s)
        if m:
            pending = html.unescape(m.group(1)).strip(); continue
        if s.upper().startswith("<DL>"):
            stack.append(pending or ""); pending = None; continue
        if s.upper().startswith("</DL>"):
            if stack: stack.pop()
            continue
        a = A.search(s)
        if a:
            top = next((i for i, f in enumerate(stack) if f.lower() in want), None)
            if top is not None:
                d = re.search(r'ADD_DATE="(\d+)"', a.group(2))
                out.setdefault(stack[top], []).append((" / ".join(stack[top + 1:]), html.unescape(a.group(3)).strip(),
                                                       html.unescape(a.group(1)), d.group(1) if d else None))
    return out


if __name__ == "__main__":
    import sys, collections
    from urllib.parse import urlparse
    res = folder_links(sys.argv[1], sys.argv[2:])
    for k, v in res.items():
        dom = collections.Counter(urlparse(u or "").netloc.replace("www.", "") for _, _, u, _ in v)
        subs = collections.Counter(s for s, _, _, _ in v)
        print(f"{k}: {len(v)} links; subfolders {dict(subs)}\n   top sites {dom.most_common(15)}")
