# OCS LLC — CRM + Cloudinary Setup (one-time, ~10 minutes total)

This is the second-round setup that activates two things:
1. **HubSpot Free CRM** — every quote-form submission becomes a contact + deal in your HubSpot account, with full pipeline tracking, email logging, and a mobile app.
2. **Cloudinary** — drag-drop photo uploads at https://ocsllc.services/admin/upload/, no Flickr-app workflow needed.

Until you finish setup, the existing FormSubmit email + Flickr sync keep working — nothing breaks.

---

## Part 1: HubSpot Free CRM (~5 minutes)

HubSpot's free CRM is industry-standard for service businesses. It's actually free forever, has unlimited contacts, includes a mobile app, and lets you log every call/email tied to a contact. You'll want this.

### Step 1: Sign up

1. Go to https://www.hubspot.com/products/crm
2. Click **Get HubSpot free**.
3. Sign up with your `barrett@ocsllc.services` email.
4. Skip every "would you like a sales call" prompt. Pick "small business" / "1 person" / "service business" — exact answers don't matter.

### Step 2: Get your Portal ID

1. Once you're in HubSpot, click your profile (top right) → **Account & Billing**.
2. Your **Hub ID** / **Portal ID** is shown — looks like `12345678` (8 digits).
3. Copy it.

### Step 3: Create a "Quote Request" form

1. In HubSpot, go to **Marketing → Lead Capture → Forms**.
2. Click **Create form** → **Embedded form**.
3. Name it `OCS LLC quote request`.
4. Add these fields (in this order, all required where noted):
   - **First name** (required)
   - **Phone number** (required)
   - **Email** (not required — sometimes customers won't have one)
   - **Message** (multi-line, not required)
5. Click **Save**.
6. Click **Embed** at top right. The script tag has `formId="..."` — copy that **Form GUID** (a long UUID like `a1b2c3d4-...`).

### Step 4: Wire it up

Edit `admin-config.js` in the repo (https://github.com/barrettteeney/ocsllc.services/blob/main/admin-config.js):

```js
window.OCS_CONFIG = {
    hubspotPortalId:        "12345678",
    hubspotFormId:          "a1b2c3d4-...",
    ...
};
```

Commit. Within ~1 minute the form is wired up. Test by submitting from https://ocsllc.services/#quote — you'll see the contact appear in HubSpot under **Contacts**.

### Step 5: Set up the deal pipeline (optional, recommended)

In HubSpot → **Sales → Deals**:
1. Create a pipeline called "Window cleaning jobs" with stages: *New lead → Quoted → Booked → Done → Invoiced*.
2. Right-click any new contact → **Create deal** → assign to the pipeline.
3. (Optional) Set up a workflow that auto-creates a deal when a contact comes in via the form.

Now your "centralized place" is real: every contact, every deal, every call, every email — all in HubSpot.

---

## Part 2: Cloudinary (~5 minutes)

### Step 1: Sign up

1. Go to https://cloudinary.com/users/register/free
2. Sign up with your `barrett@ocsllc.services` email.
3. Pick "I'm a developer" → "Free plan" (25 GB storage / 25 GB bandwidth — plenty).

### Step 2: Find your cloud name

After signup you land in the dashboard. The **Cloud name** is shown at the top — looks like `ocsllc-llc` or a random string. Copy it.

### Step 3: Create an unsigned upload preset

1. **Settings (⚙️) → Upload** tab.
2. Scroll to **Upload presets** → **Add upload preset**.
3. Name: `ocsllc-website-uploads`.
4. **Signing mode**: change to **Unsigned**. (Critical — this lets uploads happen from the browser without a server.)
5. **Folder**: `ocsllc-website`.
6. Save.

### Step 4: Wire it up

Edit `admin-config.js`:

```js
window.OCS_CONFIG = {
    ...
    cloudinaryCloudName:    "your-cloud-name",
    cloudinaryUploadPreset: "ocsllc-website-uploads"
};
```

Commit. Now https://ocsllc.services/admin/upload/ accepts drag-and-drop photos straight from your phone or laptop.

### Step 5: First photo

1. Go to https://ocsllc.services/admin/upload/.
2. Drag a job photo in (or click to choose from camera roll).
3. It uploads to Cloudinary.
4. Within 24 hours the daily Cloudinary sync workflow pulls it into `/gallery/`.
5. To make it appear immediately: go to https://github.com/barrettteeney/ocsllc.services/actions/workflows/sync-cloudinary.yml → **Run workflow**.

---

## What you get

After both setups (~10 min), every job follows this loop automatically:

1. **Customer fills the form** → contact + deal in HubSpot, email backup, Bing notified.
2. **You take photos on the job** → upload at /admin/upload/ → in /gallery/ within hours.
3. **Customer leaves a Google review** → daily GBP sync picks it up → on the website within hours.
4. **You log the deal stage in HubSpot** → conversion data visible on mobile app, email reminders.

End-to-end: every customer interaction is captured in one place (HubSpot), every photo is in one place (Cloudinary, mirrored to your site), every review is on the public site automatically.

---

## Bookmark this

Save https://ocsllc.services/admin/ to your phone home screen. It's your one-stop dashboard with shortcuts to HubSpot, Cloudinary, GitHub, GBP, and everything else.
