"""OCR the scanned (image-only) pages of the kept PDFs listed in _work/scanned_pdfs.json
(made by 30_find_scanned.py).

For every flagged page:
  * render it (resolution raised for low-res scans) and OCR it with RapidOCR (ONNX, offline);
  * rebuild reading order (two-page spreads split, two-column pages read column by column);
  * add an invisible text layer to the PDF so it becomes searchable (page image untouched);
  * cache the result in _work/ocr/<slug>.json (resumable).
Then the sidecar .md's full-text section is rewritten: native text for normal pages,
OCR text for scanned pages (marked "[Page N - OCR]"), and OCR details are added to the front-matter.

Usage:  31_ocr_pdfs.py [--test pdf_relpath page_no]   (test prints one page and changes nothing)
"""
import json, os, re, sys, time
import numpy as np
import pymupdf
import yaml
sys.path.insert(0, os.path.dirname(__file__))
from common import RESEARCH, TODAY, front_matter

W = os.path.join(RESEARCH, "_work")
CACHE = os.path.join(W, "ocr")
MIN_SCORE = 0.5
ENGINE = "RapidOCR (rapidocr_onnxruntime, PP-OCR models), offline"
_ocr = None


def engine():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def native_dpi(page):
    imgs = page.get_images()
    if not imgs:
        return 200
    return 72.0 * max(i[2] for i in imgs) / max(page.rect.width, 1)


