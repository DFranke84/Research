"""Vegetable pages for Local Area (used by 69_build_local_area.py for plants of kind 'vegetable').

Everything is computed from local_veg_specs.VEG (MSU MontGuide MT199308AG table, NMSU H-252 hoop-house table, University
of Idaho BUL 863 variety tables via veg_varieties.py) and the Flathead Valley frost statistics (69.frost_stats: median
last spring freeze / first fall freeze at MSU's Creston station). The user's greenhouse is UNHEATED.
"""
import datetime, os, re
import local_veg_specs as VS
import veg_varieties

YEAR = 2001   # any non-leap year - only month/day are shown
_IDAHO = None


def idaho():
    global _IDAHO
    if _IDAHO is None:
        try:
            _IDAHO = veg_varieties.tables()
        except Exception:
            _IDAHO = {}
    return _IDAHO


def _date(s):
    return datetime.datetime.strptime(f"{s} {YEAR}", "%B %d %Y").date()


def frost_dates(f):
    """(last spring freeze, first fall freeze, frost-free days) from 69.frost_stats(); MSU Creston medians."""
    last = _date(f.get("last", "May 20"))
    first = _date(f.get("first", "September 20"))
    return last, first, f.get("season", (first - last).days)


def fmt(d):
    return d.strftime("%B %d").replace(" 0", " ")


def frange(a, b):
    if a == b:
        return fmt(a)
    if a.month == b.month:
        return f"{fmt(a)}-{b.day}"
    return f"{fmt(a)}-{fmt(b)}"


def nrange(lo, hi):
    return str(lo) if lo == hi else f"{lo}-{hi}"


def point(spec, last, first):
    """'L-1' / 'F-12' / 'L0' / 'mid' (mid-summer) / 'mid-7' (7 weeks before mid-summer) -> date."""
    spec = spec.strip()
    if spec.startswith("mid"):
        d = datetime.date(YEAR, 7, 1)
        m = re.match(r"mid-(\d+)", spec)
        return d - datetime.timedelta(weeks=int(m.group(1))) if m else d
    base = last if spec[0] == "L" else first
    return base + datetime.timedelta(weeks=int(spec[1:] or 0))


def span(spec, last, first):
    """'L-6..L-4' -> (earliest, latest); a single point -> (d, d)."""
    a, _, b = spec.partition("..")
    return point(a, last, first), point(b or a, last, first)


def window(spec, last, first):
    """'L-1/F-12' -> ((start lo, start hi), (end lo, end hi)) or a single point."""
    s, _, e = spec.partition("/")
    return span(s, last, first), (span(e, last, first) if e else None)


def window_text(spec, last, first):
    (s1, s2), end = window(spec, last, first)
    if not end:
        return frange(s1, s2)
    return f"from {frange(s1, s2)} until {frange(*end)}"


def window_words(spec):
    """MSU's own wording for a window spec, e.g. 'L-1/F-12' -> '1 week before last frost to 12 weeks before first frost'."""
    def one(p):
        if p.startswith("mid"):
            m = re.match(r"mid-(\d+)", p)
            return f"{m.group(1)} weeks before mid-summer" if m else "mid-summer"
        n = int(p[1:] or 0)
        which = "last frost" if p[0] == "L" else "first frost"
        if n == 0:
            return which
        return f"{abs(n)} week{'s' if abs(n) > 1 else ''} {'before' if n < 0 else 'after'} {which}"
    def part(x):
        if ".." not in x:
            return one(x)
        a, b = x.split("..")
        if a[0] == b[0] and not a.startswith("mid") and (int(a[1:] or 0) < 0) == (int(b[1:] or 0) < 0):
            n = sorted([abs(int(a[1:] or 0)), abs(int(b[1:] or 0))])
            return f"{n[0]}-{n[1]} weeks {'before' if int(a[1:] or 0) < 0 else 'after'} {'last frost' if a[0] == 'L' else 'first frost'}"
        return f"{one(a)} to {one(b)}"
    s, _, e = spec.partition("/")
    return part(s) + (f" until {part(e)}" if e else "")


def weeks(t):
    n = [int(x) for x in re.findall(r"\d+", t or "")]
    return (min(n), max(n)) if n else None


def days(t):
    n = [int(x) for x in re.findall(r"\d+", t or "")]
    return (min(n), max(n)) if n else None


