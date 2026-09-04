"""Global forest areas and OSM land-cover persistence migration (Phase 1 / GIS-013).

Revision ID: 0009_forest_areas
Revises: 0008_pipeline_runs_and_jobs
Create Date: 2026-09-04 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_forest_areas"
down_revision: str | None = "0008_pipeline_runs_and_jobs"
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
    """Create forest_areas table, indexes, and constraints."""
    op.create_table(
        "forest_areas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("forest_id", sa.String(length=128), nullable=False),
        sa.Column("osm_id", sa.BigInteger(), nullable=False),
        sa.Column("osm_type", sa.String(length=32), nullable=False),
        sa.Column("osm_identity", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("name_en", sa.String(length=512), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("region", sa.String(length=256), nullable=True),
        sa.Column("forest_type", sa.String(length=64), nullable=False),
        sa.Column("osm_tag", sa.String(length=128), nullable=False),
        sa.Column("geometry", Geometry("Geometry", 4326), nullable=False),
        sa.Column("centroid_geometry", Geometry("Point", 4326), nullable=False),
        sa.Column("centroid_lat", sa.Float(precision=53), nullable=False),
        sa.Column("centroid_lon", sa.Float(precision=53), nullable=False),
        sa.Column("area_km2", sa.Float(precision=53), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=64),
            server_default="openstreetmap",
            nullable=False,
        ),
        sa.Column("source_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "is_repaired",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_forest_areas")),
        sa.UniqueConstraint("osm_identity", name=op.f("uq_forest_areas_osm_identity")),
        sa.UniqueConstraint("forest_id", name=op.f("uq_forest_areas_forest_id")),
        sa.CheckConstraint(
            "area_km2 >= 0.0",
            name="chk_forest_areas_area_non_negative",
        ),
        sa.CheckConstraint(
            "centroid_lat >= -90.0 AND centroid_lat <= 90.0",
            name="chk_forest_areas_centroid_lat_range",
        ),
        sa.CheckConstraint(
            "centroid_lon >= -180.0 AND centroid_lon <= 180.0",
            name="chk_forest_areas_centroid_lon_range",
        ),
    )

    op.create_index(
        op.f("ix_forest_areas_geometry"),
        "forest_areas",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_forest_areas_centroid_geometry"),
        "forest_areas",
        ["centroid_geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_forest_areas_country_code"),
        "forest_areas",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forest_areas_forest_type"),
        "forest_areas",
        ["forest_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forest_areas_name"),
        "forest_areas",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forest_areas_osm_type"),
        "forest_areas",
        ["osm_type"],
        unique=False,
    )


def downgrade() -> None:
    """Drop forest_areas table, indexes, and constraints."""
    op.drop_index(op.f("ix_forest_areas_osm_type"), table_name="forest_areas")
    op.drop_index(op.f("ix_forest_areas_name"), table_name="forest_areas")
    op.drop_index(op.f("ix_forest_areas_forest_type"), table_name="forest_areas")
    op.drop_index(op.f("ix_forest_areas_country_code"), table_name="forest_areas")
    op.drop_index(
        op.f("ix_forest_areas_centroid_geometry"),
        table_name="forest_areas",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_forest_areas_geometry"),
        table_name="forest_areas",
        postgresql_using="gist",
    )
    op.drop_table("forest_areas")
