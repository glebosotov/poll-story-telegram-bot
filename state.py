"""Datasource for the story state."""

import json
import logging
from pathlib import Path
from typing import NamedTuple

STATE_FILE = Path(__file__).parent / "story_state.json"

current_story_key = "current_story"
last_poll_message_id_key = "last_poll_message_id"
story_finished_key = "story_finished"


class StoryState(NamedTuple):
    """A named tuple to represent the story state."""

    current_story: str
    last_poll_message_id: int | None
    story_finished: bool


def load_state() -> StoryState:
    """Load the story state (current_story, last_poll_message_id) from the JSON file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
                logging.info(f"State loaded from {STATE_FILE}: {state}")
                current_story = state.get(current_story_key, "")
                last_poll_message_id = state.get(last_poll_message_id_key, None)
                story_finished = state.get(story_finished_key, False)
                return StoryState(current_story, last_poll_message_id, story_finished)
        except (OSError, json.JSONDecodeError) as e:
            logging.error(
                f"Error loading state file {STATE_FILE}: {e}.",
            )
    else:
        logging.info("State file not found.")
    return StoryState("", None, False)


def save_state(state: StoryState) -> None:
    """Save the story state to the JSON file."""
    state = {
        current_story_key: state.current_story,
        last_poll_message_id_key: state.last_poll_message_id,
        story_finished_key: state.story_finished,
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        logging.info(f"Story state saved to {STATE_FILE}: {state}")
    except OSError as e:
        logging.error(f"Error saving state file {STATE_FILE}: {e}")
