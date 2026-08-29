"""Source registry persistence migration.

Revision ID: 0003_source_registry
Revises: 0002_scientific_contracts
Create Date: 2026-08-29 17:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_source_registry"
down_revision: str | None = "0002_scientific_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create source_registry table, indexes, and constraints."""
    op.create_table(
        "source_registry",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("observation_family", sa.String(length=64), nullable=True),
        sa.Column("coverage_notes", sa.Text(), nullable=True),
        sa.Column("access_method", sa.String(length=128), nullable=True),
        sa.Column(
            "auth_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("license_notes", sa.Text(), nullable=True),
        sa.Column("rate_limit_notes", sa.Text(), nullable=True),
        sa.Column(
            "fallback_source_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_registry")),
        sa.UniqueConstraint("name", name=op.f("uq_source_registry_name")),
        sa.ForeignKeyConstraint(
            ["fallback_source_id"],
            ["source_registry.id"],
            name=op.f("fk_source_registry_fallback_source_id"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="chk_source_registry_name_non_empty",
        ),
        sa.CheckConstraint(
            "length(trim(provider)) > 0",
            name="chk_source_registry_provider_non_empty",
        ),
        sa.CheckConstraint(
            "length(trim(source_type)) > 0",
            name="chk_source_registry_source_type_non_empty",
        ),
        sa.CheckConstraint(
            "length(trim(status)) > 0",
            name="chk_source_registry_status_non_empty",
        ),
        sa.CheckConstraint(
            "role IN ('OBSERVATION', 'REFERENCE', 'CONTEXT', 'VALIDATION', "
            "'ENVIRONMENTAL', 'DERIVED', 'GROUND_TRUTH_CANDIDATE', "
            "'GROUND_TRUTH_EVIDENCE', 'OPTIONAL', 'DEMO_ONLY')",
            name="chk_source_registry_role_valid",
        ),
        sa.CheckConstraint(
            "fallback_source_id IS NULL OR fallback_source_id != id",
            name="chk_source_registry_fallback_not_self",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="chk_source_registry_updated_at_after_created_at",
        ),
    )
    op.create_index(
        op.f("ix_source_registry_role"),
        "source_registry",
        ["role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_registry_source_type"),
        "source_registry",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_registry_provider"),
        "source_registry",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_registry_status"),
        "source_registry",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_registry_fallback_source_id"),
        "source_registry",
        ["fallback_source_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop source_registry table, indexes, and constraints."""
    op.drop_index(
        op.f("ix_source_registry_fallback_source_id"),
        table_name="source_registry",
    )
    op.drop_index(
        op.f("ix_source_registry_status"),
        table_name="source_registry",
    )
    op.drop_index(
        op.f("ix_source_registry_provider"),
        table_name="source_registry",
    )
    op.drop_index(
        op.f("ix_source_registry_source_type"),
        table_name="source_registry",
    )
    op.drop_index(
        op.f("ix_source_registry_role"),
        table_name="source_registry",
    )
    op.drop_table("source_registry")
