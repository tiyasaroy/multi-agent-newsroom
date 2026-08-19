import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
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


class RunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    REVIEW = "review"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class AgentRole(enum.StrEnum):
    ASSIGNMENT_EDITOR = "assignment_editor"
    RESEARCHER = "researcher"
    REPORTER = "reporter"
    FACT_CHECKER = "fact_checker"


class EventStatus(enum.StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ClaimVerdict(enum.StrEnum):
    SUPPORTED = "supported"
    UNCORROBORATED = "uncorroborated"
    DISPUTED = "disputed"


class DraftStatus(enum.StrEnum):
    BLOCKED = "blocked"
    HUMAN_REVIEW = "human_review"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class EditorialAction(enum.StrEnum):
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


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
    investigation_runs: Mapped[list["InvestigationRun"]] = relationship(
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
    claims: Mapped[list["Claim"]] = relationship(back_populates="source")
    citations: Mapped[list["Citation"]] = relationship(back_populates="source")


class InvestigationRun(TimestampMixin, Base):
    __tablename__ = "investigation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    provider_requested: Mapped[str] = mapped_column(String(40), default="auto", nullable=False)
    provider_used: Mapped[str] = mapped_column(String(40), default="deterministic", nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.QUEUED, nullable=False
    )
    current_stage: Mapped[str | None] = mapped_column(String(80))
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    story: Mapped[Story] = relationship(back_populates="investigation_runs")
    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AgentEvent.sequence"
    )
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    draft: Mapped["Draft | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )
    editorial_decisions: Mapped[list["EditorialDecision"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="EditorialDecision.created_at"
    )


class AgentEvent(TimestampMixin, Base):
    __tablename__ = "agent_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent: Mapped[AgentRole] = mapped_column(Enum(AgentRole, name="agent_role"), nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"), nullable=False
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(80))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float)
    run: Mapped[InvestigationRun] = relationship(back_populates="events")

    __table_args__ = (Index("uq_agent_events_run_sequence", "run_id", "sequence", unique=True),)


class Claim(TimestampMixin, Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[ClaimVerdict] = mapped_column(
        Enum(ClaimVerdict, name="claim_verdict"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    run: Mapped[InvestigationRun] = relationship(back_populates="claims")
    source: Mapped[Source] = relationship(back_populates="claims")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class Citation(TimestampMixin, Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[Claim] = relationship(back_populates="citations")
    source: Mapped[Source] = relationship(back_populates="citations")


class Draft(TimestampMixin, Base):
    __tablename__ = "drafts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        Enum(DraftStatus, name="draft_status"), default=DraftStatus.BLOCKED, nullable=False
    )
    run: Mapped[InvestigationRun] = relationship(back_populates="draft")


class EditorialDecision(Base):
    __tablename__ = "editorial_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[EditorialAction] = mapped_column(
        Enum(EditorialAction, name="editorial_action"), nullable=False
    )
    editor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    run: Mapped[InvestigationRun] = relationship(back_populates="editorial_decisions")
