import asyncio
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from newsroom_api.models import (
    AdversarialFinding,
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
    Source,
    Story,
    StoryStatus,
)


@dataclass(frozen=True)
class ExtractedClaim:
    source_id: uuid.UUID
    text: str
    quote: str


def _first_sentence(text: str) -> str:
    compact = " ".join(text.split())
    sentence = re.split(r"(?<=[.!?])\s+", compact, maxsplit=1)[0]
    return sentence[:500]


async def _research_source(source: Source) -> ExtractedClaim:
    await asyncio.sleep(0)
    return ExtractedClaim(
        source_id=source.id,
        text=_first_sentence(source.snapshot_text),
        quote=source.snapshot_text[:280],
    )


class DeterministicNewsroomWorkflow:
    """A predictable workflow used to prove orchestration before live model calls."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sequence = 0

    def record_event(
        self,
        run: InvestigationRun,
        agent: AgentRole,
        summary: str,
        payload: dict[str, object],
    ) -> None:
        self.sequence += 1
        run.events.append(
            AgentEvent(
                sequence=self.sequence,
                agent=agent,
                status=EventStatus.COMPLETED,
                summary=summary,
                payload=payload,
            )
        )

    async def execute(self, run: InvestigationRun) -> InvestigationRun:
        persisted_run = await self.session.scalar(
            select(InvestigationRun)
            .where(InvestigationRun.id == run.id)
            .options(
                selectinload(InvestigationRun.events),
                selectinload(InvestigationRun.claims),
                selectinload(InvestigationRun.draft),
                selectinload(InvestigationRun.adversarial_findings),
            )
        )
        if persisted_run is None:
            raise ValueError("Investigation disappeared before execution")
        run = persisted_run
        story = await self.session.scalar(
            select(Story).where(Story.id == run.story_id).options(selectinload(Story.sources))
        )
        if story is None:
            raise ValueError("Story disappeared before the investigation started")

        run.status = RunStatus.RUNNING
        run.current_stage = AgentRole.ASSIGNMENT_EDITOR.value
        await self.session.flush()

        source_count = len(story.sources)
        self.record_event(
            run,
            AgentRole.ASSIGNMENT_EDITOR,
            f"Created assignments for {source_count} source snapshots",
            {
                "assignments": [
                    "extract_atomic_claims",
                    "prepare_cited_draft",
                    "verify_source_independence",
                ],
                "source_count": source_count,
            },
        )

        run.current_stage = AgentRole.RESEARCHER.value
        extracted = await asyncio.gather(*(_research_source(source) for source in story.sources))
        source_by_id = {source.id: source for source in story.sources}
        for item in extracted:
            claim = Claim(
                source_id=item.source_id,
                text=item.text,
                verdict=ClaimVerdict.SUPPORTED,
                confidence=0.65,
            )
            claim.citations.append(Citation(source_id=item.source_id, quote=item.quote))
            run.claims.append(claim)
        self.record_event(
            run,
            AgentRole.RESEARCHER,
            f"Extracted {len(extracted)} source-backed claims in parallel",
            {"claim_count": len(extracted), "mode": "parallel_deterministic"},
        )

        run.current_stage = AgentRole.REPORTER.value
        paragraphs = [f"{claim.text} [{index}]" for index, claim in enumerate(run.claims, 1)]
        sources = [
            f"[{index}] {source_by_id[claim.source_id].title}"
            for index, claim in enumerate(run.claims, 1)
        ]
        body = "\n\n".join(paragraphs) or "No reportable claims were found."
        if sources:
            body = f"{body}\n\nSources\n" + "\n".join(sources)
        draft = Draft(title=story.title, body=body, status=DraftStatus.BLOCKED)
        run.draft = draft
        self.record_event(
            run,
            AgentRole.REPORTER,
            "Prepared a draft with sentence-level source markers",
            {"paragraph_count": len(paragraphs), "citation_count": len(sources)},
        )

        misinformation_terms = {"hoax", "secretly", "everyone knows", "undeniable"}
        misinformation_findings = 0
        for index, claim in enumerate(run.claims):
            matched = next(
                (term for term in misinformation_terms if term in claim.text.casefold()), None
            )
            if matched:
                misinformation_findings += 1
                run.adversarial_findings.append(
                    AdversarialFinding(
                        agent=AgentRole.MISINFORMATION_ANALYST.value,
                        severity="high",
                        category="unsupported_rhetoric",
                        claim_index=index,
                        summary=f"Claim uses high-risk assertion language: {matched}.",
                        recommendation="Replace the assertion with directly sourced language.",
                    )
                )
        self.record_event(
            run,
            AgentRole.MISINFORMATION_ANALYST,
            f"Red-teamed claims and raised {misinformation_findings} findings",
            {
                "finding_count": misinformation_findings,
                "publication_blocked": misinformation_findings > 0,
            },
        )

        bias_terms = {"disaster", "shocking", "obviously", "outrageous"}
        draft_text = f"{draft.title} {draft.body}".casefold()
        matched_bias = sorted(term for term in bias_terms if term in draft_text)
        for term in matched_bias:
            run.adversarial_findings.append(
                AdversarialFinding(
                    agent=AgentRole.BIAS_AUDITOR.value,
                    severity="medium",
                    category="loaded_language",
                    claim_index=None,
                    summary=f"Draft framing includes loaded term: {term}.",
                    recommendation="Use neutral, attributable language.",
                )
            )
        self.record_event(
            run,
            AgentRole.BIAS_AUDITOR,
            f"Audited framing and raised {len(matched_bias)} findings",
            {"finding_count": len(matched_bias), "publication_blocked": False},
        )

        run.current_stage = AgentRole.FACT_CHECKER.value
        publishers = {
            (source.publisher or source.url or str(source.id)).casefold()
            for source in story.sources
        }
        independently_sourced = len(publishers) >= 2
        if source_count == 0:
            blocked_reason = "No source snapshots are attached to this story."
        elif not independently_sourced:
            blocked_reason = "At least two independent sources are required for human review."
        else:
            blocked_reason = None

        if misinformation_findings:
            blocked_reason = "Misinformation analyst found high-risk unsupported rhetoric."

        if blocked_reason:
            for claim in run.claims:
                claim.verdict = ClaimVerdict.UNCORROBORATED
                claim.confidence = 0.45
            run.status = RunStatus.BLOCKED
            run.blocked_reason = blocked_reason
            draft.status = DraftStatus.BLOCKED
        else:
            for claim in run.claims:
                claim.confidence = 0.8
            run.status = RunStatus.REVIEW
            draft.status = DraftStatus.HUMAN_REVIEW
            story.status = StoryStatus.REVIEW

        self.record_event(
            run,
            AgentRole.FACT_CHECKER,
            "Completed deterministic evidence and independence checks",
            {
                "independent_source_count": len(publishers),
                "publication_blocked": blocked_reason is not None,
                "human_approval_required": True,
            },
        )
        run.current_stage = "human_editor"
        run.completed_at = datetime.now(UTC)
        await self.session.commit()
        return run
