"""The North America map (local-area/maps/north-america) for Library Manager: shown in a window of its own (Chrome / Edge
"app" mode) and fed by a tiny web server on this computer only
(127.0.0.1), because the map is a web page that needs byte-range reads of its big map file.

  /...                 files of the map folder (with byte ranges, which the .pmtiles map files need)
  /api/library.json    the topo sheets (bounds) + your waypoints, read fresh each time
  /api/open?lat&lon&which=detail|regional   ask Library Manager to open that topo map zoomed to the spot
  /api/addwp?lat&lon   ask Library Manager to add a waypoint there (its own Add window opens)

The two /api actions are handed to the app through on_action(name, lat, lon, which), which must be thread-safe.
"""
import http.server, json, os, posixpath, re, subprocess, threading, urllib.parse, webbrowser

RESEARCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_DIR = os.path.join(RESEARCH, "local-area", "maps", "north-america")
PROFILE = os.path.join(RESEARCH, "_work", "na_map_window")   # the map window's own browser profile (size, location permission)
PORT = 8777


def app_browser():
    """Chrome, else Edge - both can open a page as a plain app window."""
    from common import find_browser
    b = find_browser()
    return b if b and os.path.exists(b) else None


def available():
    return os.path.exists(os.path.join(MAP_DIR, "index.html"))


class _Handler(http.server.SimpleHTTPRequestHandler):
    on_action = None

    def translate_path(self, path):
        path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        parts = [p for p in posixpath.normpath(path).split("/") if p and p not in (".", "..")]
        return os.path.join(MAP_DIR, *parts) if parts else os.path.join(MAP_DIR, "index.html")

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path.startswith("/api/"):
            return self.api(u.path[5:], urllib.parse.parse_qs(u.query))
        return super().do_GET()

    def api(self, name, q):
        import waypoints as wpt
        if name == "library.json":
            maps = [{"md": os.path.relpath(m["md"], RESEARCH).replace(os.sep, "/"), "title": m["title"], "set": m["set"],
                     "s": m["s"], "n": m["n"], "w": m["w"], "e": m["e"]} for m in wpt.index()]
            return self.reply({"waypoints": wpt.load(), "maps": maps})
        if name in ("open", "addwp"):
            try:
                lat, lon = float(q["lat"][0]), float(q["lon"][0])
            except (KeyError, ValueError):
                return self.reply({"ok": False}, 400)
            if self.on_action:
                self.on_action(name, lat, lon, (q.get("which") or ["detail"])[0])
            return self.reply({"ok": True})
        self.send_error(404)

    def reply(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_head(self):   # byte ranges (the map file is read piece by piece)
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = os.path.getsize(path)
        start = int(m[1]) if m and m[1] else max(0, size - int(m[2] or 0)) if m else 0
        end = min(int(m[2]) if m and m[1] and m[2] else size - 1, size - 1)
        if start > end:
            self.send_error(416); return None
        f = open(path, "rb"); f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "_left", None)
        if left is None:
            return super().copyfile(source, outputfile)
        while left > 0:
            buf = source.read(min(1 << 20, left))
            if not buf:
                break
            outputfile.write(buf); left -= len(buf)

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass   # the browser cancelled a request it no longer needed (normal while panning / zooming)

    def log_message(self, *a):
        pass


_Handler.extensions_map.update({".json": "application/json", ".pbf": "application/x-protobuf", ".pmtiles": "application/octet-stream",
                                ".js": "text/javascript", ".css": "text/css"})


class MapServer:
    def __init__(self, on_action=None):
        self.on_action, self.srv, self.port = on_action, None, None

    def start(self):
        if self.srv:
            return self.port
        _Handler.on_action = staticmethod(self.on_action) if self.on_action else None
        # this computer only.  A fixed port when free: the map window's size and the location permission are remembered
        # per address, so a new port each time would forget them
        for port in list(range(PORT, PORT + 10)) + [0]:
            try:
                self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), _Handler)
                break
            except OSError:
                continue
        self.srv.daemon_threads = True
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self.port

    def open(self, lat=None, lon=None, name=None, zoom=None):
        """Open the map in a window of its own (optionally at a spot with a marker): Chrome / Edge in 'app' mode - no tabs,
        address bar or bookmarks - with a small profile of its own in _work, so it never mixes with normal browsing.
        Falls back to the default browser if neither is installed."""
        port = self.start()
        q = {"src": "pc"}
        if lat is not None and lon is not None:
            q.update(lat=f"{lat:.6f}", lon=f"{lon:.6f}")
            if name:
                q["name"] = name
            if zoom:
                q["z"] = str(zoom)
        url = f"http://127.0.0.1:{port}/index.html?" + urllib.parse.urlencode(q)
        browser = app_browser()
        if browser:
            try:
                subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={PROFILE}", "--window-size=1300,900",
                                  "--no-first-run", "--no-default-browser-check", "--disable-sync"],
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return
            except OSError:
                pass
        webbrowser.open(url)

    def stop(self):
        if self.srv:
            self.srv.shutdown(); self.srv = None
