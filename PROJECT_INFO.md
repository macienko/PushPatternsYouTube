# PushPatternsYouTube

Automated pipeline that watches a Google Drive folder for new video uploads, publishes them to YouTube as private drafts, then downloads the auto-generated captions and saves them as SRT files in a second Drive folder.

---

## Architecture

```
Railway (web service)
  Gunicorn → Flask (app.py)
    ├── GET /health     Railway health check
    ├── GET /status     JSON pipeline summary
    └── APScheduler (BackgroundScheduler)
         ├── scan_drive()    every POLL_INTERVAL_MINUTES (default 5m)
         └── check_captions() every CAPTION_CHECK_INTERVAL_MINUTES (default 15m)

PostgreSQL (Railway add-on)
  videos table — tracks each video through the pipeline
```

### Video State Machine

```
discovered → uploading → uploaded → captions_downloading → done
                                                         ↘ failed
```

| State                 | Meaning                                          |
|-----------------------|--------------------------------------------------|
| `discovered`          | Found in Drive, upload queued                    |
| `uploading`           | YouTube upload in progress                       |
| `uploaded`            | On YouTube (private), waiting for ASR captions   |
| `captions_downloading`| Downloading captions from YouTube                |
| `done`                | SRT saved to Drive captions folder               |
| `failed`              | Error — see `error_message` column               |

---

## Files

| File             | Purpose                                               |
|------------------|-------------------------------------------------------|
| `app.py`         | Flask app + APScheduler background jobs               |
| `drive.py`       | Drive API: list, download, upload                     |
| `youtube.py`     | YouTube API: upload video, check/download captions    |
| `db.py`          | PostgreSQL state management                           |
| `auth.py`        | Google credentials from env vars (refresh token)      |
| `config.py`      | Environment variable loading                          |
| `setup_auth.py`  | **LOCAL ONLY** — OAuth2 consent flow                  |
| `Procfile`       | Railway/Gunicorn startup command                      |

---

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable these APIs:
   - **Google Drive API**
   - **YouTube Data API v3**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. Choose **Desktop app**, download the JSON, save as `client_secret.json` in this directory

### 2. Get OAuth2 Tokens (local, one-time)

```bash
uv run setup_auth.py
```

A browser window will open. Sign in with the Google account that owns the YouTube channel and has access to the Drive folders. Copy the printed `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`.

### 3. Prepare Drive Folders

1. Create two Drive folders: one for source videos, one for captions
2. Copy their IDs from the URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`

### 4. Local Development

```bash
cp .env.example .env
# Fill in all values in .env

pip install -r requirements.txt

# Start a local PostgreSQL database and set DATABASE_URL in .env, then:
flask run
```

Visit `http://localhost:5000/health` and `http://localhost:5000/status`.

### 5. Railway Deployment

1. Push this directory to a GitHub repository
2. Create a new Railway project from the repo
3. Add a **PostgreSQL** add-on — Railway sets `DATABASE_URL` automatically
4. Set all environment variables from `.env.example` in Railway's Variables panel
5. Railway will detect the `Procfile` and deploy automatically

---

## Environment Variables

| Variable                      | Required | Default | Description                                   |
|-------------------------------|----------|---------|-----------------------------------------------|
| `GOOGLE_CLIENT_ID`            | Yes      | —       | OAuth2 client ID                              |
| `GOOGLE_CLIENT_SECRET`        | Yes      | —       | OAuth2 client secret                          |
| `GOOGLE_REFRESH_TOKEN`        | Yes      | —       | OAuth2 refresh token (from setup_auth.py)     |
| `SOURCE_DRIVE_FOLDER_ID`      | Yes      | —       | Drive folder to watch for new videos          |
| `CAPTIONS_DRIVE_FOLDER_ID`    | Yes      | —       | Drive folder to save .srt files               |
| `DATABASE_URL`                | Yes      | —       | PostgreSQL URL (Railway provides this)        |
| `POLL_INTERVAL_MINUTES`       | No       | `5`     | Drive scan frequency                          |
| `CAPTION_CHECK_INTERVAL_MINUTES` | No    | `15`    | YouTube caption check frequency               |
| `CAPTION_MAX_WAIT_HOURS`      | No       | `48`    | Hours before giving up on captions            |
| `PORT`                        | No       | `8080`  | HTTP port (Railway provides this)             |

---

## API Endpoints

### `GET /health`
```json
{"status": "ok", "timestamp": "2024-01-15T10:30:00+00:00"}
```

### `GET /status`
```json
{
  "counts": {
    "discovered": 0,
    "uploading": 0,
    "uploaded": 2,
    "done": 14,
    "failed": 1
  },
  "recent": [
    {
      "drive_filename": "tutorial_part1.mp4",
      "state": "done",
      "youtube_video_id": "abc123xyz",
      "error_message": null,
      "updated_at": "2024-01-15T10:28:00+00:00"
    }
  ]
}
```

---

## Notes

- **YouTube upload quota**: ~1,600 units per video upload (default quota: 10,000/day). ~6 uploads per day maximum on a fresh project. Request a quota increase in Google Cloud Console if needed.
- **ASR caption timing**: Usually 10 minutes to a few hours after upload. Videos with no speech or non-English audio may not get ASR captions — they will be marked `failed` after `CAPTION_MAX_WAIT_HOURS`.
- **Gunicorn workers**: Must use `--workers 1` to avoid running APScheduler in multiple processes.
- **Large videos**: Files are downloaded into memory. For videos >500MB, Railway's memory limit may be reached. Contact support or switch to a higher-memory plan if needed.
