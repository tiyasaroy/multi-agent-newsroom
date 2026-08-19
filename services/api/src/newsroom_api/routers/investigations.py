import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from newsroom_api.database import get_session
from newsroom_api.models import Claim, InvestigationRun, RunStatus, Story
from newsroom_api.orchestration.deterministic import DeterministicNewsroomWorkflow
from newsroom_api.schemas import InvestigationRunRead

router = APIRouter(tags=["investigations"])
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


def run_query() -> object:
    return select(InvestigationRun).options(
        selectinload(InvestigationRun.events),
        selectinload(InvestigationRun.claims).selectinload(Claim.citations),
        selectinload(InvestigationRun.draft),
    )


async def load_run(session: AsyncSession, run_id: uuid.UUID) -> InvestigationRun:
    run = await session.scalar(run_query().where(InvestigationRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return run


async def execute_new_run(
    session: AsyncSession, story_id: uuid.UUID, request_key: str
) -> InvestigationRun:
    run = InvestigationRun(story_id=story_id, request_key=request_key)
    session.add(run)
    await session.commit()
    try:
        await DeterministicNewsroomWorkflow(session).execute(run)
    except Exception as exc:
        await session.rollback()
        failed_run = await session.get(InvestigationRun, run.id)
        if failed_run is not None:
            failed_run.status = RunStatus.FAILED
            failed_run.error_message = str(exc)
            await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation workflow failed",
        ) from exc
    return await load_run(session, run.id)


@router.post(
    "/stories/{story_id}/investigations",
    response_model=InvestigationRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_investigation(
    story_id: uuid.UUID,
    session: DatabaseSession,
    idempotency_key: Annotated[str | None, Header(max_length=120)] = None,
) -> InvestigationRun:
    request_key = idempotency_key or str(uuid.uuid4())
    existing = await session.scalar(run_query().where(InvestigationRun.request_key == request_key))
    if existing is not None:
        if existing.story_id != story_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key belongs to another story",
            )
        return existing

    story_exists = await session.scalar(select(Story.id).where(Story.id == story_id))
    if story_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    return await execute_new_run(session, story_id, request_key)


@router.get("/investigations/{run_id}", response_model=InvestigationRunRead)
async def get_investigation(run_id: uuid.UUID, session: DatabaseSession) -> InvestigationRun:
    return await load_run(session, run_id)


@router.post("/investigations/{run_id}/retry", response_model=InvestigationRunRead)
async def retry_investigation(
    run_id: uuid.UUID,
    session: DatabaseSession,
    idempotency_key: Annotated[str | None, Header(max_length=120)] = None,
) -> InvestigationRun:
    previous = await load_run(session, run_id)
    if previous.status not in {RunStatus.BLOCKED, RunStatus.FAILED, RunStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only blocked, failed, or cancelled investigations can be retried",
        )
    return await execute_new_run(session, previous.story_id, idempotency_key or str(uuid.uuid4()))


@router.post("/investigations/{run_id}/cancel", response_model=InvestigationRunRead)
async def cancel_investigation(run_id: uuid.UUID, session: DatabaseSession) -> InvestigationRun:
    run = await load_run(session, run_id)
    if run.status not in {RunStatus.QUEUED, RunStatus.RUNNING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only queued or running investigations can be cancelled",
        )
    run.status = RunStatus.CANCELLED
    run.current_stage = None
    await session.commit()
    return await load_run(session, run.id)
