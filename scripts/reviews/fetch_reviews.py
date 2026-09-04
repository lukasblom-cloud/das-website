#!/usr/bin/env python3
"""Refresh the Google reviews block on the DAS home page.

Pulls reviews for the DAS Google Business Profile via the Business
Profile API (v4) and rewrites the block between the
<!-- reviews:start --> / <!-- reviews:end --> markers in index.html as
static, on-brand review cards. No client-side Google code is ever
served and no reviewer photos are stored.

Run by .github/workflows/reviews.yml on a daily schedule. Can also be
run locally:

    GBP_REFRESH_TOKEN=... python3 scripts/reviews/fetch_reviews.py
    python3 scripts/reviews/fetch_reviews.py --sample      # fixture data, no token
    python3 scripts/reviews/fetch_reviews.py --list-locations

--list-locations prints the account and location ids you need for
GBP_ACCOUNT_ID / GBP_LOCATION_ID. See scripts/reviews/README.md.

Environment:
    GBP_CLIENT_ID       required (OAuth client id)
    GBP_CLIENT_SECRET   required (OAuth client secret)
    GBP_REFRESH_TOKEN   required (see README — minted once, offline access)
    GBP_ACCOUNT_ID      required (digits only, e.g. 123456789)
    GBP_LOCATION_ID     required (digits only, e.g. 987654321)
    GBP_REVIEWS_URL     "read all reviews" link target
    GBP_MIN_STARS       default: 4   (reviews below this are not shown)
    GBP_REVIEW_COUNT    default: 6   (cards rendered)
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[2]
HOME_PAGE = SITE_ROOT / "index.html"
JSON_OUT = SITE_ROOT / "reviews.json"
SAMPLE_FILE = Path(__file__).parent / "sample-reviews.json"

MIN_STARS = int(os.environ.get("GBP_MIN_STARS") or 4)
REVIEW_COUNT = int(os.environ.get("GBP_REVIEW_COUNT") or 6)
REVIEWS_URL = os.environ.get("GBP_REVIEWS_URL") or "https://www.google.com/maps/search/?api=1&query=Disability+Advocacy+Service+Alice+Springs"

MARKER_RE = re.compile(r"(<!-- reviews:start -->)(.*?)(<!-- reviews:end -->)", re.S)
# NT has no daylight saving; ACST is a fixed offset.
ACST = timedelta(hours=9, minutes=30)
MAX_CHARS = 260

TOKEN_URL = "https://oauth2.googleapis.com/token"
REVIEWS_HOST = "https://mybusiness.googleapis.com/v4"
ACCOUNTS_HOST = "https://mybusinessaccountmanagement.googleapis.com/v1"
INFO_HOST = "https://mybusinessbusinessinformation.googleapis.com/v1"

STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}

FALLBACK_HTML = """
        <div class="reviews-empty">
          <p>Reviews from the people we work with will appear here.</p>
        </div>
