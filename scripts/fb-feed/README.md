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

Full runbook: "DAS - Website FB Feed Runbook" in the DAS vault folder.

- **Schedule silently disabled**: GitHub auto-disables cron workflows in
  public repos after ~60 days without repository activity (the feed's own
  commits count, so this only bites after a long quiet stretch). Fix:
  Actions tab → Facebook feed refresh → Enable workflow.
- Workflow fails with `FB_PAGE_TOKEN is not set` — the secret is missing;
  restore it from 1Password ("das fb token").
- **Graph error 190** — the token was invalidated. Causes: page-admin's
  Facebook password changed, their page admin role removed, the app
  disconnected under Business integrations, the app/portfolio deleted, or
  a Meta checkpoint on the admin's profile. Re-mint: Explorer → generate
  user token with `pages_show_list` + `pages_read_engagement` → the
  [Access Token Tool](https://developers.facebook.com/tools/accesstoken/)
  lists it already long-lived (no app secret needed) → `GET /me/accounts`
  → copy the page's `access_token` (debugger should say type PAGE,
  expires Never) → update BOTH the Actions secret and 1Password.
- **Graph API version retired**: the script defaults to `v23.0`
  (retirement due around mid-2027). Bump the default in `fetch_feed.py`
  or set a `FB_GRAPH_VERSION` env in the workflow.
- **`fb-feed markers not found`** — someone deleted the
  `<!-- fb-feed:start/end -->` comments from `news/index.html`; restore
  them (see git history for placement).
- **Green run but stale site** — Netlify side; check the site's deploy
  log in the Netlify dashboard, then re-run the workflow.
- A push race with a human commit fails one run and self-heals the next
  night.
- A missing image never fails the run; the card just renders without a
  thumbnail.
- **Unwanted post showing**: hide/delete it on Facebook, then manually
  run the workflow (hidden posts are filtered out).
