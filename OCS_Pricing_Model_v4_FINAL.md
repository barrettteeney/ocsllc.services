# OCS LLC — Complete Pricing Algorithm (v4)

**Status:** Live as of May 2026. Reflects exactly what the booking form at `ocsllc.services` (homepage form + `/estimate/` page) calculates on the customer's screen.

**Where this lives in code:** `index.html` and `estimate/index.html`, inside the embedded quote-form `<script>` blocks. Constants are at the top of the IIFE; calculation flow is in `compute()`.

---

## 1. Sqft method — Interior + Exterior

| Tier | Home size | Rate per sqft |
|------|-----------|---------------|
| 1 | ≤ 1,000 sqft | $0.15 |
| 2 | 1,001 – 2,000 sqft | $0.17 |
| 3 | 2,001 – 3,000 sqft | $0.19 |
| 4 | 3,001 – 4,000 sqft | $0.21 |
| 5 | 4,001 – 5,000 sqft | $0.23 |
| 6 | 5,001 – 6,000 sqft | $0.25 |
| — | Over 6,000 sqft | In-person quote required (form blocks online booking and shows call/text CTAs) |

## 2. Sqft method — Exterior Only

| Tier | Home size | Rate per sqft |
|------|-----------|---------------|
| 1 | ≤ 1,000 sqft | $0.09 |
| 2 | 1,001 – 2,000 sqft | $0.10 |
| 3 | 2,001 – 3,000 sqft | $0.11 |
| 4 | 3,001 – 4,000 sqft | $0.13 |
| 5 | 4,001 – 5,000 sqft | $0.14 |
| 6 | 5,001 – 6,000 sqft | $0.15 |

## 3. Per-pane flat rates (alternate measurement method)

| Service | Rate per pane |
|---------|---------------|
| Exterior only | $8 |
| Interior + Exterior | $14 |

Customer counts individual panes of glass. A double-hung counts as 2, triple-pane as 3, sliding-glass door as 2, fixed picture window as 1.

## 4. Percentage surcharges (applied to base, NOT compounded)

Each surcharge multiplies against the **original base**, not the running total. They stack additively, not multiplicatively.

| Trigger | Surcharge |
|---------|-----------|
| 2 or more stories | +10% of base |
| Hard water (Yes / No) | +20% of base |
| Last cleaned 5+ years ago (or never cleaned with no construction clean) | +15% of base |
| Post-construction cleanup (paint, stucco, debris, sticker residue) | +25% of base |

**Stacking example:** 2-story + hard water = +10% + +20% = **+30% of base** total. NOT 32% (1.10 × 1.20).

## 5. Flat add-ons (applied after percentage surcharges)

| Item | Cost |
|------|------|
| Screens (if customer says "Yes" to the screens question) | $4 × screen count |
| French / divided-light panes | **Flagged Yes/No only — not auto-priced.** Manual review on intake at **$2 per pane** ($8 per side per 4 panes, inside or outside, no bundle discount). |

### Why French panes are flagged, not auto-priced

The customer-facing form asks **"Do you have French / divided-light windows? Yes / No"** — no count. Because divided-light pane counts vary wildly (a single window can have 6, 9, 12, or 15 individual panes), and most homeowners don't know the count, asking would either produce inaccurate data or scare customers off. Instead:

- Customer answers Yes or No.
- If **No** → nothing added, nothing flagged.
- If **Yes** → the submission email to Barrett includes a clear **"REVIEW: price may need adjustment depending on divided pane count"** flag so he knows to confirm the divided pane count during the on-site visit and adjust accordingly.
- The rate Barrett applies manually: **$2 per individual French pane** (equivalent to $8 per side for every 4 panes, no bundle pricing for inside+outside).

## 6. Floors and rounding rules

- **Minimum charge:** $150. Any calculated total below this rounds up to $150.
- **Customer-facing range:** ±15% of the calculated total, rounded to nearest $5, with a minimum spread of $25. Low end can never go below $150.
- **No price is shown to the customer until they commit to a booking time** — the form gates the price reveal behind the HCP scheduler modal.

