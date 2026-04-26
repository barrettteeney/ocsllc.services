#!/usr/bin/env python3
"""auto_blog.py — auto-publish a new seasonal blog post once per quarter.

Drives organic search traffic + signals freshness to Google. Posts are real
content tailored to the Flathead Valley's seasons.
"""
import os, json, re, datetime, pathlib

ROOT = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()

today = datetime.date.today()
month = today.month
year = today.year
quarter = (month - 1) // 3 + 1  # 1=Jan-Mar, 2=Apr-Jun, 3=Jul-Sep, 4=Oct-Dec

POSTS = {
    1: {
        "slug": "winter-window-cleaning-flathead-valley",
        "title": "Winter window cleaning in the Flathead Valley: what works, what doesn't",
        "lead": "Six things we've learned about cleaning glass at 25°F — and the one rule that changes everything.",
        "body": [
            ("When to clean", "Window cleaning works in winter as long as it's above ~25°F and dry. Below that, the cleaning solution starts freezing on the glass before you can squeegee it off, leaving streaks that bond as the temperature drops further. Above freezing — even in light snow — we can usually get a clean."),
            ("The right solution", "Standard dish soap and water freezes too fast. Winter window cleaning uses a low-temperature solution with isopropyl alcohol (about 1 part rubbing alcohol to 4 parts soapy water) that resists freezing down to about 15°F. We mix on-site to match the day's conditions."),
            ("Snow on sills first", "Wet snow on sills will dump mid-clean and refreeze. We brush snow off every sill before starting and lay drop cloths under each window inside in case any meltwater drips."),
            ("Inside-only days", "On the coldest weeks, we book interior-only appointments. Insides stay clean longer because Montana winter air is drier than summer air — humidity averages 30-40% indoors vs. 60% in summer."),
            ("Why bother in winter", "Winter sun is low-angle and brutal — every smudge, fingerprint, and water spot shows. People who clean their windows in November and February consistently say their light feels different. It's not magic, it's photons."),
            ("The one rule", "Don't clean your windows the day before snow. Snow + cold-soaked glass = condensation on contact, which redistributes any residual cleaner into streaks. Wait until the day after the last storm.")
        ]
    },
    2: {
        "slug": "spring-window-cleaning-checklist",
        "title": "Spring window cleaning checklist — Flathead Valley homeowners",
        "lead": "Eight steps to undo a Montana winter, in the right order.",
        "body": [
            ("Wait for the right week", "Don't start the day after snowmelt. Wait until daytime highs are consistently above 45°F and overnight lows above freezing for at least 3 days. In Kalispell that's usually mid-April."),
            ("Cottonwood pollen first", "If your property has cottonwoods nearby, hose down the exterior glass before any cleaning. Pollen rehydrates with morning dew and smears."),
            ("Vacuum tracks dry", "Wet sand makes mud. Vacuum every track before water touches it."),
            ("Hand-wash screens", "Pop them out, lay flat, gentle scrub with soft brush, rinse, air-dry standing up."),
            ("Squeegee top-to-bottom", "Wet thoroughly with soapy water, single passes top-to-bottom, wipe blade between every pass."),
            ("Detail sills + check rot", "Wipe down sills and look for soft spots. Montana freeze-thaw cycles drive water into hairline cracks."),
            ("Re-caulk failed seals", "Spring is when you catch failed seals before summer thunderstorms find them."),
            ("Address hard-water staining", "Lakefront and sprinkler-spotted glass needs specialty treatment. Regular cleaner won't touch it.")
        ]
    },
    3: {
        "slug": "summer-deck-and-pressure-wash-flathead",
        "title": "Summer pressure washing in the Flathead Valley: decks, driveways, and what not to power-wash",
        "lead": "How to clean an outdoor space without etching concrete or stripping the wood.",
        "body": [
            ("Surface dictates pressure", "Concrete tolerates 3000 PSI. Wood decks max around 1500 PSI with a fan tip. Vinyl siding is in between. Every surface has a sweet spot — too high etches, too low doesn't clean."),
            ("Soft-wash for delicates", "Stained wood, painted siding, and aluminum gutters need 'soft wash' — low pressure plus a biocide solution that does the chemical work. We apply, dwell, rinse."),
            ("Driveways: pre-treat first", "Oil stains lift better with a degreaser pre-treatment than with raw pressure. Cold-water pressure alone smears oil; heat or chemistry breaks it."),
            ("Deck-day timing", "Cleaned decks need to dry 24-48 hours before sealing. Plan for two clear days in your forecast."),
            ("Don't power-wash these", "Roof shingles (rip off granules), composite decking (specific-product needed), painted brick (peels), historical mortar joints, electrical fittings, AC units."),
            ("Bundle with windows", "Pressure washing kicks dust onto fresh glass. We always do siding/concrete first, then windows the same day or next day. Bundling saves you a return trip + 10-20% off the combined rate.")
        ]
    },
    4: {
        "slug": "fall-prep-window-cleaning-flathead-valley",
        "title": "Fall prep: clean windows before the snow flies",
        "lead": "Why mid-October is the most important window cleaning of the year.",
        "body": [
            ("The October sweet spot", "Mid-October has the best conditions of the year for window cleaning: cool but not cold, dry, low pollen, no bugs. The clean lasts five months because winter air doesn't carry dust."),
            ("Cottonwood seed cleanup", "Fall cottonwood fluff is more annoying than spring pollen because it sticks to everything fibrous — screens, weatherstripping, gutter inserts. Brush screens dry first; wet seed-fluff turns to glue."),
            ("Gutters and roof debris", "Debris from gutters splashes onto windows on the next rain. If you clean gutters in fall, do it before windows."),
            ("Inside cleaning before holidays", "Interior cleans look great in low-angle winter sun and through holiday lights. Mid-November booking is the move."),
            ("Lockup-the-cabin checklist", "Seasonal residents leaving for the season: clean windows last after everything else. Final lockup, departure-ready glass means you walk into a fresh house in spring."),
            ("Schedule before the calendar fills", "We book up two to three weeks out by mid-October. Spring is the same — call early.")
        ]
    }
}

