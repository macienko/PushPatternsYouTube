import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID     = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]

SOURCE_DRIVE_FOLDER_ID          = os.environ["SOURCE_DRIVE_FOLDER_ID"]
CAPTIONS_DRIVE_FOLDER_ID        = os.environ["CAPTIONS_DRIVE_FOLDER_ID"]
COMMUNITY_POSTS_DRIVE_FOLDER_ID = os.environ["COMMUNITY_POSTS_DRIVE_FOLDER_ID"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_PROMPT  = os.getenv(
    "OPENAI_PROMPT",
    "Create a captivating and engaging community post that teases our upcoming video without "
    "giving away too much detail. The post should generate excitement and anticipation among "
    "our audience of Ableton Live electronic music producers, 30 - 50 years old males. "
    "Use the context from the video script provided below.",
)

POLL_INTERVAL_MINUTES          = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))
CAPTION_CHECK_INTERVAL_MINUTES = int(os.getenv("CAPTION_CHECK_INTERVAL_MINUTES", "15"))
CAPTION_MAX_WAIT_HOURS         = int(os.getenv("CAPTION_MAX_WAIT_HOURS", "48"))

# Railway injects DATABASE_URL with postgres:// prefix; psycopg2 needs postgresql://
_raw_db_url = os.environ["DATABASE_URL"]
DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql://", 1)

PORT = int(os.getenv("PORT", "8080"))