## 7. Averaging (when customer enters both sqft AND pane count)

If a customer measures their home both ways (sqft + pane count), the form computes both estimates separately, then averages them before applying screens. This produces a more accurate range for tricky homes (lots of glass for the sqft, or unusually little glass for the sqft).

```
avg_total = (sqft_path_total + panes_path_total) / 2 + screens_fee
```

## 8. Time-slot duration estimate

The form translates the calculated total into appointment duration to drive the booking widget's time-slot picker:

- **30 minutes per $62.50 of estimate**, rounded to nearest $62.50 increment
- Minimum 30 minutes
- Anything ≥ 8 hours (≥ $1,000 estimate) flags as a **full-day job** with the multi-day disclaimer
- Below 8 hours, the customer picks a start time between 9:30 AM and "latest possible start to finish by 7 PM"

---

## 9. The complete formula, step by step

```
STEP 1 — PICK A BASE
  if method == sqft:
      base = home_sqft × tier_rate[service][tier]
  if method == panes:
      base = pane_count × pane_rate[service]

STEP 2 — APPLY % SURCHARGES (each against original base, stacked additively)
  surcharge_total = 0
  if stories >= 2:                       surcharge_total += base × 0.10
  if hard_water == "yes":                surcharge_total += base × 0.20
  if last_cleaned_5+yrs:                 surcharge_total += base × 0.15
  if post_construction == "yes":         surcharge_total += base × 0.25

  primary_total = base + surcharge_total

STEP 3 — (RESERVED — no flat add-ons here; French panes are flagged only,
          not auto-priced; screens added in step 5)

STEP 4 — IF AVERAGING, REPEAT 1–2 FOR SECONDARY MEASUREMENT, THEN AVERAGE
  if customer entered both sqft AND pane_count:
      total = (primary_total + secondary_total) / 2
  else:
      total = primary_total

STEP 5 — ADD SCREENS SURCHARGE (after averaging, before min-charge floor)
  if wants_screens == "yes":
      total += screen_count × $4

STEP 6 — APPLY MINIMUM CHARGE FLOOR
  if total < $150:
      total = $150

STEP 7 — DERIVE CUSTOMER-FACING RANGE
  low  = round_to_$5( total × 0.85 )
  high = round_to_$5( total × 1.15 )
  if low < $150: low = $150
  if high - low < $25: high = low + $25

NOTE: French panes are NOT in the calculation. They are captured as
a Yes/No flag and surfaced in the submission email so Barrett can
adjust the booking price manually at $2/pane after counting on-site.
```

---

## 10. Worked examples

### Example A — 2-story home, 2,816 sqft, hard water, no screens, Interior + Exterior

```
Step 1 — Base:
  2,816 sqft → Tier 3 → $0.19/sqft (Interior + Exterior)
  base = 2,816 × $0.19 = $535.04

Step 2 — Surcharges (% against base):
  2-story:    $535.04 × 0.10 = $53.50
  Hard water: $535.04 × 0.20 = $107.01
  surcharge_total = $160.51
  primary_total   = $535.04 + $160.51 = $695.55

Step 3 — (No flat add-ons in this step.)
Step 4 — No averaging.
Step 5 — No screens.
Step 6 — Above $150 minimum.

Step 7 — Range:
  low  = round_to_$5($695.55 × 0.85) = $590
  high = round_to_$5($695.55 × 1.15) = $800

CUSTOMER SEES:        "$590 – $800"
INTERNAL CALCULATION: $695.55
```

### Example B — Real job: 2,328 sqft, Exterior only, 15 screens, no surcharges

```
Step 1: 2,328 × $0.11 = $256.08
Step 2: no surcharges → primary_total = $256.08
Step 3: no flat add-ons here
Step 4: no averaging
Step 5: screens → +15 × $4 = +$60 → total = $316.08
Step 6: above minimum
Step 7: range = $270 – $365

CUSTOMER SEES:        "$270 – $365"
INTERNAL CALCULATION: $316.08
```

