import config
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_credentials() -> Credentials:
    """Build Google OAuth2 credentials from env vars (refresh token approach).

    The access token is None initially; the Google client library will
    automatically call the token endpoint to obtain a fresh access token
    using the refresh token when the first API call is made.
    """
    return Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ],
    )


def build_drive_service():
    return build("drive", "v3", credentials=get_credentials())


def build_youtube_service():
    return build("youtube", "v3", credentials=get_credentials())