def ripen_line(v, last, first, season):
    """Will it ripen in Kalispell's season? Compares MSU days-to-maturity with the frost-free days left."""
    m = v["msu"]
    dd = days(m["dtm"])
    if not dd:
        return None
    hardy = "hardy" in m["frost"].lower()
    (s1, s2), _ = window(m["spring"], last, first)
    plant = max(s1, last) if not hardy else s1
    left = (first - plant).days
    lo, hi = dd
    trans = "transplant" in m["dtm"] or (m["trans"] not in ("direct",) and not m["trans"].startswith("direct"))
    unit = "days" + (" from transplanting" if "transplant" in m["dtm"] else "")
    if hardy and hi > season - 10:
        return (f"Usually - {nrange(lo, hi)} {unit} is about as long as our {season}-day frost-free season, but it is frost-hardy, "
                "so light frosts at either end do not stop it. Start it early" + (" (transplants)" if trans else "") + " and choose early varieties.")
    if hardy:
        return (f"Yes - frost-hardy, {nrange(lo, hi)} {unit}; it tolerates our spring and fall frosts, so the {season}-day frost-free "
                "season is not the limit.")
    if hi <= left - 14:
        return (f"Yes - {nrange(lo, hi)} {unit} fits: about {left} days from planting ({fmt(plant)}) to the usual first fall frost ({fmt(first)})."
                + (" Those days assume warm weather - our cool nights slow it down, so pick early varieties; the greenhouse makes it surer."
                   if v["season"] == "warm" else ""))
    if lo <= left:
        return (f"Usually - {nrange(lo, hi)} {unit} against about {left} days from planting ({fmt(plant)}) to the usual first fall frost "
                f"({fmt(first)}). Choose early varieties" + (", start transplants indoors" if trans else "") + " and use season extension.")
    return (f"Only with help - {nrange(lo, hi)} {unit} is more than the about {left} days from planting ({fmt(plant)}) to the usual first "
            f"fall frost ({fmt(first)}). Grow it in the greenhouse or under covers, and pick the earliest varieties.")


def facts(p, f):
    """Key facts rows for a vegetable page."""
    v = VS.VEG.get(p.get("veg"), {})
    last, first, season = frost_dates(f)
    rows = []
    m = v.get("msu")
    if m:
        r = ripen_line(v, last, first, season)
        if r:
            rows.append(("Will it ripen in Kalispell?", r))
        rows.append(("Cool- or warm-season crop", "Cool-season (likes cool weather, takes some frost)" if v["season"] == "cool"
                     else "Warm-season (needs warm soil and air, killed by frost)"))
        rows.append(("Frost tolerance (MSU)", m["frost"]))
        rows.append(("Days to maturity (MSU)", m["dtm"] + ("" if "after" in m["dtm"] else " days")))
        sp = window_text(m["spring"], last, first)
        rows.append(("Plant outdoors - Kalispell dates", f"{sp} (MSU: {window_words(m['spring'])})"
                     + (f"; fall crop: {window_text(m['fall'], last, first)} (MSU: {window_words(m['fall'])})" if m.get("fall") else "")))
        w = weeks(m["trans"])
        if w and not m["trans"].startswith("direct"):
            (s1, s2), _ = window(m["spring"], last, first)
            a, b = s1 - datetime.timedelta(weeks=w[1]), s1 - datetime.timedelta(weeks=w[0])
            fa = point(m["fall"].split("/")[0].split("..")[0], last, first) if m.get("fall") else None
            rows.append(("Start indoors (transplants)", f"{frange(a, b)} - {m['trans']} weeks before the first outdoor planting date"
                         + (f"; for a fall crop start {frange(fa - datetime.timedelta(weeks=w[1]), fa - datetime.timedelta(weeks=w[0]))}" if fa else "")))
        else:
            rows.append(("How to plant", "Direct seed in the garden" if m["trans"] == "direct" else m["trans"].capitalize()))
        if p.get("veg") in VS.WYO_LATE:
            rows.append(("⚠ Cold soil", "Wyoming Extension (B-1148R): this crop will not grow in cool soil - plant it 10-14 days AFTER the "
                         f"last frost (about {fmt(last + datetime.timedelta(days=10))}-{fmt(last + datetime.timedelta(days=14))} here), "
                         "or earlier in the greenhouse."))
        rows.append(("Soil temperature to germinate (MSU)", m["soil"] + "°F"))
        rows.append(("Sun (MSU)", m["sun"]))
        rows.append(("Unheated greenhouse", gh_short(v)))
    else:
        rows.append(("Cool- or warm-season crop", "Cool-season" if v.get("season") == "cool" else "Warm-season (killed by frost)"))
        ex = VS.EXTRA.get(p.get("veg"), {})

        def fill(t):
            t = re.sub(r"\{(last|first)([+-]\d+)\}", lambda m_: fmt((last if m_.group(1) == "last" else first)
                                                                     + datetime.timedelta(days=int(m_.group(2)))), t)
            return t.replace("{last}", fmt(last)).replace("{first}", fmt(first)).replace("{season}", str(season))
        rows += [(a_, fill(b_)) for a_, b_ in ex.get("facts", [])]
        if not ex.get("facts"):
            rows.append(("Planting dates", "Not in MSU's planting table - see the growing notes and Montana sources below."))
        if v.get("season") == "warm":
            rows.append(("Unheated greenhouse", "The surest way to grow it here - warmer days and nights, and frost protection at both ends of the season"))
    rows.append(("Our frost dates", f"last spring freeze usually about {fmt(last)}, first fall freeze about {fmt(first)} - about {season} "
                 "frost-free days (MSU Creston station, Flathead Valley)"))
    return rows


