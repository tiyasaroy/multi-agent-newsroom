"""Add model provider and usage telemetry.

Revision ID: 20260819_0003
Revises: 20260819_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0003"
down_revision: str | None = "20260819_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigation_runs",
        sa.Column(
            "provider_requested", sa.String(length=40), server_default="auto", nullable=False
        ),
    )
    op.add_column(
        "investigation_runs",
        sa.Column(
            "provider_used", sa.String(length=40), server_default="deterministic", nullable=False
        ),
    )
    op.add_column("agent_events", sa.Column("provider", sa.String(length=80), nullable=True))
    op.add_column("agent_events", sa.Column("model", sa.String(length=120), nullable=True))
    op.add_column(
        "agent_events", sa.Column("prompt_version", sa.String(length=80), nullable=True)
    )
    op.add_column("agent_events", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("agent_events", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("agent_events", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column("agent_events", sa.Column("estimated_cost_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_events", "estimated_cost_usd")
    op.drop_column("agent_events", "latency_ms")
    op.drop_column("agent_events", "output_tokens")
    op.drop_column("agent_events", "input_tokens")
    op.drop_column("agent_events", "prompt_version")
    op.drop_column("agent_events", "model")
    op.drop_column("agent_events", "provider")
    op.drop_column("investigation_runs", "provider_used")
    op.drop_column("investigation_runs", "provider_requested")
