"""Interactive story generator bot for Telegram using OpenAI and Gemini APIs."""

import logging
import random

import telegram
from config import Config
from google_tts import generate_audio_from_text
from image_gen import make_gemini_image
from open_ai_gen import (
    generate_imagen_prompt,
    generate_poll_options,
    generate_story_continuation,
)
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from state import StoryState, load_state, save_state
from telegram import Bot, Message, Poll, ReplyParameters
from telemetry import tracer


@tracer.start_as_current_span("get_poll_winner")
async def get_poll_winner(bot: Bot, chat_id: str | int, message_id: int) -> str | None:
    """Get the winner of a poll by stopping it and checking the results."""
    current_span = trace.get_current_span()
    current_span.set_attribute("message_id", message_id)
    if message_id is None:
        current_span.set_status(
            StatusCode.ERROR,
            "No message ID provided to get_poll_winner",
        )
        return None

    current_span.add_event("Attempting to stop poll")
    try:
        updated_poll: Poll = await bot.stop_poll(chat_id=chat_id, message_id=message_id)
        current_span.add_event("Poll stopped")
        options = updated_poll.options
        if not options:
            current_span.set_status(
                StatusCode.ERROR,
                "Poll closed with no votes and no options found.",
            )
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
            current_span.add_event(
                "Poll winner determined",
                {"winner": winner_text, "votes": max_votes},
            )
            current_span.set_status(StatusCode.OK)
            return winner_text
        if max_votes > 0:
            winner_text = random.choice(winning_options)
            current_span.add_event(
                "Poll winner chosen by random because of a tie",
                {"winner": winner_text, "votes": max_votes},
            )
            current_span.set_status(StatusCode.OK)
            return winner_text
        random_winner = random.choice(options)
        winner_text = random_winner.text
        current_span.add_event(
            "Poll winner chosen by random because of no votes",
            {"winner": winner_text, "votes": max_votes},
        )
        current_span.set_status(StatusCode.OK)
        return winner_text

    except telegram.error.BadRequest as e:
        current_span.record_exception(e)
        err_text = str(e).lower()
        if "poll has already been closed" in err_text:
            logging.info(f"Poll (ID: {message_id}) was already closed.")
        if "message to stop poll not found" in err_text:
            logging.error(f"Could not find the poll message to stop (ID: {message_id})")
    except telegram.error.Forbidden as e:
        current_span.record_exception(e)
    except telegram.error.TelegramError as e:
        current_span.record_exception(e)
    current_span.set_status(StatusCode.ERROR)
    return None


