"""Main file to invoke for generation."""

import asyncio
import logging
import sys

from config import Config
from openai import OpenAI
from telegram_poster import run_story_step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main() -> None:
    """Run the script."""
    logging.info("Script execution started.")
    config = Config()

    if not config.validate():
        logging.critical("Configuration validation failed. Check .env")
        sys.exit(1)

    openai_client = OpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )

    logging.info("Configuration validated. Running async story step.")
    asyncio.run(run_story_step(config, openai_client))

    logging.info("Script execution finished.")


if __name__ == "__main__":
    main()
