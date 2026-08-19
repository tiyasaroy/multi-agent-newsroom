"""Create stories and sources.

Revision ID: 20260819_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

story_status = sa.Enum("DEVELOPING", "REVIEW", "APPROVED", "PUBLISHED", name="story_status")
source_kind = sa.Enum(
    "ARTICLE", "DOCUMENT", "PRESS_RELEASE", "SOCIAL", "MANUAL", name="source_kind"
)


def upgrade() -> None:
    op.create_table(
        "stories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", story_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stories_status_updated_at", "stories", ["status", "updated_at"])
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("story_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=320), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("publisher", sa.String(length=240), nullable=True),
        sa.Column("kind", source_kind, nullable=False),
        sa.Column("snapshot_text", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_story_id", "sources", ["story_id"])


def downgrade() -> None:
    op.drop_index("ix_sources_story_id", table_name="sources")
    op.drop_table("sources")
    op.drop_index("ix_stories_status_updated_at", table_name="stories")
    op.drop_table("stories")
    source_kind.drop(op.get_bind(), checkfirst=True)
    story_status.drop(op.get_bind(), checkfirst=True)
