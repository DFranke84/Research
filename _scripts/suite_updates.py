"""Check for updates - the Library Manager side of the AI Research Suite updater.

With the suite installed next to the library (..\\AI-Research-Suite\\update.ps1) its updater does the work: it
knows every piece of the suite, checks GitHub (or a folder of zips) and replaces only program files, never the
library. On its own, GitHub is asked about this library's code only and the download page is offered.
The weekly check is off unless the user turned it on; it lives in AI-Research-Suite\\settings.json, shared with
the AI apps. Only api.github.com is ever contacted.
"""
import datetime, json, os, re, subprocess, sys, urllib.request

from lm_ui import RESEARCH

NAME, REPO, TITLE = "Research", "DFranke84/Research", "Research library and Library Manager"
SUITE = os.path.join(os.path.dirname(RESEARCH), "AI-Research-Suite")
UPDATER = os.path.join(SUITE, "update.ps1")
SETTINGS = os.path.join(SUITE, "settings.json")
LAUNCHER = os.path.join(RESEARCH, "Library Manager.vbs")
WEEK = datetime.timedelta(days=7)


def _read_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def version_key(v):
    return [int(x) if x.isdigit() else 0 for x in re.split(r"[.-]", str(v or "0").lstrip("vV"))]


def newer(a, b):
    ka, kb = version_key(a), version_key(b)
    n = max(len(ka), len(kb))
    return ka + [0] * (n - len(ka)) > kb + [0] * (n - len(kb))


def installed_version():
    m = _read_json(os.path.join(RESEARCH, "release-manifest.json"))
    if m and m.get("version"):
        return m["version"]
    try:
        with open(os.path.join(RESEARCH, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def has_suite():
    return sys.platform == "win32" and os.path.exists(UPDATER)


def is_git():
    return os.path.isdir(os.path.join(RESEARCH, ".git"))


def settings():
    return {"weeklyCheck": False, "lastCheck": None, **(_read_json(SETTINGS) or {})}


def save_settings(**changes):
    if os.path.isdir(SUITE):
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump({**settings(), **changes}, f, indent=2)


def _first_line(text):
    for line in str(text or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return re.sub(r"^[-*]\s*", "", line)[:110]
    return ""


def check():
    """{'components': [{name, title, installed, latest, update, status, notes, page}], 'updates': n}. Raises on failure."""
    if has_suite():
        p = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", UPDATER, "-Check", "-Json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = p.stdout[p.stdout.find("{"):] if "{" in p.stdout else ""
        try:
            data = json.loads(out)
        except ValueError:
            raise RuntimeError("the suite updater gave no answer")
        if data.get("error"):
            raise RuntimeError(data["error"])
        save_settings(lastCheck=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        return data
    row = {"name": NAME, "title": TITLE, "installed": installed_version(), "latest": "", "update": False, "status": "",
           "notes": "", "page": f"https://github.com/{REPO}/releases"}
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                     headers={"User-Agent": "AI-Research-Suite-Updater", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            rel = json.load(r)
        row["latest"] = str(rel.get("tag_name", "")).lstrip("vV")
        row["notes"], row["page"] = _first_line(rel.get("body")), rel.get("html_url") or row["page"]
        row["update"] = newer(row["latest"], row["installed"])
        row["status"] = "update available" if row["update"] else "up to date"
    except Exception as e:
        row["status"] = f"could not check ({e})"
    return {"components": [row], "updates": int(row["update"])}


def weekly_due():
    s = settings()
    if not s.get("weeklyCheck") or not has_suite():
        return False
    try:
        last = datetime.datetime.fromisoformat(str(s.get("lastCheck")).replace("Z", "+00:00"))
    except ValueError:
        return True
    return datetime.datetime.now(datetime.timezone.utc) - last >= WEEK


def start_update():
    """Starts the suite updater in its own window; it waits for Library Manager to close, then starts it again."""
    args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", UPDATER, "-Yes", "-WaitPid", str(os.getpid())]
    if os.path.exists(LAUNCHER):
        args += ["-Restart", LAUNCHER]
    subprocess.Popen(args, cwd=SUITE, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0), close_fds=True)
