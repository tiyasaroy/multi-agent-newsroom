import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from newsroom_api.models import SourceKind, StoryStatus


class SourceCreate(BaseModel):
    title: str = Field(min_length=3, max_length=320)
    url: HttpUrl | None = None
    publisher: str | None = Field(default=None, max_length=240)
    kind: SourceKind = SourceKind.ARTICLE
    snapshot_text: str = Field(min_length=20)
    published_at: datetime | None = None

    @model_validator(mode="after")
    def require_url_for_web_sources(self) -> "SourceCreate":
        if self.kind != SourceKind.MANUAL and self.url is None:
            raise ValueError("url is required unless the source kind is manual")
        return self


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    story_id: uuid.UUID
    title: str
    url: str | None
    publisher: str | None
    kind: SourceKind
    snapshot_text: str
    published_at: datetime | None
    created_at: datetime


class StoryCreate(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    summary: str | None = Field(default=None, max_length=2000)


class StoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: str | None
    status: StoryStatus
    created_at: datetime
    updated_at: datetime


class StoryDetail(StoryRead):
    sources: list[SourceRead]
