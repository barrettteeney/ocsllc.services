"""AI-search strategy changes, applied site-wide (idempotent).

1. New town pages: Lakeside, Somers, Evergreen, Eureka (cloned from the Bigfork page).
2. Nav: FAQ link + new towns in the Areas menu. Footer: FAQ link.
3. "Other areas we serve" lists include the new towns.
4. Business schema: Facebook in sameAs, Evergreen + Eureka in areaServed.
"""
import pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
FB = "https://www.facebook.com/1064180896780151"

TOWNS = {
    "lakeside": {
        "name": "Lakeside",
        "hero": "Window cleaning for Lakeside homes, lake-view properties, and vacation rentals on the west shore of Flathead Lake.",
        "desc": "Professional window cleaning in Lakeside, Montana: lake-view homes, vacation rentals, storefronts and post-construction. Free estimates — call (406) 607-2151.",
        "p1": "Lakeside homes are built for the view, which means big panes of glass facing Flathead Lake and the morning sun. Lake spray, pollen and hard water from sprinklers and wells show up fast on that glass. We hand-detail every window inside and out, wipe the frames, and take extra care on high lake-side elevations.",
        "p2": "Many Lakeside properties are second homes and vacation rentals. We can set up a spring and fall schedule, or clean between guests, so the glass is ready without you having to be there.",
        "bullets": [
            "Residential window cleaning, including large lake-view picture windows",
            "Vacation-rental and second-home cleans",
            "Seasonal scheduling (spring open, fall close)",
            "Hard-water stain treatment",
            "Storefront glass along Highway 93",
        ],
    },
    "somers": {
        "name": "Somers",
        "hero": "Window cleaning for Somers homes and lake properties at the north end of Flathead Lake.",
        "desc": "Professional window cleaning in Somers, Montana: lake homes, new builds, storefronts and screens. Free estimates — call (406) 607-2151.",
        "p1": "Somers sits right where Flathead Lake meets the valley, a short drive from Kalispell. Lakefront and lake-view homes here catch wind-blown dust and lake spray, and hard water spots build up where sprinklers hit the glass. We clean every window by hand inside and out and wipe down the frames.",
        "p2": "Building new? Post-construction cleans clear the dust, paint specks and sticker residue so the glass is ready for move-in day.",
        "bullets": [
            "Residential window cleaning, inside and out",
            "Lakefront and lake-view picture windows",
            "Post-construction cleans for new homes",
            "Hard-water stain treatment",
            "Screen cleaning",
        ],
    },
    "evergreen": {
        "name": "Evergreen",
        "hero": "Window cleaning for Evergreen homes and the businesses along Highway 2, just east of Kalispell.",
        "desc": "Professional window cleaning in Evergreen, Montana: homes, storefronts and commercial glass along Highway 2. Free estimates — call (406) 607-2151.",
        "p1": "Evergreen is next door to Kalispell, so we're in the area often. Homes here deal with road dust, pollen and hard water from sprinklers, and businesses along Highway 2 need storefront glass that looks clean every day. We hand-detail the glass and wipe the frames on every visit.",
        "p2": "Storefronts can go on a regular route, weekly, every two weeks or monthly, so the glass stays clean without you having to call.",
        "bullets": [
            "Residential window cleaning, inside and out",
            "Storefront and commercial glass along Highway 2",
            "Recurring routes for businesses",
            "Post-construction cleans",
            "Screen cleaning",
        ],
    },
    "eureka": {
        "name": "Eureka",
        "hero": "Window cleaning for Eureka and Tobacco Valley homes, cabins and businesses.",
        "desc": "Professional window cleaning in Eureka, Montana and the Tobacco Valley: homes, cabins, rentals and storefronts. Free estimates — call (406) 607-2151.",
        "p1": "Eureka homes and cabins sit in some of the prettiest country in the valley, and big windows are how you enjoy it. Dust from gravel roads, pollen and hard water all settle on the glass. We clean every window by hand inside and out and wipe the frames.",
        "p2": "Eureka is a drive from Kalispell, so when we can, we schedule Tobacco Valley homes together on the same days. Text us a photo of each side of the house and we'll send a firm price.",
        "bullets": [
            "Residential window cleaning, inside and out",
            "Cabins, second homes and vacation rentals",
            "Hard-water stain treatment",
            "Storefront glass in town",
            "Screen cleaning",
        ],
    },
}
ORDER = ["kalispell", "whitefish", "columbia-falls", "bigfork", "lakeside", "somers", "evergreen", "eureka"]
NAMES = {"kalispell": "Kalispell", "whitefish": "Whitefish", "columbia-falls": "Columbia Falls", "bigfork": "Bigfork",
         **{k: v["name"] for k, v in TOWNS.items()}}

