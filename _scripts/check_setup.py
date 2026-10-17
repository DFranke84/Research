"""Check that everything the Research library tools need is present, and say what each thing is for.

  _scripts\\.venv\\Scripts\\python _scripts\\check_setup.py            full report (used at the end of Setup)
  _scripts\\.venv\\Scripts\\python _scripts\\check_setup.py --missing  just the names of missing optional tools
Exit code 0 = everything needed is there (optional tools may still be missing), 1 = something needed is missing.
"""
import importlib, os, sys, winreg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# (import name, what it is for)
PACKAGES = [("tkinter", "the Library Manager window"), ("PIL", "pictures and thumbnails"), ("pymupdf", "reading and showing PDFs"),
            ("rapidocr_onnxruntime", "reading scanned pages (OCR)"), ("cv2", "OCR image handling"), ("numpy", "OCR"),
            ("bs4", "reading web pages"), ("lxml", "reading web pages"), ("markdownify", "turning web pages into text"),
            ("extruct", "finding recipes inside web pages"), ("requests", "downloading recipe pages"),
            ("yt_dlp", "saving recipe videos (YouTube, Facebook, TikTok...)"), ("imageio_ffmpeg", "video frames and joining video/audio"),
            ("mutagen", "audio/video details"), ("yaml", "reading page details (front matter)"), ("openpyxl", "spreadsheets"),
            ("libzim", "the offline Wikipedia/Kiwix archives (Offline Archives, build scripts)"),
            ("tkinterweb", "the Web page tab for the Offline Archives")]


def outlook():
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Outlook.Application"))
        return True
    except OSError:
        return False


def main():
    from common import find_browser, find_antiword
    need_ok, rows, missing = True, [], []
    v = sys.version_info
    ok = v[:2] == (3, 14) and sys.maxsize > 2 ** 32
    need_ok &= ok
    rows.append((ok, True, f"Python {v.major}.{v.minor}.{v.micro} ({'64' if sys.maxsize > 2 ** 32 else '32'}-bit)", "runs everything"))
    for mod, why in PACKAGES:
        try:
            importlib.import_module(mod)
            rows.append((True, True, mod, why))
        except Exception as e:
            need_ok = False
            rows.append((False, True, mod, f"{why}  ({type(e).__name__})"))
    try:
        import imageio_ffmpeg
        ff = os.path.exists(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        ff = False
    need_ok &= ff
    rows.append((ff, True, "ffmpeg (comes with imageio-ffmpeg)", "video thumbnails, saving videos"))
    br = find_browser()
    has_br = os.path.exists(br)
    rows.append((has_br, False, os.path.basename(br) if has_br else "Chrome or Edge", "the clean one-page recipe PDFs, Facebook pages"))
    aw = find_antiword()
    rows.append((bool(aw), False, "antiword", "reading old Word .doc files (comes with Git for Windows)"))
    ol = outlook()
    rows.append((ol, False, "Microsoft Outlook", "Recipe from Email (reads the Email > Recipes folder)"))
    lib = os.path.exists(os.path.join(ROOT, "CATALOG.json"))   # a new, empty library has none until the first item is added
    rows.append((lib, False, f"Library catalog in {ROOT}" if lib else "Library catalog (empty library)",
                 "the list of everything in the library" if lib else "made automatically when you add your first item"))
    if not has_br:
        missing.append("browser")
    if not aw:
        missing.append("antiword")
    if "--missing" in sys.argv:
        print(",".join(missing))
        return 0
    print()
    for ok, needed, name, why in rows:
        mark = "  OK   " if ok else ("  NEED " if needed else "  -    ")
        print(f"{mark} {name:42} {why}")
    print()
    if need_ok:
        print("Everything needed is installed." + ("" if not missing and ol and lib else "  (Items marked - are optional.)"))
    else:
        print("Some needed parts are missing (marked NEED). Run Setup again, or ask for help with the message above.")
    return 0 if need_ok else 1


if __name__ == "__main__":
    sys.exit(main())
