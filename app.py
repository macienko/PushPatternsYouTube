import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify

import config
import db
import drive
import gpt
import youtube

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Scheduler jobs
# ---------------------------------------------------------------------------

def scan_drive():
    """Discover new videos in the source Drive folder and upload them to YouTube."""
    log.info("scan_drive: starting")
    try:
        files = drive.list_videos(config.SOURCE_DRIVE_FOLDER_ID)
        log.info("scan_drive: found %d video(s) in Drive folder", len(files))
    except Exception as exc:
        log.error("scan_drive: failed to list Drive folder — %s", exc)
        return

    for f in files:
        file_id = f["id"]
        filename = f["name"]
        mime_type = f.get("mimeType", "video/mp4")

        current_state = db.upsert_video(file_id, filename)
        if current_state != "discovered":
            continue  # already being processed or done

        log.info("scan_drive: uploading '%s' to YouTube", filename)
        db.set_state(file_id, "uploading")
        try:
            video_bytes, resolved_mime = drive.download_video(file_id)
            youtube_id = youtube.upload_video(
                title=os.path.splitext(filename)[0],
                video_bytes=video_bytes,
                mime_type=resolved_mime or mime_type,
            )
            db.set_state(file_id, "uploaded", youtube_video_id=youtube_id)
            log.info("scan_drive: '%s' uploaded → YouTube ID %s", filename, youtube_id)
        except Exception as exc:
            log.error("scan_drive: failed to upload '%s' — %s", filename, exc)
            db.set_state(file_id, "failed", error_message=str(exc))


def check_captions():
    """Check uploaded videos for available ASR captions and save SRT to Drive."""
    log.info("check_captions: starting")

    db.recover_stuck_uploading()
    db.timeout_caption_wait()

    videos = db.get_videos_in_state("uploaded")
    log.info("check_captions: %d video(s) waiting for captions", len(videos))

    for video in videos:
        drive_file_id = video["drive_file_id"]
        filename = video["drive_filename"]
        youtube_id = video["youtube_video_id"]

        try:
            caption_id = youtube.get_asr_caption_id(youtube_id)
        except Exception as exc:
            log.error("check_captions: error checking captions for '%s' — %s", filename, exc)
            continue

        if not caption_id:
            log.info("check_captions: no ASR captions yet for '%s'", filename)
            continue

        log.info("check_captions: ASR captions found for '%s', downloading", filename)
        db.set_state(drive_file_id, "captions_downloading", caption_id=caption_id)
        try:
            srt_bytes = youtube.download_caption_srt(caption_id)
            srt_filename = os.path.splitext(filename)[0] + ".txt"
            drive.upload_srt(config.CAPTIONS_DRIVE_FOLDER_ID, srt_filename, srt_bytes)
            log.info("check_captions: '%s' saved to Drive captions folder", srt_filename)

            if config.COMMUNITY_POSTS_DRIVE_FOLDER_ID and config.OPENAI_API_KEY:
                log.info("check_captions: generating community post for '%s'", filename)
                post_text = gpt.generate_community_post(srt_bytes.decode("utf-8"))
                post_filename = os.path.splitext(filename)[0] + "_community_post.txt"
                drive.upload_srt(config.COMMUNITY_POSTS_DRIVE_FOLDER_ID, post_filename, post_text.encode("utf-8"))
                log.info("check_captions: community post '%s' saved to Drive", post_filename)

            db.set_state(drive_file_id, "done")
        except Exception as exc:
            log.error("check_captions: failed to save captions for '%s' — %s", filename, exc)
            db.set_state(drive_file_id, "failed", error_message=str(exc))


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/status")
def status():
    return jsonify({
        "counts": db.get_state_counts(),
        "recent": [
            {
                **v,
                "updated_at": v["updated_at"].isoformat() if v.get("updated_at") else None,
            }
            for v in db.get_recent_videos()
        ],
    })


# ---------------------------------------------------------------------------
# App startup
# ---------------------------------------------------------------------------

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scan_drive,
        "interval",
        minutes=config.POLL_INTERVAL_MINUTES,
        id="scan_drive",
        max_instances=1,
    )
    scheduler.add_job(
        check_captions,
        "interval",
        minutes=config.CAPTION_CHECK_INTERVAL_MINUTES,
        id="check_captions",
        max_instances=1,
    )
    scheduler.start()
    log.info(
        "Scheduler started: Drive scan every %dm, caption check every %dm",
        config.POLL_INTERVAL_MINUTES,
        config.CAPTION_CHECK_INTERVAL_MINUTES,
    )
    return scheduler


# Initialise DB and start scheduler when the module is loaded (gunicorn imports app)
db.init_db()
_scheduler = start_scheduler()

# Run an immediate scan on startup so we don't wait for the first interval
import threading
threading.Thread(target=scan_drive, daemon=True).start()
threading.Thread(target=check_captions, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
