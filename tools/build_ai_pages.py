"""Build /pricing/ and /faq/ pages from the residential service page template.

Prices mirror the live pricing engine in assets/onepage.js.
"""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
tpl = (ROOT / "services/residential/index.html").read_text()

head_top = tpl.split('<script type="application/ld+json">')[0]
head_rest = tpl[tpl.index('<link rel="icon"'):tpl.index('</head>')]
nav = re.search(r'<nav class="site-nav">.*?</nav>', tpl, re.S).group(0)
foot = tpl[tpl.index('<footer'):]
foot = foot.replace(
    '<a class="underline" href="/pricing/">Pricing</a>',
    '<a class="underline" href="/pricing/">Pricing</a> &middot; <a class="underline" href="/faq/">FAQ</a>')
nav = nav.replace('<a href="/pricing/">Pricing</a>', '<a href="/pricing/">Pricing</a><a href="/faq/">FAQ</a>')

EXTRA_CSS = """
<style>
.price-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin:1.25rem 0}
.price-card{background:#fff;border:1px solid #e3eef1;border-radius:14px;padding:1.25rem;text-align:center}
.price-card .amt{font-size:2.2rem;font-weight:700;color:#0a1215;line-height:1.1}
.price-card .unit{font-size:.9rem;color:#4a5a60}
.price-card.featured{border:2px solid #00C0DF;box-shadow:0 6px 24px rgba(0,192,223,.15)}
.price-table{width:100%;border-collapse:collapse;margin:1rem 0;background:#fff;border-radius:12px;overflow:hidden}
.price-table th,.price-table td{padding:.75rem .9rem;border-bottom:1px solid #e9eef0;text-align:left;vertical-align:top}
.price-table th{background:#f2fbfd;font-size:.85rem;text-transform:uppercase;letter-spacing:.03em;color:#33464d}
.price-table td:last-child{white-space:nowrap;font-weight:600}
.example{background:#f2fbfd;border-left:4px solid #00C0DF;padding:1rem 1.1rem;border-radius:8px;margin:1rem 0}
.note{font-size:.9rem;color:#4a5a60}
.faq-item{background:#fff;border:1px solid #e3eef1;border-radius:12px;margin:.7rem 0}
.faq-item summary{cursor:pointer;padding:1rem 1.1rem;font-weight:600;list-style:none;display:flex;justify-content:space-between;gap:1rem}
.faq-item summary::-webkit-details-marker{display:none}
.faq-item summary::before{content:none!important;display:none!important}
.faq-item summary{text-align:left;align-items:center}
.faq-item summary::after{content:"+";color:#00C0DF;font-size:1.3rem;line-height:1}
.faq-item[open] summary::after{content:"\\2212"}
.faq-item .ans{padding:0 1.1rem 1.1rem;color:#26363b}
.cta-band{text-align:center}
.cta-band .btn{display:inline-block;background:#00C0DF;color:#0a1215;font-weight:700;padding:.85rem 1.4rem;border-radius:10px;text-decoration:none;margin:.3rem}
.cta-band .btn.alt{background:#0a1215;color:#fff}
</style>
"""

def ld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False) + '\n</script>\n'

def meta(title, desc, url):
    h = head_top
    h = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', h)
    h = re.sub(r'(<meta name="description" content=")[^"]*', r'\g<1>' + desc, h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r'\g<1>' + url, h)
    h = re.sub(r'(<meta property="og:title" content=")[^"]*', r'\g<1>' + title, h)
    h = re.sub(r'(<meta property="og:description" content=")[^"]*', r'\g<1>' + desc, h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r'\g<1>' + url, h)
    h = re.sub(r'(<meta name="twitter:title" content=")[^"]*', r'\g<1>' + title, h)
    h = re.sub(r'(<meta name="twitter:description" content=")[^"]*', r'\g<1>' + desc, h)
    return h

def crumbs(name, url):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://ocsllc.services/"},
        {"@type": "ListItem", "position": 2, "name": name, "item": url}]}

