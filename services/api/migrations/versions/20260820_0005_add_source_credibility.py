"""Add transparent source credibility metadata.

Revision ID: 20260820_0005
Revises: 20260820_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0005"
down_revision: str | None = "20260820_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("credibility_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "sources",
        sa.Column("credibility_signals", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("sources", "credibility_signals")
    op.drop_column("sources", "credibility_score")
