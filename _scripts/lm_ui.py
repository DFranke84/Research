"""Shared look (colours, fonts, buttons, cards, banners) and paths for the Library Manager app and its viewer."""
import os, subprocess, sys
import tkinter as tk

RESEARCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # wherever the library folder has been copied
SCRIPTS = os.path.join(RESEARCH, "_scripts")
PY = os.path.join(SCRIPTS, ".venv", "Scripts", "python.exe")
COLL = os.path.join(RESEARCH, "recipes", "personal-recipe-collection")
ICON = os.path.join(SCRIPTS, "library_manager.ico")
sys.path.insert(0, SCRIPTS)
from categories import CATEGORIES

C = {"side": "#1f3a2e", "side_hover": "#2a4b3c", "side_active": "#335a48", "side_text": "#d9e6de", "side_dim": "#8fb3a1",
     "accent": "#d98b3a", "bg": "#f4f1ea", "card": "#ffffff", "line": "#e2ddd2", "text": "#24302a", "dim": "#6b766f",
     "primary": "#2f7a55", "primary_hover": "#276848", "sec": "#e9e4d8", "sec_hover": "#ddd6c6",
     "ok_bg": "#e3f3e8", "ok_fg": "#1d6b40", "warn_bg": "#fdf1dc", "warn_fg": "#8a5a12", "err_bg": "#fbe5e2", "err_fg": "#9b2c22",
     "info_bg": "#e6eef8", "info_fg": "#2b5487", "log_bg": "#1e2522", "log_fg": "#cfd8d3"}
F = "Segoe UI"
SPECIAL = {"cbrn-hazmat": "CBRN / Hazmat", "legal-financial": "Legal & Financial", "medical-first-aid": "Medical - First Aid",
           "medical-conditions": "Medical - Conditions", "medicine-pharmacology": "Medicine & Pharmacology",
           "communications-radio": "Communications & Radio", "navigation-mapping": "Navigation & Mapping",
           "hunting-fishing-trapping": "Hunting, Fishing & Trapping", "tools-crafts-skills": "Tools, Crafts & Skills",
           "sanitation-hygiene": "Sanitation & Hygiene", "security-defense": "Security & Defense", "food-storage-preservation": "Food Storage & Preservation",
           "cooking-fire": "Cooking & Fire", "mechanical-vehicles": "Mechanical & Vehicles", "energy-power": "Energy & Power",
           "shelter-construction": "Shelter & Construction", "foraging-wild-food": "Foraging & Wild Food"}


def nice(cat):
    if cat in SPECIAL:
        return SPECIAL[cat]
    if cat.startswith("field-guide-"):
        return "Field Guide - " + cat[12:].replace("-", " & " if cat.count("-") == 3 else " ").title()
    return cat.replace("-", " ").title()


CAT_NAMES = {nice(c): c for c in CATEGORIES}
CAT_LIST = sorted(CAT_NAMES)
DECISION_TEXT = {"add": "New - will be added", "duplicate": "Already in library", "near-duplicate": "Almost the same as a library item",
                 "not-relevant": "Doesn't fit the library topics", "unreadable": "Couldn't read it", "unsupported": "File type not supported",
                 "skip": "Skipped"}


def show_in_folder(path):
    if os.path.exists(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        os.startfile(os.path.dirname(path) if os.path.isdir(os.path.dirname(path)) else RESEARCH)


# ======================================================================= small widgets
class Btn(tk.Label):
    """Flat button with hover colours (tk.Button can't be styled this cleanly on Windows)."""
    STY = {"primary": ("primary", "primary_hover", "#ffffff"), "secondary": ("sec", "sec_hover", "text"),
           "ghost": ("card", "sec", "primary")}

    def __init__(self, parent, text, command, kind="primary", size=10, padx=18, pady=8, **kw):
        bg, hov, fg = self.STY[kind]
        self.c_bg, self.c_hov = C[bg], C[hov]
        self.c_fg = C.get(fg, fg)
        super().__init__(parent, text=text, bg=self.c_bg, fg=self.c_fg, font=(F, size, "bold" if kind == "primary" else "normal"),
                         padx=padx, pady=pady, cursor="hand2", **kw)
        self.command, self.enabled = command, True
        self.bind("<Enter>", lambda e: self.enabled and self.config(bg=self.c_hov))
        self.bind("<Leave>", lambda e: self.config(bg=self.c_bg if self.enabled else "#c9cfca"))
        self.bind("<Button-1>", lambda e: self.enabled and self.command())

    def set_enabled(self, on):
        self.enabled = on
        self.config(bg=self.c_bg if on else "#c9cfca", fg=self.c_fg if on else "#f4f4f4", cursor="hand2" if on else "arrow")


def card(parent, **kw):
    return tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["line"], **kw)


def label(parent, text, size=10, bold=False, fg="text", bg="card", **kw):
    return tk.Label(parent, text=text, font=(F, size, "bold" if bold else "normal"), fg=C.get(fg, fg), bg=C.get(bg, bg),
                    justify="left", anchor="w", **kw)


def entry(parent, var, width=60):
    return tk.Entry(parent, textvariable=var, font=(F, 11), relief="flat", bg="#fbfaf7", fg=C["text"], width=width,
                    highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["primary"], insertbackground=C["text"])


def check(parent, text, var):
    return tk.Checkbutton(parent, text=text, variable=var, font=(F, 10), bg=C["card"], fg=C["text"], activebackground=C["card"],
                          selectcolor="#ffffff", anchor="w", cursor="hand2")


