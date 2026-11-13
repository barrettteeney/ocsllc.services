#!/usr/bin/env python3
"""Build the OCS LLC static site.

    python3 build.py        # writes the deployable site to ./site/

Page bodies live in src/pages/*.html; the shared <head>, header and footer
are below. Media placeholders are written in pages as:

    [[ph:photo|Label shown in the box]]
    [[ph:video|Label shown in the box]]

Shared blocks live in src/partials/ and are pulled in with [[include:name]].
Real photos go in assets/img/work/ and replace a placeholder with:

    [[img:filename.jpg|Alt text describing the photo]]
    [[img:filename.jpg|Alt text describing the photo|60%]]   (optional: vertical crop focus)
Standard library only — no installs.
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src" / "pages"
OUT = ROOT / "site"
DOMAIN = "https://ocsllc.services"
EMAIL = "barrett@ocsllc.services"
TOWNS = ["Kalispell", "Whitefish", "Columbia Falls", "Bigfork", "Lakeside", "Somers"]

# The one list of everywhere we work: home page, /service-area/, quote form, search data and llms.txt
# all read from it. ZIP codes checked against the county lists on zip-codes.com, 2026-11-08.
# A community with no ZIP of its own has an empty list.
SERVICE_AREAS = [
    dict(id="kalispell-area", name="Kalispell Area", county="Flathead County", places=[
        ("Kalispell", ["59901", "59903", "59904"]), ("Evergreen", []), ("Helena Flats", []), ("Batavia", []),
        ("Creston", []), ("Kila", ["59920"]), ("Marion", ["59925"]), ("Little Bitterroot Lake", []), ("Rhodes", []),
    ]),
    dict(id="north-valley", name="Whitefish & North Valley", county="Flathead County", places=[
        ("Whitefish", ["59937"]), ("Columbia Falls", ["59912"]), ("Forest Hill Village", []),
    ]),
    dict(id="canyon", name="The Canyon & Glacier", county="Flathead County", places=[
        ("Coram", ["59913"]), ("Hungry Horse", ["59919"]), ("Martin City", ["59926"]), ("West Glacier", ["59936"]),
        ("Apgar Village", []), ("Lake McDonald", ["59921"]), ("Essex", ["59916"]), ("Pinnacle", []), ("Snowslip", []),
    ]),
    dict(id="flathead-lake", name="Flathead Lake", county="Flathead and Lake Counties", places=[
        ("Bigfork", ["59911"]), ("Ferndale", []), ("Woods Bay", []), ("Swan Lake", []), ("Lakeside", ["59922"]),
        ("Somers", ["59932"]), ("Rollins", ["59931"]), ("Proctor", ["59929"]), ("Lake Mary Ronan", []),
        ("Dayton", ["59914"]), ("Elmo", ["59915"]), ("Big Arm", ["59910"]), ("Polson", ["59860"]), ("Finley Point", []),
    ]),
    dict(id="north-county", name="North Fork & North County", county="Flathead and Lincoln Counties", places=[
        ("Olney", ["59927"]), ("Polebridge", ["59928"]), ("Stryker", ["59933"]), ("Trego", ["59934"]),
        ("Fortine", ["59918"]), ("Eureka", ["59917"]),
    ]),
]
ALL_ZIPS = sorted({z for area in SERVICE_AREAS for _, zips in area["places"] for z in zips})
ALL_PLACES = [(name, zips) for area in SERVICE_AREAS for name, zips in area["places"]]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def place_label(name, zips):
    return f'{name} <span class="zip">{", ".join(zips)}</span>' if zips else name


def areas_accordion():
    rows = []
    for i, area in enumerate(SERVICE_AREAS):
        items = "".join(f"<li>{place_label(n, z)}</li>" for n, z in area["places"])
        rows.append(f'        <details{" open" if i == 0 else ""}>\n'
                    f'          <summary>{html.escape(area["name"])}</summary>\n'
                    f'          <ul>{items}</ul>\n        </details>')
    return "\n".join(rows)


def areas_tables():
    blocks = []
    for area in SERVICE_AREAS:
        rows = "\n".join(
            f'          <tr id="{slug(n)}"><th scope="row">{n}, MT</th><td>{", ".join(z) if z else "Served, uses a nearby ZIP"}</td></tr>'
            for n, z in area["places"])
        blocks.append(f'''    <section class="area-block" id="{area["id"]}" aria-labelledby="{area["id"]}-title">
      <h2 id="{area["id"]}-title">{html.escape(area["name"])}</h2>
      <p class="area-county">{area["county"]}, Montana</p>
      <table class="area-table">
        <thead><tr><th scope="col">Town or community</th><th scope="col">ZIP code</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </section>''')
    return "\n".join(blocks)


def town_options():
    groups = []
    for area in SERVICE_AREAS:
        options = "".join(f"<option>{n}</option>" for n, _ in area["places"])
        groups.append(f'                <optgroup label="{html.escape(area["name"])}">{options}</optgroup>')
    return "\n".join(groups)


def llms_txt(reviews):
    lines = [
        "# OCS LLC",
        "",
        f"> OCS LLC is an owner-operated, insured window cleaning company based in Kalispell, Montana, serving "
        f"homes across the Flathead Valley and northwest Montana. Rated {float(reviews['rating']):.1f} stars from "
        f"{reviews['review_count']} Google reviews. Windows are hand-cleaned.",
        "",
        "## Services",
        "- Exterior window cleaning",
        "- Interior window cleaning",
        "- Screen cleaning",
        "- Track and sill cleaning",
        "- Hard water spot treatment",
        "- Post-construction window cleaning",
        "- Permanent roofline lighting, through our lighting business Lab Lighting: https://lablightingmt.com/",
        "",
        "## Plans",
        "- Quarterly: $100 off per visit",
        "- Twice a year: $50 off per visit",
        "- One-time: full price",
        "Prices are quoted per home and confirmed before anything is booked.",
        "",
        "## Service area",
        "A travel fee may apply more than 25 miles from Kalispell.",
    ]
    for area in SERVICE_AREAS:
        lines += ["", f"### {area['name']} ({area['county']})"]
        lines += [f"- {n}, MT" + (f" {', '.join(z)}" if z else "") for n, z in area["places"]]
    lines += [
        "", "## ZIP codes served", ", ".join(ALL_ZIPS),
        "", "## Links",
        f"- [Get a quote]({DOMAIN}/quote/)",
        f"- [Service area]({DOMAIN}/service-area/)",
        f"- [Services]({DOMAIN}/services/)",
        f"- [Plans]({DOMAIN}/plans/)",
        f"- [Contact]({DOMAIN}/contact/)",
        "", "## Contact", f"Email: {EMAIL}", "",
    ]
    return "\n".join(lines)


BUSINESS = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "@id": f"{DOMAIN}/#business",
    "name": "OCS LLC",
    "description": "Hand-cleaned, insured residential window cleaning with quarterly and twice-a-year plans across the Flathead Valley, Montana.",
    "url": f"{DOMAIN}/",
    "email": EMAIL,
    "telephone": "+1-406-607-2151",
    "logo": f"{DOMAIN}/assets/img/ocs-logo.png",
    "image": f"{DOMAIN}/assets/img/og-image.jpg",
    "address": {"@type": "PostalAddress", "addressLocality": "Kalispell", "addressRegion": "MT", "addressCountry": "US"},
    "areaServed": [
        {"@type": "Place", "name": f"{name}, MT",
         **({"address": [{"@type": "PostalAddress", "addressLocality": name, "addressRegion": "MT",
                          "postalCode": z, "addressCountry": "US"} for z in zips]} if zips else {})}
        for name, zips in ALL_PLACES
    ] + [{"@type": "AdministrativeArea", "name": f"{c} County, Montana"} for c in ("Flathead", "Lake", "Lincoln")]
    + [{"@type": "Place", "name": "Flathead Valley, Montana"}],
    "knowsAbout": ["Window cleaning", "Screen cleaning", "Window track cleaning", "Hard water stain removal", "Post-construction window cleaning"],
}

PLANS_FAQ = [
    ("Why aren’t prices listed?",
     "Every home is different. Pane count, inside or out, screens, and condition all change the job. We look at your home, then confirm your exact number before anything is scheduled."),
    ("What does “per visit” mean?",
     "The plan discount comes off every scheduled cleaning. On the quarterly plan that’s $100 off each of four visits a year; on twice a year it’s $50 off each of two."),
    ("Can I book online?",
     "Not right now. Every visit starts with a quote request, and we confirm the price and the time with you directly."),
    ("What’s included in a visit?",
     "Hand-cleaned glass on every visit: exterior only, or inside and out, depending on your quote. Screens, tracks and hard water treatment can be added when you request it."),
]

# Old-site addresses that ads, search results and customers may still use. Each gets a small
# forwarding page so the link keeps working. Query strings (like Google Ads gclid) carry over.
REDIRECTS = {
    **{f"/{town}/{kind}": f"/service-area/#{town}" for town in ("bigfork", "columbia-falls", "kalispell", "whitefish")
       for kind in ("", "commercial/", "post-construction/", "residential/")},
    "/flathead-valley/": "/service-area/",
    "/blog/fall-prep-window-cleaning-flathead-valley/": "/",
    "/blog/spring-window-cleaning-checklist-flathead-valley/": "/",
    "/blog/summer-deck-and-pressure-wash-flathead/": "/",
    **{f"/services/{kind}/": "/services/" for kind in ("additional", "chandelier", "commercial", "post-construction",
                                                       "residential", "skylight", "solar-panel")},
    "/estimate/": "/quote/", "/book/": "/quote/", "/schedule/": "/quote/",
    "/pricing/": "/plans/",
    "/reviews/": "/#reviews",
    "/gallery/": "/#recent-work", "/our-work/": "/#recent-work",
    "/careers/": "/contact/",
}

REDIRECT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved | OCS LLC</title>
<link rel="canonical" href="{domain}{target}">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace("{target_path}" + location.search + "{target_hash}");</script>
</head>
<body><p>This page has moved: <a href="{target}">continue to OCS LLC</a>.</p></body>
</html>
"""