def hero(h1, sub):
    return f"""    <section class="hero-mini hero-photo">
        <h1>{h1}</h1>
        <p>{sub}</p>
        <div class="hero-cta-row">
            <a href="/estimate/" class="bg-white text-black px-6 py-3 rounded-lg hover:bg-gray-200 transition font-semibold">Get your exact price</a>
            <a href="tel:+14066072151" class="tel-link" aria-label="Call OCS LLC at (406) 607-2151">Or call or text (406) 607-2151</a>
        </div>
    </section>
"""

CTA = """    <section class="bg-white cta-band">
        <div class="container">
            <h2 class="text-2xl font-bold mb-2">Want an exact number for your home?</h2>
            <p class="mb-4">Count your windows in the instant estimate, or text a photo of each side of the house and we'll send a firm price.</p>
            <a class="btn" href="/estimate/">Get an instant estimate</a>
            <a class="btn alt" href="sms:+14066072151">Text (406) 607-2151</a>
        </div>
    </section>
"""

# ---------- FAQ content (shared by FAQ page + schema) ----------
FAQS = [
    ("How much does window cleaning cost in Kalispell?",
     "We price by the window, not by square footage, so you only pay for the glass you have. Your price depends on how many windows you have, inside and out or outside only, screens, how high the windows are and their condition. The instant estimate on our website gives you a range in about a minute, and we confirm a firm price before any work starts."),
    ("How do you count windows?",
     "Each separate piece of glass that opens or sits in its own frame counts as one window. Small French or divided panes are grouped together, so a window full of little panes isn't priced like a dozen windows."),
    ("Is there a minimum charge?",
     "Yes, there's a minimum per visit. It covers screens and any extras, so small homes and quick jobs get one simple price."),
    ("What affects the price?",
     "High or hard-to-reach windows, windows that haven't been professionally cleaned in years, post-construction dust and residue, hard water spots, and triple-pane storm windows where both layers get cleaned. We tell you about any of these before we start."),
    ("Can you remove hard water spots?",
     "Light staining usually comes out with our standard process. Heavier mineral buildup takes extra treatment, which we include in your quote. We'll look at it and tell you what to expect before we start."),
    ("Do you offer discounts for regular cleanings?",
     "Yes. Customers on a twice-a-year, quarterly or monthly plan save on every visit after the first clean."),
    ("Do you clean storefronts and commercial windows?",
     "Yes. We service storefronts and commercial buildings on weekly, every-2-week, monthly or seasonal routes, as well as one-time cleans. Ask for a storefront quote."),
    ("Which towns do you serve?",
     "Kalispell, Whitefish, Columbia Falls, Bigfork and the rest of the Flathead Valley. If you're farther out, ask and we'll let you know."),
    ("How often should I have my windows cleaned?",
     "Most homeowners do twice a year, once in spring after winter grit and once in fall before snow flies. Lakefront homes and properties under heavy tree cover often benefit from quarterly cleaning."),
    ("Do I need to be home?",
     "Not always. For exterior-only cleans, no. For interior, we just need access. We can also work with garage codes, key safes, or a neighbor."),
    ("How do I get an exact price?",
     "Use the instant estimate on our website, or call or text (406) 607-2151 with a photo of each side of the house. We confirm a firm price before any work starts."),
    ("How do I pay?",
     "You'll get an invoice by email after the job. You can pay online by card or bank transfer."),
]

def faq_html(items):
    out = []
    for q, a in items:
        out.append(f'            <details class="faq-item"><summary>{q}</summary><div class="ans"><p>{a}</p></div></details>')
    return "\n".join(out)

def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}

# ---------- Pricing page ----------
def offer(name, price, unit, desc=None):
    o = {"@type": "Offer", "name": name, "price": f"{price:.2f}", "priceCurrency": "USD",
         "priceSpecification": {"@type": "UnitPriceSpecification", "price": f"{price:.2f}", "priceCurrency": "USD", "unitText": unit}}
    if desc: o["description"] = desc
    return o