class Banner(tk.Frame):
    """Result message under an action: success / warning / error / info, with an optional 'Show in folder' link."""
    def __init__(self, parent):
        super().__init__(parent, bg=C["card"])
        self.msg = tk.Label(self, font=(F, 10), justify="left", anchor="w", padx=14, pady=10)
        self.msg.pack(side="left", fill="x", expand=True)
        self.link = tk.Label(self, text="Show in folder", font=(F, 10, "underline"), cursor="hand2", padx=14)
        self.path = None
        self.link.bind("<Button-1>", lambda e: self.path and show_in_folder(self.path))

    def show(self, kind, text, path=None):
        bg, fg = C[kind + "_bg"], C[kind + "_fg"]
        icon = {"ok": "\u2714", "warn": "\u26a0", "err": "\u2716", "info": "\u2139"}[kind]
        self.config(bg=bg)
        self.msg.config(text=f"{icon}  {text}", bg=bg, fg=fg, wraplength=640)
        self.path = path
        if path:
            self.link.config(bg=bg, fg=fg); self.link.pack(side="right")
        else:
            self.link.pack_forget()
        self.pack(fill="x", pady=(14, 0))

    def hide(self):
        self.pack_forget()


# ======================================================================= pages
class Page(tk.Frame):
    title, subtitle, show_log = "", "", True

    def __init__(self, app):
        super().__init__(app.content, bg=C["bg"])
        self.app = app
        self.build()

    def build(self):
        pass

    def on_show(self):
        pass


class Flow(tk.Frame):
    """A row of buttons/chips that wraps onto more lines when the window is too narrow, so none get cut off.
    Use flow.add(widget) instead of widget.pack(); widgets must be created with the Flow as their parent."""

    def __init__(self, parent, bg, gap=6, line_gap=6, **kw):
        super().__init__(parent, bg=bg, height=1, **kw)
        self.gap, self.line_gap, self.items, self._pending = gap, line_gap, [], False
        self.bind("<Configure>", lambda e: self.relayout())

    def add(self, w, gap=None, newline=False):
        self.items = [x for x in self.items if x[0].winfo_exists()]
        self.items.append((w, self.gap if gap is None else gap, newline))
        w.bind("<Configure>", lambda e: self.relayout(), add="+")   # its text changed size -> re-flow
        self.relayout()
        return w

    def clear(self):
        for w, _, _ in self.items:
            if w.winfo_exists():
                w.destroy()
        self.items = []
        self.configure(height=1)

    def relayout(self):
        if not self._pending:
            self._pending = True
            self.after_idle(self._layout)

    def _layout(self):
        self._pending = False
        if not self.winfo_exists():
            return
        width = self.winfo_width()
        if width <= 1:
            width = max(self.master.winfo_width(), 300)
        x = y = line_h = 0
        for w, gap, newline in self.items:
            if not w.winfo_exists():
                continue
            rw, rh = w.winfo_reqwidth(), w.winfo_reqheight()
            if x > 0 and (newline or x + rw > width):
                x, y, line_h = 0, y + line_h + self.line_gap, 0
            w.place(x=x, y=y)
            x += rw + gap
            line_h = max(line_h, rh)
        h = max(1, y + line_h)
        if int(self.cget("height")) != h:
            self.configure(height=h)



class Tip:
    """A small pop-up note: shown after hovering ~0.6 s over any of the widgets, or straight away with toggle(widget)
    (e.g. from a '?' button - it then stays until clicked, the '?' is pressed again, or 25 s pass).
    text may be a function, for help that depends on what is showing."""

    def __init__(self, widgets, text, delay=600):
        self.text, self.delay, self.win, self.job, self.owner = text, delay, None, None, None
        for w in widgets if isinstance(widgets, (list, tuple)) else [widgets]:
            w.bind("<Enter>", lambda e, w=w: self.later(w), add="+")
            w.bind("<Leave>", lambda e: self.hide(hover_only=True), add="+")
            w.bind("<ButtonPress>", lambda e: self.hide(hover_only=True), add="+")

    def later(self, w):
        self.cancel()
        if self.win is None:
            self.owner = w
            self.job = w.after(self.delay, lambda: self.show(w))

    def cancel(self):
        if self.job and self.owner is not None:
            try:
                self.owner.after_cancel(self.job)
            except tk.TclError:
                pass
        self.job = None

    def toggle(self, w):
        if self.win is not None:
            return self.hide()
        self.show(w, sticky=True)

    def show(self, w, sticky=False):
        self.hide()
        text = self.text() if callable(self.text) else self.text
        if not text or not w.winfo_exists():
            return
        self.sticky = sticky
        top = self.win = tk.Toplevel(w)
        top.wm_overrideredirect(True)
        top.attributes("-topmost", True)
        box = tk.Frame(top, bg="#fffbea", highlightthickness=1, highlightbackground="#c9b97a")
        box.pack()
        lab = tk.Label(box, text=text, font=(F, 9), bg="#fffbea", fg=C["text"], justify="left", anchor="w", padx=12, pady=8)
        lab.pack()
        for x in (top, box, lab):
            x.bind("<Button-1>", lambda e: self.hide())
        top.update_idletasks()
        x = w.winfo_rootx() + w.winfo_width() - top.winfo_reqwidth()      # right-aligned under the widget, kept on screen
        x = max(4, min(x, w.winfo_screenwidth() - top.winfo_reqwidth() - 4))
        y = w.winfo_rooty() + w.winfo_height() + 4
        if y + top.winfo_reqheight() > w.winfo_screenheight():
            y = w.winfo_rooty() - top.winfo_reqheight() - 4
        top.geometry(f"+{x}+{y}")
        if sticky:
            self.owner = w
            self.job = w.after(25000, self.hide)

    def hide(self, hover_only=False):
        if hover_only and getattr(self, "sticky", False) and self.win is not None:
            return   # a note opened with '?' stays put when the mouse moves away
        self.cancel()
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
