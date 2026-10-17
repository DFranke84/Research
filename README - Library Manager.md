# Research Library & Library Manager – How to set up and use

This folder is a self-contained offline library: about 18,000 survival, homesteading, medical, repair and recipe
items (with their PDFs, photos and videos), plus **Library Manager**, a desktop app for browsing, reading and
adding to it. Everything lives inside this folder, so you can copy the whole folder to another drive or PC.

> `README.md` (next to this file) describes what is *in* the library – categories, sources and licences. It is
> rebuilt automatically whenever the library changes. This file explains how to *set up and use* it.

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
- Your favorites, Cooking School progress and view settings travel with the folder (they're in `_work\`).

---

## Using Library Manager

The left sidebar has two groups: **Browse** (find and read things) and **Add** (put new things in).
The Home page shows totals, the most recently added items and every category; click a category to browse it.

### Browsing

| Section | What's in it |
|---|---|
| **Favorites** | Everything you've starred, grouped by section, by category, or newest first |
| **Recipes** | All recipes: web bookmarks, emails, Facebook saves, recipe cards, videos, cookbooks. Opens on tiles by kind of dish (All Recipes first, then Breads & Baking, Desserts, Breakfast, Soups, Chicken & Turkey, Beef, Pork, Fish, Pasta & Casseroles, Pizza & Sandwiches, Vegetables & Salads, Sauces, Drinks, Canning & Dairy, Air Fryer, Instant Pot, Other) – inside each, buttons by source (Web, Email, Facebook, Recipe cards, Videos, Cookbooks). A recipe can be in more than one tile (e.g. chicken soup) |
| **Cooking School** | Wardee Harmon's *Traditional Cooking School* course, laid out as its learning schedule |
| **Local Area** | Kalispell / Flathead County (zone 5b): a page for every tree, fruit variety, shrub, rose, herb, wild plant and weed on your list, plus growing guides, MSU documents and pest pages – see below |
| **Documents & Books** | PDFs, Word documents and books from every category. Opens on topic tiles (All Documents first, then Gardening & Farming, Food Storage, Cooking & Recipes, Medical, Water & Sanitation, Wilderness/Hunting/Foraging, Emergency & Disaster, Energy, Skills/Tools/Building, Radio, Security, Legal & Financial) – click one to drill in; **◀ All topics** goes back |
| **Whole Library** | Everything except the Cooking School, which only appears in its own section. Opens on topic tiles (All of the Library first, then Vehicles & Engines, Skills/Tools/Building, Gardening & Farming, Food Storage, Recipes & Cooking, Medical, Water & Sanitation, Energy, Radio, Wilderness/Hunting/Foraging, Emergency & Disaster, Security, Legal & Financial, Local Area) – inside, buttons by category or by kind (Repair guides, Q & A, Wikipedia, PDFs…) |
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

Everything here is about growing in **Kalispell / Flathead County** and is stored in the library folder
`local-area` (it works with no internet). It opens on **topic tiles** (each shows how many pages it has):
Start Here · Fruit Trees · Berries & Small Fruit · Trees · Shrubs & Roses · Herbs · Vegetables · Wild Plants & Weeds · Grasses ·
Wildlife · Fungi · Insects & Spiders · Nearby (Pacific Northwest) · Food Preservation · Living with Wildlife · Heating with Wood · Livestock & Bees · Maps · Growing Guides & References · Pests & Problems.

Click a tile to drill into that topic: a list with search, sort and buttons for the topic's own groups (e.g. Fruit
Trees → Apples & crabapples · Pears · Plums & apricots · Cherries; Wildlife → Mammals · Birds · Fish · Reptiles &
amphibians; Wild Plants & Weeds → Wildflowers & wild foods · Poisonous plants · Noxious weeds · Common weeds; Insects &
Spiders → Butterflies · Big moths · Dragonflies & damselflies · Bees & wasps · Helpful insects · Garden & orchard pests ·
Forest & tree pests · House & pantry pests · Biting & stinging · Spiders, ticks & mites · Fly-fishing hatches · Other
insects & bugs). **◀ All topics** goes back to the tiles; clicking **Local Area** in the left menu also starts again
there. Start Here is a single page, so its tile opens it straight away.

The wildlife, fungi and grass pages come from the Montana Field Guide (every Montana mammal, bird, fish, reptile and
amphibian, the Field Guide's named fungi (mushrooms, brackets, rusts and cankers), all 262 Montana grasses, and about 800 insects, spiders and ticks - butterflies, dragonflies, bees, pests, helpful
insects, biting bugs and fly-fishing hatches): Montana status and conservation rank, habitat, range,
migration and food, photos, the full Field Guide account, range maps, the Field Guide's PDF report and the Wikipedia
article. **Fungi pages: never eat a wild mushroom identified from a description or photo.**