def gh_short(v):
    m, n = v.get("msu") or {}, v.get("nmsu")
    if m.get("gh") == "Yes":
        s = "Good greenhouse crop (MSU: greenhouse grown - yes)"
    elif "cannot" in (m.get("notes") or "").lower() or "does not grow well" in (m.get("notes") or "").lower() or "do not grow well" in (m.get("notes") or "").lower():
        s = "MSU: not suited to the greenhouse"
    elif v.get("season") == "cool":
        s = "Outdoors in summer; use the greenhouse for an earlier spring and a later fall crop"
    else:
        s = "Outdoors in a warm spot, or in the greenhouse for a surer crop"
    if n:
        s += f"; grows best at {n[0]}°F, killed at {n[1]}°F (NMSU)"
    return s


def sections(p, f, refs="../references/"):
    """Growing notes, greenhouse and varieties sections for a vegetable page (Markdown)."""
    v = VS.VEG.get(p.get("veg"), {})
    m, n = v.get("msu") or {}, v.get("nmsu")
    last, first, season = frost_dates(f)
    cig = f"[Can I Grow That Here? (MSU MontGuide MT199308AG)]({refs}msu-can-i-grow-that-here-vegetable-seed-and-transplant-schedules-for-garde.md)"
    hh = f"[Hoop House Vegetable Production (NMSU H-252)]({refs}nmsu-h252-hoop-house.md)"
    ext = f"[Extending the Vegetable Growing Season (University of Wyoming B-1148R)]({refs}uwyo-b1148r-extending-season.md)"
    out = []
    # --- growing notes
    g = []
    if m.get("notes"):
        g.append(f"- MSU: {m['notes']}")
    if m.get("cont"):
        g.append(f"- Containers (MSU): {m['cont']}.")
    if v.get("season") == "warm":
        g.append(f"- Warm-season crop: soil and nights must be warm. Kalispell's last freeze is usually about {fmt(last)}, but a freeze on "
                 f"or after June 1 happened in {f.get('june', 'some')} of {f.get('n', 'the')} years - keep row covers or jugs handy for "
                 f"new transplants. Clear plastic laid on the bed a few days before planting warms the soil 10-15°F (Wyoming B-1148R).")
    else:
        g.append("- Cool-season crop: it grows best in the cool weather of spring and fall, and light frosts do not hurt it. "
                 "Summer heat can make leafy and cabbage-family crops bolt or turn bitter, so time plantings to mature before or after mid-summer.")
    g.append("- Preserving the harvest: canning pressures and times for Kalispell's altitude, freezing, drying and root-cellar storage - "
             "[Food Preservation in Kalispell](../topics/kalispell-food-preservation.md).")
    if g:
        out.append("## Growing it in Kalispell\n\n" + "\n".join(g) + (f"\n\nDates and figures: {cig}.\n" if m else "\n"))
    # --- greenhouse
    gh = [f"Your greenhouse is **unheated**, so it gains time at both ends of the season but can still freeze inside on the coldest nights. "
          f"Keep a max/min thermometer inside, vent it on sunny days (it overheats quickly), and use row covers inside for extra protection "
          f"on cold nights (NMSU H-252)."]
    if m.get("gh") == "Yes":
        gh.append(f"- **MSU lists this as a greenhouse crop.**" + (f" Greenhouse varieties (MSU): {m['ghv']}." if m.get("ghv") else ""))
    nt = (m.get("notes") or "").lower()
    if "greenhouse" in nt and ("not" in nt or "cannot" in nt):
        sent = [s.strip() for s in re.split(r"(?<=\.)\s+", m["notes"]) if "greenhouse" in s.lower()]
        gh.append(f"- **MSU: {sent[0] if sent else 'not a greenhouse crop'}**")
    if n:
        dm = n[2].replace(" from transplanting", " days from transplanting") if "from" in n[2] else n[2] + " days"
        gh.append(f"- In a hoop house (NMSU): grows best at **{n[0]}°F**, killed at **{n[1]}°F**, about {dm} to maturity."
                  + (f" {n[3]}" if n[3] else ""))
    if v.get("season") == "cool" and "cannot" not in nt and "do not grow well" not in nt and "does not grow well" not in nt:
        (s1, _), _ = window(m["spring"], last, first) if m else ((None, None), None)
        gh.append("- **Spring:** the soil inside warms weeks before the garden does, so you can sow or transplant inside earlier than the "
                  + (f"outdoor start ({fmt(s1)})" if s1 else "outdoor dates") + " and harvest sooner. Move to the garden or finish before "
                  "the greenhouse gets hot in summer.")
        gh.append(f"- **Fall:** NMSU suggests planting cool-season hoop-house crops about 4-5 weeks before the average first fall frost - "
                  f"about {fmt(first - datetime.timedelta(weeks=5))}-{fmt(first - datetime.timedelta(weeks=4))} here - to keep harvesting "
                  "well after the garden has frozen.")
    elif v.get("season") == "warm" and "cannot" not in nt and "does not grow well" not in nt:
        gh.append("- **Best use:** grow it inside for the whole season - warmer days, protection from frost and wind, and a longer harvest. "
                  "Plant inside when nights in the greenhouse stay above freezing (check the thermometer), and cover plants on cold nights.")
        if n and "Pollinating" in (n[3] or ""):
            gh.append("- **Pollination:** open the doors on warm days so bees can get in, or hand-pollinate (move pollen from male to "
                      "female flowers with a small brush).")
        gh.append(f"- **Fall:** the greenhouse keeps the plants going after the first outdoor frost (about {fmt(first)}) - "
                  "close it up at night and pick everything before a hard freeze.")
    out.append("## Your unheated greenhouse\n\n" + "\n".join(gh) + f"\n\nSources: {hh}; {ext}.\n")
    # --- varieties
    var = []
    ml = VS.MSU_LISTS.get(p.get("veg"))
    if ml:
        head, doc, groups = ml
        var.append(f"**MSU's recommended list** - [{head.split(' - ')[0]}]({refs}{doc}): {head.split(' - ', 1)[1]}\n")
        var += [f"- **{g}:** {names}" for g, names in groups]
        var.append("")
    t = v.get("idaho")
    if t:
        title, _, sub = t.partition(":")
        rows = idaho().get(title, [])
        if sub:
            rows = [r for r in rows if r[2].startswith(sub + ":")]
        if rows:
            var.append("Recommended for short-season, high-altitude gardens by the University of Idaho "
                       f"([BUL 863]({refs}uidaho-bul863-short-season-varieties.md)) - days to harvest from Idaho trials and seed catalogs; "
                       "expect a little longer in a cool year:\n")
            var.append("| Variety | Days to harvest | Notes |\n|---|---|---|\n" + "\n".join(
                f"| {a} | {b} | {re.sub(r'^([A-Z][^:]{0,20}):\s*', r'(\1) ', c)} |" for a, b, c in rows))
    ex = VS.EXTRA.get(p.get("veg"), {}).get("vars")
    if ex:
        head, rows = ex
        var.append(f"Recommended by {head}:\n")
        var.append("| Variety | Days to maturity | Notes |\n|---|---|---|\n" + "\n".join(f"| {a_} | {b_ or '-'} | {c_} |" for a_, b_, c_ in rows))
    if m.get("ghv"):
        var.append(f"\n- Greenhouse varieties (MSU): {m['ghv']}.")
    if m.get("cont"):
        var.append(f"- Container varieties (MSU): {m['cont']}.")
    if var:
        out.append("## Varieties for a short season\n\n" + "\n".join(var) + "\n\nWyoming Extension's advice: choose early varieties "
                   "listed for northern gardens or cold climates - seed companies in the northern states and Canada carry them.\n")
    return "\n".join(out)


