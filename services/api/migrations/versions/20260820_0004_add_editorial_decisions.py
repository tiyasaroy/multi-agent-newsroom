"""Add human editorial decisions and terminal review states.

Revision ID: 20260820_0004
Revises: 20260819_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0004"
down_revision: str | None = "20260819_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE run_status ADD VALUE IF NOT EXISTS 'APPROVED'")
    op.execute("ALTER TYPE run_status ADD VALUE IF NOT EXISTS 'REVISION_REQUESTED'")
    op.execute("ALTER TYPE draft_status ADD VALUE IF NOT EXISTS 'REVISION_REQUESTED'")
    editorial_action = sa.Enum("APPROVED", "REVISION_REQUESTED", name="editorial_action")
    editorial_action.create(op.get_bind())
    op.create_table(
        "editorial_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("action", editorial_action, nullable=False),
        sa.Column("editor_name", sa.String(length=120), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["investigation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_editorial_decisions_run_id", "editorial_decisions", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_editorial_decisions_run_id", table_name="editorial_decisions")
    op.drop_table("editorial_decisions")
    sa.Enum(name="editorial_action").drop(op.get_bind())
