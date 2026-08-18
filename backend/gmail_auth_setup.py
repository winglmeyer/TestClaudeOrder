"""One-time interactive script to authorize the Order Enquiry Gmail integration.

Run this once, locally, on a machine with a browser. It opens a Google
consent screen; on approval it prints a refresh token to store as
GOOGLE_REFRESH_TOKEN in backend/.env (or wherever email_watcher.py runs) —
after that, email_watcher.py never needs interactive login again.

Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (from the OAuth client
created in Google Cloud Console -> APIs & Services -> Credentials) already
set as environment variables.

If that OAuth client is a "Web application" type, add
http://localhost:8080/ to its Authorized redirect URIs first. A "Desktop
app" type client needs no extra configuration.

Usage:
  cd backend
  python gmail_auth_setup.py
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def main() -> None:
    client_config = {
        "installed": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080)

    print("\nAuthorization complete. Add this to backend/.env:\n")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
