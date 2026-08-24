# OCS LLC Pricing Model v5

Approved by Barrett Teeney. This document summarizes the live customer-estimate model. The executable source of truth is `lib/pricing/booking.ts` in the private OCS CRM repository.

## Standard services

- Inside + outside: $12 per individual piece of glass.
- One side, normally outside only: $7 per individual piece of glass.
- Screens: $4 each.
- Inside-only is not a standard service. If Barrett approves an exception, it uses the same one-side price as outside-only.

Customer-facing language says **pieces of glass**, not panes. Internal field names may retain `pane` for backward compatibility.

## Square-footage pricing through 8,000 sqft

Rates are flat across all eight 1,000-sqft guidance bands. The band controls only the pieces-of-glass guidance shown to the customer.

| Service | Fewer pieces | Average pieces | More pieces |
|---|---:|---:|---:|
| Inside + outside | $0.09/sqft | $0.12/sqft | $0.14/sqft |
| One side | $0.05/sqft | $0.07/sqft | $0.08/sqft |

| Home size | Fewer | Average | More |
|---|---:|---:|---:|
| Up to 1,000 sqft | 10 or fewer | 11–18 | 19 or more |
| 1,001–2,000 | 16 or fewer | 17–28 | 29 or more |
| 2,001–3,000 | 20 or fewer | 21–34 | 35 or more |
| 3,001–4,000 | 26 or fewer | 27–44 | 45 or more |
| 4,001–5,000 | 32 or fewer | 33–54 | 55 or more |
| 5,001–6,000 | 38 or fewer | 39–64 | 65 or more |
| 6,001–7,000 | 44 or fewer | 45–74 | 75 or more |
| 7,001–8,000 | 50 or fewer | 51–86 | 87 or more |

Homes above 8,000 sqft never auto-price and require custom confirmation from Barrett.

## Calculation order

1. Calculate the density-adjusted sqft path when sqft is known.
2. Calculate the exact glass-count path when a count is known.
3. Apply condition surcharges independently to each original path.
4. When both paths exist, blend them 50/50. Otherwise use the available path.
5. Add screens after the blend.
6. Enforce both the $150 trip minimum and the $125-per-expected-field-hour floor; the labor floor rounds up to the next $5.
7. Apply any recurring discount, without allowing the discounted price to break either floor.
8. Build the customer range at ±15%, rounded to the nearest $5, with a $25 minimum spread and a $150 minimum low end.

## Additive condition surcharges

- Two or more stories: +10%.
- Hard water or sprinkler spots: +20%.
- Last cleaned five or more years ago, or never: +15%.
- Post-construction cleanup: +25%.

Each percentage is calculated against the original base. Surcharges add; they do not compound.

Divided-light glass does not change the automatic total. It creates an internal review flag for Barrett.

## Recurring per-visit discounts

- One-time: 0%.
- Twice yearly: 10%.
- Three times yearly: 15%.
- Quarterly: 20%.

The $150 trip minimum and $125-per-expected-field-hour floor remain in force after a discount.

## Field pace and scheduling

- Inside + outside: 5 minutes total per piece of glass (2.5 minutes per side).
- One side: 2.5 minutes per piece of glass.
- Screens: 1.5 minutes each.
- Appointment duration: 30 minutes per $62.50, always rounded upward.
- Estimates of $1,000 or more reserve the full 9:30 AM–7:00 PM workday and show that the work may require more than one day.

## Verification requirement

The CRM tests must cover every density, guidance band, required boundary, surcharge combination, trip minimum, labor floor, customer range, recurring plan, and duration rule. `scripts/check-pricing-parity.mjs` must pass against every website calculator copy before deployment.
