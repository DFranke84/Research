"""The Kiwix archives (.zim) the starter packs are built from: where Kiwix keeps them, and which file to use.

Archive names carry a date (ifixit_en_all_2025-12.zim) and Kiwix replaces old versions, so nothing here names
a date: local_path() picks the newest matching file in <library>\\_sources\\zim, latest() asks Kiwix for its newest.
"""
import os, re
from common import RESEARCH

ZIM_DIR = os.path.join(RESEARCH, "_sources", "zim")
KIWIX = "https://download.kiwix.org/zim/"

# key -> (Kiwix folder, file name up to the date, what it is)
ARCHIVES = {
    "ifixit": ("ifixit", "ifixit_en_all_", "iFixit repair guides"),
    "medlineplus": ("zimit", "medlineplus.gov_en_all_", "MedlinePlus (US National Library of Medicine)"),
    "nhs": ("zimit", "nhs.uk_en_medicines_", "NHS Medicines (UK)"),
    "appropedia": ("other", "appropedia_en_all_maxi_", "Appropedia (appropriate technology, DIY)"),
    "energypedia": ("other", "energypedia_en_all_maxi_", "energypedia (off-grid energy)"),
    "wikem": ("other", "wikem_en_all_maxi_", "WikEM (emergency medicine)"),
    "wikibooks": ("wikibooks", "wikibooks_en_all_nopic_", "Wikibooks (text only)"),
}
SE_SITES = ["diy", "gardening", "mechanics", "bicycles", "cooking", "outdoors", "woodworking", "pets", "ham",
            "homebrew", "sustainability", "crafts", "lifehacks"]
for _s in SE_SITES:
    ARCHIVES["se-" + _s] = ("stack_exchange", f"{_s}.stackexchange.com_en_all_", f"Stack Exchange - {_s}")

_DATE = r"(\d{4}-\d{2}[a-z]?)\.zim$"


def _newest(names, prefix):
    hits = [(m.group(1), n) for n in names for m in [re.match(re.escape(prefix) + _DATE, n)] if m]
    return max(hits)[1] if hits else None


def local_path(key):
    """The newest copy of this archive in _sources\\zim, or None."""
    if not os.path.isdir(ZIM_DIR):
        return None
    name = _newest(os.listdir(ZIM_DIR), ARCHIVES[key][1])
    return os.path.join(ZIM_DIR, name) if name else None


def need(key):
    """local_path() or a clear message saying how to get the archive."""
    p = local_path(key)
    if not p:
        raise SystemExit(f"The {ARCHIVES[key][2]} archive is not in {ZIM_DIR} yet - "
                         f"download it first with 'Get Archives.bat' (it looks for {ARCHIVES[key][1]}<date>.zim).")
    return p


def latest(key, session=None):
    """(file name, download URL) of Kiwix's newest version of this archive."""
    import requests
    folder, prefix, _ = ARCHIVES[key]
    html = (session or requests).get(KIWIX + folder + "/", timeout=60).text
    name = _newest(re.findall(r'href="([^"/]+\.zim)"', html), prefix)
    if not name:
        raise LookupError(f"Kiwix has no {prefix}<date>.zim in {KIWIX}{folder}/")
    return name, KIWIX + folder + "/" + name
