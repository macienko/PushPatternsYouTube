from typing import Optional

import auth
import config
import drive
from googleapiclient.http import MediaInMemoryUpload


def upload_video(title: str, video_bytes: bytes, mime_type: str) -> str:
    """Upload a video to YouTube as a private draft.

    Returns the YouTube video ID.
    """
    service = auth.build_youtube_service()

    description = ""
    if config.DESCRIPTION_DRIVE_FILE_ID:
        description = drive.read_text_file(config.DESCRIPTION_DRIVE_FILE_ID)

    tags = []
    if config.TAGS_DRIVE_FILE_ID:
        raw = drive.read_text_file(config.TAGS_DRIVE_FILE_ID)
        tags = [t.strip() for t in raw.split(",") if t.strip()]

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaInMemoryUpload(
        video_bytes,
        mimetype=mime_type,
        resumable=True,
        chunksize=10 * 1024 * 1024,
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    return response["id"]


def get_asr_caption_id(video_id: str) -> Optional[str]:
    """Return the caption track ID if YouTube ASR captions are available, else None.

    YouTube auto-generated captions have trackKind == 'asr'.
    """
    service = auth.build_youtube_service()
    result = (
        service.captions()
        .list(part="id,snippet", videoId=video_id)
        .execute()
    )
    for item in result.get("items", []):
        snippet = item.get("snippet", {})
        if snippet.get("trackKind") == "asr":
            return item["id"]
    return None


def download_caption_srt(caption_id: str) -> bytes:
    """Download a YouTube caption track as SRT bytes.

    Requires the youtube.force-ssl OAuth scope.
    """
    service = auth.build_youtube_service()
    response = service.captions().download(id=caption_id, tfmt="srt").execute()
    if isinstance(response, bytes):
        return response
    return response.encode("utf-8")
