"""Baseline infrastructure migration.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-29 10:15:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Validate PostGIS extension is enabled at the baseline infrastructure level."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def downgrade() -> None:
    """Downgrade baseline infrastructure (no-op to preserve extension)."""
    pass
