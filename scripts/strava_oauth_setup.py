#!/usr/bin/env python3
"""Interactive Strava OAuth2 setup for mtb-mcp.

Run this script to obtain Strava API tokens:
  python scripts/strava_oauth_setup.py

Prerequisites:
  1. Create a Strava API application at https://strava.com/settings/api
  2. Set redirect URI to: http://localhost:3000/auth/callback
  3. Note your Client ID and Client Secret
"""

import webbrowser

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
REDIRECT_URI = "http://localhost:3000/auth/callback"
SCOPES = "read,read_all,activity:read,activity:read_all"


def main() -> None:
    """Guide user through OAuth setup."""
    print("=== Strava OAuth Setup for mtb-mcp ===\n")

    client_id = input("Enter your Strava Client ID: ").strip()
    client_secret = input("Enter your Strava Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Client ID and Secret are required.")
        return

    auth_url = (
        f"{AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
    )

    print(f"\nOpening browser for authorization...\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("After authorizing, you'll be redirected to a URL like:")
    print("  http://localhost:3000/auth/callback?code=XXXXX&scope=...")
    code = input("\nPaste the 'code' parameter from the URL: ").strip()

    if not code:
        print("Error: Authorization code is required.")
        return

    print("\nExchange this code for tokens by running:")
    print(f"""
curl -X POST {TOKEN_URL} \\
  -d client_id={client_id} \\
  -d client_secret={client_secret} \\
  -d code={code} \\
  -d grant_type=authorization_code

Then add to your .env:
  MTB_MCP_STRAVA_CLIENT_ID={client_id}
  MTB_MCP_STRAVA_CLIENT_SECRET={client_secret}
  MTB_MCP_STRAVA_ACCESS_TOKEN=<from response>
  MTB_MCP_STRAVA_REFRESH_TOKEN=<from response>
""")


if __name__ == "__main__":
    main()