"""


def require(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set (see scripts/reviews/README.md)")
    return value


def access_token():
    """Exchange the long-lived refresh token for a short-lived access token."""
    data = urllib.parse.urlencode({
        "client_id": require("GBP_CLIENT_ID"),
        "client_secret": require("GBP_CLIENT_SECRET"),
        "refresh_token": require("GBP_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }).encode()
    try:
        with urllib.request.urlopen(TOKEN_URL, data=data, timeout=30) as resp:
            return json.load(resp)["access_token"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        sys.exit(
            f"OAuth token refresh failed (HTTP {e.code}): {detail}\n"
            "A refresh token is revoked by a password change or by 6 months "
            "of disuse — re-mint it with mint_refresh_token.py."
        )


def api_get(url, token, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        if e.code == 403:
            sys.exit(
                f"Business Profile API returned 403.\n{detail}\n"
                "This is normally the access gate: the GCP project has zero "
                "quota until Google approves the API access request."
            )
        sys.exit(f"Business Profile API HTTP {e.code}: {detail}")


def list_locations():
    """Discovery helper — print account and location ids, then exit."""
    token = access_token()
    accounts = api_get(f"{ACCOUNTS_HOST}/accounts", token).get("accounts", [])
    if not accounts:
        sys.exit("No Business Profile accounts visible to this token.")
    for acct in accounts:
        acct_id = acct["name"].split("/")[-1]
        print(f"\naccount {acct_id}  {acct.get('accountName', '(unnamed)')}")
        locations = api_get(
            f"{INFO_HOST}/accounts/{acct_id}/locations", token,
            {"readMask": "name,title,storefrontAddress", "pageSize": 100},
        ).get("locations", [])
        for loc in locations:
            loc_id = loc["name"].split("/")[-1]
            city = (loc.get("storefrontAddress", {}).get("locality") or "").strip()
            print(f"  location {loc_id}  {loc.get('title', '(untitled)')}"
                  + (f"  — {city}" if city else ""))
    print("\nSet GBP_ACCOUNT_ID and GBP_LOCATION_ID to the pair you want.")


def fetch_reviews():
    """Return (reviews, average_rating, total_count) for the configured location."""
    token = access_token()
    account_id = require("GBP_ACCOUNT_ID")
    location_id = require("GBP_LOCATION_ID")
    url = f"{REVIEWS_HOST}/accounts/{account_id}/locations/{location_id}/reviews"

    reviews, average, total, page_token = [], None, None, None
    # One page is plenty for display, but paginate so the average and count
    # stay honest if the profile ever needs a full sweep.
    while True:
        params = {"pageSize": 50, "orderBy": "updateTime desc"}
        if page_token:
            params["pageToken"] = page_token
        body = api_get(url, token, params)
        if average is None:
            average = body.get("averageRating")
            total = body.get("totalReviewCount")
        reviews.extend(body.get("reviews", []))
        page_token = body.get("nextPageToken")
        if not page_token or len(reviews) >= 200:
            break

    shown = [
        r for r in reviews
        if STARS.get(r.get("starRating"), 0) >= MIN_STARS
        and (r.get("comment") or "").strip()
    ]
    return shown[:REVIEW_COUNT], average, total


def display_date(create_time):
    dt = datetime.fromisoformat(create_time.replace("Z", "+00:00")) + ACST
    return f"{dt.day} {dt.strftime('%B %Y')}"


def excerpt(comment):
    # The API returns the translated text after a "(Translated by Google)"
    # preamble; keep only the reviewer's original words where both appear.
    text = " ".join((comment or "").split())
    if "(Original)" in text:
        text = text.split("(Original)", 1)[1].strip()
    text = text.replace("(Translated by Google)", "").strip()
    if len(text) <= MAX_CHARS:
        return text
    return text[:MAX_CHARS].rsplit(" ", 1)[0].rstrip(".,;:!") + "…"


def render_card(review):
    stars = STARS.get(review.get("starRating"), 0)
    name = (review.get("reviewer", {}).get("displayName") or "A Google user").strip()
    text = excerpt(review.get("comment"))
    return f"""          <figure class="review-card">
            <div class="stars" role="img" aria-label="{stars} out of 5 stars">{"★" * stars}{"☆" * (5 - stars)}</div>
            <blockquote><p>{html.escape(text)}</p></blockquote>
            <figcaption>{html.escape(name)} <span class="date">{display_date(review["createTime"])}</span></figcaption>
          </figure>"""


def render_block(reviews, average, total):
    if not reviews:
        return FALLBACK_HTML
    summary = ""
    if average and total:
        summary = (
            f'        <p class="reviews-summary">'
            f'<strong>{average:.1f}</strong> out of 5 from {total} Google '
            f'review{"s" if total != 1 else ""} — '
            f'<a href="{html.escape(REVIEWS_URL)}" target="_blank" rel="noopener">read them on Google</a>'
            f"</p>\n"
        )
    cards = "\n".join(render_card(r) for r in reviews)
    return f'\n{summary}        <div class="reviews-grid">\n{cards}\n        </div>\n'


def inject(block):
    page = HOME_PAGE.read_text()
    if not MARKER_RE.search(page):
        sys.exit(f"reviews markers not found in {HOME_PAGE}")
    page = MARKER_RE.sub(lambda m: m.group(1) + block + "        " + m.group(3), page, count=1)
    HOME_PAGE.write_text(page)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", action="store_true",
                    help="render fixture reviews from sample-reviews.json (no token)")
    ap.add_argument("--list-locations", action="store_true",
                    help="print the account and location ids this token can see")
    args = ap.parse_args()

    if args.list_locations:
        list_locations()
        return

    if args.sample:
        fixture = json.loads(SAMPLE_FILE.read_text())
        reviews = fixture["reviews"][:REVIEW_COUNT]
        average, total = fixture.get("averageRating"), fixture.get("totalReviewCount")
    else:
        reviews, average, total = fetch_reviews()
        JSON_OUT.write_text(json.dumps(
            {"averageRating": average, "totalReviewCount": total, "reviews": reviews},
            indent=2) + "\n")

    inject(render_block(reviews, average, total))
    print(f"Rendered {len(reviews)} review(s) into {HOME_PAGE.relative_to(SITE_ROOT)}")


if __name__ == "__main__":
    main()
