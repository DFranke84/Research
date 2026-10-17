"""Regenerate E:\\Research\\README.md with current counts from CATALOG.json (run after 20_catalog.py)."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH
from categories import CATEGORIES

R = json.load(open(os.path.join(RESEARCH, "CATALOG.json"), encoding="utf-8"))
cc = collections.Counter(r["category"] for r in R)
st = collections.Counter(r["source_type"] for r in R)
pub = collections.Counter()
for r in R:
    p = r["publisher"] or ""
    for k in ["iFixit", "Stack Exchange", "MedlinePlus", "Appropedia", "WikEM", "energypedia", "NHS", "Wikibooks"]:
        if p.startswith(k):
            pub[k] += 1
gov = sum(1 for r in R if r['source_type'] == 'web-page' and not (r['publisher'] or '').startswith(('MedlinePlus', 'NHS')))
mp_old = pub['MedlinePlus'] - 1270
imgs = sum(r["images"] for r in R)
words = sum(r["words"] for r in R)
n_pdf = sum(1 for r in R if r["source_type"] == "pdf")
cat_rows = "\n".join(f"| `{c}/` | {cc[c]:,} | {d} |" for c, d in CATEGORIES.items())
f = lambda k: f"{st.get(k, 0):,}"
g = lambda k: f"{pub.get(k, 0):,}"

readme = f"""# Research Library – Source Files

> **New here?** See **[README - Library Manager.md](README%20-%20Library%20Manager.md)** for setup (`Setup.bat`) and how to use the Library Manager app.

Source material for building a new survival / prepper Library database.
Every item is a Markdown file with YAML front-matter. Each file has one category and a source. PDFs are kept as the original file plus a Markdown sidecar.

- **{len(R):,} source files** (~{words / 1e6:.0f} million words)
- **{n_pdf} original PDFs** (each with a `.md` sidecar)
- **{imgs:,} images** stored beside their articles in `<file>_images/` folders
- Compiled 2026-09 from the existing AIPortable collection (read-only; nothing in `E:\\AIPortable` was modified), the offline Wikipedia ZIM, 20 further Kiwix archives and 24 downloaded public-domain / free PDFs.

`CATALOG.csv` / `CATALOG.json` list every file with: title, category, source type, publisher, source URL, license, original PDF, image count and word count.

## Categories

| Folder | Files | Covers |
|---|---:|---|
{cat_rows}

## What is in it

| Source | Files | What it is |
|---|---:|---|
| Wikipedia articles | {f('wikipedia-article')} | Full article text and images from the offline Wikipedia ZIM (Aug 2026). Reference and external-link sections removed; infoboxes converted to key/value lists. |
| Species profiles | {f('species-profile')} | One profile per species: iNaturalist photos (photographer, license, observation link), the full Wikipedia species article, visual-ID / team-species notes and USDA PLANTS data. |
| iFixit repair guides | {g('iFixit')} | Step-by-step repairs with photos: cars and trucks, small engines (chainsaws, mowers, tillers, pumps), generators and power stations, plumbing, doors/windows, heaters, refrigerators and stoves, radios, hand tools, clothing, shoes, eyeglasses, camping/fishing gear, sewing machines, clinical equipment. |
| Stack Exchange Q&A | {g('Stack Exchange')} | Top-voted, answered questions from 13 sites (DIY, gardening, mechanics, bicycles, cooking, outdoors, woodworking, pets, amateur radio, homebrew, sustainability, crafts, life hacks). Each file has the question, the accepted answer and up to two more top answers, with every author credited. |
| MedlinePlus | {g('MedlinePlus')} | 490 drug monographs (the WHO Model Formulary list plus common OTC/primary-care drugs), 101 herb & supplement monographs, 679 encyclopedia articles (first aid, poisonings, bites/stings, infections, common conditions), plus {mp_old} health-topic pages from the earlier export. |
| Appropedia | {g('Appropedia')} | Appropriate technology: water, sanitation, stoves, solar, building, gardening, food processing. Includes ~40 whole manuals combined into one file each (e.g. Root Crops, Micro-livestock, Wood Harvesting with Hand Tools, Household Cyclopedia, Primary Trauma Care), Practical Action technical briefs and EMT skill sheets. |
| WikEM | {g('WikEM')} | Emergency-medicine reference: toxicology, envenomation, trauma, splinting, environmental illness, field infections, tactical casualty care, disaster medicine. |
| energypedia | {g('energypedia')} | Technical pages on cookstoves, biogas, micro-hydro, solar home systems, batteries, solar pumping/irrigation, drying and cooling. |
| NHS medicine guides | {g('NHS')} | Plain-language guides for 154 medicines (uses, dosing, side effects, pregnancy, interactions). |
| Wikibooks | {g('Wikibooks')} | Whole books combined into one file each (First Aid, Community Health Worker Manual, Knots, Beekeeping, Raising Chickens, Bicycles, Automobile Repair, Amateur Radio Manual, Outdoor Survival, Straw Bale Construction, Blacksmithing, Brewing …) and six themed Cookbook collections on cooking from staples. |
| Government / web pages | {gov:,} | NCHFP (canning), Ready.gov, NWS, CDC, USFA, EPA, FTC, CISA, Energy Star, FEMA (earlier exports). |
| PDFs | {n_pdf} | Field manuals, extension bulletins, government guides and books, including the gap-filling downloads: Where There Is No Animal Doctor, WHO Model Formulary 2008, Ship Captain's Medical Guide (22nd ed.), FEMA CERT manual, Psychological First Aid guides (NCTSN, WHO), Management of Dead Bodies after Disasters, NIFOG, ARRL band chart, CISA EMP guidelines, USFS chainsaw course, Beekeeping Basics, chicken/rabbit/goat guides, well disinfection, EPA wood-burning tips, Practical Blacksmithing (4 vols, 1889). |
| Kiwix "Field Guide" documents | {f('document')} | Survival and self-sufficiency guides from the original library. |

