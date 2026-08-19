"""Add deterministic investigation workflow.

Revision ID: 20260819_0002
Revises: 20260819_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0002"
down_revision: str | None = "20260819_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

run_status = sa.Enum(
    "QUEUED", "RUNNING", "REVIEW", "BLOCKED", "FAILED", "CANCELLED", name="run_status"
)
agent_role = sa.Enum(
    "ASSIGNMENT_EDITOR", "RESEARCHER", "REPORTER", "FACT_CHECKER", name="agent_role"
)
event_status = sa.Enum("STARTED", "COMPLETED", "FAILED", name="event_status")
claim_verdict = sa.Enum(
    "SUPPORTED", "UNCORROBORATED", "DISPUTED", name="claim_verdict"
)
draft_status = sa.Enum("BLOCKED", "HUMAN_REVIEW", "APPROVED", name="draft_status")


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "investigation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("story_id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.String(length=120), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("current_stage", sa.String(length=80), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_key"),
    )
    op.create_index("ix_investigation_runs_story_id", "investigation_runs", ["story_id"])
    op.create_table(
        "agent_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("agent", agent_role, nullable=False),
        sa.Column("status", event_status, nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["run_id"], ["investigation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_events_run_id", "agent_events", ["run_id"])
    op.create_index(
        "uq_agent_events_run_sequence", "agent_events", ["run_id", "sequence"], unique=True
    )
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("verdict", claim_verdict, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["run_id"], ["investigation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claims_run_id", "claims", ["run_id"])
    op.create_index("ix_claims_source_id", "claims", ["source_id"])
    op.create_table(
        "citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_claim_id", "citations", ["claim_id"])
    op.create_index("ix_citations_source_id", "citations", ["source_id"])
    op.create_table(
        "drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", draft_status, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["run_id"], ["investigation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("drafts")
    op.drop_index("ix_citations_source_id", table_name="citations")
    op.drop_index("ix_citations_claim_id", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_claims_source_id", table_name="claims")
    op.drop_index("ix_claims_run_id", table_name="claims")
    op.drop_table("claims")
    op.drop_index("uq_agent_events_run_sequence", table_name="agent_events")
    op.drop_index("ix_agent_events_run_id", table_name="agent_events")
    op.drop_table("agent_events")
    op.drop_index("ix_investigation_runs_story_id", table_name="investigation_runs")
    op.drop_table("investigation_runs")
    draft_status.drop(op.get_bind(), checkfirst=True)
    claim_verdict.drop(op.get_bind(), checkfirst=True)
    event_status.drop(op.get_bind(), checkfirst=True)
    agent_role.drop(op.get_bind(), checkfirst=True)
    run_status.drop(op.get_bind(), checkfirst=True)