PAGES = [
    dict(src="home.html", out="index.html", path="/", nav="home",
         title="OCS LLC | Kalispell & Flathead Valley Window Cleaning",
         description="Hand-cleaned, insured window cleaning for homes in Kalispell, Whitefish, Columbia Falls and Bigfork. Quarterly plans save $100 every visit. Request a quote.",
         schema=[BUSINESS]),
    dict(src="plans.html", out="plans/index.html", path="/plans/", nav="plans",
         title="Window Cleaning Plans: Quarterly & Twice a Year | OCS LLC",
         description="Compare one-time, twice-a-year and quarterly window cleaning in the Flathead Valley. Quarterly saves $100 per visit. Exact pricing confirmed before booking.",
         schema=[{
             "@context": "https://schema.org", "@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in PLANS_FAQ],
         }]),
    dict(src="quote.html", out="quote/index.html", path="/quote/", nav="quote",
         title="Get a Window Cleaning Quote | Kalispell, MT | OCS LLC",
         description="Request a window cleaning quote for your Flathead Valley home. Tell us about your windows and we’ll confirm your exact price and visit time."),
    dict(src="services.html", out="services/index.html", path="/services/", nav="services",
         title="Window Cleaning Services: Interior, Exterior, Screens | OCS LLC",
         description="Exterior and interior window cleaning, screens, tracks and sills, and hard water spot treatment for homes in Kalispell and the Flathead Valley."),
    dict(src="about.html", out="about/index.html", path="/about/", nav="about",
         title="About OCS LLC | Owner-Operated in Kalispell, MT",
         description="OCS LLC is an owner-operated, insured window cleaning company based in Kalispell, serving homes across the Flathead Valley."),
    dict(src="contact.html", out="contact/index.html", path="/contact/", nav="contact",
         title="Contact OCS LLC | Kalispell & Flathead Valley",
         description="Email barrett@ocsllc.services or send a message. Serving Kalispell, Whitefish, Columbia Falls, Bigfork and the surrounding Flathead Valley."),
    dict(src="service-area.html", out="service-area/index.html", path="/service-area/", nav="",
         title="Service Area: Flathead Valley Towns & ZIP Codes | OCS LLC",
         description="OCS LLC cleans windows across Kalispell, Whitefish, Columbia Falls, Bigfork, Lakeside, Somers, Polson and all of the Flathead Valley, Montana. See every town and ZIP code we serve.",
         schema=[BUSINESS]),
    dict(src="privacy.html", out="privacy/index.html", path="/privacy/", nav="",
         title="Privacy Policy | OCS LLC",
         description="How OCS LLC handles the information you share with us, including quote requests and text messages."),
    dict(src="terms.html", out="terms/index.html", path="/terms/", nav="",
         title="Terms of Service | OCS LLC",
         description="Plain-English terms for working with OCS LLC, including scheduling, payment and text messaging."),
    dict(src="thanks.html", out="thanks/index.html", path="/thanks/", nav="", noindex=True,
         title="Request received | OCS LLC",
         description="Thanks — we’ll review your request and confirm by reply."),
    dict(src="404.html", out="404.html", path="/404.html", nav="", noindex=True,
         title="Page not found | OCS LLC",
         description="That page doesn’t exist."),
]

