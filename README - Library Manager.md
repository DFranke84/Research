# Research Library & Library Manager – How to set up and use

This folder is a self-contained offline library (practical, medical, repair and recipe material, with its PDFs,
photos and videos) plus **Library Manager**, a desktop app for browsing, reading and adding to it. Everything lives
inside this folder, so you can copy the whole folder to another drive or PC.

> `README.md` (next to this file) is the overview: how the apps fit together, the categories, and how to fill a
> new library (your own files, links, Wikipedia, starter packs). `LIBRARY.md` is a summary of what is in *your*
> library, rewritten automatically after every change. This file explains every Library Manager page in detail.

---

## Quick start

1. **Double-click `Setup.bat`** in this folder and answer the questions (press Enter for Yes).
2. **Start Library Manager** with the **Library Manager** shortcut that Setup puts on your desktop
   (or double-click **`Library Manager.vbs`** in this folder).

That's it. Setup is only needed once per PC, and again after moving or copying the folder.

---

## Setting up

### What you need

| Needed for | What | Setup handles it? |
|---|---|---|
| Everything | Windows 10 or 11, 64-bit | – |
| Everything | **Python 3.14** (64-bit) | Yes: finds it, or offers to install it |
| Everything | ~45 Python packages (about 400 MB) | Yes: installs them into `_scripts\.venv` |
| Recipe PDFs, Facebook recipes | **Google Chrome** or **Microsoft Edge** | Edge comes with Windows; Setup offers Chrome if neither is there |
| Old Word `.doc` files | **antiword** | Offers *Git for Windows*, which includes it |
| *Recipe from Email* | **Microsoft Outlook** (desktop version) | No: must already be installed |
| Adding recipes from the web, first-time Setup | An internet connection | – |

Browsing and reading the library works completely **offline**.

### Running Setup

Double-click **`Setup.bat`**. It works through six steps, explains each one, and asks before installing anything:

1. **Python 3.14**: it uses the one already installed, or offers to download and install it (via Windows' `winget`,
   or straight from python.org).
2. **The library's Python environment** (`_scripts\.venv`): it keeps the environment if it works. If it doesn't
   (for example, the folder came from another PC), the old one is renamed `.venv.old-<date>`, not deleted, and a
   fresh one is built. You can delete the old one afterwards.
3. **Python packages**, from `_scripts\requirements.txt`. The first time takes a few minutes; later runs take seconds.
4. **Optional tools**: Chrome (only if neither Chrome nor Edge is found) and antiword.
5. **Desktop shortcut**: creates "Library Manager", or re-points it at this copy of the folder.
6. **Final check**: lists every piece as **OK**, **NEED** (missing and required) or **–** (missing but optional),
   with what each is for.

Setup is safe to run again at any time. It only adds or repairs what is missing.

*Advanced:* `Setup.bat -Yes` answers Yes to everything; `Setup.bat -NoShortcut` leaves the desktop alone.
To just check without installing: `_scripts\.venv\Scripts\python _scripts\check_setup.py`.

### Moving or copying the library

- Copy the **whole** Research folder (it is large: the library plus `_sources` with the original archives).
  The app and scripts find the library from wherever they are; nothing is tied to a drive letter.
- Then run **`Setup.bat`** in the new copy. On the same PC this just re-points the desktop shortcut. On a new PC
  it installs Python and the packages.
