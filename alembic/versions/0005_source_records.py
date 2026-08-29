"""Source records persistence migration.

Revision ID: 0005_source_records
Revises: 0004_source_snapshots
Create Date: 2026-08-29 21:10:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_source_records"
down_revision: str | None = "0004_source_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Geometry(UserDefinedType):
    """PostGIS Geometry column type for SQLAlchemy DDL."""

    def __init__(self, geometry_type: str = "Geometry", srid: int = 4326) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw: Any) -> str:
        """Return raw PostGIS DDL column specification."""
        return f"geometry({self.geometry_type}, {self.srid})"


def upgrade() -> None:
    """Create source_records table, indexes, and constraints."""
    op.create_table(
        "source_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "source_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("external_record_id", sa.String(length=128), nullable=True),
        sa.Column("raw_artifact_uri", sa.Text(), nullable=True),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.Column("record_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("geometry", Geometry("Geometry", 4326), nullable=True),
        sa.Column(
            "raw_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_records")),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["source_snapshots.id"],
            name=op.f("fk_source_records_source_snapshot_id"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_snapshot_id",
            "record_hash",
            name=op.f("uq_source_records_snapshot_record_hash"),
        ),
        sa.CheckConstraint(
            "length(trim(record_hash)) = 64",
            name="chk_source_records_record_hash_hex",
        ),
    )
    op.create_index(
        op.f("ix_source_records_source_snapshot_id"),
        "source_records",
        ["source_snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_records_record_time"),
        "source_records",
        ["record_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_records_record_hash"),
        "source_records",
        ["record_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_records_external_record_id"),
        "source_records",
        ["external_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_records_geometry"),
        "source_records",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    """Drop source_records table, indexes, and constraints."""
    op.drop_index(
        op.f("ix_source_records_geometry"),
        table_name="source_records",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_source_records_external_record_id"),
        table_name="source_records",
    )
    op.drop_index(
        op.f("ix_source_records_record_hash"),
        table_name="source_records",
    )
    op.drop_index(
        op.f("ix_source_records_record_time"),
        table_name="source_records",
    )
    op.drop_index(
        op.f("ix_source_records_source_snapshot_id"),
        table_name="source_records",
    )
    op.drop_table("source_records")