post = POSTS.get(quarter)
if not post:
    raise SystemExit("no post template for quarter " + str(quarter))

slug = post["slug"]
out_dir = ROOT / "blog" / slug
out_path = out_dir / "index.html"

if out_path.exists():
    print(f"  /blog/{slug}/ already exists; checking if update needed...")
    existing = out_path.read_text()
    quarter_start = datetime.date(year, (quarter-1)*3+1, 1).isoformat()
    if quarter_start in existing:
        print("  current quarter post already published; nothing to do")
        raise SystemExit(0)

iso_date = today.isoformat()

article_ld = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": post["title"],
    "description": post["lead"],
    "image": "https://ocsllc.services/assets/og.png",
    "datePublished": iso_date,
    "dateModified": iso_date,
    "author": {"@type": "Person", "name": "Barrett Teeney", "url": "https://ocsllc.services/about/"},
    "publisher": {"@id": "https://ocsllc.services/#business"},
    "mainEntityOfPage": f"https://ocsllc.services/blog/{slug}/"
}

breadcrumbs_ld = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://ocsllc.services/"},
        {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://ocsllc.services/blog/"},
        {"@type": "ListItem", "position": 3, "name": post["title"], "item": f"https://ocsllc.services/blog/{slug}/"}
    ]
}

body_html = "\n".join(
    f"                <h2>{section[0]}</h2>\n                <p>{section[1]}</p>"
    for section in post["body"]
)

ART_LD_STR = json.dumps(article_ld, indent=2)
BC_LD_STR  = json.dumps(breadcrumbs_ld, indent=2)
DATE_PRETTY = today.strftime("%B %-d, %Y")

