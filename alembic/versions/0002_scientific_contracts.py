"""Scientific contracts persistence migration.

Revision ID: 0002_scientific_contracts
Revises: 0001_baseline
Create Date: 2026-08-29 12:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_scientific_contracts"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create scientific_contracts table and supporting indexes/constraints."""
    op.create_table(
        "scientific_contracts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column(
            "name",
            sa.String(length=128),
            server_default=sa.text("'default'"),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        # 1. Spatial Clustering Parameters (Nullable, No Default)
        sa.Column(
            "spatial_cluster_radius_meters",
            sa.Float(),
            nullable=True,
        ),
        # 2. Temporal Clustering Parameters (Nullable, No Default)
        sa.Column(
            "temporal_window_hours",
            sa.Float(),
            nullable=True,
        ),
        # 3. Persistence Criteria (Nullable, No Default)
        sa.Column(
            "persistence_threshold_days",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "persistence_min_observations",
            sa.Integer(),
            nullable=True,
        ),
        # 4. Attribution Parameters (Nullable, No Default)
        sa.Column(
            "attribution_radius_meters",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "attribution_confidence_threshold",
            sa.Float(),
            nullable=True,
        ),
        # 5. Decision & Abstention Thresholds (Nullable, No Default)
        sa.Column(
            "minimum_event_confidence",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "abstention_confidence_threshold",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "raw_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scientific_contracts")),
        sa.UniqueConstraint("version", name=op.f("uq_scientific_contracts_version")),
        sa.CheckConstraint(
            "spatial_cluster_radius_meters IS NULL OR "
            "spatial_cluster_radius_meters > 0",
            name="chk_scientific_contracts_spatial_radius",
        ),
        sa.CheckConstraint(
            "temporal_window_hours IS NULL OR temporal_window_hours > 0",
            name="chk_scientific_contracts_temporal_window",
        ),
        sa.CheckConstraint(
            "persistence_threshold_days IS NULL OR persistence_threshold_days > 0",
            name="chk_scientific_contracts_persistence_days",
        ),
        sa.CheckConstraint(
            "persistence_min_observations IS NULL OR persistence_min_observations >= 1",
            name="chk_scientific_contracts_persistence_min_obs",
        ),
        sa.CheckConstraint(
            "attribution_radius_meters IS NULL OR attribution_radius_meters > 0",
            name="chk_scientific_contracts_attribution_radius",
        ),
        sa.CheckConstraint(
            "attribution_confidence_threshold IS NULL OR "
            "(attribution_confidence_threshold >= 0.0 AND "
            "attribution_confidence_threshold <= 1.0)",
            name="chk_scientific_contracts_attribution_conf",
        ),
        sa.CheckConstraint(
            "minimum_event_confidence IS NULL OR "
            "(minimum_event_confidence >= 0.0 AND "
            "minimum_event_confidence <= 1.0)",
            name="chk_scientific_contracts_min_conf",
        ),
        sa.CheckConstraint(
            "abstention_confidence_threshold IS NULL OR "
            "(abstention_confidence_threshold >= 0.0 AND "
            "abstention_confidence_threshold <= 1.0)",
            name="chk_scientific_contracts_abstention_conf",
        ),
    )
    op.create_index(
        op.f("ix_scientific_contracts_fingerprint"),
        "scientific_contracts",
        ["fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scientific_contracts_is_active"),
        "scientific_contracts",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Drop scientific_contracts table and its indexes."""
    op.drop_index(
        op.f("ix_scientific_contracts_is_active"),
        table_name="scientific_contracts",
    )
    op.drop_index(
        op.f("ix_scientific_contracts_fingerprint"),
        table_name="scientific_contracts",
    )
    op.drop_table("scientific_contracts")
