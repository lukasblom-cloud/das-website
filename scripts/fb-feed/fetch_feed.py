#!/usr/bin/env python3
"""Refresh the Facebook feed section on the DAS News page.

Pulls the latest posts from the DAS Facebook page via the Graph API,
downloads post images into images/fb/, and rewrites the block between
the <!-- fb-feed:start --> / <!-- fb-feed:end --> markers in
news/index.html as static, on-brand news cards. No client-side
Facebook code is ever served.

Run by .github/workflows/fb-feed.yml on a daily schedule. Can also be
run locally:

    FB_PAGE_TOKEN=... python3 scripts/fb-feed/fetch_feed.py
    python3 scripts/fb-feed/fetch_feed.py --sample   # fixture data, no token

Environment:
    FB_PAGE_TOKEN     required (long-lived Page access token)
    FB_PAGE_ID        default: DisabilityAdvocacyCentralAustralia
    FB_GRAPH_VERSION  default: v23.0
    FB_POST_COUNT     default: 6
"""

import argparse
import hashlib
import html
import json
import re
import sys
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[2]
NEWS_PAGE = SITE_ROOT / "news" / "index.html"
IMG_DIR = SITE_ROOT / "images" / "fb"
JSON_OUT = SITE_ROOT / "news" / "fb-feed.json"
SAMPLE_FILE = Path(__file__).parent / "sample-feed.json"

PAGE_ID = os.environ.get("FB_PAGE_ID") or "DisabilityAdvocacyCentralAustralia"
GRAPH_VERSION = os.environ.get("FB_GRAPH_VERSION") or "v23.0"
POST_COUNT = int(os.environ.get("FB_POST_COUNT") or 6)

MARKER_RE = re.compile(r"(<!-- fb-feed:start -->)(.*?)(<!-- fb-feed:end -->)", re.S)
# NT has no daylight saving; ACST is a fixed offset.
ACST = timedelta(hours=9, minutes=30)
MAX_CHARS = 240

FALLBACK_HTML = """
        <div class="panel" style="max-width:720px;">
          <h3>Posts are on their way</h3>
          <p>Recent posts from our Facebook page will appear here.</p>
        </div>
"""


def graph_get(path, params):
    params = dict(params, access_token=os.environ["FB_PAGE_TOKEN"])
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e)["error"]
            sys.exit(f"Graph API error {err.get('code')}: {err.get('message')}")
        except (ValueError, KeyError):
            sys.exit(f"Graph API HTTP {e.code} on {path}")
    return body


def fetch_posts():
    data = graph_get(
        f"{PAGE_ID}/posts",
        {
            "fields": "message,created_time,permalink_url,full_picture,is_hidden",
            "limit": 25,
        },
    ).get("data", [])
    posts = [
        p for p in data
        if not p.get("is_hidden") and (p.get("message") or p.get("full_picture"))
    ]
    return posts[:POST_COUNT]


def download_image(post):
    """Save the post's picture locally (Facebook CDN URLs expire).

    Returns the site-relative src for news/index.html, or None.
    """
    url = post.get("full_picture")
    if not url:
        return None
    stem = hashlib.sha1(post["id"].encode()).hexdigest()[:12]
    ext = {"image/png": ".png", "image/webp": ".webp"}
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            suffix = ext.get(resp.headers.get_content_type(), ".jpg")
            dest = IMG_DIR / f"{stem}{suffix}"
            dest.write_bytes(resp.read())
    except Exception as e:  # a missing thumb should never sink the run
        print(f"  ! image skipped for {post['id']}: {e}", file=sys.stderr)
        return None
    return f"../images/fb/{dest.name}"


def prune_images(keep):
    """Drop previously downloaded post images that are no longer in the feed."""
    if not IMG_DIR.is_dir():
        return
    keep_names = {Path(src).name for src in keep if src and src.startswith("../images/fb/")}
    for f in IMG_DIR.iterdir():
        if f.is_file() and f.name != ".gitkeep" and f.name not in keep_names:
            f.unlink()


def display_date(created_time):
    dt = datetime.fromisoformat(created_time.replace("+0000", "+00:00")) + ACST
    return f"{dt.day} {dt.strftime('%B %Y')}"


def excerpt(message):
    text = " ".join((message or "").split())
    if len(text) <= MAX_CHARS:
        return text
    return text[:MAX_CHARS].rsplit(" ", 1)[0].rstrip(".,;:!") + "…"


def render_card(post, img_src):
    date = display_date(post["created_time"])
    text = excerpt(post.get("message")) or "See this post on Facebook."
    thumb = (
        f'<div class="thumb"><img src="{html.escape(img_src)}" alt="" loading="lazy"></div>'
        if img_src else ""
    )
    return f"""          <a class="news-card" href="{html.escape(post["permalink_url"])}" target="_blank" rel="noopener">
            {thumb}
            <div class="body">
              <span class="date">{date}</span>
              <p>{html.escape(text)}</p>
              <span class="more">View on Facebook</span>
            </div>
          </a>"""


def render_block(cards):
    if not cards:
        return FALLBACK_HTML
    return "\n        <div class=\"news-grid\">\n" + "\n".join(cards) + "\n        </div>\n"


def inject(block):
    page = NEWS_PAGE.read_text()
    if not MARKER_RE.search(page):
        sys.exit(f"fb-feed markers not found in {NEWS_PAGE}")
    page = MARKER_RE.sub(lambda m: m.group(1) + block + "        " + m.group(3), page, count=1)
    NEWS_PAGE.write_text(page)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", action="store_true",
                    help="render fixture posts from sample-feed.json (no token, no downloads)")
    args = ap.parse_args()

    if args.sample:
        posts = json.loads(SAMPLE_FILE.read_text())
        pairs = [(p, p.get("local_image")) for p in posts]
    else:
        if not os.environ.get("FB_PAGE_TOKEN"):
            sys.exit("FB_PAGE_TOKEN is not set (see scripts/fb-feed/README.md)")
        posts = fetch_posts()
        pairs = [(p, download_image(p)) for p in posts]
        prune_images([img for _, img in pairs])
        JSON_OUT.write_text(json.dumps(
            [dict(p, image=img) for p, img in pairs], indent=2) + "\n")

    inject(render_block([render_card(p, img) for p, img in pairs]))
    print(f"Rendered {len(pairs)} post(s) into {NEWS_PAGE.relative_to(SITE_ROOT)}")


if __name__ == "__main__":
    main()