### Example C — Single-story, 2,816 sqft, hard water only, Interior + Exterior

```
Base:       2,816 × $0.19 = $535.04
Hard water: $535.04 × 0.20 = $107.01
Total:      $642.05
Range:      $545 – $740
```

### Example D — Same home as C but Exterior only with screens

```
Base:       2,816 × $0.11 = $309.76
Hard water: $309.76 × 0.20 = $61.95
Subtotal:   $371.71
Screens:    +15 × $4 = $60
Total:      $431.71
Range:      $365 – $495
```

---

## 11. Constants reference (exact values from the live form)

```javascript
const SQFT_TIERS = [
  {max:1000, both:0.15, ext:0.09},   // Tier 1
  {max:2000, both:0.17, ext:0.10},   // Tier 2
  {max:3000, both:0.19, ext:0.11},   // Tier 3
  {max:4000, both:0.21, ext:0.13},   // Tier 4
  {max:5000, both:0.23, ext:0.14},   // Tier 5
  {max:6000, both:0.25, ext:0.15}    // Tier 6
];

const PER_PANE        = {ext: 8, both: 14, screen: 4};
const HW_PCT          = {none: 0, yes: 0.20};
const HW_LABEL        = {none: 'No', yes: 'Yes'};
const MIN_CHARGE      = 150;
// NOTE: No FRENCH_PANE_FEE constant — French panes are intentionally not
// auto-priced. The customer answers Yes/No; if Yes, the submission email
// flags it for Barrett to adjust manually at $2/pane on the booking.

// Surcharges (hardcoded in applySurcharges())
STORIES_2_PLUS    = 0.10
LAST_CLEANED_5YR  = 0.15
POST_CONSTRUCTION = 0.25

// Range derivation
RANGE_LOW_MULT  = 0.85   // 15% below calculated total
RANGE_HIGH_MULT = 1.15   // 15% above calculated total
ROUND_TO        = 5      // round both ends to nearest $5
MIN_SPREAD      = 25     // ensure at least $25 between low and high

// Time-slot duration
MIN_PER_INCREMENT = 30   // 30 min per $62.50 increment
INCREMENT_DOLLARS = 62.5
FULL_DAY_THRESHOLD_MIN = 480   // ≥ 8 hours flags as full-day
```

---

## 12. What changed from v3

| Change | v3 (old) | v4 (current) |
|--------|----------|--------------|
| Hard water tiers | Light +15%, Moderate +25%, Heavy +40% | **Single Yes/No: +20%** |
| Post-construction | +30% | **+25%** |
| Screens (per-pane flow only) | $2/screen, baked into base | **$4/screen, global Yes/No question, applied as flat add-on** |
| Screens question | Implicit (per-pane only) | **Explicit Yes/No on Step 1, applies to both sqft and per-pane flows** |
| 2-story | +10% | +10% (unchanged) |
| Never cleaned 5+ yrs | +15% | +15% (unchanged) |
| French panes | $5/pane, auto-calculated in form (customer entered count) | **Yes/No flag only; manual review at $2/pane** ($8/side per 4 panes, no bundle pricing) |
| Minimum charge | $150 | $150 (unchanged) |

---

## 13. Notes for future updates

- Sqft tiers, per-pane rates, screen rate, and all surcharge percentages live in 2 places: `index.html` (homepage form) and `estimate/index.html` (standalone form). Both files must be edited in sync.
- The submission email (FormSubmit.co) captures every input plus the calculated quote and customer-facing range, so you always have a full record of what the customer saw vs. what the math produced.
- HCP's service duration is fixed per-service (Basic plan limitation) — the form's per-job duration math is advisory to the customer only, not enforced by HCP's scheduler.
- If you want to change the customer-facing range width (currently ±15%), edit `priceRange()` in both files.
- If you want to change the duration mapping (currently 30 min per $62.50), edit `minutesFromQuote()` in both files.
