import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import config

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS videos (
    id               SERIAL PRIMARY KEY,
    drive_file_id    TEXT UNIQUE NOT NULL,
    drive_filename   TEXT NOT NULL,
    state            TEXT NOT NULL DEFAULT 'discovered',
    youtube_video_id TEXT,
    caption_id       TEXT,
    error_message    TEXT,
    discovered_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
"""


@contextmanager
def _conn():
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)


def upsert_video(drive_file_id: str, filename: str) -> str:
    """Insert video if not already known. Returns current state."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO videos (drive_file_id, drive_filename)
                VALUES (%s, %s)
                ON CONFLICT (drive_file_id) DO NOTHING
                """,
                (drive_file_id, filename),
            )
            cur.execute(
                "SELECT state FROM videos WHERE drive_file_id = %s",
                (drive_file_id,),
            )
            row = cur.fetchone()
            return row[0] if row else "discovered"


def set_state(drive_file_id: str, state: str, **kwargs):
    """Update state and optional extra fields (youtube_video_id, caption_id, error_message)."""
    allowed = {"youtube_video_id", "caption_id", "error_message"}
    extra = {k: v for k, v in kwargs.items() if k in allowed}

    set_clauses = ["state = %s", "updated_at = NOW()"]
    values = [state]

    for col, val in extra.items():
        set_clauses.append(f"{col} = %s")
        values.append(val)

    values.append(drive_file_id)
    sql = f"UPDATE videos SET {', '.join(set_clauses)} WHERE drive_file_id = %s"

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)


def get_videos_in_state(state: str) -> list[dict]:
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM videos WHERE state = %s ORDER BY discovered_at",
                (state,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_recent_videos(limit: int = 50) -> list[dict]:
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT drive_filename, state, youtube_video_id, error_message, updated_at "
                "FROM videos ORDER BY updated_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_state_counts() -> dict:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT state, COUNT(*) FROM videos GROUP BY state")
            return {row[0]: row[1] for row in cur.fetchall()}


def recover_stuck_uploading():
    """Mark as failed any video stuck in 'uploading' for more than 2 hours."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE videos
                SET state = 'failed',
                    error_message = 'Upload timed out (stuck in uploading for >2h)',
                    updated_at = NOW()
                WHERE state = 'uploading'
                  AND updated_at < NOW() - INTERVAL '2 hours'
                """
            )


def timeout_caption_wait():
    """Mark as failed any video waiting for captions beyond CAPTION_MAX_WAIT_HOURS."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE videos
                SET state = 'failed',
                    error_message = %s,
                    updated_at = NOW()
                WHERE state = 'uploaded'
                  AND updated_at < NOW() - INTERVAL '%s hours'
                """,
                (
                    f"No ASR captions appeared within {config.CAPTION_MAX_WAIT_HOURS} hours",
                    config.CAPTION_MAX_WAIT_HOURS,
                ),
            )