- Your favorites and view settings travel with the folder (they're in `_work\`).

---

## Using Library Manager

The left sidebar has two groups: **Browse** (find and read things) and **Add** (put new things in).
The Home page shows totals, the most recently added items and every category; click a category to browse it.

### Browsing

| Section | What's in it |
|---|---|
| **Favorites** | Everything you've starred, grouped by section, by category, or newest first |
| **Recipes** | All recipes: web bookmarks, emails, Facebook saves, recipe cards, videos, cookbooks. Opens on tiles by kind of dish (All Recipes first, then Breads & Baking, Desserts, Breakfast, Soups, Chicken & Turkey, Beef, Pork, Fish, Pasta & Casseroles, Pizza & Sandwiches, Vegetables & Salads, Sauces, Drinks, Canning & Dairy, Air Fryer, Instant Pot, Other) – inside each, buttons by source (Web, Email, Facebook, Recipe cards, Videos, Cookbooks). A recipe can be in more than one tile (e.g. chicken soup) |
| **Local Area** | Your home area: plants, wildlife, growing guides, maps and waypoints (built for the first owner's area - empty in a new library; see below) |
| **Documents & Books** | PDFs, Word documents and books from every category. Opens on topic tiles (All Documents first, then Gardening & Farming, Food Storage, Cooking & Recipes, Medical, Water & Sanitation, Wilderness/Hunting/Foraging, Emergency & Disaster, Energy, Skills/Tools/Building, Radio, Security, Legal & Financial) – click one to drill in; **◀ All topics** goes back |
| **Whole Library** | Everything. Opens on topic tiles (All of the Library first, then Vehicles & Engines, Skills/Tools/Building, Gardening & Farming, Food Storage, Recipes & Cooking, Medical, Water & Sanitation, Energy, Radio, Wilderness/Hunting/Foraging, Emergency & Disaster, Security, Legal & Financial, Local Area) – inside, buttons by category or by kind (Repair guides, Q & A, Wikipedia, PDFs…) |
| **Offline Archives** | The Kiwix .zim archives (Wikipedia, iFixit, Stack Exchange…) - read-only, see below |

The window remembers its size and position (and whether it was maximised) from the last time you closed it. In a
narrow window, rows of buttons wrap onto a second line instead of disappearing.

On the browse pages:

- **Search box**: type words from the title (results update as you type).
- **Filter buttons** (e.g. *Web recipes*, *Email*, *Fungi*) and, on some pages, **category / type** drop-downs.
- **Sort**: *Title A–Z*, *Newest added* or *Oldest added*.
- **Show 24 · 48 · 96 · 200 · All** (bottom right): every page starts on **All**, which loads more cards as you
  scroll. The paging buttons are **«** first, **‹ Previous**, a page box you can type into, **Next ›** and **»** last.
- **▲ Top / ▼ Bottom** buttons (lower right of long lists), or **Ctrl+Home / Ctrl+End**. On a very long "All"
  list, Bottom offers to switch to pages of 200 and open the last page instead.
- Each card shows a picture, title, type and a short description. **📷 8** means it has 8 pictures; click that
  badge to go straight to them.
- **☆** on a card adds it to Favorites (★ = already a favorite; click again to remove).

The app keeps your place: going **Back** from an item, or deleting one, returns you to where you were in the list.
Clicking a section in the left-hand menu starts it afresh: filters back to *All* (Offline Archives: *All archives*),
search cleared, any open item closed, back to the top. The Add pages keep what you were typing.

### Local Area

Local Area is the section about where you live, in the library folder `local-area`. Make it with
**`Build Local Area.bat`** (see `README.md`, *Your Local Area*): it asks for your town and builds Start Here
(frost dates, growing season, hardiness zone, monthly weather), species pages for the plants, wildlife, insects
and fungi seen near you, and - in the US - topographic maps. Until then the section is not shown. The species pages'
Wikipedia articles come from wikipedia.org, which slows down (throttles) big batches; with a Wikipedia archive in
`_sources\zim` (Get Archives.bat → *Wikipedia - text only*) they are read from that file instead. (The first owner's
Kalispell section was put together by hand and is not part of the download.)

- **Start Here** opens straight away. The other tiles - **Plants**, **Wildlife**, **Insects & Spiders**,
  **Fungi & Lichens**, **Maps** and **Your Documents** (local documents you added with *Add a Document*, category
  Local Area) - show how many pages they hold; buttons inside split them further (Birds, Mammals, Conifers…).
- Each species page has key facts (scientific name, family, how often it is seen near you and in which months),
  photos with their photographers' licenses, a month-by-month sightings table and the Wikipedia article.
- **◀ All topics** goes back to the tiles. Plant, wildlife and fungi pages offer **Change type…** to file them
  under another group.
- **Maps** - topographic GeoPDF maps open on the **Pages** tab; moving the mouse shows the position under it.
  **Search by position**: type or paste a position into a Local Area search box (`48.1958, -114.3129`,
  `48°11'45"N 114°18'46"W`, `N48 11.748 W114 18.774` or a Google Maps link) to find the map it is on.
- **📍 Waypoints** (menu, under Local Area) are your own named places - home, springs, trailheads. **+ Add a
  waypoint** takes a name, a position in any of the forms above, and notes; or click **📍 Add waypoint** on an
  open map and click the spot (or right-click it). Each waypoint opens the map it is on, zoomed in on a red pin;
  **Edit…**, **Copy position** and **Delete** are in the list. Waypoints are saved in `_work\waypoints.json` and go
  to the tablet with the next viewer update.
- **📏 Measure** (on every map): click points - each leg's straight-line distance is drawn and the total is shown
  (miles and km). **↶ Undo last point**, **Clear**, **Done**.
- A **🌎 North America map**, when the library has one (`local-area\maps\north-america\`), opens in a window of its
  own, served from this computer only, with place search and **📍 Where am I?**.

**Fungi pages: never eat a wild mushroom identified from a description or photo.**

### Offline Archives

**Offline Archives** (in Browse) reads the Kiwix archives (`.zim` files) in `_sources\zim` directly - whatever you
downloaded with **Get Archives.bat** or put there yourself: Wikipedia, iFixit, Wikibooks, WikEM, MedlinePlus, NHS
medicines, Appropedia, energypedia, Stack Exchange Q&A sites, Project Gutenberg books and more (all free from
https://library.kiwix.org). It is read-only: nothing from the archives is copied into the library. With no archives
the page is empty.

- With the search box empty you see a card for every archive. Click one to open its front page.
- Archives tagged **🔍 Search-first** (WikEM, Wikipedia, MedlinePlus and the Stack Exchange Q&A sites) have little to
  browse, so clicking them shows a short guide instead: what the archive is, how to search it, example searches you
  can click, and tips (*Open front page anyway* is at the bottom). Translated copies of pages (…/de, …/es) are left out
  of the results.
- Type to search. **Titles** shows matching article titles; **Pages mentioning …** searches the full text. The drop-down
  next to the search box picks one archive or *All archives*.
- Articles open in the normal reader (text, **Pictures** tab, clickable links to other articles in the archive).
  **← Back** steps back one page at a time, like a web browser - from a book to the bookshelf or author page you
  picked it from, at the place you had scrolled to - and finally to the search results or the archive's guide.
- **Web page** tab (next to Read) shows the archive's own page - its layout, tables and styles - inside the app.
  Links in it open the next article (Previous article still works); web addresses open in your normal browser. The tab
  you pick (Read or Web page) is remembered for the next archive article.
- **🌐 Open in browser** shows the same page in Edge/Chrome. Both are served from this PC only - nothing goes on the internet.
- The document libraries list their PDFs; clicking one opens it on the **Pages** tab.
- **Gutenberg** (English and American literature): click the card for its most popular books and **Browse the bookshelf**.
  The bookshelf adds more books as you scroll down, all the way to the end; **▼ Bottom** loads the rest and jumps there.
  The **Sort:** bar (fixed at the top - it stays put while you scroll) orders the bookshelf by *Most popular*, *Title A–Z / Z–A* or *Author A–Z / Z–A* (by
  surname); author pages sort by popularity or title.
  Searching shows **Authors** first (accents don't matter - *bronte* finds Brontë); click an author for all their books,
  most popular first (long lists add more as you scroll, like the bookshelf). Books open whole on the Read tab, with their illustrations.
- Pictures for the article you are reading are kept briefly in Windows' temporary folder and removed when the app closes.

### Reading an item

Click any card to open it. At the top: a large picture, labels (category, type, source) and buttons, such as
**Play video / Play audio**, **Open PDF**, **Open original**, **Open web page**, **Show in folder**,
**☆ Add to favorites** and **🗑 Delete…**. Below are the tabs:

- **Read**: the full text, with headings, lists, pictures and clickable links.
- **Pictures (n)**: every picture that belongs to the item. Click one to see it large. Use **‹ ›**, the arrow
  keys or a click to flip through, **Esc** to return to the grid, and **Open full size** for your normal picture viewer.
- **Pages**: for PDFs, flip through the actual pages inside the app. Keep scrolling down with the mouse wheel at the
  bottom of a page and it turns to the next page (scrolling up at the top goes back to the end of the page before).
  Maps are the exception - there the wheel just moves around the map.

On long pages (whole books, long articles, lists) **▲ Top / ▼ Bottom** buttons appear in the corner; **Ctrl+Home / Ctrl+End** do the same.

**Zoom:** on the **Read** and **Pages** tabs and in the large picture view, the **−  100%  +  Fit** buttons at the right of the tabs make the text, the PDF page or the picture bigger or smaller - or use **Ctrl +**, **Ctrl −**, **Ctrl 0** (back to normal) or **Ctrl + mouse wheel**. In the picture view the plain mouse wheel zooms too, and a zoomed picture can be dragged around with the mouse (a click at Fit still goes to the next picture). A zoomed PDF page scrolls sideways (scrollbar, or **Shift + wheel**). Your text size is remembered; PDFs and pictures open at Fit.

- **Note**: your own note about the item (see *Notes* below).

**Back** returns to the list where you left it.

### Favorites

Star anything with **☆** (on a card or in the reader). The Favorites page groups them **By section**
(Recipes → Web / Email / …, Documents & Books, Library), **By category**
or **Newest first**.

### Notes

Any item (a recipe, document, field guide, lesson video, recipe card…) can have your own note. Open the item and
click the **+ Add note** tab, type, and click **Save note** (or press **Ctrl+S**). The note is also saved
automatically when you switch tabs, go **Back**, use Previous/Next or close the app.

- The note is a plain text file with the **same name as the item, beside it**: `bread-pudding.md` → `bread-pudding.txt`,
  `Apple Pie Bake.mp4` → `Apple Pie Bake.txt`. You can open it in any editor (**Open in Notepad** does that).
- Items with a note show a small **📝** on their card (click it to go straight to the note), a **📝 Note** label in
  the reader, and the tab reads **📝 Note**.
- **Delete note** sends just the note to the Recycle Bin. Saving an empty note offers to delete it.
- Deleting the item also deletes its note (it is listed as "← your note" in the delete window). Re-fetching a web
  recipe or replacing an email recipe keeps the note.

### Fixing where an item shows up

- **Recipe tiles…** (on any recipe): tick the Recipes tiles it belongs in (Breads, Desserts, Chicken…, Air Fryer,
  Instant Pot). Your choice replaces the automatic guess from the title; no ticks puts it in *Other Recipes*;
  **Use automatic** goes back to the guess. Saved in `_work\recipe_tiles.json` – no files are moved.
- **Change category…** (on documents and articles): tick the category it belongs in – the line underneath says what
  will move (the page, its original PDF, photos and your note) – then **Save**. Favorites follow it and the catalog refreshes on its own.
  Items inside collections (your recipe collection, Local Area) and items that other pages link to
  can't be moved – the window says why.
- **Change type…** (on Local Area plant, grass, wildlife and fungi pages): pick the type it belongs under (e.g. from
  *Shrubs & hedges* to *Trees - Shade & ornamental*). It then shows under that tile and button. The page itself stays
  where it is (Local Area pages link to each other); your choice is saved in `_work\local_area\type_overrides.json`, so
  rebuilding the Local Area pages keeps it.

### Deleting an item

In the reader, **🗑 Delete…** first shows exactly what would go: the item's page, its PDF, photos and videos,
and its lines on list pages. Nothing happens until you click **Move to Recycle Bin**. Files go to the Windows
**Recycle Bin**, so you can restore them from there. Files that another item also uses are kept.

### Adding things

All the Add pages show their progress in the **Activity** panel at the bottom. Only one job runs at a time.

**Recipe from Link**: paste a recipe's web address. Choose *Sort automatically* (air fryer / Instant Pot /
everything else) or pick the folder, then click **Add Recipe**. You get only the recipe (title, photo,
ingredients, steps), saved as a page plus a clean one-page PDF. Video links (YouTube, Facebook, TikTok…) are saved
as the video. Duplicates are caught, including the same recipe under a different address. Tick *Replace* to fetch
it again.

**Recipe from Email**: first move the email into the Outlook folder **Email › Recipes**. Then type a few words
from its subject and click **Add Recipe** (or **Preview only** to see what would be saved). An email holding
several recipes becomes one entry with every recipe in it. Names, addresses and signatures are removed.

**Add a Document**: choose one file (PDF, Word `.docx`/`.doc`, `.odt`, `.rtf`, `.txt`, `.md`, web page,
`.epub` e-book or `.pptx` slides). The app checks whether it is already in the library and reads scanned pages
with OCR. It then suggests a title and category, which you can change before clicking **Add to Library**.
The original file is kept beside a searchable text copy.

**Bulk Add Folder**: for many documents at once.
1. Choose a folder and click **Review folder**. Nothing is added yet. Every file is listed as *New*,
   *Already in library*, *Almost the same as a library item*, *Doesn't fit the library topics*, *Couldn't read it*
   or *File type not supported*.
2. Double-click rows to tick or untick them, fix titles or categories in the *Selected* line, then click
   **Add ticked files**. *Open an earlier review…* reloads a previous review.

After anything is added or deleted, the catalog (`CATALOG.csv` / `.json`) and `LIBRARY.md` update themselves.

Web pages, PDFs from links, Wikipedia articles and the starter packs are added from outside the window - see
`README.md` (*Filling your library*).

---

## Where things are kept

| Location | What |
|---|---|
| Category folders (`recipes\`, `water\`, `medical-first-aid\`, …) | The library itself: one `.md` page per item, with its PDF/original, `<name>_images\` pictures and videos beside it |
| `recipes\personal-recipe-collection\` | Recipes you add: `bookmarks\` (Recipe from Link), `email-recipes\` (Recipe from Email) |
| `CATALOG.csv` / `CATALOG.json` | The list of every item (open the CSV in Excel) |
| `LIBRARY.md` | A summary of your library (counts per category and source) |
| `_work\favorites.json` | Your favorites |
| `<item name>.txt` beside an item | Your note for that item |
| `_work\viewer_settings.json` | Remembered choices such as the sort order |
| `_work\thumbs\` | Picture previews; safe to delete, they are remade as needed |
| `_scripts\` | The app and tools (`library_manager.pyw`, `library_viewer.py`, numbered scripts), `requirements.txt`, the Python environment `.venv` |
| `_sources\zim\` | Downloaded Kiwix archives (Offline Archives, starter packs, the AI apps' 🗃️ search) |
| `starter\` | The starter pack lists |

---

## Troubleshooting

| Problem | Try this |
|---|---|
| The shortcut does nothing, or says it can't find Python | Run **`Setup.bat`** (this is normal after moving the folder or on a new PC). |
| The final check shows **NEED** lines | Run Setup again with the internet connected. The line says what is missing. |
| Recipe from Email says no email was found | Check the email is in **Email › Recipes** in Outlook, and try fewer or different subject words. |
| A recipe link fails | Some sites block downloads or have closed. The app also tries the Internet Archive; if both fail, nothing is added. |
| An old `.doc` file can't be read | Run Setup and accept *Git for Windows* (it provides antiword). |
| Pictures or previews look wrong or stale | Close the app and delete the `_work\thumbs` folder; previews are remade. |
| Something was deleted by mistake | Restore it from the Windows Recycle Bin, then reopen Library Manager. |
| A job seems stuck | Watch the **Activity** panel; OCR of big scanned PDFs and video downloads can take several minutes. |

---

## For the technically minded

Every Add page runs a script in `_scripts\` that you can also run from a command prompt in this folder, using the
library's Python: `_scripts\.venv\Scripts\python _scripts\<script>`.

| Page | Script |
|---|---|
| Recipe from Link | `63_add_recipe.py <url> [--folder air-fryer\|instant-pot\|food-recipes] [--force]` |
| Recipe from Email | `64_add_email_recipe.py "<subject words>" [--force] [--check]` |
| Add a Document | `65_add_document.py "<file>" [--check] [--category <folder>] [--title "<title>"] [--force]` |
| Bulk Add Folder | `50_ingest_folder.py "<folder>"`, then `50_ingest_folder.py --apply <review.csv>` |
| (after changes) | `20_catalog.py` then `21_readme.py` (writes `LIBRARY.md`) |

Tools without a page of their own:

| Tool | Script |
|---|---|
| Web pages from links | `68_add_web_page.py [--check] --category <CODE> <url> …` or `--file list.txt` |
| PDFs from links | `69_add_pdf_link.py --category <CODE> <url> …` or `--file list.txt` |
| Wikipedia articles | `67_add_wiki_articles.py [--check] "Title:CODE" …` or `--file list.txt` |
| Get Archives.bat | `get_archives.py [--list] [<archive> … \| all]` |
| Build Starter Library.bat | `build_starter.py [--list] [<pack> … \| all]` |
| Build Local Area.bat | `build_local_area.py [--place "<town>"] [--radius <km>] [--per-group <n>] [--groups birds,fungi…] [--maps <km> \| --no-maps] [--yes]` |
| Archive builders used by the packs | `15_build_zim_docs.py <source>`, `18_stackexchange.py build <site>` |
| Share your own choices as packs | `make_starter_packs.py` - rewrites `starter\` from what is in your library |
| Recipes from a browser bookmarks export (one folder or several) | `58_fetch_bookmarks.py <bookmarks.html> "<folder name>" …`, then `20_catalog.py` and `21_readme.py` |

If you add a script that needs a new Python package, add it to `_scripts\requirements.txt` so Setup installs it on
other PCs.