# Build the HTML in pieces to avoid f-string nesting headaches
parts = []
parts.append('<!DOCTYPE html>')
parts.append('<html lang="en">')
parts.append('<head>')
parts.append('    <meta charset="UTF-8">')
parts.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">')
parts.append('    <meta name="robots" content="index, follow, max-image-preview:large">')
parts.append('    <meta name="theme-color" content="#0CC0DF">')
parts.append(f'    <title>{post["title"]} | OCS LLC</title>')
parts.append(f'    <meta name="description" content="{post["lead"]}">')
parts.append(f'    <link rel="canonical" href="https://ocsllc.services/blog/{slug}/">')
parts.append('')
parts.append('    <meta property="og:type" content="article">')
parts.append(f'    <meta property="og:title" content="{post["title"]}">')
parts.append(f'    <meta property="og:description" content="{post["lead"]}">')
parts.append(f'    <meta property="og:url" content="https://ocsllc.services/blog/{slug}/">')
parts.append('    <meta property="og:image" content="https://ocsllc.services/assets/og.png">')
parts.append('')
parts.append('    <script type="application/ld+json">')
parts.append(ART_LD_STR)
parts.append('    </script>')
parts.append('    <script type="application/ld+json">')
parts.append(BC_LD_STR)
parts.append('    </script>')
parts.append('')
parts.append("    <link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='16' fill='%230CC0DF'/%3E%3Ctext x='50' y='62' font-family='Arial,sans-serif' font-size='44' font-weight='700' text-anchor='middle' fill='white'%3EO%3C/text%3E%3C/svg%3E\">")
parts.append('    <link rel="manifest" href="/manifest.webmanifest">')
parts.append('    <script src="https://cdn.tailwindcss.com"></script>')
parts.append('    <link rel="stylesheet" href="/assets/site.css">')
parts.append('    <link rel="stylesheet" href="/assets/responsive.css">')
parts.append('</head>')
parts.append('<body class="bg-gray-50 text-black">')
parts.append('    <nav class="bg-custom-cyan text-white p-4 sticky top-0 z-10">')
parts.append('        <div class="container nav-container">')
parts.append('            <a href="/" class="text-lg font-bold">OCS LLC</a>')
parts.append('            <div class="contact-info">')
parts.append('                <p><a href="tel:+14066072151">(406) 607-2151</a></p>')
parts.append('                <p><a href="mailto:barrett@ocsllc.services">barrett@ocsllc.services</a></p>')
parts.append('            </div>')
parts.append('        </div>')
parts.append('    </nav>')
parts.append('')
parts.append('    <section class="hero-mini hero-photo" style="background-image: url(\'/assets/og.png\');">')
parts.append(f'        <h1>{post["title"]}</h1>')
parts.append(f'        <p>{post["lead"]}</p>')
parts.append('    </section>')
parts.append('')
parts.append('    <section class="bg-white">')
parts.append('        <div class="container max-w-3xl">')
parts.append(f'            <p class="breadcrumbs"><a href="/">Home</a> &rsaquo; <a href="/blog/">Blog</a> &rsaquo; {post["title"]}</p>')
parts.append(f'            <p class="text-sm text-gray-500 mb-6">Posted {DATE_PRETTY} · By Barrett Teeney</p>')
parts.append('')
parts.append('            <div class="article-prose">')
parts.append(body_html)
parts.append('            </div>')
parts.append('')
parts.append('            <div class="cta-box mt-12">')
parts.append('                <h2>Want pro help?</h2>')
parts.append('                <p>We do this every day across the Flathead Valley. Get a free same-day quote.</p>')
parts.append('                <a href="/#quote" class="btn-white">Get a Free Estimate</a>')
parts.append('                <a href="tel:+14066072151" class="tel-link">Or call (406) 607-2151</a>')
parts.append('            </div>')
parts.append('        </div>')
parts.append('    </section>')
parts.append('')
parts.append('    <footer class="bg-custom-cyan text-white py-8 mt-auto">')
parts.append('        <div class="container text-center">')
parts.append('            <p>&copy; 2025 OCS LLC / Licensed and Insured</p>')
parts.append('            <p class="mt-2 text-sm"><a class="underline" href="/">Home</a> · <a class="underline" href="/blog/">Blog</a> · <a class="underline" href="/about/">About</a> · <a class="underline" href="/privacy/">Privacy</a> · <a class="underline" href="/terms/">Terms</a></p>')
parts.append('        </div>')
parts.append('    </footer>')
parts.append('    <a href="tel:+14066072151" class="mobile-call-bar">📞 Call (406) 607-2151</a>')
parts.append('</body>')
parts.append('</html>')

html_doc = "\n".join(parts)

out_dir.mkdir(parents=True, exist_ok=True)
out_path.write_text(html_doc)
print(f"  PUBLISHED: /blog/{slug}/  ({len(html_doc)} bytes)")

blog_index = ROOT / "blog" / "index.html"
if blog_index.exists():
    bidx = blog_index.read_text()
    new_post_html = (
        f'            <article class="border-b border-gray-200 pb-6 mb-6">\n'
        f'                <p class="text-sm text-gray-500 mb-1">{today.strftime("%B")} · Q{quarter} {year}</p>\n'
        f'                <h2 class="text-2xl font-bold mb-2"><a href="/blog/{slug}/" class="hover:text-custom-cyan">{post["title"]}</a></h2>\n'
        f'                <p class="text-gray-700 mb-2">{post["lead"]}</p>\n'
        f'                <a href="/blog/{slug}/" class="text-custom-cyan font-semibold">Read the post →</a>\n'
        f'            </article>\n\n'
    )
    if f"/blog/{slug}/" not in bidx:
        bidx = re.sub(r'(<article class="border-b)', new_post_html + r'\1', bidx, count=1)
        blog_index.write_text(bidx)
        print(f"  Updated /blog/ index with new post link")