def ocr_page(page):
    """Render and OCR one page. Normal scans render at 200 dpi. Low-resolution scans (<150 dpi)
    are rendered at native resolution, then upscaled (cubic) and lightly smoothed, which reads
    far better than rendering them large directly."""
    import cv2
    nat = native_dpi(page)
    if nat >= 150:
        dpi = 200
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]
    else:
        base = max(int(nat), 50)
        f = min(max(250.0 / base, 2.0), 4.0)
        pix = page.get_pixmap(dpi=base)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]
        img = cv2.GaussianBlur(cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC), (3, 3), 0)
        dpi = base * f
    res, _ = engine()(np.ascontiguousarray(img))
    scale = 72.0 / dpi
    boxes = []
    for quad, text, score in res or []:
        if float(score) < MIN_SCORE or not text.strip():
            continue
        xs = [p[0] * scale for p in quad]; ys = [p[1] * scale for p in quad]
        boxes.append({"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys), "t": text.strip(), "s": round(float(score), 3)})
    return {"dpi": round(dpi), "w": page.rect.width, "h": page.rect.height, "boxes": boxes}


def _lines(boxes):
    """Group boxes into text lines (by vertical overlap) and join left-to-right."""
    out, cur = [], []
    for b in sorted(boxes, key=lambda b: (b["y0"] + b["y1"]) / 2):
        if cur:
            h = min(b["y1"] - b["y0"], cur[-1]["y1"] - cur[-1]["y0"])
            cy = sum((c["y0"] + c["y1"]) / 2 for c in cur) / len(cur)
            if abs((b["y0"] + b["y1"]) / 2 - cy) > 0.5 * max(h, 1):
                out.append(cur); cur = []
        cur.append(b)
    if cur:
        out.append(cur)
    return [" ".join(x["t"] for x in sorted(l, key=lambda b: b["x0"])) for l in out]


def _region(boxes, x0, x1):
    """Reading order inside one page region: detect two columns, else plain top-to-bottom."""
    mid = (x0 + x1) / 2
    left = [b for b in boxes if b["x1"] <= mid + 4]
    right = [b for b in boxes if b["x0"] >= mid - 4]
    if len(left) < 5 or len(right) < 5:
        return _lines(boxes)
    # walk top-to-bottom; full-width boxes flush the pending left/right column bands
    lines, L, R = [], [], []
    for b in sorted(boxes, key=lambda b: b["y0"]):
        if b in left:
            L.append(b)
        elif b in right:
            R.append(b)
        else:
            lines += _lines(L) + _lines(R) + [b["t"]]; L, R = [], []
    return lines + _lines(L) + _lines(R)


def page_text(o):
    boxes = o["boxes"]
    if not boxes:
        return ""
    if o["w"] > o["h"] * 1.15:          # two-page spread scanned as one landscape page
        m = o["w"] / 2
        a = [b for b in boxes if (b["x0"] + b["x1"]) / 2 < m]
        c = [b for b in boxes if (b["x0"] + b["x1"]) / 2 >= m]
        lines = _region(a, 0, m) + [""] + _region(c, m, o["w"])
    else:
        lines = _region(boxes, 0, o["w"])
    txt = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


def add_text_layer(page, o):
    for b in o["boxes"]:
        h = max(b["y1"] - b["y0"], 2)
        fs = max(min(h * 0.8, 40), 3)
        width = pymupdf.get_text_length(b["t"], fontname="helv", fontsize=fs) or 1
        # horizontal scale so the invisible text spans the detected box (better selection/search hits)
        sx = (b["x1"] - b["x0"]) / width
        mat = pymupdf.Matrix(sx, 1) if 0.2 < sx < 5 else None
        try:
            page.insert_text((b["x0"], b["y1"] - h * 0.2), b["t"], fontsize=fs, fontname="helv",
                             render_mode=3, morph=((pymupdf.Point(b["x0"], b["y1"]), mat) if mat else None))
        except Exception:
            pass


def rewrite_sidecar(md_path, pdf_path, ocr_pages, n_pages_total, words_ocr, conf):
    txt = open(md_path, encoding="utf-8").read()
    _, fm_txt, body = txt.split("---\n", 2)
    meta = yaml.safe_load(fm_txt)
    head = body.split("\n## Full text", 1)[0].rstrip() + "\n"
    doc = pymupdf.open(pdf_path)
    parts = []
    for i in range(doc.page_count):
        if i in ocr_pages:
            t = ocr_pages[i]
            if t:
                parts.append(f"\n\n[Page {i + 1} - OCR]\n\n{t}")
        else:
            t = doc[i].get_text().strip()
            if t:
                parts.append(f"\n\n[Page {i + 1}]\n\n{t}")
    doc.close()
    meta["text_layer"] = True
    meta["ocr"] = {"engine": ENGINE, "pages_ocrd": len(ocr_pages), "pages_total": n_pages_total,
                   "ocr_words": words_ocr, "mean_confidence": conf,
                   "quality": ("figure/diagram pages only - little text" if words_ocr < 300 else
                               "good" if conf >= 0.9 else "fair" if conf >= 0.8 else
                               "poor - low-resolution scan, expect many errors"), "date": TODAY,
                   "note": "Scanned pages were OCR'd; an invisible text layer was added to the PDF. "
                           "OCR text may contain recognition errors - check the page image for critical details."}
    meta["sha256_before_ocr"] = meta.get("sha256_before_ocr") or meta.get("sha256")
    with open(pdf_path, "rb") as fh:
        import hashlib
        meta["sha256"] = hashlib.sha256(fh.read()).hexdigest()
    note = ("_Pages marked **OCR** were machine-read from scanned images and may contain recognition errors._\n"
            if ocr_pages else "")
    out = front_matter(meta) + head + "\n## Full text (extracted from the original file; scanned pages OCR'd)\n\n" + note + "".join(parts).strip() + "\n"
    open(md_path, "w", encoding="utf-8").write(out)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        d = pymupdf.open(os.path.join(RESEARCH, sys.argv[2]))
        t = time.time(); o = ocr_page(d[int(sys.argv[3])])
        print(f"dpi {o['dpi']}  boxes {len(o['boxes'])}  {time.time() - t:.1f}s\n")
        print(page_text(o)); return
    os.makedirs(CACHE, exist_ok=True)
    list_name = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--list" else "scanned_pdfs.json"
    todo = json.load(open(os.path.join(W, list_name)))
    total = sum(len(x["scanned"]) for x in todo); done_pages = 0; t0 = time.time()
    summary = []
    for item in todo:
        pdf_path = os.path.join(RESEARCH, item["pdf"]); md_path = os.path.join(RESEARCH, item["md"])
        slug = os.path.splitext(os.path.basename(item["pdf"]))[0]
        cfile = os.path.join(CACHE, slug + ".json")
        cache = json.load(open(cfile, encoding="utf-8")) if os.path.exists(cfile) else {}
        if cache.get("_finished"):
            done_pages += len(item["scanned"]); continue
        doc = pymupdf.open(pdf_path)
        for i in item["scanned"]:
            if str(i) not in cache:
                cache[str(i)] = ocr_page(doc[i])
                json.dump(cache, open(cfile, "w", encoding="utf-8"))
            done_pages += 1
            if done_pages % 25 == 0:
                el = time.time() - t0
                print(f"{done_pages}/{total} pages  ({el / 60:.0f} min)", flush=True)
        # add invisible text layer and save
        for i in item["scanned"]:
            add_text_layer(doc[i], cache[str(i)])
        tmp = pdf_path + ".ocrtmp"
        doc.save(tmp, garbage=3, deflate=True)
        doc.close()
        os.replace(tmp, pdf_path)
        ocr_pages = {i: page_text(cache[str(i)]) for i in item["scanned"]}
        words = sum(len(t.split()) for t in ocr_pages.values())
        bx = [b for i in item["scanned"] for b in cache[str(i)]["boxes"]]
        n = sum(len(b["t"]) for b in bx)   # confidence weighted by text length (short figure labels count less)
        conf = round(sum(b["s"] * len(b["t"]) for b in bx) / n, 3) if n else 0.0
        rewrite_sidecar(md_path, pdf_path, ocr_pages, item["pages"], words, conf)
        cache["_finished"] = True
        json.dump(cache, open(cfile, "w", encoding="utf-8"))
        summary.append({"pdf": item["pdf"], "pages_ocrd": len(item["scanned"]), "words": words, "confidence": conf})
        print("done", item["pdf"], len(item["scanned"]), "pages", words, "words, conf", conf, flush=True)
    out = "ocr_summary.json" if list_name == "scanned_pdfs.json" else "ocr_summary_" + list_name
    json.dump(summary, open(os.path.join(W, out), "w"), indent=1)
    print("finished", len(summary), "pdfs")


if __name__ == "__main__":
    main()