## Front-matter conventions

Every `.md` begins with YAML front-matter. It always contains `title`, `category` (matches the folder), `source_type`, a source (`source_url`, a `sources:` list, or `provenance`) and `license`.
Depending on the source it can also carry `revision_url`, `retrieved_from` (the Kiwix archive), `publisher`, `file` (original PDF), `images` (per-image caption, source page and license), `ocr` (OCR details), `tags`, `content_type` and `compiled`.

### Licenses – read before redistributing

- **Wikipedia, Wikibooks, Appropedia, energypedia, Stack Exchange:** CC BY-SA (attribution + share-alike). Stack Exchange authors are named in each file.
- **WikEM:** CC BY-SA 3.0.
- **iFixit:** CC BY-NC-SA 3.0 – **non-commercial** use only; the guide author is named in each file.
- **MedlinePlus drug, herb and encyclopedia pages:** licensed content (ASHP AHFS, Natural Medicines, A.D.A.M.) – **copyrighted, personal/reference use**, labelled per file. MedlinePlus health-topic pages are public domain.
- **NHS:** Open Government Licence v3.0.
- **US government works:** public domain. **iNaturalist photos:** each observer's license, stored per photo.
- **Copyrighted books and publisher PDFs:** labelled per file (e.g. `Copyrighted - all rights reserved`, `(c) WHO … non-commercial`). Personal/offline reference only.

## How items were selected

- **Relevance:** only material that helps in a *current* survival or self-reliance situation. Excluded: articles about specific past disasters, wars, people, places and media; general science; site/organisation/event pages; hobby and consumer-electronics content.
- **Wikipedia:** the existing ~15k-title set was rule-filtered and hand-reviewed, then expanded with curated seed topics and linked neighbours (also hand-reviewed).
- **MedlinePlus / WikEM / Appropedia / energypedia / Cookbook:** candidate lists were keyword-filtered and then hand-reviewed title by title (`_work/*_keep_*.txt`, `mplus_*`).
- **Stack Exchange:** per-site tag rules plus a minimum vote score and a per-site cap (`18b_select_stackexchange.py`); only answered questions.
- **iFixit:** chosen by device category (`16_select_ifixit.py`); phones, laptops, game consoles, power tools and other consumer electronics excluded.
- **Military / government manuals:** survival-applicable titles only, newest edition kept. **Species:** everything kept, no geographic filter.

## How duplicates were removed

- **PDFs:** identical files by SHA-256 (1,615 → 911 unique), then title/edition review (newest kept); new downloads checked against the library by hash and title.
- **Species:** four sources merged on the resolved Wikipedia article and taxon; species are not repeated as plain Wikipedia articles.
- **Kiwix zimgit archives** (post-disaster, water, medicine, food, knots) are the same 108-document "Field Guide" collection already reviewed in the original library, so nothing new was taken from them.
- **WikEM:** the 38 articles already exported earlier were skipped when building from the full archive.
- **Final checks:** identical bodies and identical source URLs across the whole library. Removals are logged in `_work/removed_duplicates.txt` (empty "under development" stubs, one mislabelled FTC export, six older copies of MedlinePlus articles).
- **Same topic, different publisher** (e.g. *Hypothermia* on Wikipedia, MedlinePlus and WikEM) is intentionally kept – content, depth and audience differ.

