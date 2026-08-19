import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StoryStatus(enum.StrEnum):
    DEVELOPING = "developing"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"


class SourceKind(enum.StrEnum):
    ARTICLE = "article"
    DOCUMENT = "document"
    PRESS_RELEASE = "press_release"
    SOCIAL = "social"
    MANUAL = "manual"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Story(TimestampMixin, Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus, name="story_status"), default=StoryStatus.DEVELOPING, nullable=False
    )
    sources: Mapped[list["Source"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (Index("ix_stories_status_updated_at", "status", "updated_at"),)


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(320), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048))
    publisher: Mapped[str | None] = mapped_column(String(240))
    kind: Mapped[SourceKind] = mapped_column(
        Enum(SourceKind, name="source_kind"), default=SourceKind.ARTICLE, nullable=False
    )
    snapshot_text: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    story: Mapped[Story] = relationship(back_populates="sources")