REVIEWS = """            <div class="review-card">
                <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                <p class="italic mt-1">"Highly recommended, fantastic service in all ways; the window cleaning itself and the customer service. Great price as well, highly recommend."</p>
                <p class="mt-2 text-sm font-semibold">— Jayden Jacobson</p>
            </div>
            <div class="review-card">
                <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                <p class="italic mt-1">"Barrett did an amazing job on my windows inside and out very polite and very hard-working. I definitely will use him again and I highly recommend him."</p>
                <p class="mt-2 text-sm font-semibold">— Debbie Turner</p>
            </div>
            <div class="review-card">
                <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
                <p class="italic mt-1">"Interior and exterior our windows look so clear and beautiful! The job Barrett and his company did exceeded our expectations. Really good communication throughout."</p>
                <p class="mt-2 text-sm font-semibold">— Addie C</p>
            </div>
"""

def other_areas_list(indent="                "):
    return "\n".join(f'{indent}<li><a href="/{s}/" class="text-custom-cyan underline">Window cleaning in {NAMES[s]}</a></li>' for s in ORDER)

def build_town(slug, d):
    t = (ROOT / "bigfork/index.html").read_text()
    n = d["name"]
    # head
    t = t.replace("Window Cleaning in Bigfork, MT | OCS LLC", f"Window Cleaning in {n}, MT | OCS LLC")
    t = re.sub(r'(<meta name="description" content=")[^"]*', r"\g<1>" + d["desc"], t)
    t = re.sub(r'(<meta (?:property="og:description"|name="twitter:description") content=")[^"]*', r"\g<1>" + d["desc"], t)
    t = t.replace("https://ocsllc.services/bigfork/", f"https://ocsllc.services/{slug}/")
    t = t.replace('"name": "Window Cleaning in Bigfork, MT"', f'"name": "Window Cleaning in {n}, MT"')
    t = t.replace("post-construction window cleaning in Bigfork, Montana.", f"post-construction window cleaning in {n}, Montana.")
    t = t.replace('"name": "Bigfork, MT"', f'"name": "{n}, MT"')
    t = t.replace('"name": "Bigfork",\n      "item"', f'"name": "{n}",\n      "item"')
    # hero
    t = t.replace("/assets/videos/bg/bigfork.jpg", "/assets/videos/bg/flathead-valley.jpg").replace("/assets/videos/bg/bigfork.mp4", "/assets/videos/bg/flathead-valley.mp4")
    t = t.replace("<h1>Window Cleaning in Bigfork</h1>", f"<h1>Window Cleaning in {n}</h1>")
    t = re.sub(r"(<h1>Window Cleaning in [^<]+</h1>\s*<p>)[^<]*", r"\g<1>" + d["hero"], t)
    t = t.replace("&rsaquo; Bigfork</p>", f"&rsaquo; {n}</p>")
    # body copy
    t = re.sub(r'(<h2 class="text-2xl font-bold mb-3">Local cleaning, done right</h2>\s*)<p class="mb-4">.*?</p>\s*<p class="mb-4">.*?</p>',
               lambda m: m.group(1) + f'<p class="mb-4">{d["p1"]}</p>\n            <p class="mb-4">{d["p2"]}</p>', t, flags=re.S)
    t = t.replace("What we do for Bigfork customers", f"What we do for {n} customers")
    t = re.sub(r'(<ul class="checklist">).*?(</ul>)', lambda m: m.group(1) + "\n" + "\n".join(f"                <li>{b}</li>" for b in d["bullets"]) + "\n            " + m.group(2), t, count=1, flags=re.S)
    # services links -> general service pages
    t = t.replace("Services in Bigfork", f"Services in {n}")
    t = t.replace('href="/bigfork/residential/"', 'href="/services/residential/"').replace('href="/bigfork/commercial/"', 'href="/services/commercial/"').replace('href="/bigfork/post-construction/"', 'href="/services/post-construction/"')
    # reviews: general, not town-attributed
    t = re.sub(r'<h2 class="text-2xl font-bold mb-4 text-center">What Bigfork-area customers say</h2>\s*(?:<div class="review-card">.*?</div>\s*</div>\s*)+',
               lambda m: '<h2 class="text-2xl font-bold mb-4 text-center">What our customers say</h2>\n' + REVIEWS, t, count=1, flags=re.S)
    t = t.replace("Get a free estimate in Bigfork", f"Get a free estimate in {n}")
    # feature split copy
    t = t.replace("On the glass in Bigfork.", f"On the glass in {n}.").replace("Spotless windows for Bigfork homes and lakefront properties.", f"Spotless windows for {n} homes and businesses.")
    t = t.replace("Bigfork", n) if False else t
    leftover = [m.start() for m in re.finditer("Bigfork", t)]
    return t, leftover

