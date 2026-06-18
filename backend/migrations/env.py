from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.dialects.postgresql.base import PGDialect

from app.config import settings
from app.models import *
from app.models.base import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


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


def get_database_url() -> str:
    return normalize_database_url(settings.DATABASE_URL)


def run_migrations_offline() -> None:
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    patch_sqlalchemy_postgresql_dialect()

    connectable = create_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        use_native_hstore=False,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()