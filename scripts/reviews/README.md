# Google reviews feed

Nightly pull of the DAS Google Business Profile reviews into the home page.
Same shape as `scripts/fb-feed/`: a GitHub Action runs a stdlib-only Python
script, the script rewrites a marker block in the committed HTML, and the
commit to `main` triggers the normal Netlify deploy. Nothing Google-owned is
served to visitors — no widget, no client-side script, no reviewer photos.

| Piece | Path |
| --- | --- |
| Fetch + render | `scripts/reviews/fetch_reviews.py` |
| One-time token minting | `scripts/reviews/mint_refresh_token.py` |
| Fixture for `--sample` | `scripts/reviews/sample-reviews.json` |
| Schedule | `.github/workflows/reviews.yml` (06:15 ACST daily) |
| Render target | `index.html`, between `<!-- reviews:start -->` / `<!-- reviews:end -->` |
| Machine-readable copy | `reviews.json` (repo root) |

Edits inside the marker block are overwritten on the next run. Change the
renderer in `fetch_reviews.py`, not the generated markup.

## Why this is not the Places API

The Places API needs no approval but returns **at most 5** reviews, with no
paging or sorting, and its terms cap caching at 30 days. The Business Profile
API returns every review, is free, and also allows replying. The cost is an
access-approval gate — see below.

## Setup, in order

### 1. Request API access (this is the long pole)

A new Google Cloud project has **zero quota** on the Business Profile APIs
until Google approves a written request. Budget 2–4 weeks.

1. Create (or reuse) a Google Cloud project.
2. Enable these APIs on it:
   - `mybusinessaccountmanagement.googleapis.com`
   - `mybusinessbusinessinformation.googleapis.com`
   - `mybusiness.googleapis.com` — the v4 endpoint reviews live on. It does
     not appear in the API Library until access is granted.
3. Submit the Business Profile API access request form, choosing
   *Application for Basic API Access*. It asks for the GCP project number,
   the business website, and how the data will be used. "Displaying our own
   Google reviews on das.org.au, refreshed nightly, server-side" is the
   accurate answer.
4. Google replies to the requesting account. Approval is silent in the
   console — the sign is that the v4 API stops returning 403.

Requirements Google checks: a verified profile active 60+ days, complete
profile information, and a working website on the listing.

### 2. Create the OAuth client

In the same project, *APIs & Services → Credentials → Create credentials →
OAuth client ID → Desktop app*. Note the client ID and secret.

The consent screen needs the scope
`https://www.googleapis.com/auth/business.manage`. While the app is in
*Testing*, add the profile-owning Google account as a test user, and note
that refresh tokens expire after 7 days in that state — publish the app
(internal or in production) before relying on the nightly run.

### 3. Mint the refresh token

Run locally, signed in as an account that owns or manages the DAS profile:

```
GBP_CLIENT_ID=... GBP_CLIENT_SECRET=... python3 scripts/reviews/mint_refresh_token.py
```

It opens the consent screen, catches the loopback redirect, and prints the
refresh token. File a copy in the 1Password **Automation** vault.

### 4. Find the account and location ids

```
GBP_CLIENT_ID=... GBP_CLIENT_SECRET=... GBP_REFRESH_TOKEN=... \
  python3 scripts/reviews/fetch_reviews.py --list-locations
```

### 5. Add the repo settings

Actions **secrets**:

| Name | Value |
| --- | --- |
| `GBP_CLIENT_ID` | OAuth client id |
| `GBP_CLIENT_SECRET` | OAuth client secret |
| `GBP_REFRESH_TOKEN` | from step 3 |

Actions **variables**:

| Name | Value |
| --- | --- |
| `GBP_ACCOUNT_ID` | digits from step 4 |
| `GBP_LOCATION_ID` | digits from step 4 |
| `GBP_REVIEWS_URL` | the "read them on Google" link target |

Then run the workflow once via *Actions → Google reviews refresh → Run
workflow* to confirm it commits a real render.

## Local use

```
python3 scripts/reviews/fetch_reviews.py --sample          # fixture, no token
python3 scripts/reviews/fetch_reviews.py --list-locations  # ids
python3 scripts/reviews/fetch_reviews.py                   # live render
```

## Tuning

| Variable | Default | Effect |
| --- | --- | --- |
| `GBP_MIN_STARS` | `4` | reviews below this are not rendered |
| `GBP_REVIEW_COUNT` | `6` | cards rendered |

`GBP_MIN_STARS` is a display filter, not moderation — the reviews stay public
on Google either way. Set it to `1` to show everything.

## When it breaks

- **403 from the v4 API** — the access request is not approved yet, or the
  approval was granted to a different GCP project.
- **`invalid_grant` on token refresh** — the refresh token was revoked by a
  password change, by 6 months of disuse, or by the 7-day expiry that applies
  while the OAuth app is still in *Testing*. Re-run `mint_refresh_token.py`.
- **Markers not found** — someone removed the comment pair from `index.html`.
- **Empty block** — no review cleared `GBP_MIN_STARS`; the fallback copy shows
  instead of an empty grid.
