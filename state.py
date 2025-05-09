import json
import logging
from pathlib import Path

STATE_FILE = Path(__file__).parent / "story_state.json"

current_story_key = "current_story"
last_poll_message_id_key = "last_poll_message_id"
story_finished_key = "story_finished"


def load_state():
    """Loads the story state (current_story, last_poll_message_id) from the JSON file."""
    default_state = {
        current_story_key: "",
        last_poll_message_id_key: None,
        story_finished_key: False,
    }
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                # Ensure both keys exist, provide defaults if not
                if current_story_key not in state:
                    state[current_story_key] = default_state[current_story_key]
                if last_poll_message_id_key not in state:
                    state[last_poll_message_id_key] = default_state[
                        last_poll_message_id_key
                    ]
                if story_finished_key not in state:
                    state[story_finished_key] = default_state[story_finished_key]
                logging.info(f"State loaded from {STATE_FILE}: {state}")
                return state
        except (json.JSONDecodeError, IOError) as e:
            logging.error(
                f"Error loading state file {STATE_FILE}: {e}. Starting fresh."
            )
            return default_state
    else:
        logging.info("State file not found. Starting fresh.")
        return default_state


def save_state(
    current_story,
    last_poll_message_id,
    story_finished=False,
):
    state = {
        current_story_key: current_story,
        last_poll_message_id_key: last_poll_message_id,
        story_finished_key: story_finished,
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        logging.info(f"Story state saved to {STATE_FILE}: {state}")
    except IOError as e:
        logging.error(f"Error saving state file {STATE_FILE}: {e}")
