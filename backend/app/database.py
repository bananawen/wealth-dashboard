import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from .config import get_settings

settings = get_settings()


def get_connection():
    return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()