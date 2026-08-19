import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from newsroom_api.models import (
    AgentEvent,
    AgentRole,
    Citation,
    Claim,
    ClaimVerdict,
    Draft,
    DraftStatus,
    EventStatus,
    InvestigationRun,
    RunStatus,
    Story,
    StoryStatus,
)
from newsroom_api.providers.base import ModelResult, NewsroomModelProvider, SourceInput


class ModelNewsroomWorkflow:
    def __init__(self, session: AsyncSession, provider: NewsroomModelProvider) -> None:
        self.session = session
        self.provider = provider
        self.sequence = 0

    def record_event(
        self,
        run: InvestigationRun,
        agent: AgentRole,
        summary: str,
        payload: dict[str, object],
        result: ModelResult | None = None,
    ) -> None:
        self.sequence += 1
        run.events.append(
            AgentEvent(
                sequence=self.sequence,
                agent=agent,
                status=EventStatus.COMPLETED,
                summary=summary,
                payload=payload,
                provider=result.provider if result else "workflow",
                model=result.model if result else None,
                prompt_version=result.prompt_version if result else "assignment-editor-v1",
                input_tokens=result.input_tokens if result else 0,
                output_tokens=result.output_tokens if result else 0,
                latency_ms=result.latency_ms if result else 0,
                estimated_cost_usd=result.estimated_cost_usd if result else 0,
            )
        )

    async def load_context(
        self, run_id: uuid.UUID
    ) -> tuple[InvestigationRun, Story]:
        run = await self.session.scalar(
            select(InvestigationRun)
            .where(InvestigationRun.id == run_id)
            .options(
                selectinload(InvestigationRun.events),
                selectinload(InvestigationRun.claims),
                selectinload(InvestigationRun.draft),
            )
        )
        if run is None:
            raise ValueError("Investigation context disappeared before execution")
        story = await self.session.scalar(
            select(Story).where(Story.id == run.story_id).options(selectinload(Story.sources))
        )
        if story is None:
            raise ValueError("Investigation context disappeared before execution")
        return run, story

    async def execute(self, run: InvestigationRun) -> InvestigationRun:
        run, story = await self.load_context(run.id)
        run.status = RunStatus.RUNNING
        run.current_stage = AgentRole.ASSIGNMENT_EDITOR.value
        self.record_event(
            run,
            AgentRole.ASSIGNMENT_EDITOR,
            f"Assigned {len(story.sources)} source snapshots to the model newsroom",
            {"source_count": len(story.sources), "human_approval_required": True},
        )
        await self.session.commit()

        run, story = await self.load_context(run.id)
        run.current_stage = AgentRole.RESEARCHER.value
        sources = [
            SourceInput(
                id=source.id,
                title=source.title,
                publisher=source.publisher,
                snapshot_text=source.snapshot_text,
            )
            for source in story.sources
        ]
        research = await self.provider.research(story.title, sources)
        source_by_id = {source.id: source for source in story.sources}
        model_claims = []
        for item in research.output.claims:
            source = source_by_id.get(item.source_id)
            if source is None or item.quote not in source.snapshot_text:
                raise ValueError("Research output contained an invalid source citation")
            model_claims.append(item)
            claim = Claim(
                source_id=item.source_id,
                text=item.text,
                verdict=ClaimVerdict.SUPPORTED,
                confidence=item.confidence,
            )
            claim.citations.append(Citation(source_id=item.source_id, quote=item.quote))
            run.claims.append(claim)
        self.record_event(
            run,
            AgentRole.RESEARCHER,
            f"Extracted {len(model_claims)} schema-validated claims",
            {"claim_count": len(model_claims)},
            research,
        )
        await self.session.commit()

        run, story = await self.load_context(run.id)
        run.current_stage = AgentRole.REPORTER.value
        draft_result = await self.provider.draft(story.title, model_claims)
        run.draft = Draft(
            title=draft_result.output.title,
            body=draft_result.output.body,
            status=DraftStatus.BLOCKED,
        )
        self.record_event(
            run,
            AgentRole.REPORTER,
            "Generated a schema-validated cited draft",
            {"character_count": len(draft_result.output.body)},
            draft_result,
        )
        await self.session.commit()

        run, story = await self.load_context(run.id)
        run.current_stage = AgentRole.FACT_CHECKER.value
        publishers = {
            (source.publisher or source.url or str(source.id)).casefold()
            for source in story.sources
        }
        fact_check = await self.provider.fact_check(model_claims, len(publishers))
        review_by_index = {review.claim_index: review for review in fact_check.output.reviews}
        if set(review_by_index) != set(range(len(run.claims))):
            raise ValueError("Fact-check output did not review every claim exactly once")
        for index, claim in enumerate(run.claims):
            review = review_by_index[index]
            claim.verdict = ClaimVerdict(review.verdict)
            claim.confidence = review.confidence

        blocked = fact_check.output.publication_blocked
        if run.draft is None:
            raise ValueError("Draft disappeared before fact-checking")
        run.status = RunStatus.BLOCKED if blocked else RunStatus.REVIEW
        run.draft.status = DraftStatus.BLOCKED if blocked else DraftStatus.HUMAN_REVIEW
        run.blocked_reason = fact_check.output.blocked_reason if blocked else None
        if not blocked:
            story.status = StoryStatus.REVIEW
        self.record_event(
            run,
            AgentRole.FACT_CHECKER,
            "Completed model-assisted evidence review",
            {
                "independent_source_count": len(publishers),
                "publication_blocked": blocked,
                "human_approval_required": True,
            },
            fact_check,
        )
        run.current_stage = "human_editor"
        run.completed_at = datetime.now(UTC)
        await self.session.commit()
        return run
