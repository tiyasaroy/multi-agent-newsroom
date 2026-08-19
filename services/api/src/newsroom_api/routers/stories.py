import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from newsroom_api.database import get_session
from newsroom_api.models import Source, Story, StoryStatus
from newsroom_api.schemas import SourceCreate, SourceRead, StoryCreate, StoryDetail, StoryRead

router = APIRouter(prefix="/stories", tags=["stories"])
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


async def get_story_or_404(session: AsyncSession, story_id: uuid.UUID) -> Story:
    result = await session.execute(
        select(Story).where(Story.id == story_id).options(selectinload(Story.sources))
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


@router.post("", response_model=StoryRead, status_code=status.HTTP_201_CREATED)
async def create_story(payload: StoryCreate, session: DatabaseSession) -> Story:
    story = Story(**payload.model_dump())
    session.add(story)
    await session.commit()
    await session.refresh(story)
    return story


@router.get("", response_model=list[StoryRead])
async def list_stories(
    session: DatabaseSession,
    story_status: StoryStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Story]:
    query = select(Story).order_by(Story.updated_at.desc()).limit(limit).offset(offset)
    if story_status is not None:
        query = query.where(Story.status == story_status)
    return list((await session.scalars(query)).all())


@router.get("/{story_id}", response_model=StoryDetail)
async def get_story(story_id: uuid.UUID, session: DatabaseSession) -> Story:
    return await get_story_or_404(session, story_id)


@router.post(
    "/{story_id}/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED
)
async def add_source(
    story_id: uuid.UUID, payload: SourceCreate, session: DatabaseSession
) -> Source:
    story_exists = await session.scalar(select(func.count()).where(Story.id == story_id))
    if not story_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    source_data = payload.model_dump()
    source_data["url"] = str(payload.url) if payload.url is not None else None
    source = Source(story_id=story_id, **source_data)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source