ICONS = {
    "photo": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M3 17l5.5-5.5 4 4L15 13l6 6"/></svg>',
    "video": '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="24" cy="24" r="21"/><path d="M20 16.5v15l12-7.5z" fill="currentColor" stroke="none"/></svg>',
}


def review_cards(data):
    """One card per review, from assets/data/reviews.json. Everything is escaped: reviews are other people's words."""
    cards = []
    for review in data["reviews"]:
        name = html.escape(review["author"])
        stars = max(1, min(5, int(review.get("rating", 5))))
        cards.append(
            f'        <figure class="rev-card">\n'
            f'          <figcaption><span class="rev-initial" aria-hidden="true">{html.escape(review["author"][:1].upper())}</span><strong>{name}</strong></figcaption>\n'
            f'          <span class="stars" role="img" aria-label="{stars} out of 5 stars">{"★" * stars}</span>\n'
            f'          <blockquote>{html.escape(review["body"], quote=False)}</blockquote>\n'
            f'          <button class="rev-more" type="button" hidden>Read more</button>\n'
            f'        </figure>')
    return "\n".join(cards)


def fill_reviews(body, data):
    """Bake the current rating, count and reviews into a page."""
    return (body.replace("[[reviews]]", review_cards(data))
            .replace("[[rating]]", f"{float(data['rating']):.1f}")
            .replace("[[review_count]]", str(data["review_count"]))
            .replace("[[review_shown]]", str(len(data["reviews"])))
            .replace("[[maps_uri]]", html.escape(data["maps_uri"])))


