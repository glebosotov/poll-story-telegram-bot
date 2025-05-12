"""Interactive story generator bot for Telegram using OpenAI and Gemini APIs."""

import logging
import random

import telegram
from openai import OpenAI
from telegram import Bot, Message, Poll, ReplyParameters

from config import Config
from image_gen import make_gemini_image
from open_ai_gen import (
    generate_imagen_prompt,
    generate_poll_options,
    generate_story_continuation,
)
from state import StoryState, load_state, save_state


async def get_poll_winner(bot: Bot, chat_id: str | int, message_id: int) -> str | None:
    """Get the winner of a poll by stopping it and checking the results."""
    if message_id is None:
        logging.warning("No message ID provided to get_poll_winner.")
        return None

    logging.info(f"Attempting to stop poll (Message ID: {message_id})...")
    try:
        updated_poll: Poll = await bot.stop_poll(chat_id=chat_id, message_id=message_id)
        logging.info(f"Poll stopped (Message ID: {message_id}).")
        options = updated_poll.options
        if not options:
            logging.warning("Poll closed with no votes and no options found.")
            return None

        winning_options = []
        max_votes = -1
        for option in options:
            if option.voter_count > max_votes:
                max_votes = option.voter_count
                winning_options = [option.text]
            elif option.voter_count == max_votes and max_votes > 0:
                winning_options.append(option.text)

        if max_votes > 0 and len(winning_options) == 1:
            winner_text = winning_options[0]
            logging.info(f"Poll winner determined: '{winner_text}' ({max_votes} votes)")
            return winner_text
        if max_votes > 0:
            winner_text = random.choice(winning_options)
            logging.warning(
                f"Poll resulted in a tie ({len(winning_options)} options with "
                f"{max_votes} votes). Picking first option: '{winner_text}'",
            )
            return winner_text
        random_winner = random.choice(options)
        winner_text = random_winner.text
        logging.info(f"Randomly selected winner (no votes): '{winner_text}'")
        return winner_text

    except telegram.error.BadRequest as e:
        err_text = str(e).lower()
        if "poll has already been closed" in err_text:
            logging.info(f"Poll (ID: {message_id}) was already closed.")
        if "message to stop poll not found" in err_text:
            logging.error(f"Could not find the poll message to stop (ID: {message_id})")
        logging.error(f"Error stopping poll (BadRequest - ID: {message_id}): {e}")
    except telegram.error.Forbidden as e:
        logging.error(f"Error stopping poll (Forbidden - ID: {message_id}): {e}.")
    except telegram.error.TelegramError as e:
        logging.error(f"Error stopping poll (ID: {message_id}): {e}")
    return None


async def run_story_step(config: Config, openai_client: OpenAI) -> None:
    """Post the story continuation, an image and a poll."""
    logging.info("Entering run_story_step")
    state = load_state()
    current_story = state.current_story
    last_poll_message_id = state.last_poll_message_id
    story_finished = state.story_finished
    if story_finished:
        logging.info("Story is already finished. Exiting.")
        return

    bot = Bot(token=config.bot_token)

    next_prompt: str | None = None
    new_poll_message_id: int | None = None
    new_story_part: str | None = None
    new_story_part_message: Message | None = None
    finish_story = False
    sentences = 0

    try:
        # try to get next prompt from poll
        if last_poll_message_id:
            logging.info(f"Checking previous poll (ID: {last_poll_message_id})")
            poll_winner = await get_poll_winner(
                bot,
                config.channel_id,
                last_poll_message_id,
            )
            if poll_winner:
                next_prompt = poll_winner
                if poll_winner == config.end_story_option:
                    finish_story = True
                    logging.info("Ending story based on poll.")

        if not current_story:
            logging.info("No existing story found. Posting initial idea.")
            message_to_send = config.initial_story_idea
            current_story = config.initial_story_idea
            logging.info(f"Sending initial story part to {config.channel_id}")
            await bot.send_message(chat_id=config.channel_id, text=message_to_send)
            logging.info("Initial story part sent.")
        else:
            sentences = len(current_story.split("."))
            if sentences > config.story_max_sentences:
                logging.info(
                    f"Current story has {sentences} sentences. "
                    "Ending story based on length.",
                )
                finish_story = True

            if not next_prompt:
                logging.error("No prompt available for continuation. Using fallback.")
                next_prompt = config.fallback_continue_prompt

            logging.info(
                "Generating story "
                f"{'finish' if finish_story else f'continuation using {next_prompt}'} ",
            )
            new_story_part = generate_story_continuation(
                openai_client,
                current_story,
                next_prompt,
                config,
                end_story=finish_story,
            )

            imagen_prompt = generate_imagen_prompt(
                openai_client,
                new_story_part,
                config.image_prompt_start,
                config.openai_model,
            )

            image = make_gemini_image(
                config.gemini_api_key,
                config.gemini_image_model,
                imagen_prompt or new_story_part,
            )

            if not new_story_part or new_story_part.strip() == "":
                logging.error(
                    "Story continuation failed or returned empty. "
                    "Story not updated. Interrupting step.",
                )
                raise RuntimeError("Failed to generate story continuation.")

            logging.info(f"Sending new story part to {config.channel_id}")
            reply_parameters = None
            if image:
                photo_message = await bot.send_photo(
                    chat_id=config.channel_id,
                    photo=image,
                    has_spoiler=True,
                )
                reply_parameters = ReplyParameters(photo_message.id)
            new_story_part_message = await bot.send_message(
                chat_id=config.channel_id,
                text=new_story_part,
                reply_parameters=reply_parameters,
            )
            logging.info("New story part sent.")
            current_story += new_story_part

        if not finish_story:
            logging.info("Generating poll options based on current story...")
            make_end_story_option = False
            if sentences > config.story_max_sentences * 0.8:
                make_end_story_option = True
                logging.info(
                    f"Story is {sentences} sentences long. "
                    "Adding end story option to the poll.",
                )
            poll_options = generate_poll_options(
                openai_client,
                current_story,
                config,
                make_end_story_option=make_end_story_option,
            )

            if not poll_options or len(poll_options) > telegram.Poll.MAX_OPTION_LENGTH:
                logging.error(
                    "Could not generate valid poll options. Skipping poll posting.",
                )
                new_poll_message_id = None
            else:
                truncated_options = [opt[:90] for opt in poll_options]
                logging.info(f"Generated {len(truncated_options)} poll options.")
                try:
                    reply_params = (
                        ReplyParameters(new_story_part_message.id)
                        if new_story_part_message
                        else None
                    )
                    sent_poll_message: Message = await bot.send_poll(
                        chat_id=config.channel_id,
                        question=config.poll_question_template,
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

        if not config.dry_run:
            state = StoryState(
                current_story,
                new_poll_message_id,
                finish_story,
            )
            save_state(state)
        else:
            logging.info("DRY_RUN is enabled. State not saved. ")
        logging.info("Story Step Completed Successfully ")

    except Exception as e:
        logging.error("\n--- An Unexpected Error Occurred During Story Step --- ")
        logging.error(f"Error message: {e}")
        logging.error(
            "Script interrupted due to unexpected error. State NOT saved for this run.",
        )