## Known gaps

- DOE and U.S. State Department pages failed to fetch in the original export.
- **NHS:** 109 medicines in the Kiwix snapshot were contents pages only (no sub-pages), so they are absent; MedlinePlus covers those drugs.
- **Ship Captain's Medical Guide:** the 23rd/24th editions are sold, not free – the free 22nd edition is included.
- Oklahoma State meat-goat manual and the ATTRA rabbit guide could not be downloaded (site blocking); substitutes are included.
- **OCR:** scanned pages in 105 PDFs were OCR'd offline with RapidOCR (invisible text layer added; sidecars mark `[Page N - OCR]`; front-matter `ocr:` gives confidence/quality). Poor results: Ranger Handbook SH 21-76, NEETS Module 01, NAVPERS 10512 – check the page image for critical details.
- A few Appropedia pages contain characters already corrupted in the source (shown as `ï¿½`).
- **Local information** is not included and must come from you: regional maps, planting zone/frost dates, local repeaters and frequencies, family plans and personal documents.

## Folders

- Category folders – the library (one `.md` per item, PDFs beside their sidecars, `<file>_images/`).
- `_sources/zim/` – the 25 downloaded Kiwix archives (16 GB, checksums verified); `_sources/pdf/` – the 24 downloaded PDFs (source list: `_work/pdf_sources_new.tsv`).
- `_work/` – inventories, review/decision files, build logs. `_scripts/` – the build scripts and Python venv.

## Adding your own documents

Put the files in any folder (sub-folders are included; PDF, DOCX, DOC, ODT, RTF, TXT, MD, HTML, EPUB), then:

1. Review: `_scripts\\.venv\\Scripts\\python _scripts\\50_ingest_folder.py "D:\\My Docs"` – writes `_work\\ingest\\ingest_<date-time>.csv`
   with a decision per file (`add`, `duplicate`, `near-duplicate`, `not-relevant`, `unreadable`, `unsupported`), the suggested category and the reason.
2. Optionally edit the CSV in Excel (change `decision`, `category` or `title`).
3. Apply: `_scripts\\.venv\\Scripts\\python _scripts\\50_ingest_folder.py --apply _work\\ingest\\ingest_<date-time>.csv` – copies the originals,
   writes the Markdown sidecars, and regenerates the catalog and this README.

Duplicates are caught by identical file hash and by shared text (the same document in another format or edition); scanned PDFs are OCR'd.
Added files are labelled `Unknown - user-provided document` for license – correct it in the front-matter if you know it.

## Rebuilding

Python environment: `_scripts/.venv` (libzim, pymupdf, bs4, lxml, markdownify, pyyaml, rapidocr_onnxruntime).

| Script | Purpose |
|---|---|
| `02_wiki_features.py <title list>`, `04_wiki_links.py`, `wiki_rules.py`, `13_build_wiki.py 1 2` | Wikipedia selection and build |
| `67_add_wiki_articles.py "Title:CODE" ... [--check]` | Add individual Wikipedia articles from the offline ZIM |
| `68_add_gov_page.py --file list.txt [--check]` | Add US-government web pages (CDC, DOE, ...) from Internet Archive captures |
| `14_build_new_pdfs.py` | The 24 gap-filling PDFs (`_work/pdf_sources_new.tsv`) |
| `16_select_<source>.py` + `15_build_zim_docs.py <source>` | Kiwix archives: nhs, medlineplus, wikem, appropedia, energypedia, wikibooks, ifixit (`17_reset_source.py` clears a source for rebuilding) |
| `18_stackexchange.py index/build <site>`, `18b_select_stackexchange.py` | Stack Exchange Q&A |
| `30_find_scanned.py`, `31_ocr_pdfs.py [--list file]` | Find image-only PDF pages and OCR them |
| `40_download_zims.sh` | Download / verify the Kiwix archives |
| `50_ingest_folder.py` | Add your own folder of documents (review report, then `--apply`) |
| `20_catalog.py`, `21_readme.py` | Validate front-matter, write CATALOG.csv/.json and this README |

Shared helpers: `common.py` (slugs, front-matter, unique-filename registry), `zimlib.py` (ZIM → Markdown + images), `categories.py`.
"""
open(os.path.join(RESEARCH, "README.md"), "w", encoding="utf-8").write(readme)
print("README written:", len(R), "files")
