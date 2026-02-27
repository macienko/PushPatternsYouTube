# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "google-auth-oauthlib>=1.2.1",
# ]
# ///
"""One-time local script to obtain a Google OAuth2 refresh token.

Run this on your local machine (NOT on Railway):

    uv run setup_auth.py

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project (or select an existing one)
  3. Enable the following APIs:
       - Google Drive API
       - YouTube Data API v3
  4. Go to "APIs & Services" - "Credentials" - "Create Credentials" - "OAuth client ID"
  5. Choose "Desktop app" as the application type
  6. Download the JSON file and save it as client_secret.json in this directory

After running this script, copy the printed values into your Railway environment variables.
"""

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CLIENT_SECRET_FILE = "client_secret.json"


def main():
    if not Path(CLIENT_SECRET_FILE).exists():
        print(f"ERROR: {CLIENT_SECRET_FILE} not found.")
        print("Download your OAuth2 Desktop client credentials from Google Cloud Console")
        print("and save them as client_secret.json in this directory.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("SUCCESS - copy these into Railway environment variables:")
    print("=" * 60)
    print(f"GOOGLE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 60)
    print("\nKeep these values secret. Never commit them to git.")

    # Also save locally for quick reference (gitignored)
    token_data = {
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
    }
    Path("token.json").write_text(json.dumps(token_data, indent=2))
    print("\nSaved to token.json (gitignored) for local use.")


if __name__ == "__main__":
    main()