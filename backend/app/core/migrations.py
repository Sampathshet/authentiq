"""Lightweight, idempotent schema upgrades.

The project ships without a migration framework. ``Base.metadata.create_all``
creates missing tables but never adds columns to tables that already exist, so
an upgraded database would break on the new fields. This module applies the
additive column and index changes introduced after the first release.

Every statement is written so that running it twice is a no-op.
"""

import logging

from sqlalchemy import inspect, text

from app.core.database import engine

logger = logging.getLogger("authentiq")

# (table, column, portable DDL type)
COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("registrations", "team_project_id", "VARCHAR(36)"),
)

# (index name, table, column)
INDEX_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("ix_registrations_team_project_id", "registrations", "team_project_id"),
)


def ensure_schema() -> None:
    """Add columns and indexes that are missing from an existing database."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        for table, column, ddl_type in COLUMN_MIGRATIONS:
            if table not in tables:
                continue
            columns = {item["name"] for item in inspector.get_columns(table)}
            if column in columns:
                continue
            logger.info("Applying schema upgrade: %s.%s", table, column)
            connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl_type}'))

        for index_name, table, column in INDEX_MIGRATIONS:
            if table not in tables:
                continue
            indexes = {item["name"] for item in inspector.get_indexes(table)}
            if index_name in indexes:
                continue
            logger.info("Creating index: %s", index_name)
            connection.execute(
                text(f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table}" ("{column}")')
            )
