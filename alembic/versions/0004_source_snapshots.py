"""Source snapshots persistence migration.

Revision ID: 0004_source_snapshots
Revises: 0003_source_registry
Create Date: 2026-08-29 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_source_snapshots"
down_revision: str | None = "0003_source_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create source_snapshots table, indexes, and constraints."""
    op.create_table(
        "source_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("external_version", sa.String(length=128), nullable=True),
        sa.Column(
            "retrieved_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("acquired_from", sa.Text(), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "availability_status",
            sa.String(length=32),
            server_default=sa.text("'AVAILABLE'"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_snapshots")),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_registry.id"],
            name=op.f("fk_source_snapshots_source_id"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "availability_status IN ('AVAILABLE', 'EMPTY_RESULT', 'FAILED', "
            "'UNAVAILABLE', 'RATE_LIMITED', 'PENDING')",
            name="chk_source_snapshots_availability_status_valid",
        ),
        sa.CheckConstraint(
            "content_hash IS NULL OR length(trim(content_hash)) = 64",
            name="chk_source_snapshots_content_hash_hex",
        ),
        sa.CheckConstraint(
            "request_fingerprint IS NULL OR length(trim(request_fingerprint)) = 64",
            name="chk_source_snapshots_request_fingerprint_hex",
        ),
    )
    op.create_index(
        op.f("ix_source_snapshots_source_id"),
        "source_snapshots",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_snapshots_retrieved_at"),
        "source_snapshots",
        ["retrieved_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_snapshots_content_hash"),
        "source_snapshots",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_snapshots_availability_status"),
        "source_snapshots",
        ["availability_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_snapshots_request_fingerprint"),
        "source_snapshots",
        ["request_fingerprint"],
        unique=False,
    )


def downgrade() -> None:
    """Drop source_snapshots table, indexes, and constraints."""
    op.drop_index(
        op.f("ix_source_snapshots_request_fingerprint"),
        table_name="source_snapshots",
    )
    op.drop_index(
        op.f("ix_source_snapshots_availability_status"),
        table_name="source_snapshots",
    )
    op.drop_index(
        op.f("ix_source_snapshots_content_hash"),
        table_name="source_snapshots",
    )
    op.drop_index(
        op.f("ix_source_snapshots_retrieved_at"),
        table_name="source_snapshots",
    )
    op.drop_index(
        op.f("ix_source_snapshots_source_id"),
        table_name="source_snapshots",
    )
    op.drop_table("source_snapshots")
