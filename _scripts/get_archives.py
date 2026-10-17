"""Get Archives - download the free Kiwix archives (.zim) that the starter packs are built from.

Always fetches Kiwix's CURRENT version of each archive, resumes an interrupted download, and checks the file
against Kiwix's published SHA-256 before using it. Files go to <library>\\_sources\\zim.

  Get Archives.bat                         pick from a list
  get_archives.py --list                   just show the list
  get_archives.py ifixit se-diy ...        download these (keys as shown in the list);  all = every one
"""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import requests
from archives import ARCHIVES, ZIM_DIR, latest, local_path
from common import RESEARCH

S = requests.Session()
S.headers["User-Agent"] = "ResearchLibrary-starter/1.0 (Get Archives)"


def pack_archives():
    """Archives used by the starter packs, in pack order, with the pack's item count."""
    pf = os.path.join(RESEARCH, "starter", "packs.json")
    packs = json.load(open(pf, encoding="utf-8"))["packs"] if os.path.exists(pf) else []
    out = [(p["archive"], p["title"], p["items"]) for p in packs if p.get("archive") in ARCHIVES]
    return out or [(k, v[2], 0) for k, v in ARCHIVES.items()]


def gb(n):
    return f"{n / 1e9:.1f} GB" if n >= 1e8 else f"{n / 1e6:.0f} MB"


def size(url):
    try:
        return int(S.head(url, allow_redirects=True, timeout=60).headers.get("Content-Length") or 0)
    except Exception:
        return 0


def download(key):
    name, url = latest(key, S)
    dest = os.path.join(ZIM_DIR, name)
    if os.path.exists(dest):
        print(f"  {name}: already here")
        return True
    os.makedirs(ZIM_DIR, exist_ok=True)
    part = dest + ".part"
    want = S.get(url + ".sha256", timeout=60).text.split()[0:1]
    total = size(url)
    for attempt in range(6):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if total and have >= total:
            break
        try:
            with S.get(url, stream=True, timeout=120, headers={"Range": f"bytes={have}-"} if have else {}) as r:
                if have and r.status_code != 206:   # the server ignored the resume request: start again
                    have = 0
                r.raise_for_status()
                t0, done = time.time(), have
                with open(part, "ab" if have else "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk); done += len(chunk)
                        if time.time() - t0 > 5:
                            t0 = time.time()
                            print(f"\r  {name}: {gb(done)} of {gb(total) if total else '?'}   ", end="", flush=True)
            break
        except Exception as e:
            print(f"\n  connection problem ({type(e).__name__}) - trying again in {10 * (attempt + 1)} s")
            time.sleep(10 * (attempt + 1))
    else:
        print(f"\n  {name}: could not finish - run Get Archives again to continue where it stopped")
        return False
    print(f"\r  {name}: downloaded, checking it...            ", flush=True)
    h = hashlib.sha256()
    with open(part, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    if want and h.hexdigest() != want[0]:
        os.replace(part, dest + ".bad")
        print(f"  {name}: the file is damaged (checksum does not match) - kept as {name}.bad; run Get Archives again")
        return False
    os.replace(part, dest)
    print(f"  {name}: ready" + (" (checksum OK)" if want else ""))
    return True


def main():
    args = sys.argv[1:]
    rows = pack_archives()
    print("Checking Kiwix for the current versions...\n")
    table = []
    for i, (key, title, items) in enumerate(rows, 1):
        try:
            name, url = latest(key, S)
            sz = size(url)
        except Exception as e:
            name, sz = None, 0
        lp = local_path(key)
        if lp and name and os.path.basename(lp) == name:
            state = "have it"
        elif lp:
            state = f"have older {os.path.basename(lp)[len(ARCHIVES[key][1]):-4]}"
        else:
            state = "-"
        table.append((i, key, title, items, name, sz, state))
        print(f"{i:3}. {title:46} {gb(sz) if sz else '?':>9}  {state}")
    print(f"\nFiles go to {ZIM_DIR}")
    if "--list" in args:
        return
    if not args:
        ans = input("\nType the numbers to download (e.g. 1 4 7), 'all' for every one you don't have, or Enter to stop: ").strip()
        if not ans:
            return
        args = ["all"] if ans.lower() == "all" else [t[1] for t in table for a in ans.replace(",", " ").split() if a == str(t[0])]
    keys = [t[1] for t in table if t[6] != "have it"] if args == ["all"] else [a for a in args if a in ARCHIVES]
    if not keys:
        print("Nothing to download.")
        return
    total = sum(t[5] for t in table if t[1] in keys)
    print(f"\nDownloading {len(keys)} archive(s), about {gb(total)}. You can stop any time (close the window) and run it again to continue.\n")
    ok = sum(download(k) for k in keys)
    print(f"\n{ok} of {len(keys)} ready. Next: 'Build Starter Library.bat' to turn them into library pages.")


if __name__ == "__main__":
    main()
