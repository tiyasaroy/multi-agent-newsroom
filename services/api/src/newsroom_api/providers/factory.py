from newsroom_api.config import Settings
from newsroom_api.providers.base import NewsroomModelProvider
from newsroom_api.providers.gemini_provider import GeminiNewsroomProvider
from newsroom_api.providers.mock import MockNewsroomProvider
from newsroom_api.providers.openai_provider import OpenAINewsroomProvider


def create_model_provider(settings: Settings, requested: str) -> NewsroomModelProvider | None:
    selected = settings.newsroom_provider if requested == "auto" else requested
    if selected == "mock":
        return MockNewsroomProvider()
    if selected == "gemini" and settings.gemini_api_key:
        return GeminiNewsroomProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            input_cost_per_million=settings.gemini_input_cost_per_million,
            output_cost_per_million=settings.gemini_output_cost_per_million,
        )
    if selected != "openai" or not settings.openai_api_key:
        return None
    return OpenAINewsroomProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        input_cost_per_million=settings.openai_input_cost_per_million,
        output_cost_per_million=settings.openai_output_cost_per_million,
    )
