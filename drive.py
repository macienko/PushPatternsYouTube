import io
import auth
from googleapiclient.http import MediaIoBaseDownload, MediaInMemoryUpload


def list_videos(folder_id: str) -> list[dict]:
    """List video files in a Drive folder.

    Returns a list of dicts with keys: id, name, mimeType.
    """
    service = auth.build_drive_service()
    query = (
        f"'{folder_id}' in parents "
        f"and mimeType contains 'video/' "
        f"and trashed = false"
    )
    results = (
        service.files()
        .list(q=query, fields="files(id, name, mimeType)", pageSize=100)
        .execute()
    )
    return results.get("files", [])


def download_video(file_id: str) -> tuple[bytes, str]:
    """Download a Drive file by ID.

    Returns (file_bytes, mime_type).
    """
    service = auth.build_drive_service()

    # Fetch MIME type
    meta = service.files().get(fileId=file_id, fields="mimeType").execute()
    mime_type = meta.get("mimeType", "video/mp4")

    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request, chunksize=10 * 1024 * 1024)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buf.getvalue(), mime_type


def upload_srt(folder_id: str, filename: str, content: bytes) -> str:
    """Upload an SRT file to a Drive folder.

    Returns the new Drive file ID.
    """
    service = auth.build_drive_service()
    media = MediaInMemoryUpload(
        content,
        mimetype="application/x-subrip",
        resumable=False,
    )
    file_meta = {"name": filename, "parents": [folder_id]}
    result = (
        service.files()
        .create(body=file_meta, media_body=media, fields="id")
        .execute()
    )
    return result["id"]
