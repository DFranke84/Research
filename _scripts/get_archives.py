"""Get Archives - download the free Kiwix archives (.zim) that the starter packs are built from.

Always fetches Kiwix's CURRENT version of each archive, resumes an interrupted download, and checks the file
against Kiwix's published SHA-256 before using it. Files go to <library>\\_sources\\zim.

  Get Archives.bat                         pick from a list
  get_archives.py --list                   just show the list
  get_archives.py ifixit se-diy ...        download these (keys as shown in the list);  all = every one
"""
import hashlib, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import requests
from archives import ARCHIVES, EXTRA, ZIM_DIR, latest, local_path
from common import RESEARCH

S = requests.Session()
S.headers["User-Agent"] = "ResearchLibrary-starter/1.0 (Get Archives)"


def pack_archives():
    """Archives used by the starter packs, in pack order, with the pack's item count."""
    pf = os.path.join(RESEARCH, "starter", "packs.json")
    packs = json.load(open(pf, encoding="utf-8"))["packs"] if os.path.exists(pf) else []
    out = [(p["archive"], p["title"], p["items"]) for p in packs if p.get("archive") in ARCHIVES]
    out = out or [(k, v[2], 0) for k, v in ARCHIVES.items() if k not in EXTRA]
    return out + [(k, v[2], 0) for k, v in EXTRA.items()]


def gb(n):
    return f"{n / 1e9:.1f} GB" if n >= 1e8 else f"{n / 1e6:.0f} MB"


def size(url):
    try:
        return int(S.head(url, allow_redirects=True, timeout=60).headers.get("Content-Length") or 0)
    except Exception:
        return 0


def published_sha256(url):
    """Kiwix's SHA-256 for a file as [hash], or [] when there is none (a short network hiccup is retried)."""
    for attempt in range(3):
        try:
            r = S.get(url + ".sha256", timeout=60)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            h = (r.text.split() or [""])[0].lower()
            return [h] if re.fullmatch(r"[0-9a-f]{64}", h) else []   # an error page is not a checksum
        except Exception:
            time.sleep(5 * (attempt + 1))
    return []


def older_copies(key, name):
    """Earlier versions of this archive in _sources\\zim (the current one is `name`)."""
    prefix = ARCHIVES[key][1]
    return [os.path.join(ZIM_DIR, f) for f in sorted(os.listdir(ZIM_DIR))
            if f != name and re.fullmatch(re.escape(prefix) + r"\d{4}-\d{2}[a-z]?\.zim", f)]


def download(key):
    try:
        name, url = latest(key, S)
    except Exception as e:
        print(f"  {key}: could not ask Kiwix for the current version ({e}) - check the internet connection and run it again")
        return False
    dest = os.path.join(ZIM_DIR, name)
    if os.path.exists(dest):
        print(f"  {name}: already here")
        return True
    os.makedirs(ZIM_DIR, exist_ok=True)
    part = dest + ".part"
    want = published_sha256(url)
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
    got = os.path.getsize(part) if os.path.exists(part) else 0
    if total and got < total:   # the connection closed early without an error: keep the part, continue next time
        print(f"\n  {name}: stopped at {gb(got)} of {gb(total)} - run Get Archives again to continue where it stopped")
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
        return 0
    interactive = not args   # picked from the list by a person (the installer passes keys and is never asked)
    if not args:
        ans = input("\nType the numbers to download (e.g. 1 4 7), 'all' for every one you don't have, or Enter to stop: ").strip()
        if not ans:
            return 0
        args = ["all"] if ans.lower() == "all" else [t[1] for t in table for a in ans.replace(",", " ").split() if a == str(t[0])]
    unknown = [a for a in args if a != "all" and a not in ARCHIVES]
    for a in unknown:
        print(f"  '{a}' is not one of the archives in the list - skipped")
    keys = [t[1] for t in table if t[6] != "have it"] if args == ["all"] else [a for a in args if a in ARCHIVES]
    if not keys:
        print("Nothing to download.")
        return 1 if unknown else 0
    total = sum(t[5] for t in table if t[1] in keys)
    print(f"\nDownloading {len(keys)} archive(s), about {gb(total)}. You can stop any time (close the window) and run it again to continue.\n")
    done = [k for k in keys if download(k)]
    print(f"\n{len(done)} of {len(keys)} ready. Next: 'Build Starter Library.bat' to turn them into library pages.")
    offer_cleanup(done, ask=interactive)
    # exit code 1 when something did not finish, so the AI Research Suite installer tries again and says so
    return 0 if len(done) == len(keys) and not unknown else 1


def offer_cleanup(keys, ask):
    """A newer archive replaces the old one: offer to move the old copies to the Recycle Bin (they can be very big)."""
    old = []
    for k in keys:
        lp = local_path(k)
        if lp:
            old += older_copies(k, os.path.basename(lp))
    if not old:
        return
    print(f"\nOlder versions of these archives are still here ({gb(sum(os.path.getsize(f) for f in old))}):")
    for f in old:
        print(f"  {os.path.basename(f)}")
    if not ask:
        print("Run 'Get Archives.bat' on its own to be offered to move them to the Recycle Bin.")
        return
    if input("Move them to the Recycle Bin? [y/N]: ").strip().lower() not in ("y", "yes"):
        return
    from library_delete import recycle
    left = recycle(old)
    print("Moved to the Recycle Bin." if not left else f"Could not move {len(left)} of them - are they open in another program?")


if __name__ == "__main__":
    sys.exit(main())
