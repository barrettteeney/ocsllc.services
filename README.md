# OCS LLC — ocsllc.services

Static site (plain HTML/CSS/JS). There are no dependencies and nothing to install.

```
src/pages/      page bodies (home, plans, quote, services, about, contact, thanks, 404)
src/partials/   shared blocks: plan-cards.html, cta.html  →  [[include:name]]
assets/         css, js, images (logo, favicon, og-image)
build.py        wraps pages in the shared head/header/footer, adds old-address redirects → writes ./site/
site/           the deployable output. Don't edit by hand; run the build.
```

## Build & preview

```bash
python3 build.py
python3 -m http.server 4321 --directory site   # http://localhost:4321
```

## Before going live

See `LAUNCH.md` for the decisions, publishing steps and post-launch checks.

To change a photo, put it in `assets/img/work/` (strip location data, and hide house numbers and license
plates) and use `[[img:filename.jpg|Alt text|40%]]`. The percent is the vertical crop focus and is optional.

## Service area

Every town and ZIP lives in `SERVICE_AREAS` in `build.py`. The home page list, `/service-area/`, the quote
form, the search data and `llms.txt` (a plain summary for AI assistants) are all built from it.

## Sending leads to Rotor

The quote page uses Rotor's own form in an iframe (`forms.getrotor.com/f/1ku4mx2d1eyg?embed=true`). Customer
details land directly in Rotor as a new lead, with Source: Website. The fields are set in Rotor, not on the site.
The contact page form goes by email to barrett@ocsllc.services through FormSubmit.

Google Ads counts a quote when someone reaches `/thanks/`. For that, set the Rotor form's Redirect URL to
`https://ocsllc.services/thanks/` in Rotor.

## Google reviews

The home page cycles through every review in `assets/data/reviews.json`, and `build.py` fills in the
rating and count from the same file. Don't edit reviews by hand.

`.github/workflows/site.yml` runs every 6 hours: it pulls reviews with `scripts/sync_reviews.py`,
rebuilds, and publishes `site/` to GitHub Pages. To turn it on:

1. Push this project to a GitHub repo and set Pages to deploy from "GitHub Actions".
2. Add the secrets `GBP_CLIENT_ID`, `GBP_CLIENT_SECRET`, `GBP_REFRESH_TOKEN`, `GBP_ACCOUNT_ID` and
   `GBP_LOCATION_ID` (the old site's repo, `barrettteeney/ocsllc.services`, already has them).

If Google fails, the current reviews stay up. Star-only reviews count toward the total but aren't shown.
Every review is shown, whatever its rating. Test the sync with `python3 scripts/test_sync_reviews.py`.

## Rules baked in

- Steel Blue `#4A6A8A` is used only on buttons and plan accents.
- There is no self-booking: every CTA leads to `/quote/`, and we confirm the price and time with the customer.
  The one outside link is the Permanent lights tile, which goes to Lab Lighting (lablightingmt.com).
- There are no fixed prices or awards, and no made-up reviews or counts. Reviews and the rating come
  from Google (see "Google reviews" below).
  Plan math ($100 / $400 per year saved) comes straight from the per-visit discounts.
- Small secondary text uses `#68635C` (Warm Stone darkened) to pass WCAG AA on cream.
  Raw Warm Stone `#A39E96` is used for dividers and decorative lines.
