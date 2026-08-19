import asyncio
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from newsroom_api.config import get_settings
from newsroom_api.database import get_session, session_factory
from newsroom_api.models import AgentEvent, Claim, InvestigationRun, RunStatus, Story
from newsroom_api.orchestration.deterministic import DeterministicNewsroomWorkflow
from newsroom_api.orchestration.model_workflow import ModelNewsroomWorkflow
from newsroom_api.providers.factory import create_model_provider
from newsroom_api.schemas import AgentEventRead, InvestigationRunRead

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
    session: AsyncSession, story_id: uuid.UUID, request_key: str, provider_requested: str = "auto"
) -> InvestigationRun:
    provider = create_model_provider(get_settings(), provider_requested)
    provider_used = provider.provider_name if provider is not None else "deterministic"
    run = InvestigationRun(
        story_id=story_id,
        request_key=request_key,
        provider_requested=provider_requested,
        provider_used=provider_used,
    )
    session.add(run)
    await session.commit()
    try:
        if provider is None:
            await DeterministicNewsroomWorkflow(session).execute(run)
        else:
            await ModelNewsroomWorkflow(session, provider).execute(run)
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


async def execute_background_run(run_id: uuid.UUID, provider_requested: str) -> None:
    async with session_factory() as session:
        run = await session.get(InvestigationRun, run_id)
        if run is None or run.status != RunStatus.QUEUED:
            return
        provider = create_model_provider(get_settings(), provider_requested)
        try:
            if provider is None:
                await DeterministicNewsroomWorkflow(session).execute(run)
            else:
                await ModelNewsroomWorkflow(session, provider).execute(run)
        except Exception as exc:
            await session.rollback()
            failed_run = await session.get(InvestigationRun, run_id)
            if failed_run is not None:
                failed_run.status = RunStatus.FAILED
                failed_run.error_message = str(exc)
                await session.commit()


@router.post(
    "/stories/{story_id}/investigations",
    response_model=InvestigationRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_investigation(
    story_id: uuid.UUID,
    session: DatabaseSession,
    background_tasks: BackgroundTasks,
    response: Response,
    idempotency_key: Annotated[str | None, Header(max_length=120)] = None,
    provider: Literal["auto", "deterministic", "mock", "openai"] = "auto",
    background: bool = False,
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

    if background:
        model_provider = create_model_provider(get_settings(), provider)
        run = InvestigationRun(
            story_id=story_id,
            request_key=request_key,
            provider_requested=provider,
            provider_used=(
                model_provider.provider_name if model_provider is not None else "deterministic"
            ),
        )
        session.add(run)
        await session.commit()
        background_tasks.add_task(execute_background_run, run.id, provider)
        response.status_code = status.HTTP_202_ACCEPTED
        return await load_run(session, run.id)

    return await execute_new_run(session, story_id, request_key, provider)


@router.get("/investigations/{run_id}", response_model=InvestigationRunRead)
async def get_investigation(run_id: uuid.UUID, session: DatabaseSession) -> InvestigationRun:
    return await load_run(session, run_id)


@router.get("/investigations/{run_id}/events")
async def stream_investigation_events(
    run_id: uuid.UUID, session: DatabaseSession
) -> StreamingResponse:
    await load_run(session, run_id)

    async def event_stream():
        last_sequence = 0
        terminal = {RunStatus.REVIEW, RunStatus.BLOCKED, RunStatus.FAILED, RunStatus.CANCELLED}
        while True:
            events = list(
                (
                    await session.scalars(
                        select(AgentEvent)
                        .where(
                            AgentEvent.run_id == run_id,
                            AgentEvent.sequence > last_sequence,
                        )
                        .order_by(AgentEvent.sequence)
                    )
                ).all()
            )
            for event in events:
                last_sequence = event.sequence
                payload = AgentEventRead.model_validate(event).model_dump_json()
                yield f"event: agent_event\ndata: {payload}\n\n"
            run_status = await session.scalar(
                select(InvestigationRun.status).where(InvestigationRun.id == run_id)
            )
            if run_status in terminal:
                yield f'event: complete\ndata: {{"status":"{run_status.value}"}}\n\n'
                return
            yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/investigations/{run_id}/retry", response_model=InvestigationRunRead)
async def retry_investigation(
    run_id: uuid.UUID,
    session: DatabaseSession,
    idempotency_key: Annotated[str | None, Header(max_length=120)] = None,
    provider: Literal["auto", "deterministic", "mock", "openai"] = "auto",
) -> InvestigationRun:
    previous = await load_run(session, run_id)
    if previous.status not in {RunStatus.BLOCKED, RunStatus.FAILED, RunStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only blocked, failed, or cancelled investigations can be retried",
        )
    return await execute_new_run(
        session, previous.story_id, idempotency_key or str(uuid.uuid4()), provider
    )


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