def pest_links(p, rel_to):
    """Links to the Local Area insect pages for this crop's pests."""
    v = VS.VEG.get(p.get("veg"), {})
    base = os.path.join(os.path.dirname(rel_to), "insects")
    out = []
    for s in v.get("pests", []) + VS._ALL:
        f = os.path.join(base, s + ".md")
        if os.path.exists(f):
            t = open(f, encoding="utf-8").read(400)
            m = re.search(r'^title: "(.*)"', t, re.M)
            out.append(f"[{m.group(1) if m else s}](../insects/{s}.md)")
    return list(dict.fromkeys(out))


def calendar(plants, f, refs="../references/"):
    """Kalispell month-by-month planting calendar (Markdown body) for every vegetable with MSU dates."""
    last, first, season = frost_dates(f)
    ev = []   # (date, kind, text)
    for p in plants:
        v = VS.VEG.get(p.get("veg"))
        if not v or not v.get("msu"):
            continue
        m = v["msu"]
        link = f"[{p['title']}]({p['slug']}.md)"
        (s1, s2), end = window(m["spring"], last, first)
        w = weeks(m["trans"])
        if w and not m["trans"].startswith("direct"):
            ev.append((s1 - datetime.timedelta(weeks=w[1]), "Start indoors", f"{link} ({m['trans']} weeks before planting out)"))
        late = p.get("veg") in VS.WYO_LATE
        ev.append((s1, "Plant outdoors", link + (" - only if the soil is warm; Wyoming advises 10-14 days after the last frost" if late else "")
                   + (f" (until {fmt(end[1])})" if end else "")))
        if m.get("fall"):
            fs = span(m["fall"].split("/")[0], last, first)[0]
            ev.append((fs, "Plant for a fall crop", link))
    ev.sort(key=lambda x: (x[0], x[1], x[2]))
    months = {}
    for d, kind, txt in ev:
        months.setdefault(d.strftime("%B"), []).append((d, kind, txt))
    out = [f"Dates are worked out from MSU's planting schedule ([Can I Grow That Here? MT199308AG]({refs}msu-can-i-grow-that-here-vegetable-seed-and-transplant-schedules-for-garde.md)) "
           f"and Kalispell's frost dates: the last spring freeze is usually about **{fmt(last)}** and the first fall freeze about "
           f"**{fmt(first)}** - about **{season} frost-free days** (MSU Creston station). A freeze on or after June 1 happened in "
           f"{f.get('june', 'some')} of {f.get('n', 'the')} years, so watch the forecast and keep covers handy.\n",
           "Each date is the **earliest** MSU suggests; most crops can go in over several weeks after it (see each crop's page). "
           "Your **unheated greenhouse** can take cool-season crops about the same time or a little earlier, and warm-season crops as "
           "soon as nights inside stay above freezing.\n"]
    for mon in ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October"):
        if mon not in months:
            continue
        out.append(f"## {mon}\n")
        for kind in ("Start indoors", "Plant outdoors", "Plant for a fall crop"):
            items = [(d, t) for d, k, t in months[mon] if k == kind]
            if items:
                out.append(f"**{kind}:**\n\n" + "\n".join(f"- {fmt(d)} - {t}" for d, t in items) + "\n")
    out.append("## Unheated greenhouse through the year\n\n"
               "- **March-April:** start transplants; cool-season crops (lettuce, spinach, radish, onions, Chinese cabbage) can be sown "
               "inside once the soil there thaws and warms.\n"
               "- **May-June:** move warm-season crops (tomatoes, cucumbers, melons, peppers, eggplant) inside as soon as greenhouse nights "
               "stay above freezing; harden the rest for the garden (Wyoming: 10-14 days of gradual exposure).\n"
               "- **July-August:** vent hard - an unheated greenhouse overheats in summer (NMSU H-252). Open doors so pollinators reach "
               "cucumbers, melons and squash. In mid-August plant fall greens inside (NMSU: 4-5 weeks before the first fall frost).\n"
               f"- **September-October:** after the first outdoor freeze (about {fmt(first)}) the greenhouse keeps tomatoes and peppers "
               "going and fall greens growing - close it at night and pick everything before a hard freeze.\n\n"
               f"Sources: [Hoop House Vegetable Production (NMSU H-252)]({refs}nmsu-h252-hoop-house.md); "
               f"[Extending the Vegetable Growing Season (Wyoming B-1148R)]({refs}uwyo-b1148r-extending-season.md); "
               f"[Hotbeds, Cold Frames and Low Tunnels (MSU MT199803AG)]({refs}msu-hotbeds-cold-frames-and-low-tunnels-for-montana-gardeners.md).\n")
    return "\n".join(out)