def placeholder(match):
    kind, label = match.group(1), match.group(2)
    noun = "Video" if kind == "video" else "Photo"
    return (f'<div class="ph ph--{kind}" role="img" aria-label="{noun} placeholder: {label}">'
            f'<span class="ph-label">{ICONS[kind]}{noun} · {label}</span></div>')


def photo(match):
    filename, alt, focus = match.group(1), match.group(2), match.group(3)
    style = f' style="object-position:center {focus}"' if focus else ""
    return (f'<div class="ph ph--filled ocs-vintage"><img src="/assets/img/work/{filename}" alt="{alt}"{style} loading="lazy" decoding="async"></div>')


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
{robots}<meta name="theme-color" content="#F7F5F2">
<meta property="og:type" content="website">
<meta property="og:site_name" content="OCS LLC">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{domain}/assets/img/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700;800&display=swap">
<link rel="stylesheet" href="/assets/css/site.css">
<script>document.documentElement.classList.add("js")</script>
<script src="/assets/js/tracking.js" defer></script>
<script src="/assets/js/site.js" defer></script>
{schema}</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header" data-header>
  <div class="nav-shell">
    <a class="brand" href="/" aria-label="OCS LLC home">
      <img src="/assets/img/ocs-logo.png" alt="OCS LLC" width="720" height="624">
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" data-nav-toggle>
      <span class="sr-only">Open menu</span><span class="nav-toggle-bars" aria-hidden="true"></span>
    </button>
    <nav id="site-nav" class="site-nav" aria-label="Main">
      <ul>
        <li><a href="/plans/" data-nav="plans">Plans</a></li>
        <li><a href="/services/" data-nav="services">Services</a></li>
        <li><a href="/about/" data-nav="about">About</a></li>
        <li><a href="/contact/" data-nav="contact">Contact</a></li>
      </ul>
      <a class="btn btn-primary btn-sm" href="/quote/" data-nav="quote">Get a Same-Day Price</a>
    </nav>
  </div>
