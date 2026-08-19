import asyncio
import uuid
from types import SimpleNamespace

from newsroom_api.providers.base import ResearchOutput, SourceInput
from newsroom_api.providers.gemini_provider import GeminiNewsroomProvider


class FakeModels:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


def test_gemini_research_returns_structured_output_and_telemetry() -> None:
    source_id = uuid.uuid4()
    parsed = ResearchOutput(
        claims=[
            {
                "source_id": source_id,
                "text": "The council approved the proposal.",
                "quote": "approved the proposal",
                "confidence": 0.94,
            }
        ]
    )
    response = SimpleNamespace(
        parsed=parsed,
        text=None,
        usage_metadata=SimpleNamespace(
            prompt_token_count=120,
            candidates_token_count=30,
        ),
    )
    models = FakeModels(response)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiNewsroomProvider(
        api_key="test-key",
        model="gemini-test",
        input_cost_per_million=1,
        output_cost_per_million=2,
        client=client,
    )

    result = asyncio.run(
        provider.research(
            "Council vote",
            [
                SourceInput(
                    id=source_id,
                    title="Council minutes",
                    publisher="City Council",
                    snapshot_text="The council approved the proposal.",
                )
            ],
        )
    )

    assert result.output == parsed
    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.prompt_version == "researcher-v1"
    assert result.input_tokens == 120
    assert result.output_tokens == 30
    assert result.estimated_cost_usd == 0.00018
    assert models.calls[0]["model"] == "gemini-test"


def test_gemini_parses_json_when_sdk_has_no_parsed_value() -> None:
    response = SimpleNamespace(
        parsed=None,
        text='{"claims": []}',
        usage_metadata=None,
    )
    models = FakeModels(response)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiNewsroomProvider(
        api_key="test-key",
        model="gemini-test",
        client=client,
    )

    result = asyncio.run(provider.research("Empty story", []))

    assert result.output == ResearchOutput(claims=[])
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.estimated_cost_usd is None
