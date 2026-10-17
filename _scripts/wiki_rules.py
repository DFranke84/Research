"""Rule-based pre-filter for Wikipedia candidates. Returns a reason string
when an article is clearly off-topic (people, ships, events, organisations,
places, media, finance/business trivia), else None. Anything not dropped here
is reviewed manually (see _work/wiki_decisions_*.txt)."""
import re

DROP_CAT = re.compile(
    r"(\bbirths\b|\bdeaths\b|Living people|people from|\bpeople\b$|Year of birth|Survivalists|Hikers|activists|"
    r"\bships\b|Ship infoboxes|Captured ships|shipwrecks|Maritime incidents|Royal Navy|\bfrigates\b|\bsloops\b|\bbrigs\b|"
    r"earthquakes? in|\bearthquakes\b|Earthquake stubs|Earthquake clusters|aftershock|Strike-slip|Megathrust|tsunamis in|"
    r"floods in|\bfloods\b|Flood stubs|wildfires in|Wildfire stubs|Wildfire articles|tornadoes|Tornado|tropical cyclones|"
    r"hurricanes|typhoons|Tropical cyclones by year|cyclone seasons|avalanches in|landslides in|volcanic eruptions|"
    r"disasters in|Natural disaster stubs|\d{4} (in|disasters|fires|natural disasters)|\d{4}s (disasters|in)|"
    r"heat waves|droughts in|blizzards|famines|epidemics in|pandemics|outbreaks|explosions in|fires in|"
    r"accidents|incidents in|Military raids|battles|\bwars\b|conflicts|operations involving|military units|"
    r"regiments|squadrons|Military history|military operations|"
    r"companies|Companies|brands|manufacturers|retailers|\bbanks\b|Bank stubs|Banking in|stock exchange|"
    r"organizations|organisations|societies|Organizations|agencies of|charities|non-profit|Non-profit|foundations|"
    r"member societies|clubs|associations|Radio organization|"
    r"populated places|villages|towns in|cities in|municipalities|counties of|Rivers of|Mountains of|Lakes of|Islands of|"
    r"neighbourhoods|National parks of|Protected areas|Buildings and structures|Museums|museums|"
    r"films|albums|songs|novels|\bbooks\b|television|Television|video games|magazines|newspapers|journals|podcasts|"
    r"comics|anime|fictional|Fictional|board games|musical|bands\b|"
    r"sports|Sports|football|baseball|basketball|Olympic|championships|competitions|"
    r"legislation|Acts of the|court cases|Supreme Court|United States federal|elections|political parties|politicians|"
    r"satellites|spacecraft|Spacecraft|rockets|aircraft|Aircraft|airlines|airports|"
    r"universities|colleges|schools in|Schools|research institutes|"
    r"Intellectual property activism|Consumer rights activists|Actuarial|Mortgage|Taxation|Bankruptcy|Banking terms|"
    r"History of banking|Banking technology|Types of insurance|Insurance|Securities|Investment|Stock market|"
    r"English-language journals|Hunting in art|Amateur radio people|Amateur radio stubs|"
    r"military personnel|police officers|explorers|mountaineers|writers|Writers|YouTubers|scientists|physicians|"
    r"Infectious causes of cancer|Radio resource management|Computer networking|Data transmission)",
)
DROP_FIRST = re.compile(
    r"^\S.{0,200}?\b(was|is) (an?|the) ((former|retired|late|professional|British|American|Canadian|English|French|German|"
    r"Australian|Indian|Japanese|Russian|Italian|Spanish|Chinese|Dutch|Swedish|Norwegian|Irish|Scottish)\s)*"
    r"(ship|vessel|brig|frigate|sloop|schooner|merchantman|whaler|privateer|company|corporation|brand|manufacturer|"
    r"retailer|bank|organization|organisation|charity|agency|politician|businessman|businesswoman|author|writer|actor|"
    r"singer|musician|journalist|film|album|song|novel|television|magazine|newspaper|village|town|city|municipality|"
    r"river|lake|mountain|museum|school|university|college|website|podcast|video game|professor|engineer|physician|"
    r"explorer|mountaineer|survivalist|scientist|journal|rapper|footballer|athlete|politician)\b", re.I)
DROP_TITLE = re.compile(r"^(\d{3,4}|List of|Lists of|Timeline of|History of|Outline of|Index of|Glossary of .* terms$)|\(\d{4}( ship)?\)|\bship\)$|\(film\)|\(album\)|\(band\)|\(song\)|\(novel\)|\(TV|\(magazine\)|\bearthquake$|\bflood$|\bfire$|\btsunami$|\bwildfire$|\bcyclone\b|\bHurricane\b|\bTyphoon\b|\bTornado\b|\boutbreak\b|\bepidemic\b|\bpandemic\b|\bdisaster$|\bfamine\b")


def rule_drop(rec):
    if rec.get("missing"):
        return "missing-from-zim"
    t = rec["title"]
    if DROP_TITLE.search(t):
        return "title-pattern"
    for c in rec.get("cats", []):
        if DROP_CAT.search(c):
            return "category:" + c
    if DROP_FIRST.search(rec.get("first", "")[:260]):
        return "first-sentence"
    ib = rec.get("infobox", "")
    if re.search(r"infobox (ship|person|company|organization|settlement|military|event|earthquake|storm|film|album|book|"
                 r"television|website|video game|aircraft|spaceflight|university|school|officeholder|sportsperson|"
                 r"football|musical|writer|scientist|disaster|flood|wildfire|tornado|hurricane|legislation|court)", ib, re.I):
        return "infobox:" + ib[:40]
    return None
