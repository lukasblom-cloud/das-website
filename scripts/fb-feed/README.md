# Facebook feed → News page

Nightly pipeline that mirrors the latest posts from the DAS Facebook page
onto das.org.au/news/ as static, on-brand news cards.

Why not an embed: the official Page Plugin loads Meta trackers, renders
blank for visitors with tracking protection, and fails the site's WCAG AAA
bar. This pipeline serves plain HTML — no Facebook code touches visitors.

## How it works

1. `.github/workflows/fb-feed.yml` runs daily at 06:00 ACST (and on
   manual dispatch from the Actions tab).
2. `fetch_feed.py` pulls the latest posts via the Graph API, downloads
   post images into `images/fb/` (Facebook CDN URLs expire, so hotlinking
   is not an option), and rewrites the block between
   `<!-- fb-feed:start -->` / `<!-- fb-feed:end -->` in `news/index.html`.
3. If anything changed, the workflow commits to `main`, which triggers
   the normal Netlify deploy.

Local preview without a token:

```bash
python3 scripts/fb-feed/fetch_feed.py --sample
```

(renders fixture posts from `sample-feed.json` — don't commit the result).

## One-time setup (needs a DAS Page admin)

1. **Confirm the page.** The site links
   `facebook.com/DisabilityAdvocacyCentralAustralia`; an older
   `DisabilityAdvocacyServiceInc` page also exists. The feed defaults to
   the former — override with a `FB_PAGE_ID` repository variable if wrong.
2. **Create a Meta app** at <https://developers.facebook.com/apps/>
   (type: Business, or "Other" → Business). It never needs App Review —
   reading your own Page with an admin's token works in Development mode.
3. **Get a long-lived Page token:**
   1. In [Graph API Explorer](https://developers.facebook.com/tools/explorer/),
      select the app, then *Get Token → Get User Access Token* with the
      `pages_read_engagement` and `pages_show_list` permissions.
      Log in as a DAS Page admin.
   2. Exchange it for a long-lived user token:
      `GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-token}`
   3. With the long-lived user token, call `GET /me/accounts` and copy the
      `access_token` for the DAS page. Page tokens obtained from a
      long-lived user token do not expire (they die only if the admin
      changes their password, loses admin, or the app is removed).
4. **Store it:** repo → Settings → Secrets and variables → Actions →
   new secret `FB_PAGE_TOKEN`. Also file it in 1Password (Automation vault)
   so it can be re-added if the secret is ever rotated.
5. **Test:** Actions tab → *Facebook feed refresh* → Run workflow, then
   check the deploy preview of the resulting commit.

## Where things live (set up 2 Sep 2026)

- Meta app: **DAS Website Feed**, app ID `1083464360733368` — owned by the
  **Trilemma** business portfolio (`162338298995684`), which is purely the
  app's administrative container; it grants Trilemma no access to the DAS
  page. The token comes from Lukas's profile-level admin on the page.
- Facebook page: **DAS Disability Advocacy Service Central Australia**,
  page ID `150975168107356` (repo variable `FB_PAGE_ID` pins it).
- Token: never-expiring Page token in the `FB_PAGE_TOKEN` Actions secret,
  with a backup copy in 1Password (Automation vault → "das fb token").
  It dies only if Lukas's FB password changes, his page admin is removed,
  or the app is disconnected under the page's Business integrations.

## Failure modes

- Workflow fails with `FB_PAGE_TOKEN is not set` — the secret is missing.
- Graph error 190 — the token was invalidated (see 3.3 above); mint a new
  one the same way.
- A missing image never fails the run; the card just renders without a
  thumbnail.
