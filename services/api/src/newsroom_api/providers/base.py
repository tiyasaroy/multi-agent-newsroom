import uuid
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, Field


class SourceInput(BaseModel):
    id: uuid.UUID
    title: str
    publisher: str | None
    snapshot_text: str


class ModelClaim(BaseModel):
    source_id: uuid.UUID
    text: str = Field(min_length=3, max_length=500)
    quote: str = Field(min_length=3, max_length=500)
    confidence: float = Field(ge=0, le=1)


class ResearchOutput(BaseModel):
    claims: list[ModelClaim]


class DraftOutput(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    body: str = Field(min_length=20)


class ClaimReview(BaseModel):
    claim_index: int = Field(ge=0)
    verdict: str = Field(pattern="^(supported|uncorroborated|disputed)$")
    confidence: float = Field(ge=0, le=1)


class FactCheckOutput(BaseModel):
    reviews: list[ClaimReview]
    publication_blocked: bool
    blocked_reason: str | None = None


OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class ModelResult(Generic[OutputT]):
    output: OutputT
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float | None


class NewsroomModelProvider(Protocol):
    provider_name: str

    async def research(
        self, story_title: str, sources: list[SourceInput]
    ) -> ModelResult[ResearchOutput]: ...

    async def draft(
        self, story_title: str, claims: list[ModelClaim]
    ) -> ModelResult[DraftOutput]: ...

    async def fact_check(
        self, claims: list[ModelClaim], independent_source_count: int
    ) -> ModelResult[FactCheckOutput]: ...
