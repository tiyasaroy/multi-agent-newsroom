from newsroom_api.providers.base import (
    ClaimReview,
    DraftOutput,
    FactCheckOutput,
    ModelClaim,
    ModelResult,
    ResearchOutput,
    SourceInput,
)


class MockNewsroomProvider:
    """Deterministic model-shaped provider for tests and demonstrations."""

    provider_name = "mock"
    model = "mock-newsroom-v1"

    def result(self, output: object, prompt_version: str) -> ModelResult:
        return ModelResult(
            output=output,
            provider=self.provider_name,
            model=self.model,
            prompt_version=prompt_version,
            input_tokens=100,
            output_tokens=50,
            latency_ms=5,
            estimated_cost_usd=0.0,
        )

    async def research(
        self, story_title: str, sources: list[SourceInput]
    ) -> ModelResult[ResearchOutput]:
        del story_title
        claims = [
            ModelClaim(
                source_id=source.id,
                text=source.snapshot_text.split(".", maxsplit=1)[0] + ".",
                quote=source.snapshot_text[:280],
                confidence=0.72,
            )
            for source in sources
        ]
        return self.result(ResearchOutput(claims=claims), "researcher-v1")

    async def draft(
        self, story_title: str, claims: list[ModelClaim]
    ) -> ModelResult[DraftOutput]:
        body = "\n\n".join(f"{claim.text} [{index}]" for index, claim in enumerate(claims, 1))
        return self.result(DraftOutput(title=story_title, body=body), "reporter-v1")

    async def fact_check(
        self, claims: list[ModelClaim], independent_source_count: int
    ) -> ModelResult[FactCheckOutput]:
        blocked = independent_source_count < 2
        verdict = "uncorroborated" if blocked else "supported"
        return self.result(
            FactCheckOutput(
                reviews=[
                    ClaimReview(
                        claim_index=index,
                        verdict=verdict,
                        confidence=0.5 if blocked else 0.82,
                    )
                    for index in range(len(claims))
                ],
                publication_blocked=blocked,
                blocked_reason=(
                    "At least two independent sources are required for human review."
                    if blocked
                    else None
                ),
            ),
            "fact-checker-v1",
        )