</header>
<main id="main">
"""

FOOT = """</main>
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <a href="/" aria-label="OCS LLC home"><img src="/assets/img/ocs-logo.png" alt="OCS LLC" width="720" height="624" loading="lazy"></a>
        <p>Hand-cleaned, insured window cleaning for homes across the Flathead Valley, on a schedule that works for you.</p>
        <p class="footer-phone"><a class="footer-email" href="tel:+14066072151">406-607-2151</a></p>
        <a class="footer-email" href="mailto:{email}">{email}</a>
      </div>
      <div>
        <h2 class="footer-h">Plans</h2>
        <ul class="footer-list">
          <li><a href="/plans/">Quarterly: $100 off / visit</a></li>
          <li><a href="/plans/">Twice a year: $50 off / visit</a></li>
          <li><a href="/plans/">One-time</a></li>
        </ul>
      </div>
      <div>
        <h2 class="footer-h">Company</h2>
        <ul class="footer-list">
          <li><a href="/services/">Services</a></li>
          <li><a href="/about/">About</a></li>
          <li><a href="/contact/">Contact</a></li>
          <li><a href="/quote/">Get a Same-Day Price</a></li>
        </ul>
      </div>
      <div>
        <h2 class="footer-h">Areas Served</h2>
        <ul class="footer-list">
{towns}
          <li><a href="/service-area/">All towns &amp; ZIP codes →</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; <span data-year>2026</span> OCS LLC · Kalispell, Montana</p>
      <p><a href="/privacy/">Privacy</a> · <a href="/terms/">Terms</a> · Quotes are requests. We confirm every price and visit with you.</p>
    </div>
  </div>
</footer>
</body>
</html>
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets",
                    ignore=shutil.ignore_patterns("ocs-logo-source.jpg", "ocs-brand-sheet-source.webp", ".DS_Store"))

    reviews = json.loads((ROOT / "assets" / "data" / "reviews.json").read_text())
    towns = "\n".join(f"          <li>{t}</li>" for t in TOWNS)
    foot = FOOT.format(email=EMAIL, towns=towns)

    for page in PAGES:
        body = (SRC / page["src"]).read_text()
        body = re.sub(r"\[\[include:([\w-]+)\]\]",
                      lambda m: (SRC.parent / "partials" / f"{m.group(1)}.html").read_text(), body)
        body = fill_reviews(body, reviews)
        body = (body.replace("[[areas_accordion]]", areas_accordion())
                .replace("[[areas_tables]]", areas_tables())
                .replace("[[town_options]]", town_options())
                .replace("[[all_zips]]", ", ".join(ALL_ZIPS))
                .replace("[[zip_count]]", str(len(ALL_ZIPS)))
                .replace("[[place_count]]", str(len(ALL_PLACES))))
        body = re.sub(r"\[\[ph:(photo|video)\|([^\]]+)\]\]", placeholder, body)
        body = re.sub(r"\[\[img:([^|\]]+)\|([^|\]]+)(?:\|([^\]]+))?\]\]", photo, body)
        schema = "".join(
            f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>\n'
            for s in page.get("schema", []))
        head = HEAD.format(
            title=page["title"], description=page["description"], domain=DOMAIN,
            canonical=DOMAIN + page["path"],
            robots='<meta name="robots" content="noindex">\n' if page.get("noindex") else "",
            schema=schema)
        if page["nav"]:
            head = head.replace(f'data-nav="{page["nav"]}"', f'data-nav="{page["nav"]}" aria-current="page"')
        dest = OUT / page["out"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(head + body + foot)
        print("  wrote", dest.relative_to(ROOT))

    for old, target in REDIRECTS.items():
        path, _, fragment = target.partition("#")
        dest = OUT / old.strip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(REDIRECT_PAGE.format(domain=DOMAIN, target=target, target_path=path,
                                             target_hash=f"#{fragment}" if fragment else ""))

    urls = [p for p in PAGES if not p.get("noindex")]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{DOMAIN}{p['path']}</loc></url>" for p in urls]
    sitemap.append("</urlset>\n")
    (OUT / "sitemap.xml").write_text("\n".join(sitemap))
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
    (OUT / "CNAME").write_text("ocsllc.services\n")
    (OUT / "llms.txt").write_text(llms_txt(reviews))
    print("Built", len(PAGES), "pages ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
