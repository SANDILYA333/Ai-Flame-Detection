"""Canonical detections persistence migration.

Revision ID: 0006_detections
Revises: 0005_source_records
Create Date: 2026-08-29 21:18:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_detections"
down_revision: str | None = "0005_source_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Geometry(UserDefinedType[Any]):
    """PostGIS Geometry column type for SQLAlchemy DDL."""

    def __init__(self, geometry_type: str = "Point", srid: int = 4326) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw: Any) -> str:
        """Return raw PostGIS DDL column specification."""
        return f"geometry({self.geometry_type}, {self.srid})"


def upgrade() -> None:
    """Create detections table, indexes, and scientific constraints."""
    op.create_table(
        "detections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "source_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("satellite", sa.String(length=64), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column("product_type", sa.String(length=64), nullable=False),
        sa.Column("product_version", sa.String(length=64), nullable=False),
        sa.Column("acquired_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("latitude", sa.Float(precision=53), nullable=False),
        sa.Column("longitude", sa.Float(precision=53), nullable=False),
        sa.Column("geometry", Geometry("Point", 4326), nullable=False),
        sa.Column("frp_mw", sa.Float(precision=53), nullable=True),
        sa.Column("brightness_ti4_k", sa.Float(precision=53), nullable=True),
        sa.Column("brightness_ti5_k", sa.Float(precision=53), nullable=True),
        sa.Column("confidence_raw", sa.String(length=64), nullable=True),
        sa.Column("day_night", sa.String(length=8), nullable=True),
        sa.Column("scan", sa.Float(precision=53), nullable=True),
        sa.Column("track", sa.Float(precision=53), nullable=True),
        sa.Column("raw_identifier", sa.String(length=128), nullable=True),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_detections")),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_records.id"],
            name=op.f("fk_detections_source_record_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["source_snapshots.id"],
            name=op.f("fk_detections_source_snapshot_id"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "latitude BETWEEN -90.0 AND 90.0",
            name="chk_detections_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180.0 AND 180.0",
            name="chk_detections_longitude_range",
        ),
        sa.CheckConstraint(
            "frp_mw IS NULL OR frp_mw >= 0.0",
            name="chk_detections_frp_mw_non_negative",
        ),
        sa.CheckConstraint(
            "brightness_ti4_k IS NULL OR brightness_ti4_k >= 0.0",
            name="chk_detections_brightness_ti4_k_non_negative",
        ),
        sa.CheckConstraint(
            "brightness_ti5_k IS NULL OR brightness_ti5_k >= 0.0",
            name="chk_detections_brightness_ti5_k_non_negative",
        ),
        sa.CheckConstraint(
            "scan IS NULL OR scan > 0.0",
            name="chk_detections_scan_positive",
        ),
        sa.CheckConstraint(
            "track IS NULL OR track > 0.0",
            name="chk_detections_track_positive",
        ),
        sa.CheckConstraint(
            "day_night IS NULL OR day_night IN ('D', 'N', 'unknown')",
            name="chk_detections_day_night_valid",
        ),
        sa.CheckConstraint(
            "length(trim(raw_hash)) = 64",
            name="chk_detections_raw_hash_hex",
        ),
    )
    op.create_index(
        op.f("ix_detections_geometry"),
        "detections",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_detections_acquired_at"),
        "detections",
        ["acquired_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_detections_source_snapshot_id"),
        "detections",
        ["source_snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_detections_source_record_id"),
        "detections",
        ["source_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_detections_raw_hash"),
        "detections",
        ["raw_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_detections_satellite_instrument"),
        "detections",
        ["satellite", "instrument"],
        unique=False,
    )
    op.create_index(
        op.f("ix_detections_source"),
        "detections",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    """Drop detections table, indexes, and constraints."""
    op.drop_index(
        op.f("ix_detections_source"),
        table_name="detections",
    )
    op.drop_index(
        op.f("ix_detections_satellite_instrument"),
        table_name="detections",
    )
    op.drop_index(
        op.f("ix_detections_raw_hash"),
        table_name="detections",
    )
    op.drop_index(
        op.f("ix_detections_source_record_id"),
        table_name="detections",
    )
    op.drop_index(
        op.f("ix_detections_source_snapshot_id"),
        table_name="detections",
    )
    op.drop_index(
        op.f("ix_detections_acquired_at"),
        table_name="detections",
    )
    op.drop_index(
        op.f("ix_detections_geometry"),
        table_name="detections",
        postgresql_using="gist",
    )
    op.drop_table("detections")