def patch_common(html):
    # nav: FAQ link
    if '<a href="/faq/">FAQ</a>' not in html:
        html = html.replace('<a href="/pricing/">Pricing</a>', '<a href="/pricing/">Pricing</a><a href="/faq/">FAQ</a>', 1)
    # nav: towns in Areas menu
    if '<a href="/lakeside/">Lakeside</a>' not in html:
        html = html.replace('<a href="/bigfork/">Bigfork</a><a href="/flathead-valley/">',
                            '<a href="/bigfork/">Bigfork</a><a href="/lakeside/">Lakeside</a><a href="/somers/">Somers</a><a href="/evergreen/">Evergreen</a><a href="/eureka/">Eureka</a><a href="/flathead-valley/">')
    # footer FAQ link
    if '<a class="underline" href="/faq/">FAQ</a>' not in html:
        html = html.replace('<a class="underline" href="/pricing/">Pricing</a>', '<a class="underline" href="/pricing/">Pricing</a> &middot; <a class="underline" href="/faq/">FAQ</a>', 1)
    # other areas lists
    html = re.sub(r'(<h2 class="text-2xl font-bold mb-3">Other areas we serve</h2>\s*<ul class="list-disc pl-6 space-y-1">)\s*(?:<li>.*?</li>\s*)+(</ul>)',
                  lambda m: m.group(1) + "\n" + other_areas_list() + "\n            " + m.group(2), html, flags=re.S)
    # schema: Facebook + towns
    if FB not in html:
        html = re.sub(r'("sameAs": \[ )("https://www\.google\.com/maps[^"]*")', r'\1\2, "' + FB + '"', html)
    if '"name": "Evergreen"' not in html and '{ "@type": "City", "name": "Somers" },' in html:
        html = html.replace('{ "@type": "City", "name": "Somers" },',
                            '{ "@type": "City", "name": "Somers" },\n    { "@type": "City", "name": "Evergreen" },\n    { "@type": "City", "name": "Eureka" },')
    return html

if __name__ == "__main__":
    for slug, d in TOWNS.items():
        html, left = build_town(slug, d)
        p = ROOT / slug / "index.html"
        p.parent.mkdir(exist_ok=True)
        p.write_text(html)
        print(slug, "leftover 'Bigfork' mentions:", len(left))
    changed = 0
    for p in ROOT.rglob("*.html"):
        if any(part in {".git", "admin", "docs", "node_modules"} for part in p.parts):
            continue
        s = p.read_text()
        n = patch_common(s)
        if n != s:
            p.write_text(n); changed += 1
    print("pages patched:", changed)


