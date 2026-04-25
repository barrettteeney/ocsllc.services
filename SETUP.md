# OCS LLC website automation — setup guide

This site auto-syncs with the OCS LLC Google Business Profile and self-monitors. Most of it works without you touching anything. **Two things require a one-time setup from you** to fully enable the GBP sync:

## 1. Google Cloud Places API key

1. Go to https://console.cloud.google.com/ and sign in with the Google account that manages the OCS LLC GBP listing.
2. Click the project dropdown (top of the page) → **New Project**. Name it `ocsllc-website-sync` and click Create.
3. Wait a few seconds for the project to be created, then make sure it's selected in the project dropdown.
4. Go to **APIs & Services → Library**. Search for **"Places API (New)"** and click Enable. (Important: pick the *new* one, not the old "Places API".)
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**.
6. Copy the key.
7. Click **Restrict Key** on the same page:
   - Application restrictions: choose **HTTP referrers** and add `https://ocsllc.services/*` (this prevents the key from being abused if it ever leaks).
   - API restrictions: choose **Restrict key** and tick only **Places API (New)**.
   - Click Save.
8. (Required by Google) Go to **Billing** in the left nav and link a credit card. Google gives a generous free monthly credit and our usage will stay well under it — typical cost: $0/month. Without billing enabled, the API will return errors.

## 2. Find your Place ID

1. Go to https://developers.google.com/maps/documentation/places/place-id
2. Type **OCS LLC** (or your business name as it appears on Google Maps) into the search box.
3. Click your business in the dropdown.
4. Copy the Place ID — it looks like `ChIJN1t_tDeuEmsRUsoyG83frY4`.

## 3. Add both as GitHub repo secrets

1. Go to https://github.com/barrettteeney/ocsllc.services/settings/secrets/actions
2. Click **New repository secret**.
3. Name: `GOOGLE_PLACES_API_KEY` — Value: the API key from step 1.
4. Add another: name `PLACE_ID` — value: the Place ID from step 2.

## 4. Trigger the first sync

1. Go to https://github.com/barrettteeney/ocsllc.services/actions/workflows/sync-gbp.yml
2. Click **Run workflow → Run workflow**.
3. After ~30 seconds, refresh — there should be a new commit on main like `auto: sync from Google Business Profile [skip ci]`.
4. Within a couple minutes the live site will show your latest GBP reviews, hours, and photos.

## 5. (Optional but recommended) Quote form backend

The on-site quote form posts to https://web3forms.com — a free, no-account form-to-email service. To activate:

1. Go to https://web3forms.com/ → enter `barrett@ocsllc.services` → click **Create Access Key**.
2. They email you a key (looks like `1a2b3c4d-1234-...`).
3. Replace `WEB3FORMS_KEY_PLACEHOLDER` in `index.html` with the key. (Or tell me the key and I'll do it.)

Alternative: **Formspree** (free up to 50 submissions/month). Sign up at https://formspree.io, create a new form, copy the endpoint URL, and replace the form's `action` attribute.

# What runs automatically

| Workflow | When | What it does |
|---|---|---|
| `sync-gbp.yml` | Every 6 hours + on demand | Pulls reviews, rating, hours, photos from your GBP and updates the site. |
| `auto-sitemap.yml` | On every push that changes HTML | Regenerates `sitemap.xml` from the filesystem. |
| `schema-validate.yml` | On every push to main | Validates JSON-LD on live URLs after deploy. Opens an issue if any are broken. |
| `link-check.yml` | Every Monday at noon UTC | Scans every page for broken links. Opens an issue if any found. |
| `lighthouse.yml` | Every Monday at 13:13 UTC | Runs Lighthouse against 6 representative URLs. |

# What's where

```
/scripts/
  sync_gbp.py       # pulls from Google Places API (New) and updates HTML + JSON-LD
  build_sitemap.py  # walks the repo, regenerates sitemap.xml
/.github/workflows/
  sync-gbp.yml         # cron + manual GBP sync
  auto-sitemap.yml     # auto-regen sitemap on HTML changes
  schema-validate.yml  # validate JSON-LD post-deploy
  link-check.yml       # weekly broken-link scan
  lighthouse.yml       # weekly Lighthouse audit
/.lighthouserc.json    # Lighthouse score thresholds
/assets/gbp/           # photos and metadata downloaded from GBP (auto-managed; don't edit by hand)
```

# Running anything manually

Open https://github.com/barrettteeney/ocsllc.services/actions, pick a workflow, click **Run workflow**.

# Cost

Everything is free as long as:
- GBP sync stays under ~3,000 calls/month (we run 4×/day = ~120/month).
- Repo stays under GitHub's free 2,000 Action minutes/month.
- Web3Forms / Formspree stays under their free tier (50/month).

In practice, $0/month all-in.
