"""Pipeline runs and authoritative jobs migration (DB-014 / Migrations 025 & 026).

Revision ID: 0008_pipeline_runs_and_jobs
Revises: 0007_thermal_events
Create Date: 2026-08-30 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_pipeline_runs_and_jobs"
down_revision: str | None = "0007_thermal_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create pipeline_runs and jobs tables with indexes and constraints."""
    # 1. Table: pipeline_runs (Migration 025)
    op.create_table(
        "pipeline_runs",
        sa.Column("pipeline_run_id", sa.String(length=128), nullable=False),
        sa.Column("pipeline_name", sa.String(length=128), nullable=False),
        sa.Column(
            "pipeline_version",
            sa.String(length=64),
            nullable=False,
            server_default="v1.0.0",
        ),
        sa.Column("scientific_contract_id", sa.String(length=128), nullable=True),
        sa.Column(
            "input_snapshot_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("dataset_version_id", sa.String(length=128), nullable=True),
        sa.Column("model_version_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column("code_version", sa.String(length=128), nullable=True),
        sa.Column("configuration_hash", sa.String(length=128), nullable=True),
        sa.Column("output_manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("pipeline_run_id", name="pk_pipeline_runs"),
    )
    op.create_index(
        "ix_pipeline_runs_pipeline_name",
        "pipeline_runs",
        ["pipeline_name"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_runs_status",
        "pipeline_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_runs_started_at",
        "pipeline_runs",
        ["started_at"],
        unique=False,
    )

    # 2. Table: jobs (Migration 026)
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
        sa.Column(
            "state",
            sa.String(length=32),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column(
            "input_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("job_id", name="pk_jobs"),
    )
    op.create_index(
        "ix_jobs_job_type",
        "jobs",
        ["job_type"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_pipeline_run_id",
        "jobs",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_idempotency_key",
        "jobs",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_state",
        "jobs",
        ["state"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_created_at",
        "jobs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop jobs and pipeline_runs tables and indexes."""
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_state", table_name="jobs")
    op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_pipeline_run_id", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_pipeline_runs_started_at", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_pipeline_name", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
