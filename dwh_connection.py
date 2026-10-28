import os
from functools import lru_cache

from sqlalchemy import create_engine


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATABASE_URL = "postgresql+psycopg2://dataeng:dataeng123@localhost:5432/dwh"
DEFAULT_SQLITE_URL = "sqlite:///" + os.path.join(BASE_DIR, "database", "retail_dwh.db").replace("\\", "/")


def default_database_url():
    return "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        user=os.getenv("PGUSER", "dataeng"),
        password=os.getenv("PGPASSWORD", "dataeng123"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "dwh")
    )


@lru_cache(maxsize=4)
def get_engine(database_url=None):
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)
    if os.getenv("DWH_DATABASE_URL"):
        return create_engine(os.getenv("DWH_DATABASE_URL"), pool_pre_ping=True)

    # Thử kết nối Postgres, nếu Docker chưa bật thì tự động fallback về SQLite
    try:
        pg_engine = create_engine(default_database_url(), pool_pre_ping=True)
        with pg_engine.connect() as conn:
            pass
        return pg_engine
    except Exception:
        return create_engine(DEFAULT_SQLITE_URL, pool_pre_ping=True)