pricing_ld = {
    "@context": "https://schema.org", "@type": "Service", "name": "Window Cleaning",
    "serviceType": "Window cleaning", "provider": {"@id": "https://ocsllc.services/#business"},
    "areaServed": [{"@type": "City", "name": c + ", MT"} for c in ["Kalispell", "Whitefish", "Columbia Falls", "Bigfork"]],
    "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Window cleaning prices", "itemListElement": [
        offer("Inside and outside window cleaning", 12, "window"),
        offer("Outside-only window cleaning", 8, "window"),
        offer("Inside-only window cleaning", 4, "window"),
        offer("Screen cleaning", 3, "screen"),
        offer("Hard water spot removal", 4, "window", "Added per affected window"),
        offer("Minimum visit, outside only", 150, "visit"),
        offer("Minimum visit, inside and outside", 225, "visit"),
        offer("Storefront glass, outside", 5, "pane"),
        offer("Storefront glass, inside", 3, "pane"),
        offer("Storefront minimum", 55, "visit"),
    ]}}

PRICE_FAQ = [FAQS[0], FAQS[1], FAQS[2], FAQS[3], FAQS[5]]

pricing_body = hero("Window Cleaning Prices in the Flathead Valley",
                    "Straight pricing, no surprises: $12 per window inside and out. Here's exactly how we price every home and storefront in Kalispell, Whitefish, Columbia Falls and Bigfork.") + f"""
    <section class="bg-white">
        <div class="container">
            <p class="breadcrumbs"><a href="/">Home</a> &rsaquo; Pricing</p>
            <h2 class="text-2xl font-bold mb-2">Home window cleaning</h2>
            <p>We price by the window, not by square footage, so you only pay for the glass you actually have.</p>
            <div class="price-grid">
                <div class="price-card featured"><div class="unit">Inside &amp; outside</div><div class="amt">$12</div><div class="unit">per window</div></div>
                <div class="price-card"><div class="unit">Outside only</div><div class="amt">$8</div><div class="unit">per window</div></div>
                <div class="price-card"><div class="unit">Inside only</div><div class="amt">$4</div><div class="unit">per window</div></div>
                <div class="price-card"><div class="unit">Screens</div><div class="amt">$3</div><div class="unit">per screen</div></div>
            </div>
            <div class="example"><strong>Example:</strong> a single-level home with 20 windows, inside and out, is 20 &times; $12 = <strong>$240</strong>. Add 15 screens for $45.</div>
            <h3 class="text-xl font-semibold mt-6 mb-2">Minimum visit</h3>
            <table class="price-table">
                <tr><th>Service</th><th>Minimum</th></tr>
                <tr><td>Outside only</td><td>$150</td></tr>
                <tr><td>Inside &amp; outside</td><td>$225</td></tr>
            </table>
            <p class="note">The minimum includes screens and any surcharges. Travel outside the Flathead Valley is quoted separately, up front.</p>
        </div>
    </section>

    <section class="bg-gray-50">
        <div class="container">
            <h2 class="text-2xl font-bold mb-2">When the price changes</h2>
            <table class="price-table">
                <tr><th>Situation</th><th>Adjustment</th></tr>
                <tr><td>High or hard-to-reach windows (second story and up)</td><td>+15% per side</td></tr>
                <tr><td>Not professionally cleaned in years (heavy buildup)</td><td>+25%</td></tr>
                <tr><td>Post-construction clean (dust, paint and residue)</td><td>+50%</td></tr>
                <tr><td>Hard water spot removal</td><td>+$4 per affected window</td></tr>
                <tr><td>Triple-pane / storm windows (both layers cleaned)</td><td>+$12 per side</td></tr>
                <tr><td>Small French or divided panes</td><td>about 3 lites = 1 window</td></tr>
            </table>
        </div>
    </section>

    <section class="bg-white">
        <div class="container">
            <h2 class="text-2xl font-bold mb-2">Save with a cleaning plan</h2>
            <p>Your first clean is full price. Every visit after that is discounted for as long as you're on the plan.</p>
            <div class="price-grid">
                <div class="price-card"><div class="unit">One-time</div><div class="amt">0%</div><div class="unit">full price</div></div>
                <div class="price-card"><div class="unit">Twice a year</div><div class="amt">10%</div><div class="unit">off from visit 2</div></div>
                <div class="price-card featured"><div class="unit">Quarterly</div><div class="amt">20%</div><div class="unit">off from visit 2</div></div>
                <div class="price-card"><div class="unit">Monthly</div><div class="amt">20%</div><div class="unit">off from visit 2</div></div>
            </div>
        </div>
    </section>

    <section class="bg-gray-50">
        <div class="container">
            <h2 class="text-2xl font-bold mb-2">Storefront &amp; commercial glass</h2>
            <table class="price-table">
                <tr><th>Item</th><th>Price</th></tr>
                <tr><td>Outside glass</td><td>$5 per pane</td></tr>
                <tr><td>Inside glass</td><td>$3 per pane</td></tr>
                <tr><td>High glass</td><td>+$2 per pane</td></tr>
                <tr><td>Minimum per visit</td><td>$55</td></tr>
            </table>
            <table class="price-table">
                <tr><th>How often</th><th>Price</th></tr>
                <tr><td>Weekly, every 2 weeks, every 4 weeks</td><td>Standard</td></tr>
                <tr><td>Every 8 weeks</td><td>+20%</td></tr>
                <tr><td>Every 12 weeks</td><td>+25%</td></tr>
                <tr><td>One-time clean</td><td>+50%</td></tr>
            </table>
        </div>
    </section>

    <section class="bg-white">
        <div class="container">
            <h2 class="text-2xl font-bold mb-3">Pricing questions</h2>
{faq_html(PRICE_FAQ)}
            <p class="mt-4"><a class="underline" href="/faq/">See all frequently asked questions &rarr;</a></p>
        </div>
    </section>
""" + CTA

