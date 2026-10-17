"""Parse a browser-saved Facebook "Saved items" page into a list of items (title, type, source, url, text)."""
import re
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

KIND = re.compile(r"^(Video|Link|Post|Photo|Reel|Event|Product|Page)\s*•\s*Saved to$")
SKIP = {"Add to Collection", "Saved from", "Food", "Other", "Pinball"}
DUR = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def clean_url(h):
    if not h:
        return None
    if "l.facebook.com/l.php" in h:
        u = parse_qs(urlparse(h).query).get("u")
        h = unquote(u[0]) if u else h
    h = re.sub(r"(?<=[?&])(fbclid|__cft__\[0\]|__tn__|ref)=[^&]*&?", "", h)
    return h.rstrip("?&")


def parse(path):
    s = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "lxml")
    items, seen = [], set()
    for node in s.find_all(string=lambda t: t and t.strip() == "Add to Collection"):
        box = node.parent
        for _ in range(15):   # climb to the smallest container holding the whole item
            if box.parent is None:
                break
            box = box.parent
            lines = box.get_text("\n", strip=True).split("\n")
            if "Saved from" in lines and any(KIND.match(l) for l in lines) and box.find("a", href=True):
                if lines.index(next(l for l in lines if KIND.match(l))) > 0:
                    break
        lines = box.get_text("\n", strip=True).split("\n")
        k = next((i for i, l in enumerate(lines) if KIND.match(l)), None)
        if k is None:
            continue
        body = [l for l in lines[:k] if not DUR.match(l) and l not in SKIP]
        kind = KIND.match(lines[k]).group(1)
        src = ""
        if "Saved from" in lines:
            j = lines.index("Saved from")
            src = re.sub(r"'s (post|video|reel|photo)$", "", lines[j + 1]) if j + 1 < len(lines) else ""
        url = None
        hrefs = [a["href"] for a in box.find_all("a", href=True)]
        if kind == "Link":   # the saved thing is the external page, not the Facebook post that shared it
            ext = [h for h in hrefs if "l.facebook.com/l.php" in h or (h.startswith("http") and "facebook.com" not in h)]
            if ext:
                url = clean_url(ext[0])
        if not url:
            for h in hrefs:
                if re.search(r"/watch/\?|/videos/|/posts/|/permalink/|/reel/|l\.facebook\.com/l\.php|story_fbid|/photo", h) and h.rstrip("/") != "https://www.facebook.com/watch":
                    url = clean_url(h); break
        if not body:
            continue
        title, text = body[0], "\n".join(body[1:])
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        items.append({"title": title, "kind": kind, "source": src, "url": url, "text": text})
    return items


if __name__ == "__main__":
    import sys, collections
    it = parse(sys.argv[1])
    print(len(it), collections.Counter(i["kind"] for i in it), "with url:", sum(1 for i in it if i["url"]))
    for i in it[:8] + it[-3:]:
        print(i["kind"], "|", i["title"][:60], "|", i["source"][:30], "|", (i["url"] or "")[:80], "| text lines:", len(i["text"].splitlines()))
