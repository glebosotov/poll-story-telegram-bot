"""Config class to load and validate environment variables."""

import logging
import os

from dotenv import dotenv_values, load_dotenv
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from telemetry import tracer


class Config:
    """Configuration class to load and validate environment variables."""

    def __init__(self) -> None:
        config = {
            **dotenv_values(".env"),
            **dotenv_values("../.env"),
            **os.environ,
        }
        load_dotenv()
        self.bot_token = config.get("BOT_TOKEN")
        self.channel_id = config.get("CHANNEL_ID")
        self.openai_api_key = config.get("OPENAI_API_KEY")
        self.openai_base_url = config.get("OPENAI_BASE_URL")
        self.google_api_key = config.get("GOOGLE_API_KEY")
        self.gemini_image_model = config.get("GEMINI_IMAGE_MODEL")
        self.gemini_tts_model = config.get("GEMINI_TTS_MODEL")
        self.image_prompt_start = config.get("IMAGE_PROMPT_START")
        self.dry_run = eval(config.get("DRY_RUN", "False"))
        self.openai_model = config.get("OPENAI_MODEL")
        self.max_context_chars = int(config.get("MAX_CONTEXT_CHARS", "15000"))
        self.initial_story_idea = config.get("INITIAL_STORY_IDEA")
        self.story_max_sentences = int(config.get("STORY_MAX_SENTENCES", "500"))
        self.poll_question_template = "Как продолжится история?"
        self.fallback_continue_prompt = "Продолжай как считаешь нужным."
        self.end_story_option = "Закончить историю"

    @tracer.start_as_current_span("validate")
    def validate(self) -> bool:
        """Validate the configuration loaded from environment variables."""
        valid = True
        current_span = trace.get_current_span()
        if not self.bot_token:
            logging.error("BOT_TOKEN is not set correctly.")
            valid = False
        if not self.channel_id:
            logging.error("CHANNEL_ID is not set correctly.")
            valid = False
        if not self.initial_story_idea:
            logging.error("INITIAL_STORY_IDEA cannot be empty.")
            valid = False
        if not self.openai_api_key or not self.openai_base_url:
            logging.error("Missing OpenAI API key or base URL.")
            valid = False
        if (
            not self.google_api_key
            or not self.gemini_image_model
            or not self.image_prompt_start
        ):
            logging.error(
                "GOOGLE_API_KEY and GEMINI_IMAGE_MODEL "
                "and IMAGE_PROMPT_START cannot be empty.",
            )
            valid = False
        if not self.initial_story_idea:
            logging.error("INITIAL_STORY_IDEA cannot be empty.")
            valid = False
        if not self.gemini_tts_model:
            logging.warning("GEMINI_TTS_MODEL is not set. Audio will not be generated.")
        if not valid:
            current_span.set_status(Status(StatusCode.ERROR))
        return valid
