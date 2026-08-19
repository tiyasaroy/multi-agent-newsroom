"""Add adversarial newsroom agents and structured findings.

Revision ID: 20260820_0006
Revises: 20260820_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0006"
down_revision: str | None = "20260820_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE agent_role ADD VALUE IF NOT EXISTS 'MISINFORMATION_ANALYST'")
    op.execute("ALTER TYPE agent_role ADD VALUE IF NOT EXISTS 'BIAS_AUDITOR'")
    op.create_table(
        "adversarial_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("agent", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("claim_index", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("recommendation", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["investigation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adversarial_findings_run_id", "adversarial_findings", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_adversarial_findings_run_id", table_name="adversarial_findings")
    op.drop_table("adversarial_findings")