**Vegetables** has one page per home-garden crop (43) plus the **Kalispell Vegetable Planting Calendar**. Each crop page starts with Kalispell planting and indoor-start dates worked out from MSU's planting schedule and our frost dates (last freeze about May 20, first about September 20), whether it will ripen here, what to do with it in your unheated greenhouse, short-season variety lists (MSU, University of Idaho and others) and links to its pests in Insects & Spiders.

**Kalispell topic guides** (added 2026-10-12): **Food Preservation** (canning pressures and times for Kalispell's 2,984 ft - dial gauge 12 lb, weighted gauge 15 lb - plus freezing, drying and root cellars, linking the MSU guides in Food Storage & Preservation), **Living with Wildlife** (Montana FWP: securing garbage, gardens, coops and hives from bears, the FWP electric-fence guide, deer fencing, 20 FWP pages on smaller animals), **Heating with Wood** (Flathead National Forest firewood permits, heat value of local woods, EPA safe-burning tips), **Livestock & Bees** (Montana apiary registration, backyard poultry testing and health, goats) and **Maps** (16 USGS 1:24,000 topographic maps of the Flathead Valley, GeoPDFs that GPS apps can use offline, with an index page laid out north to south). In each topic, open the Kalispell guide page (type "Kalispell guide") first - it sums up the source documents listed beside it.

**📍 Waypoints** (menu, under Local Area; added 2026-10-13) are your own named places - home, hunting spots,
trailheads, springs. Each one opens the topographic map it is on, **zoomed in and centred on a red pin**:
- **Add one** with **+ Add a waypoint**: a name, the position and notes. The position can be typed or pasted in most forms -
  `48.1958, -114.3129`, `48°11'45"N 114°18'46"W`, `N48 11.748 W114 18.774`, or a Google Maps link. A longitude without a
  minus or W is taken as West. As you type, the window shows which map it falls on.
- **Or drop one on a map**: open any Local Area map (Pages tab), click **📍 Add waypoint**, then click the spot - or
  right-click the spot (*Add a waypoint here* / *Copy position*). Moving the mouse over a map shows the position under it.
- In the list: double-click (or **Open detailed map**) for the 1:24,000 map, **Open regional map** for the 1:100,000 one;
  **Edit…**, **Copy position**, **Delete**. On an open map, **Same spot on the regional / detailed map** switches scale,
  every saved waypoint is drawn as a pin (click a pin to edit it), and you can drag a zoomed-in map to move around it.
- **📏 Measure** (on every map, and on the North America map): click points - each leg's straight-line distance is
  drawn on the map and the strip above shows the total (miles and km; feet/metres for short legs). **↶ Undo last point**,
  **Clear**, **Done**. Distances are along the earth's surface (great circle).
- The Maps topic bar also has a **📍 My waypoints** button, and the Waypoints page has **🗺 All maps**.
- **Search by position:** in Local Area › Maps, type or paste a position into the search box (any of the forms above, or
  a Google Maps link). The list shows the detailed and regional map that position is on. Opening one zooms in on the spot
  and marks it with a blue target. Right-click the spot to save it as a waypoint. This works from the search box of any
  Local Area topic, and from **Find** on the Waypoints page (which also offers **+ Save as waypoint**).
- Waypoints are saved in `_work\waypoints.json`. The pins are placed from each map's own GeoPDF georeferencing, so they
  land within a few metres on the 2024 maps; the 1979–87 regional maps use the older NAD27 datum, about 80 m (under 1 mm on
  the sheet) from a GPS position.
- They go to the tablet with the next viewer update (see the tablet guide), where they are read-only, and the tablet can
  also show **where you are** from its GPS.

**🌎 North America map** (added 2026-10-13) is an offline road map of all of the US, Canada and Mexico - the fallback
for anywhere outside the topo maps. Open it with **🌎 North America map** on the Waypoints page or in Local Area › Maps,
from the map's own page in Maps, or from **Find** on the Waypoints page when a position isn't on a topo map. It opens in a
**window of its own** ("North America Map" - Chrome or Edge with no tabs or address bar, using its own small profile in
`_work\na_map_window`, separate from your normal browsing). Library Manager serves the map from this computer only
(127.0.0.1, port 8777); nothing goes on the internet. Keep Library Manager open while you use it.
- OpenStreetMap roads, towns, rivers, lakes and parks to zoom 13 everywhere, and full street-and-trail detail (zoom 15)
  in NW Montana; shaded terrain and county lines; the topo sheets as green boxes; your waypoints as red pins.
- Search a town (311,868 places - add ", Montana" to narrow it) or a position in any form. Click a spot for its
  position, the nearest town and which topo map it is on, with **Open topo map** / **Regional map** (they open here in
  Library Manager, zoomed in), **+ Save as waypoint** and **Copy position**.
- **📍 Where am I?** uses Windows location on the PC (needs Wi-Fi/internet) or the GPS on the tablet (no internet needed).
- Files: `local-area\maps\north-america\` (about 8.7 GB, almost all of it `data\north-america-z13.pmtiles`).

**Nearby (Pacific Northwest)** holds plants, fungi, insects, reptiles & amphibians and mammals that live close to Montana (Idaho, Washington, Oregon, Wyoming, British Columbia, Alberta) but are not recorded here. Each page starts with a 📍 note saying where it has been seen. (These came from the old Field Guides section, which was retired on 2026-10-12: every Montana species is in Local Area, and general articles went to Foraging & Wild Food / Wilderness Survival.)

Every plant page starts with **Key facts for Kalispell**: whether it grows in zone 5b, bloom / pollination time,
whether it needs a pollinator and **which trees on your own list pollinate it**, harvest time and keeping, size and
spacing, sun and soil, edibility (or a ⚠ poison / noxious-weed warning) and disease resistance. Below that: photos,
description, Montana Field Guide data and range maps, what the Montana (MSU / Flathead County) documents say about it,
links to its growing guide, documents and pest pages, videos, and the Wikipedia article. **Start Here – Growing in
Kalispell** has the zone, the Flathead Valley frost-free-days chart and a list of every plant by type.

The plant list itself lives in `_scripts\local_area_specs.py`; to add a plant, add a line there and run
`_scripts\69_build_local_area.py "<plant title>"`.

### Offline Archives

**Offline Archives** (in Browse) reads the Kiwix archives in `_sources\zim` directly: the full Wikipedia (21.7 million
articles, with pictures), iFixit, Wikibooks, WikEM, MedlinePlus, NHS medicines, Appropedia, energypedia, 15 Stack Exchange
Q&A sites and 5 document libraries (food preparation, knots, medicine, water, post-disaster). It is read-only: nothing
from the archives is copied into the library.

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

### The Cooking School

- The left side is the course outline: **Modules 1–12** in order, then the **Extras**
  (Cultures for Health eBooks, Roundtables & eBooklets, Menu Plans). The number shows how many lessons each has.
- Each module shows, top to bottom: **Course materials** (eBooks and handouts), **Start here**, the numbered
  **Lessons** (all parts of a lesson together), then **More videos**, **Q&A and bonus videos** and **Audio**.
- **Start this module** opens the first item. In the reader, **‹ Previous / Next ›** walk through the course in
  order and carry on into the next module.
- **Continue where you left off** (top of the outline) reopens the last lesson you viewed.
- The search box above the outline searches just the course.

### Favorites

Star anything with **☆** (on a card or in the reader). The Favorites page groups them **By section**
(Recipes → Web / Email / …, Cooking School → by module, Documents & Books, Library), **By category**
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
  Items inside collections (your recipe collection, the Cooking School, Local Area) and items that other pages link to
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

After anything is added or deleted, the catalog (`CATALOG.csv` / `.json`) and `README.md` update themselves.

---

## Where things are kept

| Location | What |
|---|---|
| Category folders (`recipes\`, `water\`, `field-guide-plants\`, …) | The library itself: one `.md` page per item, with its PDF/original, `<name>_images\` pictures and videos beside it |
| `recipes\personal-recipe-collection\` | Your own recipes: `bookmarks\` (web), `email-recipes\`, `facebook-saved\`, `recipe-cards\`, `videos\`, `documents\` |
| `recipes\wardee-traditional-cooking-school\` | The Cooking School course, one folder per module |
| `CATALOG.csv` / `CATALOG.json` | The list of every item (open the CSV in Excel) |
| `_work\favorites.json` | Your favorites |
| `_work\course_progress.json` | Where you left off in the Cooking School |
| `<item name>.txt` beside an item | Your note for that item |
| `_work\viewer_settings.json` | Remembered choices such as the sort order |
| `_work\thumbs\` | Picture previews; safe to delete, they are remade as needed |
| `_scripts\` | The app and tools (`library_manager.pyw`, `library_viewer.py`, numbered scripts), `requirements.txt`, the Python environment `.venv` |
| `_sources\` | Original downloaded archives and PDFs the library was built from |

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
| (after changes) | `20_catalog.py` then `21_readme.py` |

The build scripts that created the library are listed in `README.md`. If you add a script that needs a new Python
package, add it to `_scripts\requirements.txt` so Setup installs it on other PCs.