def patch_home():
    import json, html as H
    p = ROOT / "index.html"
    t = p.read_text()
    # business schema
    i = t.index('"@type": "HomeAndConstructionBusiness"')
    s = t.rindex('<script type="application/ld+json">', 0, i) + len('<script type="application/ld+json">')
    e = t.index('</script>', i)
    biz = json.loads(t[s:e])
    names = [a["name"] for a in biz["areaServed"]]
    for town in ["Evergreen", "Eureka"]:
        if town not in names:
            biz["areaServed"].insert(-1, {"@type": "City", "name": town})
    if FB not in biz.get("sameAs", []):
        biz.setdefault("sameAs", []).append(FB)
    biz.setdefault("knowsAbout", ["Residential window cleaning", "Commercial and storefront window cleaning",
                                  "Post-construction window cleaning", "Screen cleaning", "Hard water stain removal"])
    if "hasOfferCatalog" not in biz:
        biz["hasOfferCatalog"] = {"@type": "OfferCatalog", "name": "Window cleaning services", "itemListElement": [
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": n, "url": u}} for n, u in [
                ("Residential window cleaning", "https://ocsllc.services/services/residential/"),
                ("Commercial and storefront window cleaning", "https://ocsllc.services/services/commercial/"),
                ("Post-construction window cleaning", "https://ocsllc.services/services/post-construction/"),
                ("Screen, track and specialty cleaning", "https://ocsllc.services/services/additional/")]]}
    t = t[:s] + "\n" + json.dumps(biz, indent=2) + "\n" + t[e:]
    # FAQPage schema from the visible homepage FAQ
    if '"FAQPage"' not in t:
        sec = t[t.index('<section id="faq">'):]
        sec = sec[:sec.index('</section>')]
        qa = re.findall(r'<summary>(.*?)</summary>\s*<p>(.*?)</p>', sec, re.S)
        clean = lambda x: H.unescape(re.sub(r'<[^>]+>', '', x)).strip()
        faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": clean(q), "acceptedAnswer": {"@type": "Answer", "text": clean(a)}} for q, a in qa]}
        t = t.replace('</head>', '<script type="application/ld+json">\n' + json.dumps(faq, indent=2, ensure_ascii=False) + '\n</script>\n</head>', 1)
    # link to the full FAQ page under the homepage FAQ
    if 'href="/faq/"' not in t:
        t = re.sub(r'(<section id="faq">.*?</div>\s*)(</div>\s*</section>)',
                   lambda m: m.group(1) + '<p style="margin-top:1.2rem"><a href="/faq/" style="text-decoration:underline">More questions answered &rarr;</a></p>\n  ' + m.group(2), t, count=1, flags=re.S)
        t = t.replace('<li><a href="#faq">FAQ</a></li>', '<li><a href="#faq">FAQ</a></li>\n          <li><a href="/faq/">All questions</a></li>', 1)
    # coverage tiles: link each town, add Eureka
    if 'href="/lakeside/"' not in t[t.index('class="v4-towns"'):t.index('class="v4-towns"') + 1500]:
        tiles = """<div class="v4-towns">
        <div><b><a href="/kalispell/" style="color:inherit;text-decoration:none">Kalispell</a></b><span class="is-home">Home base</span></div>
        <div><b><a href="/whitefish/" style="color:inherit;text-decoration:none">Whitefish</a></b><span>Lake &amp; resort</span></div>
        <div><b><a href="/bigfork/" style="color:inherit;text-decoration:none">Bigfork</a></b><span>Lakefront</span></div>
        <div><b><a href="/columbia-falls/" style="color:inherit;text-decoration:none">Columbia Falls</a></b><span>Weekly route</span></div>
        <div><b><a href="/lakeside/" style="color:inherit;text-decoration:none">Lakeside</a> &amp; <a href="/somers/" style="color:inherit;text-decoration:none">Somers</a></b><span>Flathead Lake</span></div>
        <div><b><a href="/evergreen/" style="color:inherit;text-decoration:none">Evergreen</a> &amp; <a href="/eureka/" style="color:inherit;text-decoration:none">Eureka</a></b><span>And beyond</span></div>
      </div>"""
        t = re.sub(r'<div class="v4-towns">.*?</div>\s*</div>(?=\s*<p class="v4-slogan">)', tiles, t, count=1, flags=re.S)
    p.write_text(t)
    print("home patched")

patch_home()