@tracer.start_as_current_span("run_story_step")
async def run_story_step(config: Config, openai_client: OpenAI) -> None:
    """Post the story continuation, an image and a poll."""
    current_span = trace.get_current_span()
    state = load_state()
    current_story = state.current_story
    last_poll_message_id = state.last_poll_message_id
    main_idea = state.main_idea
    story_finished = state.story_finished
    current_span.set_attributes(
        {
            "story_finished": story_finished,
            "last_poll_message_id": last_poll_message_id
            if last_poll_message_id
            else -1,
        },
    )
    if story_finished:
        current_span.add_event("Story is already finished. Exiting.")
        return

    bot = Bot(token=config.bot_token)

    next_prompt: str | None = None
    new_poll_message_id: int | None = None
    new_story_part: str | None = None
    new_story_part_message: Message | None = None
    finish_story = False
    sentences = 0
    audio: bytes | None = None

    try:
        # try to get next prompt from poll
        if last_poll_message_id:
            poll_winner = await get_poll_winner(
                bot,
                config.channel_id,
                last_poll_message_id,
            )
            if poll_winner:
                current_span.set_attribute("poll_winner", poll_winner)
                next_prompt = poll_winner
                if poll_winner == config.end_story_option:
                    finish_story = True
                    current_span.add_event("Ending story based on poll.")

        if not current_story:
            current_span.add_event("No existing story found. Posting initial idea.")
            message_to_send = config.initial_story_idea
            current_story = config.initial_story_idea
            (_, new_idea) = generate_story_continuation(
                openai_client,
                main_idea,
                current_story,
                "",
                0,
                config,
            )
            current_span.set_attribute("main_idea", new_idea)
            if config.gemini_tts_model:
                audio = generate_audio_from_text(
                    config.gemini_tts_model,
                    current_story,
                )
            current_span.add_event("Sending initial story part")
            message = await bot.send_message(
                chat_id=config.channel_id,
                text=message_to_send,
            )
            if audio:
                reply_parameters = ReplyParameters(message.message_id)
                await bot.send_audio(
                    chat_id=config.channel_id,
                    audio=audio,
                    reply_parameters=reply_parameters,
                    filename="poll-story-telegram-bot",
                )
                current_span.add_event("Audio sent")
        else:
            sentences = len(current_story.split("."))
            completion = sentences / config.story_max_sentences
            if sentences > config.story_max_sentences:
                current_span.add_event(
                    "Current story has to many sentences. "
                    "Ending story based on length.",
                    {"sentences": sentences},
                )
                finish_story = True

            if not next_prompt:
                logging.error("No prompt available for continuation. Using fallback.")
                next_prompt = config.fallback_continue_prompt

            current_span.set_attribute("finish_story", finish_story)
            current_span.set_attribute("next_prompt", next_prompt)
            (new_story_part, new_idea) = generate_story_continuation(
                openai_client,
                main_idea,
                current_story,
                next_prompt,
                completion,
                config,
                end_story=finish_story,
            )
            current_span.set_attributes(
                {
                    "new_story_part": new_story_part,
                    "new_idea": new_idea,
                },
            )

            imagen_prompt = generate_imagen_prompt(
                openai_client,
                new_story_part,
                new_idea,
                config.image_prompt_start,
                config.openai_model,
            )
            current_span.set_attribute("imagen_prompt", imagen_prompt)

            image = make_gemini_image(
                config.gemini_image_model,
                imagen_prompt or new_story_part,
            )
            if config.gemini_tts_model:
                audio = generate_audio_from_text(
                    config.gemini_tts_model,
                    new_story_part,
                )

            if not new_story_part or new_story_part.strip() == "":
                current_span.set_status(
                    StatusCode.ERROR,
                    "Story continuation failed or returned empty. "
                    "Story not updated. Interrupting step.",
                )
                raise RuntimeError("Failed to generate story continuation.")

            reply_parameters = None
            if image:
                photo_message = await bot.send_photo(
                    chat_id=config.channel_id,
                    photo=image,
                    has_spoiler=True,
                )
                current_span.add_event(
                    "Sent photo",
                    {"photo_message_id": photo_message.id},
                )
                reply_parameters = ReplyParameters(photo_message.id)
            telegram_max_message_length = 4096
            if len(new_story_part) > telegram_max_message_length:
                current_span.add_event("Story part exceeds allowed limit of 4096")
                parts = [
                    new_story_part[i : i + telegram_max_message_length]
                    for i in range(0, len(new_story_part), telegram_max_message_length)
                ]
                for part in parts:
                    new_story_part_message = await bot.send_message(
                        chat_id=config.channel_id,
                        text=part,
                    )
            else:
                new_story_part_message = await bot.send_message(
                    chat_id=config.channel_id,
                    text=new_story_part,
                    reply_parameters=reply_parameters,
                )
                current_span.add_event("New story part sent.")
            if audio:
                reply_parameters = ReplyParameters(new_story_part_message.message_id)
                await bot.send_audio(
                    chat_id=config.channel_id,
                    audio=audio,
                    reply_parameters=reply_parameters,
                    filename="poll-story-telegram-bot",
                )
                current_span.add_event("Audio sent.")
            current_story += new_story_part
        if not finish_story:
            current_span.add_event("Generating poll options based on current story")
            make_end_story_option = False
            if sentences > config.story_max_sentences * 0.8:
                make_end_story_option = True
                current_span.add_event(
                    "Story is too long. Adding end story option to the poll.",
                )
            poll_options = generate_poll_options(
                openai_client,
                current_story,
                config,
                make_end_story_option=make_end_story_option,
            )

            if not poll_options or len(poll_options) > telegram.Poll.MAX_OPTION_LENGTH:
                current_span.add_event(
                    "Could not generate valid poll options. Skipping poll posting.",
                )
                new_poll_message_id = None
            else:
                truncated_options = [opt[:90] for opt in poll_options]
                current_span.add_event("Generated poll options.")
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
                    current_span.add_event(
                        "New poll sent",
                        {"new_poll_message_id": new_poll_message_id},
                    )
                except telegram.error.TelegramError as poll_error:
                    current_span.record_exception(poll_error)
                    new_poll_message_id = None
        else:
            current_span.add_event("Ending story. No new poll will be posted.")
            new_poll_message_id = None

        if not config.dry_run:
            state = StoryState(
                current_story,
                new_idea,
                new_poll_message_id,
                finish_story,
            )
            save_state(state, dry_run=config.dry_run)
        else:
            current_span.add_event("DRY_RUN is enabled. State not saved. ")
        current_span.set_status(StatusCode.OK)

    except Exception as e:
        current_span.record_exception(e)
        current_span.set_status(StatusCode.ERROR)
