# Test a fresh install - step-by-step checklist

This checklist sets up all four apps **from scratch in a separate test folder**, the way a brand-new user would,
and checks that each one works. You don't need any programming experience - just follow the steps in order and
tick each box. If you already use the apps, nothing in your own copy is changed.

It takes about **1½ - 2 hours**, mostly waiting for downloads, and needs an internet connection.

The four apps (see each README for what they do): **Research** (the library and Library Manager),
**LibraryViewer** (the tablet copy), and the AI chat - **AIPortable** or **AIPortable-JustAI**. You can test all
four, or only the ones you use.

---

## Before you start

- [ ] Windows 10 or 11, 64-bit. You do **not** need administrator rights.
- [ ] Free disk space: about **15 GB** for a full test (each AI app about 5 GB with one AI model, the library
      with a few samples about 3 GB). Less if you skip an AI app.
- [ ] Pick a test folder that is **not** inside OneDrive and **not** inside your own AI-Research folder, for example
      **`C:\AI-Test`**. Create it in File Explorer.
- [ ] If you already use the apps on this PC: **close** AIPortable / JustAI and Library Manager first (only one
      AI app can run its AI engine at a time).

---

## Step 1 - Download the apps

For each app you want to test (Research, LibraryViewer, AIPortable, AIPortable-JustAI):

- [ ] Open its page on GitHub, click the green **Code** button → **Download ZIP**.
- [ ] Unzip it into `C:\AI-Test`.
- [ ] **Rename the folder** so it has exactly the app's name - GitHub adds `-main` (`Research-main` → `Research`).
      The apps find each other by these names.

(If you have git: open a command window in `C:\AI-Test` and run `git clone https://github.com/DFranke84/Research`,
and the same for `LibraryViewer`, `AIPortable` and `AIPortable-JustAI` - no renaming needed.)

- [ ] Check the layout in File Explorer:

```
C:\AI-Test\
    AIPortable\
    AIPortable-JustAI\
    LibraryViewer\
    Research\
```

---

## Step 2 - Set up the library (Research)

- [ ] Double-click **`Research\Setup.bat`**. Press **Enter** (= Yes) at each question, **except**:
      if you already have Library Manager on this PC, it asks *"Update the desktop shortcut to open this copy of
      the library?"* - type **N**, so your desktop shortcut keeps opening your own library.
- [ ] Wait for the final check (first time: about 5 minutes, it downloads about 400 MB). Every line should say
      **OK**; `Library catalog (empty library)` with a **-** is normal for a new library.
- [ ] Double-click **`Research\Library Manager.vbs`**. It opens with the 24 categories, all at 0.
      ✔ There is **no** Local Area or Waypoints in the menu yet (they appear when there is something for them).
- [ ] Close Library Manager.

---

## Step 3 - Put some things in the library

Pick any of these - each one tests a different part.

- [ ] **A recipe from a link**: in Library Manager, **Recipe from Link**, paste
      `https://www.simplyrecipes.com/recipes/banana_bread/`, click **Add Recipe**. ✔ It appears under **Recipes**.
- [ ] **A document**: **Add a Document**, pick any PDF or Word file, click **Add to Library**. ✔ It appears under
      **Documents & Books** with a picture of its first page.
- [ ] **Free archives**: close Library Manager, double-click **`Research\Get Archives.bat`**. Type the numbers of two
      small ones - **NHS Medicines (UK)** and **Stack Exchange - lifehacks** (about 65 MB together) - and press
      Enter. ✔ Each ends with *ready (checksum OK)*.
- [ ] **Starter packs**: double-click **`Research\Build Starter Library.bat`**, type the numbers of the same two
      packs. ✔ *nhs built 154*, *lifehacks built 100*, then *Done*. (A minute or two.)
- [ ] **Your Local Area**: double-click **`Research\Build Local Area.bat`**. Type your town (e.g. `Asheville, NC`),
      Enter for 50 km, type **10** for species per group. In the US it then offers topographic maps: type a small
      number of km (e.g. **5**) and **Y**. ✔ It ends with *Start Here written (zone …)* and *Done*. (10 - 20 minutes.)
      Each species page fetches its Wikipedia article from wikipedia.org, which limits how fast pages may be fetched
      (throttling) - if it seems to pause for minutes, that is why; let it carry on. To avoid it completely, first
      download a Wikipedia archive with `Get Archives.bat` (*Wikipedia - text only*, about 53 GB) - the tools then
      read Wikipedia from that file instead.
- [ ] Open Library Manager again and look:
  - [ ] **Home**: the item count went up; **Recently added** shows your recipe and document.
  - [ ] **Local Area** is now in the menu: tiles Start Here, Plants, Wildlife, Insects & Spiders, Fungi & Lichens
        (and Maps in the US). Open **Start Here** - frost dates and monthly weather for your town.
  - [ ] Open a species page: photos, key facts, a month table, the Wikipedia article.
  - [ ] US only - **📍 Waypoints**: **+ Add a waypoint**, type a name and your town's position, **Save**, then open it:
        the topographic map opens zoomed in on a red pin.
  - [ ] Search the **Whole Library** for a word (e.g. `aspirin`): NHS pages come up.
