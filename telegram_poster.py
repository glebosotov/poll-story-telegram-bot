import asyncio
import logging
import os
import random

import telegram
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from telegram import Bot, Message, Poll, ReplyParameters

from image_gen import make_gemini_image
from open_ai_gen import (
    generate_imagen_prompt,
    generate_poll_options_openai,
    generate_story_continuation_openai,
)
from state import (
    current_story_key,
    last_poll_message_id_key,
    load_state,
    save_state,
    story_finished_key,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- Configuration ---
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL")
IMAGE_PROMPT_START = os.getenv("IMAGE_PROMPT_START")
DRY_RUN = os.getenv("DRY_RUN", False)
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", 15000))
STORY_MAX_SENTENCES = int(os.getenv("STORY_MAX_SENTENCES", 500))


# Story settings
INITIAL_STORY_IDEA = """
Вселенная: Киберпанк-антиутопия 2049 года (в духе Blade Runner 2049)
Главный герой: Игорь Калинин, 26 лет, хакер-одиночка, специалист по машинному обучению. Вырос в трущобах Мегаполиса-47, не подозревает о существовании "Цифрового Эдема" — тайной нейросети, где сливаются сознания элиты и ИИ.
Начало сюжета:
Дождь. Вечный дождь. Он стекал по бронированному стеклу капсулы-кафе "Neon Samovar", оставляя за окном размытые блики неоновых реклам: «Обнови чипсы VisionCorp — увидишь мир иначе!», «Кредиты под 300% одобряем за 5 секунд!».
Игорь прижал ладонь к виску, пытаясь заглушить гул нейроимпланта. Дешёвый китайский чип глючил уже третью неделю, но на новый не хватало даже крипты. На счету светилось 0.003 BTC — хватит разве что на синткофе и плазменный батончик. Последний перевод от заказчика рассыпался в прах, когда агенты корпорации "НоваСейф" ворвались в его подпольную лабораторию. «Вас нет, Калинин. Ваш код — наша собственность». Спасли только резервные дроны-пчёлы, утянувшие жёсткий диск в вентиляционные шахты.
"""

POLL_QUESTION_TEMPLATE = "Как продолжится история?"
END_STORY_OPTION = "Закончить историю"

# --- End Configuration ---


def validate_config():
    valid = True
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set correctly.")
        valid = False
    if not CHANNEL_ID:
        logging.error("CHANNEL_ID is not set correctly.")
        valid = False
    if not INITIAL_STORY_IDEA:
        logging.error("INITIAL_STORY_IDEA cannot be empty.")
        valid = False
    if not OPENAI_API_KEY or not OPENAI_BASE_URL:
        logging.error("Missing OpenAI API key or base URL.")
        valid = False
    if not GEMINI_API_KEY or not GEMINI_IMAGE_MODEL or not IMAGE_PROMPT_START:
        logging.error(
            "GEMINI_API_KEY and GEMINI_IMAGE_MODEL and IMAGE_PROMPT_START cannot be empty."
        )
        valid = False
    return valid


async def get_poll_winner(bot: Bot, chat_id: str | int, message_id: int) -> str | None:
    if message_id is None:
        logging.warning("No message ID provided to get_poll_winner.")
        return None

    logging.info(f"Attempting to stop poll (Message ID: {message_id})...")
    try:
        updated_poll: Poll = await bot.stop_poll(chat_id=chat_id, message_id=message_id)
        logging.info(f"Poll stopped (Message ID: {message_id}).")

        winning_options = []
        max_votes = -1
        for option in updated_poll.options:
            if option.voter_count > max_votes:
                max_votes = option.voter_count
                winning_options = [option.text]
            elif option.voter_count == max_votes and max_votes > 0:
                winning_options.append(option.text)

        if max_votes > 0 and len(winning_options) == 1:
            winner_text = winning_options[0]
            logging.info(f"Poll winner determined: '{winner_text}' ({max_votes} votes)")
            return winner_text
        elif max_votes > 0:  # Tie, using random
            winner_text = random.choice(winning_options)
            logging.warning(
                f"Poll resulted in a tie ({len(winning_options)} options with {max_votes} votes). Picking first option: '{winner_text}'"
            )
            return winner_text
        else:
            logging.info("Poll closed with no votes. Randomly selecting a winner.")
            if updated_poll.options:
                random_winner = random.choice(updated_poll.options)
                winner_text = random_winner.text
                logging.info(f"Randomly selected winner: '{winner_text}'")
                return winner_text
            else:
                logging.warning("Poll closed with no votes and no options found.")
                return None

    except telegram.error.BadRequest as e:
        err_text = str(e).lower()
        if "poll has already been closed" in err_text:
            logging.info(
                f"Poll (ID: {message_id}) was already closed.",
                exc_info=True,
            )
            return None
        elif "message to stop poll not found" in err_text:
            logging.error(
                f"Could not find the poll message to stop (ID: {message_id}). Was it deleted?"
            )
            return None
        else:
            logging.error(f"Error stopping poll (BadRequest - ID: {message_id}): {e}")
            return None
    except telegram.error.Forbidden as e:
        logging.error(
            f"Error stopping poll (Forbidden - ID: {message_id}): {e}. Bot lacks permissions?",
            exc_info=True,
        )
        raise
    except telegram.error.TelegramError as e:
        logging.error(f"Error stopping poll (ID: {message_id}): {e}", exc_info=True)
        return None


async def run_story_step():
    """Performs one step: loads state, gets winner, generates next step, posts, saves state."""

    logging.info("--- Running Story Step --- ")
    state = load_state()
    current_story = state.get(current_story_key, "")
    last_poll_message_id = state.get(last_poll_message_id_key)
    story_finished = state.get(story_finished_key, False)
    if story_finished:
        logging.info("Story is already finished. Exiting.")
        return

    bot = Bot(token=BOT_TOKEN)

    next_prompt: str | None = None
    new_poll_message_id: int | None = None
    text_message: Message | None = None
    finish_story = False

    try:
        if last_poll_message_id:
            logging.info(
                f"Checking results for previous poll (ID: {last_poll_message_id})"
            )
            poll_winner = await get_poll_winner(bot, CHANNEL_ID, last_poll_message_id)
            if poll_winner:
                next_prompt = poll_winner
                if poll_winner == END_STORY_OPTION:
                    finish_story = True
                    logging.info("Ending story based on poll.")
            else:
                logging.warning(
                    f"No winner determined from the last poll (ID: {last_poll_message_id}). Using fallback."
                )

        new_story_part = None
        if not current_story:
            logging.info("No existing story found. Posting initial idea.")
            message_to_send = INITIAL_STORY_IDEA
            current_story = INITIAL_STORY_IDEA
            logging.info(f"Sending initial story part to channel {CHANNEL_ID}...")
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=message_to_send)
                logging.info("Initial story part sent.")
            except telegram.error.TelegramError as e:
                logging.error(f"Failed to send initial story part: {e}", exc_info=True)
                raise
        else:
            sentences = len(current_story.split("."))
            if sentences > STORY_MAX_SENTENCES:
                logging.info(
                    f"Current story has {sentences} sentences. Ending story based on length."
                )
                finish_story = True

            if not next_prompt:
                logging.error(
                    "No prompt available for continuation (should not happen!). Using fallback."
                )
                next_prompt = "Продолжай как считаешь нужным."

            logging.info(
                f"Generating story {'finish' if finish_story else 'continuation'} based on: '{next_prompt}'"
            )
            new_story_part = generate_story_continuation_openai(
                openai_client,
                current_story,
                next_prompt,
                OPENAI_MODEL,
                MAX_CONTEXT_CHARS,
                end_story=finish_story,
            )

            imagen_prompt = generate_imagen_prompt(
                openai_client,
                new_story_part,
                IMAGE_PROMPT_START,
                OPENAI_MODEL,
            )

            image = make_gemini_image(
                GEMINI_API_KEY,
                GEMINI_IMAGE_MODEL,
                imagen_prompt or new_story_part,
            )

            if new_story_part and new_story_part.strip():
                logging.info(f"Sending new story part to channel {CHANNEL_ID}...")
                try:
                    reply_parameters = None
                    if image:
                        photo_message = await bot.send_photo(
                            chat_id=CHANNEL_ID,
                            photo=image,
                            has_spoiler=True,
                        )
                        reply_parameters = ReplyParameters(photo_message.id)
                    text_message = await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=new_story_part,
                        reply_parameters=reply_parameters,
                    )
                    logging.info("New story part sent.")
                    current_story += new_story_part
                except telegram.error.TelegramError as e:
                    logging.error(f"Failed to send new story part: {e}", exc_info=True)
                    raise
            else:
                logging.error(
                    "Story continuation failed or returned empty. Story not updated. Interrupting step."
                )
                raise RuntimeError("LLM failed to generate story continuation.")
        if not finish_story:
            logging.info("Generating poll options based on current story...")
            make_end_story_option = False
            if sentences > STORY_MAX_SENTENCES * 0.8:
                make_end_story_option = True
                logging.info(
                    f"Story is {sentences} sentences long. Adding end story option to the poll."
                )
            poll_options = generate_poll_options_openai(
                openai_client,
                current_story,
                OPENAI_MODEL,
                END_STORY_OPTION,
                MAX_CONTEXT_CHARS,
                make_end_story_option=make_end_story_option,
            )

            if not poll_options or len(poll_options) != 4:
                logging.error(
                    "Could not generate valid poll options. Skipping poll posting."
                )
                new_poll_message_id = None
            else:
                truncated_options = [opt[:90] for opt in poll_options]
                logging.info(
                    f"Generated {len(truncated_options)} poll options (truncated if needed)."
                )
                try:
                    reply_params = (
                        ReplyParameters(text_message.id) if text_message else None
                    )
                    sent_poll_message: Message = await bot.send_poll(
                        chat_id=CHANNEL_ID,
                        question=POLL_QUESTION_TEMPLATE,
                        options=truncated_options,
                        is_anonymous=True,
                        reply_parameters=reply_params,
                    )
                    new_poll_message_id = sent_poll_message.message_id
                    logging.info(f"New poll sent (Message ID: {new_poll_message_id}).")
                except telegram.error.TelegramError as poll_error:
                    logging.error(
                        f"Error sending poll: {poll_error}. Skipping poll posting.",
                        exc_info=True,
                    )
                    new_poll_message_id = None
        else:
            logging.info("Ending story. No new poll will be posted.")
            new_poll_message_id = None

        if not DRY_RUN:
            save_state(
                current_story,
                new_poll_message_id,
                story_finished=finish_story,
            )
        else:
            logging.info("DRY_RUN is enabled. State not saved. ")
        logging.info("--- Story Step Completed Successfully --- ")

    except OpenAIError as e:
        logging.error("\n--- An OpenAI API Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}")
        logging.error(
            "Script interrupted due to OpenAI API error. State NOT saved for this run."
        )
    except telegram.error.TelegramError as e:
        logging.error("\n--- A Telegram API Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}")
        logging.error(
            "Script interrupted due to Telegram API error. State NOT saved for this run."
        )
    except RuntimeError as e:
        logging.error("\n--- A Runtime Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}")
        logging.error("Script interrupted. State NOT saved for this run.")
    except Exception as e:
        logging.error("\n--- An Unexpected Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}", exc_info=True)
        logging.error(
            "Script interrupted due to unexpected error. State NOT saved for this run."
        )


if __name__ == "__main__":
    logging.info("Script execution started.")

    if not validate_config():
        logging.critical("Configuration validation failed. Check .env")
        exit(1)
    openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    logging.info("Configuration validated. Running async story step.")
    asyncio.run(run_story_step())

    logging.info("Script execution finished.")
