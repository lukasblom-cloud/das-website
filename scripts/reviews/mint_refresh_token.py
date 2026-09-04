#!/usr/bin/env python3
"""One-time helper: mint the Business Profile refresh token.

Run this locally, once, signed in as a Google account that owns or
manages the Business Profile. It opens the consent screen, catches the
redirect on a loopback port, and prints the refresh token to paste into
the GitHub Actions secret GBP_REFRESH_TOKEN (and into 1Password).

    GBP_CLIENT_ID=... GBP_CLIENT_SECRET=... python3 scripts/reviews/mint_refresh_token.py

The OAuth client must be of type "Desktop app", or a "Web application"
client with http://127.0.0.1:8765/ listed as an authorised redirect URI.
"""

import http.server
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

PORT = int(os.environ.get("GBP_OAUTH_PORT") or 8765)
REDIRECT_URI = f"http://127.0.0.1:{PORT}/"
SCOPE = "https://www.googleapis.com/auth/business.manage"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

received = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        received.update(urllib.parse.parse_qs(query))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = "code" in received
        self.wfile.write(
            b"<h2>Done - you can close this tab.</h2>" if ok
            else b"<h2>No code returned. Check the terminal.</h2>"
        )

    def log_message(self, *args):
        pass  # keep the terminal clean


def main():
    client_id = os.environ.get("GBP_CLIENT_ID")
    client_secret = os.environ.get("GBP_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit("Set GBP_CLIENT_ID and GBP_CLIENT_SECRET first.")

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",  # force a refresh token even on re-consent
    })
    url = f"{AUTH_URL}?{params}"
    print(f"Opening the consent screen. If nothing opens, visit:\n{url}\n")
    webbrowser.open(url)

    with http.server.HTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.handle_request()

    if "code" not in received:
        sys.exit(f"No authorisation code returned: {received}")

    data = urllib.parse.urlencode({
        "code": received["code"][0],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    try:
        with urllib.request.urlopen(TOKEN_URL, data=data, timeout=30) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"Token exchange failed (HTTP {e.code}): {e.read().decode('utf-8', 'replace')[:300]}")

    token = body.get("refresh_token")
    if not token:
        sys.exit("No refresh_token in the response. Revoke the app's access at "
                 "https://myaccount.google.com/permissions and run this again.")
    print("\nRefresh token (store in 1Password, then add as the GBP_REFRESH_TOKEN secret):\n")
    print(token)
    print("\nNext: python3 scripts/reviews/fetch_reviews.py --list-locations")


if __name__ == "__main__":
    main()