- [ ] Close Library Manager.

---

## Step 4 - The tablet viewer (LibraryViewer)

- [ ] Double-click **`LibraryViewer\Build viewer data.bat`** (a few minutes the first time). ✔ It ends with *Done.*
- [ ] Double-click **`LibraryViewer\Preview on PC.bat`**. Your web browser opens the viewer.
  - [ ] Home shows your items; Local Area and Waypoints are in the menu.
  - [ ] Type a word in the search box - results appear as you type.
  - [ ] Open a recipe and a species page.
- [ ] Close the browser tab and the black **Preview on PC** window.
- [ ] Optional - an SD card: put a card in the PC and run **`Copy to SD card.bat`**; it says how much space it needs
      before it copies anything. The tablet part is in `README - Tablet Viewer.md`.

---

## Step 5 - The AI app (AIPortable or JustAI)

Do this for the app you use (or both, one after the other).

- [ ] Double-click **`Setup-Windows.bat`** in the app's folder.
  - [ ] **Which chat model**: type the number of the first **General** model (a good small one), or one marked for
        your graphics card.
  - [ ] AIPortable only - **Which map regions**: type the number of **My area (your town)** - Build Local Area added
        it at the top (about 20 MB for 30 km around a town) - or press Enter to skip maps.
  - [ ] Wait (about 10 - 30 minutes, depending on your internet: about 2 GB of programs plus the model).
        ✔ Every line of the final check says **OK**.
  - [ ] When it offers to start the app, type **N** (start it as below instead).
- [ ] **Start it with its own settings** so it can't mix with an AIPortable you already use. Open the Start menu,
      type `cmd`, press Enter, and paste these two lines (for JustAI use `AIPortable-JustAI` in both places):

```
cd /d C:\AI-Test\AIPortable
node_modules\electron\dist\electron.exe . --user-data-dir=C:\AI-Test\_test-settings\AIPortable
```

  (If this PC has never had the apps, you can simply double-click `AIPortable.vbs` instead.)
- [ ] In the app:
  - [ ] ✔ No old chats; the model you picked is in the drop-down at the top. Click **Load model**.
  - [ ] Ask something simple (*"How do I purify water when camping?"*). ✔ An answer streams in.
  - [ ] A bar offers to **Sync** the Research library - click **Sync now** (or 🛠️ Tools/Settings → Library →
        **Sync Research Library**). Wait until it says it is done.
  - [ ] Turn on **📚** and ask about something in your test library (*"What does NHS say about ibuprofen?"*).
        ✔ *Using: …* above the answer lists pages from your library.
  - [ ] Turn on **🗃️**, tick the archives (NHS, lifehacks), and ask again. ✔ The answer names articles it found.
  - [ ] AIPortable only - **🗺️ Map**: if you downloaded *My area*, your town's streets show; search a street name.
  - [ ] **🚪 Exit** → **OK**. The app closes and frees the memory the AI was using.

---

## Step 6 - What should be true at the end

| Check | ✔ |
|---|---|
| Every setup's final check said OK | |
| Library Manager started empty, then showed what you added | |
| Recipe, document, starter packs and Local Area all appeared in the right sections | |
| The tablet preview showed the same items and search worked | |
| The AI app answered, found your library after Sync, and used the archives | |
| Your own copy of the apps (if you have one) still opens your own library and chats | |

---

## Step 7 - Clean up

- [ ] Make sure the test apps are closed (and the black *Preview on PC* window).
- [ ] Open Task Manager (Ctrl+Shift+Esc) and check there is no **ollama** left running from `C:\AI-Test`
      (end it if there is).
- [ ] Delete `C:\AI-Test` (it goes to the Recycle Bin), then empty the Recycle Bin to get the space back.
- [ ] If you answered **Y** to the desktop shortcut in Step 2 by mistake, run your own `Research\Setup.bat` once -
      it points the shortcut back at your library.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| A setup says **NEED** or **FAILED** | Check the internet connection and run the same setup again - it continues where it stopped. |
| The AI app says *"Setup isn't finished yet"* | Run its `Setup-Windows.bat` again. |
| *"An Ollama instance was already running"* | Your own AI app (or Ollama's tray icon) is still open - quit it, then start the test copy again. |
| Antivirus removes `ollama.exe` | A known false alarm; it comes from github.com/ollama. Allow it, then run setup again. |
| A recipe link fails | Some sites block downloads; try another recipe link. |
| A tool pauses for minutes, or says *skipped: … HTTP 429* | wikipedia.org is limiting how fast pages are fetched (throttling). Let it finish and run it again later for the skipped pages - or download a Wikipedia archive with `Get Archives.bat` (*Wikipedia - text only*) so the tools read from it instead. |
| Build Local Area finds few species | Make the distance bigger (e.g. 80 km) - quiet areas have fewer recorded sightings. |
| Get Archives stops part way | Run it again - it continues the download. |
