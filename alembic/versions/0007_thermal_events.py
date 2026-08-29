"""Thermal events and detection membership persistence migration.

Revision ID: 0007_thermal_events
Revises: 0006_detections
Create Date: 2026-08-29 21:25:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_thermal_events"
down_revision: str | None = "0006_detections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Geometry(UserDefinedType[Any]):
    """PostGIS Geometry column type for SQLAlchemy DDL."""

    def __init__(self, geometry_type: str = "Geometry", srid: int = 4326) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw: Any) -> str:
        """Return raw PostGIS DDL column specification."""
        return f"geometry({self.geometry_type}, {self.srid})"


def upgrade() -> None:
    """Create thermal_events and event_detections tables, indexes, and constraints."""
    op.create_table(
        "thermal_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "scientific_contract_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("formation_run_id", sa.String(length=128), nullable=True),
        sa.Column(
            "formation_status",
            sa.String(length=32),
            server_default=sa.text("'FORMED'"),
            nullable=False,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(precision=53), nullable=True),
        sa.Column("detection_count", sa.Integer(), nullable=False),
        sa.Column("centroid_geometry", Geometry("Point", 4326), nullable=False),
        sa.Column("observation_geometry", Geometry("Geometry", 4326), nullable=True),
        sa.Column("mean_frp_mw", sa.Float(precision=53), nullable=True),
        sa.Column("max_frp_mw", sa.Float(precision=53), nullable=True),
        sa.Column("total_frp_mw", sa.Float(precision=53), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_thermal_events")),
        sa.ForeignKeyConstraint(
            ["scientific_contract_id"],
            ["scientific_contracts.id"],
            name=op.f("fk_thermal_events_scientific_contract_id"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "ended_at >= started_at",
            name="chk_thermal_events_temporal_order",
        ),
        sa.CheckConstraint(
            "detection_count >= 1",
            name="chk_thermal_events_detection_count_positive",
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0.0",
            name="chk_thermal_events_duration_non_negative",
        ),
        sa.CheckConstraint(
            "mean_frp_mw IS NULL OR mean_frp_mw >= 0.0",
            name="chk_thermal_events_mean_frp_non_negative",
        ),
        sa.CheckConstraint(
            "max_frp_mw IS NULL OR max_frp_mw >= 0.0",
            name="chk_thermal_events_max_frp_non_negative",
        ),
        sa.CheckConstraint(
            "total_frp_mw IS NULL OR total_frp_mw >= 0.0",
            name="chk_thermal_events_total_frp_non_negative",
        ),
    )
    op.create_index(
        op.f("ix_thermal_events_centroid_geometry"),
        "thermal_events",
        ["centroid_geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_thermal_events_observation_geometry"),
        "thermal_events",
        ["observation_geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_thermal_events_started_at"),
        "thermal_events",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_thermal_events_ended_at"),
        "thermal_events",
        ["ended_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_thermal_events_time_range"),
        "thermal_events",
        ["started_at", "ended_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_thermal_events_scientific_contract_id"),
        "thermal_events",
        ["scientific_contract_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_thermal_events_formation_run_id"),
        "thermal_events",
        ["formation_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_thermal_events_formation_status"),
        "thermal_events",
        ["formation_status"],
        unique=False,
    )

    op.create_table(
        "event_detections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "detection_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("membership_confidence", sa.Float(precision=53), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_detections")),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["thermal_events.id"],
            name=op.f("fk_event_detections_event_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["detection_id"],
            ["detections.id"],
            name=op.f("fk_event_detections_detection_id"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "event_id",
            "detection_id",
            name="uq_event_detections_event_detection",
        ),
        sa.CheckConstraint(
            "membership_confidence IS NULL OR (membership_confidence >= 0.0 AND membership_confidence <= 1.0)",
            name="chk_event_detections_confidence_range",
        ),
    )
    op.create_index(
        op.f("ix_event_detections_event_id"),
        "event_detections",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_detections_detection_id"),
        "event_detections",
        ["detection_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop event_detections and thermal_events tables, indexes, and constraints."""
    op.drop_index(
        op.f("ix_event_detections_detection_id"),
        table_name="event_detections",
    )
    op.drop_index(
        op.f("ix_event_detections_event_id"),
        table_name="event_detections",
    )
    op.drop_table("event_detections")

    op.drop_index(
        op.f("ix_thermal_events_formation_status"),
        table_name="thermal_events",
    )
    op.drop_index(
        op.f("ix_thermal_events_formation_run_id"),
        table_name="thermal_events",
    )
    op.drop_index(
        op.f("ix_thermal_events_scientific_contract_id"),
        table_name="thermal_events",
    )
    op.drop_index(
        op.f("ix_thermal_events_time_range"),
        table_name="thermal_events",
    )
    op.drop_index(
        op.f("ix_thermal_events_ended_at"),
        table_name="thermal_events",
    )
    op.drop_index(
        op.f("ix_thermal_events_started_at"),
        table_name="thermal_events",
    )
    op.drop_index(
        op.f("ix_thermal_events_observation_geometry"),
        table_name="thermal_events",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_thermal_events_centroid_geometry"),
        table_name="thermal_events",
        postgresql_using="gist",
    )
    op.drop_table("thermal_events")
