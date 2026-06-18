from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.orm import sessionmaker

from app.config import settings


def patch_sqlalchemy_postgresql_dialect() -> None:
    def safe_initialize(self, connection):
        self.server_version_info = (18, 4)
        self.default_schema_name = "public"
        self.default_isolation_level = "READ COMMITTED"
        self._backslash_escapes = False

    PGDialect.initialize = safe_initialize


def normalize_database_url(database_url: str) -> str:
    url = database_url.strip()

    split_url = urlsplit(url)

    query_items = dict(
        parse_qsl(
            split_url.query,
            keep_blank_values=True,
        )
    )

    query_items.pop(
        "channel_binding",
        None,
    )

    query_items["sslmode"] = "require"
    query_items["connect_timeout"] = "10"

    normalized_query = urlencode(query_items)

    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            normalized_query,
            "",
        )
    )


patch_sqlalchemy_postgresql_dialect()

engine = create_engine(
    normalize_database_url(settings.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    use_native_hstore=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()