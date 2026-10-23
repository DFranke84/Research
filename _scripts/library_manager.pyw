"""Library Manager - one window for adding things to E:\\Research one at a time or in bulk.

  Recipe from a web link   -> 63_add_recipe.py
  Recipe from an email     -> 64_add_email_recipe.py
  One document (PDF, Word) -> 65_add_document.py
  A whole folder (bulk)    -> 50_ingest_folder.py  (review, tick/untick, then add)

Double-click the "Library Manager" desktop shortcut (pythonw, no console window). The scripts run one at a time
(they share the slug registry and catalog), and their output is shown in the Activity panel.
"""
import csv, ctypes, json, os, queue, re, subprocess, sys, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lm_ui import *
from lm_ui import Page
import library_viewer as lv
import waypoints as wpt
import na_map_server as nams
import zim_viewer as zv
import suite_updates as su


class HomePage(Page):
    title = "Welcome"
    subtitle = "Browse and read everything in your Research library, or add new recipes and documents."
    show_log = False

    def build(self):
        st = card(self); st.pack(fill="x")
        top = tk.Frame(st, bg=C["card"]); top.pack(fill="x", padx=20, pady=(16, 8))
        self.stats = tk.Frame(top, bg=C["card"]); self.stats.pack(side="left", anchor="n")
        qa = tk.Frame(st, bg=C["card"]); qa.pack(fill="x", padx=20, pady=(0, 14))
        Btn(qa, "Browse recipes", lambda: self.app.show("recipes"), "primary", 9, 14, 6).pack(side="left")
        Btn(qa, "+ Recipe link", lambda: self.app.show("link"), "secondary", 9, 14, 6).pack(side="left", padx=(8, 0))
        Btn(qa, "+ Document", lambda: self.app.show("doc"), "secondary", 9, 14, 6).pack(side="left", padx=(8, 0))

        rc = card(self); rc.pack(fill="x", pady=(12, 0))
        label(rc, "Recently added", 12, True).pack(anchor="w", padx=20, pady=(14, 8))
        self.recent = tk.Frame(rc, bg=C["card"]); self.recent.pack(fill="x", padx=14, pady=(0, 14))

        cc = card(self); cc.pack(fill="both", expand=True, pady=(12, 0))
        label(cc, "Categories", 12, True).pack(anchor="w", padx=20, pady=(14, 4))
        self.cats = tk.Frame(cc, bg=C["card"]); self.cats.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self.photos = []
        # shown until the library has been read (several seconds on a cold start); fill() replaces it
        import time
        self.wait = label(self.stats, "⏳  Loading the library", 13, True, fg="dim")
        self.wait.pack(anchor="w", pady=(6, 2))
        label(self.stats, "Reading the library - a large one can take a few seconds when the computer has just started.",
              9, fg="dim").pack(anchor="w", pady=(0, 6))
        label(self.recent, "The newest items will appear here.", 9, fg="dim").pack(anchor="w", padx=6, pady=(0, 20))
        label(self.cats, "Categories will appear here.", 9, fg="dim").pack(anchor="w", pady=(0, 20))
        self.t0 = time.time()
        self.app.status.config(text="Loading the library...")
        self.tick()
        self.app.lib.on_ready(self.fill)
        self.app.favs.listeners.append(lambda: self.app.lib.ready and self.fill())

    def tick(self):
        """Animate the loading line until the library is ready."""
        import time
        if self.app.lib.ready or not self.wait.winfo_exists():
            return
        n = int(time.time() - self.t0)
        self.wait.config(text="⏳  Loading the library" + "." * (n % 4 + 1) + (f"   {n} s" if n >= 3 else ""))
        self.after(500, self.tick)

    def load(self):
        self.app.lib.reload()

    def fill(self):
        if not self.app.busy and self.app.status.cget("text").startswith("Loading the library"):
            self.app.status.config(text="Ready")
        course = [r for r in self.app.lib.items if lv.is_course(r)]
        items = [r for r in self.app.lib.items if not lv.is_course(r)]
        for w in self.stats.winfo_children() + self.cats.winfo_children() + self.recent.winfo_children():
            w.destroy()
        by = {}
        for r in items:
            by[r["category"]] = by.get(r["category"], 0) + 1
        docs = sum(1 for r in items if r["type"] in lv.DOC_TYPES)
        lessons = sum(1 for r in course if r["type"] in ("lesson-video", "audio"))
        for n, t in [(len(items), "items in the library"), (by.get("recipes", 0), "recipes"), (docs, "documents & books"),
                     *([(lessons, "Cooking School lessons")] if lessons else []), (len(self.app.favs.d), "favorites")]:
            b = tk.Frame(self.stats, bg=C["card"]); b.pack(side="left", padx=(0, 28))
            label(b, f"{n:,}", 20, True, fg="primary").pack(anchor="w")
            label(b, t, 9, fg="dim").pack(anchor="w")
        new = sorted((i for i in items if i.get("date")), key=lambda i: i["date"], reverse=True)[:6]   # newest additions (catalog date_added)
        self.slots, todo = {}, []
        for k, it in enumerate(new):
            f = tk.Frame(self.recent, bg=C["card"], cursor="hand2")
            f.grid(row=0, column=k, padx=6, sticky="n")
            box = tk.Frame(f, bg=C["card"], width=150, height=96); box.pack(); box.pack_propagate(False)
            lv.placeholder(box, it, 150, 96).pack(fill="both", expand=True)
            self.slots[it["path"]] = box
            t = it["title"] if len(it["title"]) < 46 else it["title"][:44].rsplit(" ", 1)[0] + "\u2026"
            l = tk.Label(f, text=t, font=(F, 8, "bold"), bg=C["card"], fg=C["text"], wraplength=146, justify="left", anchor="nw", height=2)
            l.pack(fill="x", pady=(4, 0))
            ws = [f, box, l] + box.winfo_children()
            for w in ws + [c for x in box.winfo_children() for c in x.winfo_children()]:
                w.bind("<Button-1>", lambda e, it=it: self.app.open_item(it))
            got = self.app.thumbs.cached(it, (150, 96))
            if got and got != "none":
                self.thumb(it, got)
            elif not got:
                todo.append(it)
        for k in range(6):
            self.recent.columnconfigure(k, weight=1, uniform="r")
        if todo:
            self.app.thumbs.request(todo, (150, 96), self.thumb)
        self.todo = todo
        cols = 3
        for i, c in enumerate(sorted(CATEGORIES, key=nice)):
            f = tk.Frame(self.cats, bg=C["card"], cursor="hand2")
            f.grid(row=i // cols, column=i % cols, sticky="ew", padx=(0, 18), pady=1)
            a = label(f, nice(c), 9); a.pack(side="left")
            b = label(f, f"{by.get(c, 0):,}", 9, fg="dim"); b.pack(side="right")
            for w in (f, a, b):
                w.bind("<Button-1>", lambda e, c=c: self.app.browse_category(c))
                w.bind("<Enter>", lambda e, a=a: a.config(fg=C["primary"], font=(F, 9, "underline")))
                w.bind("<Leave>", lambda e, a=a: a.config(fg=C["text"], font=(F, 9)))
        for k in range(cols):
            self.cats.columnconfigure(k, weight=1, uniform="c")
        label(self.cats, f"These {len(CATEGORIES)} categories add up to the {len(items):,} total.  Click one to browse it.", 8,
              fg="dim").grid(row=99, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def on_show(self):
        todo = [i for i in getattr(self, "todo", []) if self.app.thumbs.cached(i, (150, 96)) is None]
        if todo:
            self.app.thumbs.request(todo, (150, 96), self.thumb)

    def thumb(self, it, path):
        box = self.slots.get(it["path"])
        if not path or not box or not box.winfo_exists():
            return
        img = lv.ImageTk.PhotoImage(lv.Image.open(path)); self.photos.append(img)
        for w in box.winfo_children():
            w.destroy()
        l = tk.Label(box, image=img, bd=0, bg=C["card"], cursor="hand2"); l.pack(fill="both", expand=True)
        l.bind("<Button-1>", lambda e: self.app.open_item(it))


class LinkPage(Page):
    title = "Recipe from a Web Link"
    subtitle = "Saves only the recipe (title, photo, ingredients, steps) plus a clean one-page PDF. Video links are saved as the video."

    def build(self):
        f = card(self); f.pack(fill="x")
        inner = tk.Frame(f, bg=C["card"]); inner.pack(fill="x", padx=22, pady=20)
        label(inner, "Recipe web address", 10, True).pack(anchor="w")
        row = tk.Frame(inner, bg=C["card"]); row.pack(fill="x", pady=(6, 16))
        self.url = tk.StringVar()
        e = entry(row, self.url); e.pack(side="left", fill="x", expand=True, ipady=7)
        e.bind("<Return>", lambda ev: self.add())
        Btn(row, "Paste", self.paste, "secondary", 10, 14, 7).pack(side="left", padx=(8, 0))
        label(inner, "Save it in", 10, True).pack(anchor="w")
        self.folder = tk.StringVar(value="auto")
        rf = tk.Frame(inner, bg=C["card"]); rf.pack(anchor="w", pady=(4, 12))
        for t, v in [("Sort automatically", "auto"), ("Air Fryer", "air-fryer"), ("Instant Pot", "instant-pot"), ("Food Recipes", "food-recipes")]:
            tk.Radiobutton(rf, text=t, value=v, variable=self.folder, font=(F, 10), bg=C["card"], activebackground=C["card"],
                           fg=C["text"], selectcolor="#ffffff", cursor="hand2").pack(side="left", padx=(0, 16))
        self.force = tk.BooleanVar()
        check(inner, "Replace it if it's already in my collection", self.force).pack(anchor="w")
        b = Btn(inner, "Add Recipe", self.add); b.pack(anchor="w", pady=(16, 0))
        self.app.actions.append(b)
        self.banner = Banner(inner)
        e.focus_set()

    def paste(self):
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def add(self):
        url = self.url.get().strip()
        if not url.lower().startswith("http"):
            self.banner.show("warn", "Paste a full web address starting with http:// or https://"); return
        args = [os.path.join(SCRIPTS, "63_add_recipe.py"), url]
        if self.folder.get() != "auto":
            args += ["--folder", self.folder.get()]
        if self.force.get():
            args.append("--force")
        self.banner.show("info", "Fetching the recipe... this usually takes under a minute.")
        self.app.run(args, "Adding recipe from " + url, self.done)

    def done(self, rc, out):
        m = re.search(r"added: (.+)\n\s*folder: (\S+)\s+->\s+bookmarks/(\S+\.md)", out)
        if m:
            self.banner.show("ok", f"Added \"{m[1]}\" to {nice(m[2])}.", os.path.join(COLL, "bookmarks", m[3].replace("/", os.sep)))
            self.url.set(""); self.force.set(False); return
        m = re.search(r"already in the (collection|library): (\S+)", out)
        if m:
            p = os.path.join(COLL, m[2]) if m[1] == "collection" else os.path.join(RESEARCH, m[2])
            moved = "  It was moved to the folder you picked." if "moved to" in out else ""
            self.banner.show("warn", f"This recipe is already saved.{moved} Tick \"Replace\" to fetch it again.", p.replace("/", os.sep)); return
        m = re.search(r"duplicate: (.+?)\s+- nothing added", out)
        if m:
            self.banner.show("warn", "Already saved: " + m[1].replace(" is already saved as", " - saved as")); return
        m = re.search(r"FAILED: (.+)", out)
        self.banner.show("err", "Couldn't get a recipe from that page" + (f": {m[1]}" if m else ". See Activity below for details."))


class EmailPage(Page):
    title = "Recipe from an Email"
    subtitle = "Adds one recipe email from Outlook. Emails holding several recipes become one entry with every recipe in it."

    def build(self):
        f = card(self); f.pack(fill="x")
        inner = tk.Frame(f, bg=C["card"]); inner.pack(fill="x", padx=22, pady=20)
        tip = tk.Frame(inner, bg=C["info_bg"]); tip.pack(fill="x", pady=(0, 16))
        tk.Label(tip, text="\u2139  First move the email into the Outlook folder  Email \u203a Recipes.",
                 font=(F, 10), bg=C["info_bg"], fg=C["info_fg"], padx=12, pady=8, anchor="w").pack(fill="x")
        label(inner, "Words from the email's subject", 10, True).pack(anchor="w")
        self.subj = tk.StringVar()
        e = entry(inner, self.subj); e.pack(fill="x", pady=(6, 14), ipady=7)
        e.bind("<Return>", lambda ev: self.add())
        self.force = tk.BooleanVar()
        check(inner, "Replace it if it's already in my collection", self.force).pack(anchor="w")
        row = tk.Frame(inner, bg=C["card"]); row.pack(anchor="w", pady=(16, 0))
        b1 = Btn(row, "Add Recipe", self.add); b1.pack(side="left")
        b2 = Btn(row, "Preview only", self.preview, "secondary"); b2.pack(side="left", padx=(10, 0))
        self.app.actions += [b1, b2]
        self.banner = Banner(inner)

    def _args(self, extra):
        s = self.subj.get().strip()
        if not s:
            self.banner.show("warn", "Type a few words from the email's subject line."); return None
        return [os.path.join(SCRIPTS, "64_add_email_recipe.py"), s] + extra

    def preview(self):
        a = self._args(["--check"])
        if a:
            self.banner.show("info", "Looking up the email in Outlook...")
            self.app.run(a, "Previewing email recipe", self.previewed)

    def previewed(self, rc, out):
        if rc:
            return self.fail(out)
        lines = [l for l in out.strip().splitlines() if l.strip() and not l.startswith("exported")]
        self.banner.show("info", "This is what would be saved:\n" + "\n".join(lines[-12:]))

    def add(self):
        a = self._args(["--force"] if self.force.get() else [])
        if a:
            self.banner.show("info", "Looking up the email in Outlook and adding it...")
            self.app.run(a, "Adding email recipe", self.done)

    def done(self, rc, out):
        m = re.search(r"added: (.+?)\s+->\s+email-recipes/(\S+\.md)", out)
        if m:
            many = re.search(r"(\d+) recipes in it", out)
            self.banner.show("ok", f"Added \"{m[1]}\"" + (f" ({many[1]} recipes)" if many else "") + " to your email recipes.",
                             os.path.join(COLL, "email-recipes", m[2]))
            self.subj.set(""); self.force.set(False); return
        self.fail(out)

    def fail(self, out):
        m = re.search(r"already in the collection: (\S+)", out)
        if m:
            return self.banner.show("warn", "That recipe is already in your collection. Tick \"Replace\" to update it.",
                                    os.path.join(COLL, m[1].replace("/", os.sep)))
        m = re.search(r"no email in Email/Recipes with .+", out)
        self.banner.show("err", (m[0] + ".  Check the words, and that the email is in Email \u203a Recipes.") if m
                         else "Something went wrong - see Activity below.")


class DocPage(Page):
    title = "Add One Document"
    subtitle = "PDF, Word (.docx/.doc), .odt, .rtf, .txt, .md, web page (.html), e-book (.epub) or slides (.pptx). Scanned PDFs are OCR'd."

    def build(self):
        f = card(self); f.pack(fill="x")
        inner = tk.Frame(f, bg=C["card"]); inner.pack(fill="x", padx=22, pady=20)
        label(inner, "Document", 10, True).pack(anchor="w")
        row = tk.Frame(inner, bg=C["card"]); row.pack(fill="x", pady=(6, 10))
        self.path = tk.StringVar()
        e = entry(row, self.path); e.pack(side="left", fill="x", expand=True, ipady=7)
        e.bind("<Return>", lambda ev: self.check())
        b = Btn(row, "Choose file...", self.choose, "secondary", 10, 14, 7); b.pack(side="left", padx=(8, 0))
        self.ocr = tk.BooleanVar(value=True)
        check(inner, "Read scanned pages with OCR (slower, but makes scans searchable)", self.ocr).pack(anchor="w")
        b0 = Btn(inner, "Check document", self.check, "secondary"); b0.pack(anchor="w", pady=(12, 0))
        self.app.actions += [b, b0]

        self.res = tk.Frame(inner, bg=C["card"])   # filled after the check
        self.badge = tk.Label(self.res, font=(F, 10, "bold"), padx=12, pady=6, anchor="w", justify="left")
        self.badge.pack(fill="x", pady=(18, 12))
        g = tk.Frame(self.res, bg=C["card"]); g.pack(fill="x")
        label(g, "Title", 10, True).grid(row=0, column=0, sticky="w", pady=4)
        self.title_v = tk.StringVar()
        entry(g, self.title_v).grid(row=0, column=1, sticky="ew", padx=(12, 0), ipady=5)
        label(g, "Category", 10, True).grid(row=1, column=0, sticky="w", pady=4)
        self.cat_v = tk.StringVar()
        ttk.Combobox(g, textvariable=self.cat_v, values=CAT_LIST, state="readonly", font=(F, 10), width=34) \
            .grid(row=1, column=1, sticky="w", padx=(12, 0), pady=6)
        self.info = label(g, "", 9, fg="dim"); self.info.grid(row=2, column=1, sticky="w", padx=(12, 0))
        g.columnconfigure(1, weight=1)
        self.force = tk.BooleanVar()
        self.force_cb = check(self.res, "Add it anyway", self.force)
        self.add_b = Btn(self.res, "Add to Library", self.add)
        self.app.actions.append(self.add_b)
        self.banner = Banner(inner)
        self.row = None

    def choose(self):
        p = filedialog.askopenfilename(title="Choose a document to add", filetypes=[
            ("Documents", "*.pdf *.docx *.doc *.odt *.rtf *.txt *.md *.markdown *.html *.htm *.epub *.pptx"), ("All files", "*.*")])
        if p:
            self.path.set(os.path.normpath(p)); self.check()

    def check(self):
        p = self.path.get().strip().strip('"')
        if not os.path.isfile(p):
            self.banner.show("warn", "Choose a file first."); return
        self.res.pack_forget(); self.row = None
        self.banner.show("info", "Checking the document against the library...")
        args = [os.path.join(SCRIPTS, "65_add_document.py"), p, "--check"] + ([] if self.ocr.get() else ["--no-ocr"])
        self.app.run(args, "Checking " + os.path.basename(p), self.checked)

    def checked(self, rc, out):
        m = re.search(r"^RESULT (\{.*\})$", out, re.M)
        if not m:
            return self.banner.show("err", "Couldn't check that file - see Activity below.")
        self.banner.hide()
        r = self.row = json.loads(m[1])
        d = r["decision"]
        kind = {"add": "ok", "duplicate": "warn", "near-duplicate": "warn", "not-relevant": "info"}.get(d, "err")
        text = DECISION_TEXT.get(d, d) + " - " + r["reason"]
        if r.get("matches"):
            text += "\nMatches: " + r["matches"]
        self.badge.config(text=text, bg=C[kind + "_bg"], fg=C[kind + "_fg"], wraplength=640)
        self.title_v.set(r.get("title") or "")
        self.cat_v.set(nice(r["category"]) if r.get("category") in CATEGORIES else "")
        self.info.config(text=(f"{int(r['words']):,} words" if r.get("words") else "") + (f"  \u2022  suggested: {nice(r['category'])}"
                                                                                          if r.get("category") else ""))
        self.force.set(False); self.force_cb.pack_forget(); self.add_b.pack_forget()
        if d in ("unreadable", "unsupported"):
            pass
        else:
            if d != "add":
                self.force_cb.pack(anchor="w", pady=(10, 0))
            self.add_b.pack(anchor="w", pady=(14, 0))
        self.res.pack(fill="x")

    def add(self):
        if not self.row:
            return
        if self.row["decision"] != "add" and not self.force.get():
            self.banner.show("warn", "This one wasn't recommended. Tick \"Add it anyway\" if you still want it."); return
        cat = CAT_NAMES.get(self.cat_v.get())
        if not cat:
            self.banner.show("warn", "Pick a category."); return
        args = [os.path.join(SCRIPTS, "65_add_document.py"), self.row["file"], "--category", cat, "--title", self.title_v.get().strip()]
        args += (["--force"] if self.force.get() else []) + ([] if self.ocr.get() else ["--no-ocr"])
        self.banner.show("info", "Adding to the library and refreshing the catalog...")
        self.app.run(args, "Adding " + os.path.basename(self.row["file"]), self.done)

    def done(self, rc, out):
        m = re.search(r"^\s+added\s+(\S+\.md)", out, re.M)
        if m:
            self.banner.show("ok", f"Added \"{self.title_v.get()}\" to {self.cat_v.get()}.", os.path.join(RESEARCH, m[1].replace("/", os.sep)))
            self.res.pack_forget(); self.path.set(""); self.row = None
        else:
            self.banner.show("err", "It wasn't added - see Activity below.")


class BulkPage(Page):
    title = "Bulk Add a Folder"
    subtitle = "Step 1: Review - nothing is added yet.   Step 2: tick or untick files, fix titles/categories, then add."

    def build(self):
        f = card(self); f.pack(fill="x")
        inner = tk.Frame(f, bg=C["card"]); inner.pack(fill="x", padx=22, pady=(16, 14))
        row = tk.Frame(inner, bg=C["card"]); row.pack(fill="x")
        self.folder = tk.StringVar()
        entry(row, self.folder).pack(side="left", fill="x", expand=True, ipady=7)
        b1 = Btn(row, "Choose folder...", self.choose, "secondary", 10, 14, 7); b1.pack(side="left", padx=(8, 0))
        row2 = tk.Frame(inner, bg=C["card"]); row2.pack(fill="x", pady=(10, 0))
        b2 = Btn(row2, "1  Review folder", self.review); b2.pack(side="left")
        self.ocr = tk.BooleanVar(value=True)
        check(row2, "OCR scanned PDFs", self.ocr).pack(side="left", padx=(14, 0))
        b3 = Btn(row2, "Open an earlier review...", self.open_report, "ghost", 9, 8, 4); b3.pack(side="right")
        self.app.actions += [b1, b2, b3]
        self.banner = Banner(inner)

        t = card(self); t.pack(fill="both", expand=True, pady=(10, 0))
        tf = tk.Frame(t, bg=C["card"]); tf.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        cols = ("inc", "file", "result", "category", "title")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse", height=4)
        for c, w, txt in [("inc", 46, "Add"), ("file", 220, "File"), ("result", 190, "Result"), ("category", 170, "Category"), ("title", 280, "Title")]:
            self.tree.heading(c, text=txt, anchor="w")
            self.tree.column(c, width=w, anchor="center" if c == "inc" else "w", stretch=c in ("file", "title"))
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True); sb.pack(side="left", fill="y")
        self.tree.tag_configure("add", foreground=C["ok_fg"])
        self.tree.tag_configure("warn", foreground=C["warn_fg"])
        self.tree.tag_configure("off", foreground="#8a918c")
        self.tree.bind("<<TreeviewSelect>>", self.select)
        self.tree.bind("<Double-1>", lambda e: self.toggle())
        self.tree.bind("<space>", lambda e: self.toggle())

        ed = tk.Frame(t, bg=C["card"]); ed.pack(side="bottom", fill="x", padx=12, pady=8, before=tf)
        label(ed, "Selected:", 9, True).pack(side="left")
        self.sel_title = tk.StringVar(); self.sel_cat = tk.StringVar(); self.sel_inc = tk.BooleanVar()
        te = entry(ed, self.sel_title, 34); te.pack(side="left", padx=(8, 6), ipady=3)
        te.bind("<KeyRelease>", lambda e: self.edit())
        cb = ttk.Combobox(ed, textvariable=self.sel_cat, values=CAT_LIST, state="readonly", font=(F, 9), width=28)
        cb.pack(side="left", padx=6); cb.bind("<<ComboboxSelected>>", lambda e: self.edit())
        tk.Checkbutton(ed, text="Add", variable=self.sel_inc, command=self.edit, font=(F, 9), bg=C["card"], activebackground=C["card"],
                       selectcolor="#ffffff").pack(side="left", padx=6)

        bot = tk.Frame(t, bg=C["card"]); bot.pack(side="bottom", fill="x", padx=12, pady=(0, 12), before=ed)
        Btn(bot, "Tick suggested", lambda: self.tick("suggested"), "ghost", 9, 8, 4).pack(side="left")
        Btn(bot, "Tick none", lambda: self.tick("none"), "ghost", 9, 8, 4).pack(side="left")
        self.count = label(bot, "", 9, fg="dim"); self.count.pack(side="left", padx=12)
        self.apply_b = Btn(bot, "2  Add ticked files", self.apply); self.apply_b.pack(side="right")
        self.app.actions.append(self.apply_b)
        self.rows, self.report = [], None

    def choose(self):
        p = filedialog.askdirectory(title="Choose a folder of documents")
        if p:
            self.folder.set(os.path.normpath(p))

    def review(self):
        d = self.folder.get().strip().strip('"')
        if not os.path.isdir(d):
            self.banner.show("warn", "Choose a folder first."); return
        self.banner.show("info", "Reviewing every file... big folders with scanned PDFs can take a while. Progress is shown in Activity.")
        args = [os.path.join(SCRIPTS, "50_ingest_folder.py"), d] + ([] if self.ocr.get() else ["--no-ocr"])
        self.app.run(args, "Reviewing folder " + d, self.reviewed)

    def reviewed(self, rc, out):
        m = re.search(r"Review report: (.+\.csv)", out)
        if not m:
            return self.banner.show("err", "The review didn't finish - see Activity below.")
        self.load(m[1].strip())

    def open_report(self):
        p = filedialog.askopenfilename(title="Open a review report", initialdir=os.path.join(RESEARCH, "_work", "ingest"),
                                       filetypes=[("Review reports", "*.csv")])
        if p:
            self.load(os.path.normpath(p))

    def load(self, report):
        self.report = report
        self.rows = list(csv.DictReader(open(report, encoding="utf-8-sig")))
        for r in self.rows:
            r["_orig"] = r.get("_orig") or r["decision"]
            r["_inc"] = r["decision"].strip().lower() == "add"
        self.fill()
        n = sum(r["_inc"] for r in self.rows)
        self.banner.show("ok", f"Reviewed {len(self.rows)} files: {n} suggested to add. Double-click a row to tick/untick it.")

    def fill(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.rows):
            self.tree.insert("", "end", iid=str(i), values=self.vals(r), tags=self.tag(r))
        self.update_count()

    def vals(self, r):
        return ("\u2714" if r["_inc"] else "", os.path.basename(r["file"]), DECISION_TEXT.get(r["_orig"], r["_orig"]),
                nice(r["category"]) if r["category"] in CATEGORIES else "", r["title"])

    def tag(self, r):
        return ("add",) if r["_inc"] else ("warn",) if r["_orig"] in ("duplicate", "near-duplicate") else ("off",)

    def refresh_row(self, i):
        self.tree.item(str(i), values=self.vals(self.rows[i]), tags=self.tag(self.rows[i]))
        self.update_count()

    def update_count(self):
        n = sum(r["_inc"] for r in self.rows)
        self.count.config(text=f"{n} of {len(self.rows)} files ticked" if self.rows else "No review loaded yet")
        self.apply_b.config(text=f"2  Add {n} ticked file" + ("" if n == 1 else "s"))

    def current(self):
        s = self.tree.selection()
        return int(s[0]) if s else None

    def select(self, e=None):
        i = self.current()
        if i is None:
            return
        r = self.rows[i]
        self.sel_title.set(r["title"]); self.sel_cat.set(nice(r["category"]) if r["category"] in CATEGORIES else ""); self.sel_inc.set(r["_inc"])
        if r.get("reason"):
            self.app.status.config(text=os.path.basename(r["file"]) + ": " + r["reason"] + (f"  (matches {r['matches']})" if r.get("matches") else ""))

    def can_add(self, r):
        return r["_orig"] not in ("unreadable", "unsupported")

    def toggle(self):
        i = self.current()
        if i is not None and self.can_add(self.rows[i]):
            self.rows[i]["_inc"] = not self.rows[i]["_inc"]; self.sel_inc.set(self.rows[i]["_inc"]); self.refresh_row(i)

    def edit(self):
        i = self.current()
        if i is None:
            return
        r = self.rows[i]
        r["title"] = self.sel_title.get()
        if self.sel_cat.get() in CAT_NAMES:
            r["category"] = CAT_NAMES[self.sel_cat.get()]
        r["_inc"] = self.sel_inc.get() and self.can_add(r)
        self.sel_inc.set(r["_inc"])
        self.refresh_row(i)

    def tick(self, how):
        for r in self.rows:
            r["_inc"] = how == "suggested" and r["_orig"] == "add"
        self.fill()

    def apply(self):
        todo = [r for r in self.rows if r["_inc"]]
        if not todo:
            return self.banner.show("warn", "Nothing is ticked.")
        nocat = [r for r in todo if r["category"] not in CATEGORIES]
        if nocat:
            return self.banner.show("warn", f"{len(nocat)} ticked file(s) have no category - select them and pick one "
                                    f"(first: {os.path.basename(nocat[0]['file'])}).")
        if not messagebox.askyesno("Add files", f"Add {len(todo)} file(s) to the library?"):
            return
        base = re.sub(r"(_edited)?\.csv$", "", self.report)
        out = base + "_edited.csv"
        fields = [k for k in self.rows[0] if not k.startswith("_")]
        with open(out, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in self.rows:
                w.writerow({**r, "decision": "add" if r["_inc"] else ("skip" if r["_orig"] == "add" else r["_orig"])})
        self.banner.show("info", f"Adding {len(todo)} files... progress is shown in Activity.")
        args = [os.path.join(SCRIPTS, "50_ingest_folder.py"), "--apply", out] + ([] if self.ocr.get() else ["--no-ocr"])
        self.app.run(args, f"Adding {len(todo)} files", self.done)

    def done(self, rc, out):
        added = re.findall(r"^\s+added\s+(\S+\.md)", out, re.M)
        failed = re.findall(r"FAILED \(not added\)", out)
        if added:
            self.banner.show("ok" if not failed else "warn", f"Added {len(added)} files to the library"
                             + (f"; {len(failed)} failed (see Activity)" if failed else "") + ".",
                             os.path.join(RESEARCH, added[-1].replace("/", os.sep)))
            for r in self.rows:
                if r["_inc"]:
                    r["_orig"], r["_inc"] = "duplicate", False   # now in the library
            self.fill()
        else:
            self.banner.show("err", "Nothing was added - see Activity below.")


def _grp(*groups):
    return lambda i: i.get("ltype") in groups


def _typ(*types):
    return lambda i: i["type"] in types


def _title(*words):
    return lambda i: any(w in i["title"] for w in words)


def _cat(*cats):
    return lambda i: i["category"] in cats


_FORMATS = [("PDFs", _typ("pdf")), ("Word & other documents", _typ("document")), ("Books", _typ("wiki-book"))]

# Documents & Books topic tiles (same layout as Local Area): (name, icon, description, filter, [(sub-button, filter), ...]).
# Topics with one category get format buttons; mixed topics get a button per category.
DOC_TOPICS = [
    ("All Documents", "📚", "Every PDF, Word document and book in the library - search them all here",
     lambda i: True, _FORMATS),
    ("Gardening & Farming", "🌱", "Gardens, soil, seeds, orchards, grains, livestock, poultry, bees",
     _cat("food-production"), _FORMATS),
    ("Food Storage & Preservation", "🥫", "Canning, drying, smoking, curing, fermenting, root cellars, food safety",
     _cat("food-storage-preservation"), _FORMATS),
    ("Cooking & Recipes", "🍲", "Cookbooks and recipe collections; fire, stoves and off-grid cooking",
     _cat("recipes", "cooking-fire"), [("Cookbooks & recipes", _cat("recipes")), ("Cooking & fire", _cat("cooking-fire"))]),
    ("Medical", "🩺", "First aid and emergency medicine, illnesses and conditions, medicines and herbal remedies",
     _cat("medical-first-aid", "medical-conditions", "medicine-pharmacology"),
     [("First aid", _cat("medical-first-aid")), ("Conditions", _cat("medical-conditions")),
      ("Medicines & remedies", _cat("medicine-pharmacology"))]),
    ("Water & Sanitation", "💧", "Finding, purifying and storing water; waste, hygiene and disinfection",
     _cat("water", "sanitation-hygiene"), [("Water", _cat("water")), ("Sanitation & hygiene", _cat("sanitation-hygiene"))]),
    ("Wilderness, Hunting & Foraging", "🏕", "Survival manuals, hunting, fishing and trapping, wild foods, navigation",
     _cat("wilderness-survival", "hunting-fishing-trapping", "foraging-wild-food", "navigation-mapping"),
     [("Survival", _cat("wilderness-survival")), ("Hunting, fishing & trapping", _cat("hunting-fishing-trapping")),
      ("Foraging", _cat("foraging-wild-food")), ("Navigation", _cat("navigation-mapping"))]),
    ("Emergency & Disaster", "⚠", "Preparedness plans and kits; nuclear, chemical and biological hazards; weather",
     _cat("emergency-preparedness", "cbrn-hazmat", "weather"),
     [("Preparedness", _cat("emergency-preparedness")), ("Nuclear, chemical & biological", _cat("cbrn-hazmat")),
      ("Weather", _cat("weather"))]),
    ("Energy & Power", "⚡", "Solar, wind, generators, batteries, wiring, fuels, heating", _cat("energy-power"), _FORMATS),
    ("Skills, Tools & Building", "🔧", "Tools and crafts, vehicles and engines, shelters and construction",
     _cat("tools-crafts-skills", "mechanical-vehicles", "shelter-construction"),
     [("Tools & crafts", _cat("tools-crafts-skills")), ("Vehicles & engines", _cat("mechanical-vehicles")),
      ("Shelter & construction", _cat("shelter-construction"))]),
    ("Radio & Communications", "📻", "Amateur and emergency radio, antennas, electronics, signalling",
     _cat("communications-radio"), _FORMATS),
    ("Security & Defense", "🛡", "Home and personal security, firearms, self-defense", _cat("security-defense"), _FORMATS),
    ("Legal & Financial", "⚖", "Documents, insurance, disaster assistance, financial resilience", _cat("legal-financial"), _FORMATS),
]


def _rx(pattern, path=None):
    """Recipe filter: title matches the pattern (or the file sits in a bookmark folder such as /air-fryer/)."""
    rx = re.compile(pattern, re.I)
    return lambda i: bool(rx.search(i["title"])) or bool(path and path in (i.get("path") or ""))


_SRC = [("Web recipes", lambda i: i.get("group") == "web"), ("Email", lambda i: i.get("group") == "email"),
        ("Facebook", lambda i: i.get("group") == "facebook"), ("Recipe cards", lambda i: i.get("group") == "cards"),
        ("Videos", lambda i: i["type"] == "video"), ("Cookbooks & documents", lambda i: i.get("group") == "books")]
_DISH = {
    "Breads & Baking": r"bread|\bbuns?\b|\brolls?\b|biscuit|muffin|scone|loaf|sourdough|bagel|pretzel|focaccia|tortilla|crust|dough|cornbread|naan|pita|danish",
    "Desserts & Sweets": r"cake|cookie|\bpies?\b|brownie|dessert|cobbler|\bcrisp\b|pudding|fudge|candy|frosting|cheesecake|\btarts?\b|\bbars?\b|ice cream|cupcake|caramel|chocolate|doughnut|donut|cinnamon roll|turnover|dumpling|fritter|lush|delight|popsicle|curd|meringue",
    "Breakfast": r"breakfast|pancake|waffle|french toast|omelet|\beggs?\b|frittata|quiche|granola|oatmeal|hash brown",
    "Soups, Stews & Chili": r"soup|stew|chili|chowder|bisque|broth|gumbo|ramen",
    "Chicken & Turkey": r"chicken|turkey|\bwings?\b",
    "Beef": r"beef|steak|burger|meatloaf|meatball|brisket|\broast\b|prime rib|sloppy",
    "Pork & Ham": r"pork|\bham\b|bacon|sausage|\bribs\b|carnitas|pigs in a blanket",
    "Fish & Seafood": r"fish|salmon|shrimp|tuna|\bcod\b|crab|lobster|scallop|seafood|trout|halibut|walleye",
    "Pasta, Rice & Casseroles": r"pasta|spaghetti|lasagna|macaroni|mac and cheese|noodle|casserole|\brice\b|risotto|enchilada|tetrazzini|alfredo|lo mein",
    "Pizza, Sandwiches & Tacos": r"pizza|sandwich|grilled cheese|monte cristo|wrap|quesadilla|taco|burrito|calzone|sub\b",
    "Vegetables & Salads": r"potato|salad|vegetable|veggie|\bbeans?\b|\bcorn\b|esquites|carrot|broccoli|cabbage|squash|zucchini|asparagus|slaw|cauliflower|mushroom|onion|\bside",
    "Sauces, Dressings & Seasonings": r"sauce|dressing|gravy|marinade|\brub\b|seasoning|\bdip\b|salsa|spice|glaze|mayo|aioli|sugar\b|powder",
    "Drinks": r"drink|smoothie|lemonade|limeade|\btea\b|coffee|latte|punch|cocktail|wine|cider|kombucha|kefir|shake|margarita|colada|martini|mai tai|screwdriver|julius|slammer|mermaid|bahama|bramble",
    "Canning, Dairy & Preserving": r"\bjams?\b|jelly|preserve|pickle|canning|canned|relish|chutney|marmalade|ferment|sauerkraut|kimchi|pectin|yogurt|cheese making|feta|cheese \(|dairy|in a jar",
}
_DISH_RX = {k: re.compile(v, re.I) for k, v in _DISH.items()}


def _tile(name, auto):
    """A recipe's own tile choice (Recipe tiles... button, _work/recipe_tiles.json) wins over the title guess."""
    return lambda i: (name in lv.RECIPE_TILES[i["path"]]) if i["path"] in lv.RECIPE_TILES else auto(i)


def _other_recipe(i):
    return not any(t[3](i) for t in RECIPE_TOPICS[1:-1])   # in none of the dish / appliance tiles


# Recipes topic tiles (same layout as Local Area). A recipe can be in more than one tile (e.g. chicken soup).
RECIPE_TOPICS = [("All Recipes", "\U0001F4D6", "Every recipe - web bookmarks, emails, Facebook saves, recipe cards, videos and cookbooks",
                  lambda i: True, _SRC)] + [
    (name, icon, desc, _tile(name, _rx(_DISH[name])), _SRC) for name, icon, desc in [
        ("Breads & Baking", "\U0001F35E", "Breads, rolls, biscuits, muffins, sourdough, tortillas and doughs"),
        ("Desserts & Sweets", "\U0001F370", "Cakes, cookies, pies, bars, puddings, candy and other treats"),
        ("Breakfast", "\U0001F95E", "Pancakes, waffles, eggs, quiche, granola and other breakfasts"),
        ("Soups, Stews & Chili", "\U0001F35C", "Soups, stews, chili, chowders and broths"),
        ("Chicken & Turkey", "\U0001F357", "Chicken and turkey dishes, wings"),
        ("Beef", "\U0001F969", "Steaks, roasts, burgers, meatloaf, brisket"),
        ("Pork & Ham", "\U0001F953", "Pork, ham, bacon, sausage and ribs"),
        ("Fish & Seafood", "\U0001F41F", "Fish, salmon, shrimp and other seafood"),
        ("Pasta, Rice & Casseroles", "\U0001F35D", "Pasta, noodles, rice dishes and casseroles"),
        ("Pizza, Sandwiches & Tacos", "\U0001F355", "Pizza, sandwiches, wraps, tacos and burritos"),
        ("Vegetables & Salads", "\U0001F957", "Vegetables, potatoes, salads and side dishes"),
        ("Sauces, Dressings & Seasonings", "\U0001F9C2", "Sauces, gravies, dressings, dips, rubs and spice mixes"),
        ("Drinks", "\U0001F379", "Smoothies, lemonades, coffee drinks and cocktails"),
        ("Canning, Dairy & Preserving", "\U0001F36F", "Jams, jellies, pickles, ferments, yogurt and cheese"),
    ]] + [
    ("Air Fryer", "\U0001F525", "Air fryer recipes", _tile("Air Fryer", _rx(r"air fr", "/air-fryer/")), _SRC),
    ("Instant Pot", "\u23F2", "Instant Pot and pressure-cooker recipes",
     _tile("Instant Pot", _rx(r"instant pot|pressure cook", "/instant-pot/")), _SRC),
    ("Other Recipes", "\U0001F37D", "Recipes that do not fit the tiles above", _other_recipe, _SRC),
]


# kinds of item, for the sub-buttons of single-category Whole Library topics (empty ones are hidden)
_KINDS = [(name, _typ(*types)) for name, types in [
    ("Repair guides", ("repair-guide",)), ("Q & A", ("q-and-a",)), ("Wikipedia", ("wikipedia-article",)),
    ("Web pages", ("web-page",)), ("Wiki articles", ("wiki-article",)), ("Species profiles", ("species-profile",)),
    ("PDFs", ("pdf",)), ("Word & other documents", ("document",)), ("Books", ("wiki-book",)),
    ("Videos", ("video", "audio"))]]

# Whole Library topic tiles: every category is in exactly one topic; 'All of the Library' first.
LIB_TOPICS = [
    ("All of the Library", "\U0001F4DA", "Everything (except the Cooking School) - search and sort it all here", lambda i: True, _KINDS),
    ("Vehicles & Engines", "\U0001F697", "Repair guides, Q & A and articles on vehicles, small engines, bikes and boats",
     _cat("mechanical-vehicles"), _KINDS),
    ("Skills, Tools & Building", "\U0001F527", "Tools, crafts and traditional skills; shelters, construction and insulation",
     _cat("tools-crafts-skills", "shelter-construction"),
     [("Tools, crafts & skills", _cat("tools-crafts-skills")), ("Shelter & construction", _cat("shelter-construction"))]),
    ("Gardening & Farming", "\U0001F331", "Gardens, soil, seeds, orchards, grains, livestock, poultry, bees", _cat("food-production"), _KINDS),
    ("Food Storage & Preservation", "\U0001F96B", "Canning, drying, smoking, curing, fermenting, root cellars, food safety",
     _cat("food-storage-preservation"), _KINDS),
    ("Recipes & Cooking", "\U0001F372", "Your recipe collection; fire, stoves and off-grid cooking",
     _cat("recipes", "cooking-fire"), [("Recipes", _cat("recipes")), ("Cooking & fire", _cat("cooking-fire"))]),
    ("Medical", "\U0001FA7A", "First aid and emergency medicine, illnesses and conditions, medicines and remedies",
     _cat("medical-first-aid", "medical-conditions", "medicine-pharmacology"),
     [("First aid", _cat("medical-first-aid")), ("Conditions", _cat("medical-conditions")),
      ("Medicines & remedies", _cat("medicine-pharmacology"))]),
    ("Water & Sanitation", "\U0001F4A7", "Finding, purifying and storing water; waste, hygiene and disinfection",
     _cat("water", "sanitation-hygiene"), [("Water", _cat("water")), ("Sanitation & hygiene", _cat("sanitation-hygiene"))]),
    ("Energy & Power", "\u26A1", "Solar, wind, generators, batteries, wiring, fuels, heating and cooling", _cat("energy-power"), _KINDS),
    ("Radio & Communications", "\U0001F4FB", "Amateur and emergency radio, antennas, electronics, signalling",
     _cat("communications-radio"), _KINDS),
    ("Wilderness, Hunting & Foraging", "\U0001F3D5", "Survival skills, hunting, fishing and trapping, wild foods, navigation",
     _cat("wilderness-survival", "hunting-fishing-trapping", "foraging-wild-food", "navigation-mapping"),
     [("Survival", _cat("wilderness-survival")), ("Hunting, fishing & trapping", _cat("hunting-fishing-trapping")),
      ("Foraging", _cat("foraging-wild-food")), ("Navigation", _cat("navigation-mapping"))]),
    ("Emergency & Disaster", "\u26A0", "Preparedness; nuclear, chemical and biological hazards; weather",
     _cat("emergency-preparedness", "cbrn-hazmat", "weather"),
     [("Preparedness", _cat("emergency-preparedness")), ("Nuclear, chemical & biological", _cat("cbrn-hazmat")),
      ("Weather", _cat("weather"))]),
    ("Security & Defense", "\U0001F6E1", "Home and personal security, firearms, self-defense", _cat("security-defense"), _KINDS),
    ("Legal & Financial", "\u2696", "Documents, insurance, scams, disaster assistance, financial resilience", _cat("legal-financial"), _KINDS),
    ("Local Area", "\u26F0", "Your local area: plants, wildlife, fungi, growing guides and pest pages",
     _cat("local-area"), [("Plants", _typ("local-profile")), ("Wildlife & fungi", _typ("local-wildlife")),
                          ("Guides & references", _typ("growing-guide", "local-reference", "local-overview", "local-guide", "local-map")),
                          ("Pests & problems", _typ("local-pest"))]),
]


# Local Area topic tiles: (name, icon, short description, filter, [(sub-button, filter), ...]).
# Group names = the '## ' headings in local_area_specs.PLANT_TABLE and local_area_specs.WILD_GROUPS.
LOCAL_TOPICS = [
    ("Start Here", "🧭", "Kalispell's zone, frost dates and how this section is organised",
     _typ("local-overview"), []),
    ("Fruit Trees", "🍎", "Apples, crabapples, pears, plums, apricots and cherries",
     _grp("Fruit trees - Apples", "Fruit trees - Pears", "Fruit trees - Plums & apricots", "Fruit trees - Cherries"),
     [("Apples & crabapples", _grp("Fruit trees - Apples")), ("Pears", _grp("Fruit trees - Pears")),
      ("Plums & apricots", _grp("Fruit trees - Plums & apricots")), ("Cherries", _grp("Fruit trees - Cherries"))]),
    ("Berries & Small Fruit", "🍇", "Elderberries, currants, haskap, raspberries, blackberries, grapes, rhubarb...",
     _grp("Berries & small fruit"), []),
    ("Trees", "🌳", "Shade and ornamental trees, conifers and nut trees",
     _grp("Trees - Shade & ornamental", "Trees - Conifers", "Nut trees"),
     [("Shade & ornamental", _grp("Trees - Shade & ornamental")), ("Conifers", _grp("Trees - Conifers")), ("Nut trees", _grp("Nut trees"))]),
    ("Shrubs & Roses", "🌹", "Lilacs, caragana, spirea, dogwood and other shrubs; hardy and wild roses",
     _grp("Shrubs & hedges", "Roses"), [("Shrubs & hedges", _grp("Shrubs & hedges")), ("Roses", _grp("Roses"))]),
    ("Herbs", "🌿", "Culinary and medicinal herbs for Montana gardens", _grp("Herbs"), []),
    ("Vegetables", "🥕", "Home-garden vegetables for Kalispell's short season - planting dates, greenhouse use, varieties",
     _grp("Vegetables"), []),
    ("Wild Plants & Weeds", "🌼", "Native wildflowers and wild foods, poisonous plants and noxious weeds",
     _grp("Native wildflowers & wild foods", "Poisonous plants", "Noxious weeds", "Common weeds"),
     [("Wildflowers & wild foods", _grp("Native wildflowers & wild foods")), ("Poisonous plants", _grp("Poisonous plants")),
      ("Noxious weeds", _grp("Noxious weeds")), ("Common weeds", _grp("Common weeds"))]),
    ("Grasses", "🌾", "All Montana grasses - native range grasses, pasture, lawn and weedy grasses", _grp("Grasses"), []),
    ("Wildlife", "🦌", "Montana mammals, birds, fish, reptiles and amphibians",
     _grp("Wildlife - Mammals", "Wildlife - Birds", "Wildlife - Fish", "Wildlife - Reptiles & amphibians"),
     [("Mammals", _grp("Wildlife - Mammals")), ("Birds", _grp("Wildlife - Birds")), ("Fish", _grp("Wildlife - Fish")),
      ("Reptiles & amphibians", _grp("Wildlife - Reptiles & amphibians"))]),
    ("Fungi", "🍄", "Montana mushrooms, brackets, rusts and cankers - never eat one identified from a photo",
     _grp("Fungi"), []),
    ("Insects & Spiders", "🦋", "Butterflies, dragonflies, bees, pests, helpful insects, biting bugs, ticks and spiders, fly-fishing hatches",
     lambda i: (i.get("ltype") or "").startswith(("Insects", "Spiders")),
     [("Butterflies", _grp("Insects - Butterflies")), ("Big moths", _grp("Insects - Big moths")),
      ("Dragonflies & damselflies", _grp("Insects - Dragonflies & damselflies")), ("Bees & wasps", _grp("Insects - Bees & wasps")),
      ("Helpful insects", _grp("Insects - Helpful insects")), ("Garden & orchard pests", _grp("Insects - Garden & orchard pests")),
      ("Forest & tree pests", _grp("Insects - Forest & tree pests")), ("House & pantry pests", _grp("Insects - House & pantry pests")),
      ("Biting & stinging", _grp("Insects - Biting & stinging")), ("Spiders, ticks & mites", _grp("Spiders, ticks & mites")),
      ("Fly-fishing hatches", _grp("Insects - Fly-fishing hatches")), ("Other insects & bugs", _grp("Insects - Other insects & bugs"))]),
    ("Nearby (Pacific Northwest)", "🗺", "Seen near Montana - Idaho, Washington, Oregon, Wyoming, BC, Alberta - but not recorded in Montana",
     lambda i: (i.get("ltype") or "").startswith("Nearby"),
     [("Plants", _grp("Nearby - Plants")), ("Fungi", _grp("Nearby - Fungi")), ("Insects & spiders", _grp("Nearby - Insects & spiders")),
      ("Reptiles & amphibians", _grp("Nearby - Reptiles & amphibians")), ("Mammals", _grp("Nearby - Mammals"))]),
    ("Food Preservation", "🥫", "Canning at Kalispell's altitude, freezing, drying and root-cellar storage",
     _grp("Food preservation"), []),
    ("Living with Wildlife", "🐻", "Bears, deer, lions and smaller animals around the home, garden, coop and garbage - Montana FWP",
     _grp("Living with wildlife"), [("Kalispell guide", _typ("local-guide")), ("FWP & partner documents", _typ("local-reference"))]),
    ("Heating with Wood", "🔥", "Flathead National Forest firewood permits, heat value of local woods, safe burning",
     _grp("Heating with wood"), []),
    ("Livestock & Bees", "🐝", "Montana apiary registration, backyard poultry, goats, protecting animals from bears",
     _grp("Livestock & bees"), []),
    ("Maps", "📍", "USGS topographic maps of NW Montana incl. Glacier and the Bob - detailed 1:24,000 and regional 1:100,000 - "
     "plus an offline road map of all of North America",
     _grp("Maps"),
     [("Detailed maps (1:24,000)", lambda i: "/maps/usgs-topo-" in i["path"]),
      ("Regional maps (1:100,000)", lambda i: "/maps/regional/" in i["path"]),
      ("North America map", lambda i: i["path"].endswith("/north-america-map.md")),
      ("Index & how to move between maps", lambda i: i.get("ltype") == "Maps" and "/maps/usgs-topo-" not in i["path"]
       and "/maps/regional/" not in i["path"] and not i["path"].endswith("/north-america-map.md"))]),
    ("Growing Guides & References", "📚", "Stark Bro's growing guides, MSU MontGuides, Flathead County and USDA documents",
     lambda i: i["type"] in ("growing-guide", "local-reference") and not i.get("ltype"),   # topic documents have their own tiles
     [("Growing guides", _typ("growing-guide")), ("Documents", _typ("local-reference"))]),
    ("Pests & Problems", "🐛", "MSU's guide to tree and shrub diseases, insects and other problems - one page each",
     _typ("local-pest"), [("Diseases", _title("(Disease")), ("Insects & mites", _title("(Insect")),
                          ("Weather, site & animal damage", _title("(Weather")), ("Tree identification", _title("(Tree identification"))]),
]

# A Local Area made by build_local_area.py (it leaves local-area\local-area.json) gets these tiles instead - the
# groups that tool writes. The list above stays for the hand-built Kalispell section.
LOCAL_AREA_CONF = os.path.join(RESEARCH, "local-area", "local-area.json")
GENERIC_LOCAL_TOPICS = [
    ("Start Here", "🧭", "Frost dates, growing season, hardiness zone and monthly weather for your area",
     _typ("local-overview"), []),
    ("Plants", "🌿", "Flowering plants (incl. broadleaf trees and shrubs), conifers, grasses, ferns and mosses seen near you",
     lambda i: (i.get("ltype") or "").startswith("Plants"),
     [("Flowering plants", _grp("Plants - Flowering plants")), ("Conifers", _grp("Plants - Conifers")),
      ("Grasses, sedges & rushes", _grp("Plants - Grasses, sedges & rushes")), ("Ferns & mosses", _grp("Plants - Ferns & mosses"))]),
    ("Wildlife", "🦌", "Birds, mammals, fish, reptiles and amphibians seen near you",
     lambda i: (i.get("ltype") or "").startswith("Wildlife"),
     [("Birds", _grp("Wildlife - Birds")), ("Mammals", _grp("Wildlife - Mammals")), ("Fish", _grp("Wildlife - Fish")),
      ("Reptiles & amphibians", _grp("Wildlife - Reptiles & amphibians"))]),
    ("Insects & Spiders", "🦋", "Insects, spiders, ticks and mites seen near you",
     _grp("Insects", "Spiders, ticks & mites"), [("Insects", _grp("Insects")), ("Spiders, ticks & mites", _grp("Spiders, ticks & mites"))]),
    ("Fungi & Lichens", "🍄", "Mushrooms, brackets and lichens seen near you - never eat one identified from a photo",
     _grp("Fungi & lichens"), []),
    ("Maps", "📍", "USGS topographic maps of your area (open them here or from 📍 Waypoints)", _grp("Maps"), []),
    ("Your Documents", "📚", "Local guides and documents you added to the Local Area category",
     lambda i: i["type"] not in ("local-overview", "local-profile", "local-wildlife", "local-map"), []),
]
if os.path.exists(LOCAL_AREA_CONF):
    LOCAL_TOPICS = GENERIC_LOCAL_TOPICS


def local_area_intro():
    """The Local Area page's line under its title: the place Build Local Area made it for, or the hand-built section's."""
    try:
        c = json.load(open(LOCAL_AREA_CONF, encoding="utf-8"))
        return (f"{c['name']} and {c['radius']} km around it: pick a topic - plants, wildlife, insects and fungi seen there, "
                "frost dates and weather, and maps.")
    except (OSError, ValueError, KeyError):
        return ("Kalispell / Flathead County: pick a topic - your plants with key facts for zone 5b, Montana wildlife, insects, fungi "
                "and grasses, nearby Pacific Northwest species, growing guides, MSU documents and pest pages.")


class WaypointsPage(Page):
    """Your own named places: each opens the topo map it is on, zoomed in on a red marker.  Add them here (type or
    paste a position) or on a map (📍 Add waypoint / right-click).  Saved in _work/waypoints.json."""
    title = "Waypoints"
    subtitle = ("Your own places - home, hunting spots, trailheads, springs. Pick one to open the map it is on, zoomed in on it. "
                "Add them here, or on any Local Area map with \U0001F4CD Add waypoint (or right-click the map).")
    show_log = False

    def build(self):
        bar = tk.Frame(self, bg=C["bg"]); bar.pack(fill="x", pady=(0, 10))
        Btn(bar, "+  Add a waypoint", self.add, "primary", 10, 16, 6).pack(side="left")
        Btn(bar, "\U0001F5FA  All maps", self.app.show_maps, "secondary", 10, 14, 6).pack(side="left", padx=(10, 0))
        if nams.available():
            Btn(bar, "\U0001F30E  North America map", lambda: self.app.open_na_map(), "secondary", 10, 14, 6).pack(side="left", padx=(8, 0))
        self.open_b = Btn(bar, "Open detailed map", lambda: self.open("detail"), "secondary", 10, 14, 6)
        self.open_b.pack(side="left", padx=(10, 0))
        self.reg_b = Btn(bar, "Open regional map", lambda: self.open("regional"), "secondary", 10, 14, 6)
        self.reg_b.pack(side="left", padx=(8, 0))
        self.edit_b = Btn(bar, "Edit…", self.edit, "secondary", 10, 14, 6); self.edit_b.pack(side="left", padx=(8, 0))
        self.copy_b = Btn(bar, "Copy position", self.copy, "ghost", 10, 12, 6); self.copy_b.pack(side="left", padx=(8, 0))
        self.del_b = Btn(bar, "\U0001F5D1  Delete", self.delete, "secondary", 10, 14, 6); self.del_b.pack(side="right")
        self.del_b.c_fg = C["err_fg"]; self.del_b.config(fg=C["err_fg"])
        sr = tk.Frame(self, bg=C["bg"]); sr.pack(fill="x", pady=(0, 8))
        label(sr, "Find:", 10, bg="bg").pack(side="left")
        self.q = tk.StringVar(); self.q.trace_add("write", lambda *a: self.fill())
        entry(sr, self.q, 40).pack(side="left", padx=(8, 0), ipady=4)
        self.count = label(sr, "", 9, fg="dim", bg="bg"); self.count.pack(side="left", padx=12)
        label(self, "Find a waypoint by name or note - or type a position to see which map it is on, e.g.  48.1958N 114.3129W   "
              "or   48.1958, -114.3129   (a Google Maps link works too).", 9, fg="dim", bg="bg").pack(fill="x", pady=(0, 8))
        self.posbar = tk.Frame(self, bg=C["info_bg"])   # shown when Find holds a position
        self.empty = label(self, "No waypoints yet. Use + Add a waypoint, or open a map (Local Area › Maps) and click "
                           "\U0001F4CD Add waypoint.", 10, fg="dim", bg="bg")
        box = self.box = card(self); box.pack(fill="both", expand=True)
        cols = ("name", "pos", "map", "notes")
        self.tree = ttk.Treeview(box, columns=cols, show="headings", selectmode="browse")
        for c, t, w in (("name", "Name", 200), ("pos", "Position", 170), ("map", "On the map", 220), ("notes", "Notes", 300)):
            self.tree.heading(c, text=t, anchor="w"); self.tree.column(c, width=w, anchor="w", stretch=c in ("map", "notes"))
        sb = ttk.Scrollbar(box, command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.open("detail"))
        self.tree.bind("<Return>", lambda e: self.open("detail"))
        self.tree.bind("<Delete>", lambda e: self.delete())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.paint_buttons())
        self.wps = []

    def on_show(self):
        self.fill()

    def fill(self):
        sel = self.selected()
        self.wps = wpt.load()
        q = self.q.get().strip().lower()
        pos = self.position(self.q.get())
        self.paint_pos(pos)
        if pos:
            q = ""   # a position: keep the whole list, the bar above says which map it is on
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for wp in sorted(self.wps, key=lambda w: w["name"].lower()):
            d, r = wpt.maps_at(wp["lat"], wp["lon"])
            on = (d or r or {}).get("title", "not on a library map")
            on = re.sub(r" - USGS 1:([\d,]+) Topographic Map.*", r" (1:\1)", on)
            row = (wp["name"], wpt.fmt(wp["lat"], wp["lon"]), on, wp.get("notes", "").replace("\n", "  "))
            if q and q not in " ".join(row).lower():
                continue
            self.tree.insert("", "end", iid=wp["id"], values=row); shown += 1
        if sel and self.tree.exists(sel["id"]):
            self.tree.selection_set(sel["id"]); self.tree.see(sel["id"])
        n = len(self.wps)
        self.count.config(text=f"{shown} of {n}" if q else f"{n} waypoint{'s' if n != 1 else ''}")
        if self.wps:
            self.empty.pack_forget()
        else:
            self.empty.pack(anchor="w", pady=(0, 10), before=self.box)
        self.paint_buttons()

    def selected(self):
        s = self.tree.selection()
        return next((w for w in self.wps if s and w["id"] == s[0]), None)

    @staticmethod
    def position(text):
        q = text.strip()
        if not re.search(r"\d", q) or not (lv.TopicPage.COORD_RE.match(q) or ("http" in q and "@" in q)):
            return None
        try:
            return wpt.parse(q)
        except ValueError:
            return None

    def paint_pos(self, p):
        """Find holds a position: which map it is on, with Open / Save buttons."""
        for w in self.posbar.winfo_children():
            w.destroy()
        if not p:
            self.posbar.pack_forget()
            return
        d, r = wpt.maps_at(*p)
        short = lambda m: re.sub(r" - USGS 1:([\d,]+) Topographic Map.*", r" (1:\1)", m["title"])
        fg = C["info_fg"]
        tk.Label(self.posbar, text=f"\U0001F4CD  {wpt.fmt(*p)}  -  " + (" and ".join(short(m) for m in (d, r) if m) if d or r
                 else "not on any map in the library"), font=(F, 10, "bold"), bg=C["info_bg"], fg=fg).pack(side="left", padx=12, pady=8)
        spot = {"name": "Searched position", "lat": p[0], "lon": p[1]}
        if r:
            Btn(self.posbar, "Regional map", lambda: lv.open_waypoint(self.app, spot, "regional"), "secondary", 9, 12, 4).pack(side="right", padx=(0, 10))
        if d:
            Btn(self.posbar, "Detailed map", lambda: lv.open_waypoint(self.app, spot, "detail"), "primary", 9, 12, 4).pack(side="right", padx=(0, 8))
        Btn(self.posbar, "+ Save as waypoint", lambda: self.add_at(*p), "secondary", 9, 12, 4).pack(side="right", padx=(0, 8))
        if nams.available():
            Btn(self.posbar, "\U0001F30E  North America map", lambda: self.app.open_na_map(p[0], p[1], "Searched position"),
                "primary" if not (d or r) else "secondary", 9, 12, 4).pack(side="right", padx=(0, 8))
        self.posbar.pack(fill="x", pady=(0, 10), before=self.box)

    def add_at(self, lat, lon):
        wp = lv.waypoint_dialog(self.app, "Add a waypoint", lat=lat, lon=lon)
        if wp:
            lv.save_waypoint(wp); self.q.set(""); self.fill()
            self.tree.selection_set(wp["id"]); self.tree.see(wp["id"])

    def paint_buttons(self):
        wp = self.selected()
        d, r = wpt.maps_at(wp["lat"], wp["lon"]) if wp else (None, None)
        self.open_b.set_enabled(bool(d)); self.reg_b.set_enabled(bool(r))
        for b in (self.edit_b, self.copy_b, self.del_b):
            b.set_enabled(bool(wp))

    def add(self):
        wp = lv.waypoint_dialog(self.app, "Add a waypoint")
        if wp:
            lv.save_waypoint(wp); self.q.set(""); self.fill()
            self.tree.selection_set(wp["id"]); self.tree.see(wp["id"])

    def edit(self):
        wp = self.selected()
        if wp:
            new = lv.waypoint_dialog(self.app, "Edit waypoint", wp)
            if new:
                lv.save_waypoint(new); self.fill()

    def copy(self):
        wp = self.selected()
        if wp:
            self.clipboard_clear(); self.clipboard_append(wpt.fmt(wp["lat"], wp["lon"]))

    def delete(self):
        wp = self.selected()
        if wp and messagebox.askyesno("Delete waypoint", f"Delete the waypoint “{wp['name']}”?", parent=self.app):
            wpt.save([w for w in wpt.load() if w["id"] != wp["id"]]); self.fill()

    def open(self, which):
        wp = self.selected()
        if wp:
            lv.open_waypoint(self.app, wp, which)


# ======================================================================= main window
class App(tk.Tk):
    PAGES = [("home", "\u2302", "Home", HomePage),
             "BROWSE",
             ("favs", "\u2605", "Favorites", lv.FavoritesPage),
             ("recipes", "🍲", "Recipes", lambda app: lv.TopicPage(app, "Recipes",
                 "Every recipe - web bookmarks, emails, Facebook saves, recipe cards, videos and cookbooks. Pick a kind of dish, "
                 "or All Recipes to search them all.",
                 lambda i: i["category"] == "recipes" and i.get("group") != "course", RECIPE_TOPICS, unit="recipe")),
             ("school", "\U0001F393", "Cooking School", lv.CoursePage),
             ("local", "⛰", "Local Area", lambda app: lv.TopicPage(app, "Local Area", local_area_intro(),
                 lambda i: i["category"] == "local-area", LOCAL_TOPICS)),
             ("waypoints", "\U0001F4CD", "Waypoints", WaypointsPage),
             ("docs", "📚", "Documents & Books", lambda app: lv.TopicPage(app, "Documents & Books",
                 "PDFs, Word documents and books from every category - pick a topic, or All Documents to search them all.",
                 lambda i: i["type"] in lv.DOC_TYPES and not lv.is_course(i), DOC_TOPICS, unit="document")),
             ("library", "🗂", "Whole Library", lambda app: lv.TopicPage(app, "Whole Library",
                 f"Everything in {RESEARCH} - pick a topic, or All of the Library to search and sort it all.",
                 lambda i: not lv.is_course(i), LIB_TOPICS, unit="item")),
             ("zim", "\U0001F310", "Offline Archives", zv.ZimPage),
             "ADD",
             ("link", "\U0001F517", "Recipe from Link", LinkPage),
             ("email", "\u2709", "Recipe from Email", EmailPage), ("doc", "\U0001F4C4", "Add a Document", DocPage),
             ("bulk", "\U0001F4C1", "Bulk Add Folder", BulkPage)]

    @staticmethod
    def has_section(key):
        """Cooking School, Local Area and Waypoints only show in the menu when this library has something for them."""
        if key == "school":
            return os.path.isdir(os.path.join(RESEARCH, *lv.WARDEE.split("/")))
        if key == "local":
            return any(f.endswith(".md") for _, _, fs in os.walk(os.path.join(RESEARCH, "local-area")) for f in fs)
        if key == "waypoints":
            return bool(wpt.load()) or os.path.isdir(os.path.join(RESEARCH, "local-area", "maps"))
        return True

    def __init__(self):
        super().__init__()
        self.title("Library Manager")
        self.geometry("1120x800"); self.minsize(760, 560)   # button rows wrap, so it can be fairly narrow
        self.restore_window()
        self.configure(bg=C["bg"])
        if os.path.exists(ICON):
            self.iconbitmap(ICON)
        self.style()
        self.busy, self.actions, self.q = False, [], queue.Queue()
        self.na_map = nams.MapServer(on_action=lambda *a: self.q.put(("call", lambda: self.na_action(*a))))
        self.lib, self.thumbs, self.favs, self.notes = lv.Library(self), lv.Thumbs(self), lv.Favorites(), lv.Notes()
        self.lib.on_ready(self.notes.cache.clear)   # a refreshed library re-checks which items have notes
        self.bind_all("<MouseWheel>", self.wheel)
        self.bind_all("<Control-Home>", lambda e: self.jump("top"))
        self.bind_all("<Control-End>", lambda e: self.jump("bottom"))

        side = tk.Frame(self, bg=C["side"], width=230); side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Label(side, text="\U0001F4DA", font=("Segoe UI Emoji", 26), bg=C["side"], fg=C["accent"]).pack(anchor="w", padx=22, pady=(24, 0))
        tk.Label(side, text="Research Library", font=(F, 15, "bold"), bg=C["side"], fg="#ffffff").pack(anchor="w", padx=22)
        tk.Label(side, text="Library Manager", font=(F, 10), bg=C["side"], fg=C["side_dim"]).pack(anchor="w", padx=22, pady=(0, 10))
        self.nav = {}
        for e_ in self.PAGES:
            if isinstance(e_, str):
                tk.Label(side, text=e_, font=(F, 8, "bold"), bg=C["side"], fg=C["side_dim"]).pack(anchor="w", padx=24, pady=(14, 4))
                continue
            key, ic, name, _ = e_
            f = tk.Frame(side, bg=C["side"], cursor="hand2")
            if self.has_section(key):   # the page still exists (links can open it); only its menu entry is left out
                f.pack(fill="x")
            bar = tk.Frame(f, bg=C["side"], width=4); bar.pack(side="left", fill="y")
            ico = tk.Label(f, text=ic, font=("Segoe UI Emoji", 12), bg=C["side"], fg=C["side_text"], width=2, padx=0)
            ico.pack(side="left", padx=(16, 0))
            l = tk.Label(f, text=name, font=(F, 11), bg=C["side"], fg=C["side_text"], anchor="w", padx=10, pady=8)
            l.pack(side="left", fill="x", expand=True)
            l.ico = ico
            for w in (f, ico, l):
                w.bind("<Button-1>", lambda e, k=key: self.menu_click(k))
                w.bind("<Enter>", lambda e, k=key: self.hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self.hover(k, False))
            self.nav[key] = (f, bar, l)
        tk.Label(side, text=RESEARCH, font=(F, 9), bg=C["side"], fg=C["side_dim"]).pack(side="bottom", anchor="w", padx=22, pady=(4, 16))
        guide = os.path.join(RESEARCH, "README - Library Manager.md")
        hl = tk.Label(side, text="?  How to use", font=(F, 9, "underline"), bg=C["side"], fg=C["side_text"], cursor="hand2")
        hl.pack(side="bottom", anchor="w", padx=22)
        hl.bind("<Button-1>", lambda e: os.startfile(guide) if os.path.exists(guide) else None)
        self.upd_link = tk.Label(side, text="⟳  Check for updates", font=(F, 9, "underline"), bg=C["side"], fg=C["side_text"],
                                 cursor="hand2")
        self.upd_link.pack(side="bottom", anchor="w", padx=22, pady=(0, 2))
        self.upd_link.bind("<Button-1>", lambda e: self.check_updates())

        main = tk.Frame(self, bg=C["bg"]); main.pack(side="left", fill="both", expand=True)
        head = tk.Frame(main, bg=C["bg"]); head.pack(fill="x", padx=30, pady=(24, 12))
        self.h_title = tk.Label(head, font=(F, 20, "bold"), bg=C["bg"], fg=C["text"], anchor="w"); self.h_title.pack(anchor="w")
        self.h_sub = tk.Label(head, font=(F, 10), bg=C["bg"], fg=C["dim"], anchor="w", justify="left", wraplength=820)
        self.h_sub.pack(anchor="w", pady=(2, 0))
        head.bind("<Configure>", lambda e: self.h_sub.config(wraplength=max(300, e.width - 10)))   # wraps to the window width

        statusbar = tk.Frame(main, bg=C["line"]); statusbar.pack(side="bottom", fill="x")
        self.prog = ttk.Progressbar(statusbar, mode="indeterminate", length=140, style="G.Horizontal.TProgressbar")
        self.status = tk.Label(statusbar, text="Ready", font=(F, 9), bg=C["line"], fg=C["dim"], anchor="w", padx=12, pady=4)
        self.status.pack(side="left", fill="x", expand=True)

        self.logbox = tk.Frame(main, bg=C["bg"])
        lh = tk.Frame(self.logbox, bg=C["bg"]); lh.pack(fill="x")
        tk.Label(lh, text="Activity", font=(F, 10, "bold"), bg=C["bg"], fg=C["dim"]).pack(side="left")
        Btn(lh, "Clear", lambda: self.log.delete("1.0", "end"), "secondary", 8, 8, 1).pack(side="right")
        lf = tk.Frame(self.logbox, bg=C["log_bg"]); lf.pack(fill="both", expand=True, pady=(4, 0))
        self.log = tk.Text(lf, height=9, bg=C["log_bg"], fg=C["log_fg"], font=("Consolas", 9), relief="flat", wrap="word",
                           padx=10, pady=8, insertbackground=C["log_fg"])
        lsb = ttk.Scrollbar(lf, command=self.log.yview); self.log.configure(yscrollcommand=lsb.set)
        self.log.pack(side="left", fill="both", expand=True); lsb.pack(side="right", fill="y")
        self.log.tag_configure("head", foreground="#f0c27b", font=("Consolas", 9, "bold"))
        self.log.tag_configure("ok", foreground="#8fd19e"); self.log.tag_configure("err", foreground="#f19a8f")
        self.logbox.pack(side="bottom", fill="x", padx=30, pady=(8, 12))

        self.content = tk.Frame(main, bg=C["bg"]); self.content.pack(fill="both", expand=True, padx=30)
        self.pages = {e[0]: e[3](self) for e in self.PAGES if not isinstance(e, str)}
        self.pages["local"].actions["Maps"] = [("\U0001F4CD  My waypoints", self.show_waypoints)] + (
            [("\U0001F30E  North America map", lambda: self.open_na_map())] if nams.available() else [])
        self.pages["local"].hints["Maps"] = (
            "\U0001F50D  Search by map name (e.g. Whitefish) or by position to find the map a place is on - e.g.  "
            "48.1958N 114.3129W   or   48.1958, -114.3129   or   48°11'45\"N 114°18'46\"W   or paste a Google Maps link.  "
            "Opening a map from the result zooms in on that spot.")
        self.current = None
        self.show("home")
        self.after(100, self.poll)
        self.after(30000, self.weekly_updates)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def wheel(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if hasattr(w, "on_wheel"):
                return w.on_wheel(e)
            if isinstance(w, (tk.Text, ttk.Treeview)):
                return
            w = w.master

    def menu_click(self, key):
        """A click in the left-hand menu starts that section afresh; other ways of arriving (Back, links, Home buttons)
        keep the section where it was."""
        p = self.pages.get(key)
        if hasattr(p, "restart"):
            try:
                p.restart()
            except Exception as e:
                self.write(f"(could not restart {key}: {e})\n", "err")
        self.show(key)

    def jump(self, where):
        p = self.pages.get(self.current)
        if hasattr(p, "jump"):
            p.jump(where)

    def browse_category(self, cat):
        if cat == "local-area":
            self.pages["local"].restart(); self.show("local")
            return
        self.show("library"); self.pages["library"].set_category(cat)

    def show_waypoints(self):
        self.show("waypoints")

    @staticmethod
    def na_map_available():
        return nams.available()

    def open_na_map(self, lat=None, lon=None, name=None):
        """The North America map (OpenStreetMap, offline) - a web page, so it opens in the web browser."""
        if not nams.available():
            messagebox.showinfo("North America map", "The North America map isn't in the library (local-area\\maps\\north-america).",
                                parent=self)
            return
        self.na_map.open(lat, lon, name)

    def na_action(self, name, lat, lon, which):
        """A button on the North America map (in the browser) asked for something here."""
        self.deiconify(); self.lift(); self.focus_force()
        if name == "open":
            lv.open_waypoint(self, {"name": "Position from the North America map", "lat": lat, "lon": lon}, which)
        elif name == "addwp":
            self.show("waypoints"); self.pages["waypoints"].add_at(lat, lon)

    def show_maps(self):
        """Local Area > Maps (the list of every topo map)."""
        p = self.pages["local"]
        p.restart()
        self.show("local")
        k = next((k for k, t in enumerate(p.topics) if t[0] == "Maps"), None)
        if k is not None:
            p.open_topic(k)

    def waypoints_changed(self):
        """A waypoint was added / edited on a map: refresh the Waypoints list if it is the page showing."""
        p = self.pages.get("waypoints")
        if p and self.current == "waypoints":
            p.fill()

    def open_item(self, it):
        key = ("school" if lv.is_course(it) else "recipes" if it["category"] == "recipes" else
               "local" if it["category"] == "local-area" else
               "docs" if it["type"] in lv.DOC_TYPES else "library")
        self.show(key); self.pages[key].open_item(it)

    def style(self):
        s = ttk.Style(self); s.theme_use("clam")
        s.configure("Treeview", font=(F, 9), rowheight=26, background="#ffffff", fieldbackground="#ffffff", bordercolor=C["line"])
        s.configure("Treeview.Heading", font=(F, 9, "bold"), background=C["sec"], foreground=C["text"], relief="flat", padding=(6, 4))
        s.map("Treeview", background=[("selected", "#d6eadf")], foreground=[("selected", C["text"])])
        s.configure("TCombobox", padding=4, fieldbackground="#fbfaf7", background=C["sec"], bordercolor=C["line"], arrowcolor=C["text"])
        s.map("TCombobox", fieldbackground=[("readonly", "#fbfaf7")], selectbackground=[("readonly", "#fbfaf7")],
              selectforeground=[("readonly", C["text"])])
        s.configure("G.Horizontal.TProgressbar", background=C["primary"], troughcolor="#d5d0c4", bordercolor=C["line"],
                    lightcolor=C["primary"], darkcolor=C["primary"])
        s.configure("Vertical.TScrollbar", background=C["sec"], troughcolor=C["card"], bordercolor=C["line"], arrowcolor=C["dim"])
        self.option_add("*TCombobox*Listbox.font", (F, 10))

    def hover(self, key, on):
        if key != self.current:
            f, bar, l = self.nav[key]
            for w in (f, bar, l, l.ico):
                w.config(bg=C["side_hover"] if on else C["side"])

    def show(self, key):
        if self.current:
            self.pages[self.current].pack_forget()
        self.current = key
        for k, (f, bar, l) in self.nav.items():
            on = k == key
            for w in (f, l, l.ico):
                w.config(bg=C["side_active"] if on else C["side"])
            bar.config(bg=C["accent"] if on else C["side"])
            l.config(fg="#ffffff" if on else C["side_text"], font=(F, 11, "bold" if on else "normal"))
        p = self.pages[key]
        self.h_title.config(text=p.title); self.h_sub.config(text=p.subtitle)
        if p.show_log:
            self.logbox.pack(side="bottom", fill="x", padx=30, pady=(8, 12), before=self.content)
        else:
            self.logbox.pack_forget()
        p.pack(fill="both", expand=True)
        p.on_show()

    # ---------------------------------------------------------------- running the scripts
    def run(self, args, what, done=None):
        if self.busy:
            messagebox.showinfo("Busy", "Please wait - another job is still running."); return
        self.busy, self.done_cb, self.out = True, done, []
        for b in self.actions:
            b.set_enabled(False)
        self.status.config(text=what + " ..."); self.prog.pack(side="right", padx=12); self.prog.start(12)
        self.write(f"\n\u25b6 {what}\n", "head")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

        def work():
            try:
                p = subprocess.Popen([PY, "-u"] + args, cwd=RESEARCH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                     stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                for line in p.stdout:
                    self.q.put(("line", line))
                self.q.put(("done", p.wait()))
            except Exception as e:
                self.q.put(("line", f"Could not start: {e}\n")); self.q.put(("done", -1))
        threading.Thread(target=work, daemon=True).start()

    def write(self, text, tag=None):
        at_end = self.log.yview()[1] > 0.98
        self.log.insert("end", text, tag)
        if at_end:
            self.log.see("end")

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "call":   # work handed over from another thread (e.g. the North America map's server)
                    try:
                        val()
                    except Exception as e:
                        self.write(f"(could not do that: {e})\n", "err")
                    continue
                if kind == "line":
                    self.out.append(val)
                    self.write(val, "err" if re.search(r"FAILED|Traceback|Error\b", val) else None)
                    if val.strip():
                        self.status.config(text=val.strip()[:150])
                else:
                    self.finish(val)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def finish(self, rc):
        self.busy = False
        self.prog.stop(); self.prog.pack_forget()
        for b in self.actions:
            b.set_enabled(True)
        self.write("\u2714 finished\n" if rc == 0 else f"\u2716 stopped (code {rc})\n", "ok" if rc == 0 else "err")
        self.status.config(text="Ready")
        if self.done_cb:
            try:
                self.done_cb(rc, "".join(self.out))
            except Exception as e:
                self.write(f"(display error: {e})\n", "err")
        self.pages["home"].load()

    # ---------------------------------------------------------------- check for updates (see suite_updates.py)
    def check_updates(self, quiet=False):
        """Asks in the background; the answer comes back through the queue. quiet: only mark the menu link if there is news."""
        if not quiet:
            self.upd_link.config(text="⟳  Checking...")

        def work():
            try:
                r, err = su.check(), None
            except Exception as e:
                r, err = None, str(e)
            self.q.put(("call", lambda: self.updates_checked(r, err, quiet)))
        threading.Thread(target=work, daemon=True).start()

    def weekly_updates(self):
        if su.weekly_due():
            self.check_updates(quiet=True)

    def updates_checked(self, r, err, quiet):
        news = bool(r and r.get("updates"))
        self.upd_link.config(text="⟳  Update available" if news else "⟳  Check for updates",
                             fg=C["accent"] if news else C["side_text"], font=(F, 9, "bold", "underline") if news else (F, 9, "underline"))
        if quiet:
            return
        if err:
            messagebox.showerror("Check for updates", f"Couldn't check for updates:\n{err}", parent=self); return
        self.updates_dialog(r)

    def updates_dialog(self, r):
        suite, git = su.has_suite(), su.is_git()
        d = tk.Toplevel(self); d.title("Check for updates"); d.configure(bg=C["card"]); d.transient(self); d.resizable(False, False)
        if os.path.exists(ICON):
            d.iconbitmap(ICON)
        body = tk.Frame(d, bg=C["card"]); body.pack(fill="both", padx=24, pady=(20, 8))
        label(body, f"{r['updates']} update(s) available" if r["updates"] else "Everything is up to date", 14, True).pack(anchor="w")
        for c in r["components"]:
            row = tk.Frame(body, bg=C["card"]); row.pack(fill="x", pady=(10, 0))
            ver = f"{c.get('installed') or '-'}  →  {c['latest']}" if c.get("update") else (c.get("installed") or c.get("latest") or "")
            label(row, c.get("title") or c["name"], 10, True).pack(side="left")
            label(row, f"{ver}   ·   {c.get('status', '')}", 10, fg="primary" if c.get("update") else "dim").pack(side="right", padx=(24, 0))
            if c.get("update") and c.get("notes"):
                label(body, c["notes"], 9, fg="dim", wraplength=560).pack(anchor="w")
        if r["updates"] and suite and not git:
            hint = ("Only program files are replaced - your library, notes and settings stay as they are. Library Manager closes, "
                    "updates in its own window, then starts again.")
        elif r["updates"] and git:
            hint = "This copy is a git checkout - update it with git pull."
        elif r["updates"]:
            hint = "Installed without the AI Research Suite, so the new version is downloaded from the release page."
        else:
            hint = ""
        if hint:
            label(body, hint, 9, fg="dim", wraplength=560).pack(anchor="w", pady=(14, 0))
        weekly = tk.BooleanVar(value=su.settings().get("weeklyCheck", False))
        if suite:
            tk.Checkbutton(body, text="Check once a week when online (only github.com is contacted)", variable=weekly,
                           command=lambda: su.save_settings(weeklyCheck=weekly.get()), bg=C["card"], fg=C["text"],
                           activebackground=C["card"], selectcolor=C["card"], font=(F, 9)).pack(anchor="w", pady=(12, 0))
        bar = tk.Frame(d, bg=C["card"]); bar.pack(fill="x", padx=24, pady=(10, 20))
        Btn(bar, "Close", d.destroy, "secondary").pack(side="right")
        page = next((c.get("page") for c in r["components"] if c.get("update") and c.get("page")), None)
        if r["updates"] and suite and not git:
            Btn(bar, "Update now", lambda: (d.destroy(), self.run_update(r)), "primary").pack(side="right", padx=(0, 8))
        elif r["updates"] and page and not suite:
            Btn(bar, "Open the release page", lambda: os.startfile(page), "primary").pack(side="right", padx=(0, 8))
        d.update_idletasks()
        d.geometry(f"+{self.winfo_rootx() + (self.winfo_width() - d.winfo_width()) // 2}+{self.winfo_rooty() + 120}")
        d.grab_set()

    def run_update(self, r):
        if self.busy:
            messagebox.showinfo("Busy", "Please wait - another job is still running.", parent=self); return
        try:
            su.start_update()
        except Exception as e:
            messagebox.showerror("Check for updates", f"Couldn't start the updater:\n{e}", parent=self); return
        self.close()

    # ---------------------------------------------------------------- window size / place, kept between runs
    def restore_window(self):
        """Last size and position (and maximised or not) from _work/viewer_settings.json - only if it is still on screen."""
        w = lv.load_json(lv.SETTINGS_FILE, {}).get("window") or {}
        m = re.fullmatch(r"(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)", w.get("geometry", ""))
        if m:
            wd, ht, x, y = int(m[1]), int(m[2]), int(m[3]), int(m[4])
            sw, sh = self.winfo_vrootwidth() or self.winfo_screenwidth(), self.winfo_vrootheight() or self.winfo_screenheight()
            wd, ht = max(760, min(wd, sw)), max(560, min(ht, sh))
            if -wd + 120 < x < sw - 120 and 0 <= y < sh - 80:   # enough of it visible to grab
                self.geometry(f"{wd}x{ht}{x:+d}{y:+d}")
            else:
                self.geometry(f"{wd}x{ht}")
        self._normal_geom = self.geometry()
        if w.get("zoomed"):
            self.after(50, lambda: self.state("zoomed"))
        self.bind("<Configure>", self._track_window, add="+")

    def _track_window(self, e):
        if e.widget is self and self.state() == "normal":   # remember the un-maximised size
            self._normal_geom = self.geometry()

    def save_window(self):
        try:
            st = lv.load_json(lv.SETTINGS_FILE, {})
            st["window"] = {"geometry": getattr(self, "_normal_geom", self.geometry()), "zoomed": self.state() == "zoomed"}
            lv.save_json(lv.SETTINGS_FILE, st)
        except Exception:
            pass

    def close(self):
        if self.busy and not messagebox.askyesno("Still working", "A job is still running. Close anyway?\n"
                                                 "(It is safer to wait until it finishes.)"):
            return
        self.save_window()
        self.na_map.stop()
        for p in self.pages.values():   # keep a note that was being typed
            r = getattr(p, "reader", None)
            if r is not None:
                try:
                    r.autosave()
                except Exception:
                    pass
        self.destroy()


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Research.LibraryManager")
    except Exception:
        pass
    if sys.stderr is None:   # started with pythonw (no console): keep error messages in _work/library_manager_errors.log
        try:
            import datetime
            sys.stderr = open(os.path.join(RESEARCH, "_work", "library_manager_errors.log"), "a", encoding="utf-8", buffering=1)
            sys.stderr.write(f"\n--- started {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
            threading.excepthook = lambda a: __import__("traceback").print_exception(a.exc_type, a.exc_value, a.exc_traceback)
        except OSError:
            pass
    App().mainloop()