faq_body = hero("Window Cleaning FAQ",
                "Straight answers about prices, hard water, plans and scheduling for homes and businesses across the Flathead Valley.") + f"""
    <section class="bg-white">
        <div class="container">
            <p class="breadcrumbs"><a href="/">Home</a> &rsaquo; FAQ</p>
            <h2 class="text-2xl font-bold mb-3">Frequently asked questions</h2>
{faq_html(FAQS)}
            <p class="mt-4"><a class="underline" href="/estimate/">Get your instant estimate &rarr;</a></p>
        </div>
    </section>
""" + CTA

def page(title, desc, url, lds, body):
    return (meta(title, desc, url) + "".join(ld(x) for x in lds) + "\n    " + head_rest + EXTRA_CSS
            + "</head>\n<body class=\"bg-gray-50 text-black\">\n\n    " + nav + "\n" + body + foot)

out = {
    "_unused_pricing.html": page(
        "Window Cleaning Prices in Kalispell & the Flathead Valley | OCS LLC",
        "OCS window cleaning prices: $12 per window inside and out, $8 outside only, $3 screens, $150 minimum. Kalispell, Whitefish, Columbia Falls, Bigfork.",
        "https://ocsllc.services/pricing/",
        [pricing_ld, crumbs("Pricing", "https://ocsllc.services/pricing/"), faq_ld(PRICE_FAQ)], pricing_body),
    "faq/index.html": page(
        "Window Cleaning FAQ: Prices, Hard Water & Plans | OCS LLC",
        "Answers about window cleaning in Kalispell and the Flathead Valley: cost per window, minimums, hard water, cleaning plans, storefronts and scheduling.",
        "https://ocsllc.services/faq/",
        [crumbs("FAQ", "https://ocsllc.services/faq/"), faq_ld(FAQS)], faq_body),
}
for path, html in out.items():
    if path.startswith("_unused"): continue
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html)
    print(path, len(html))
