"""Datasource for the story state."""

from pathlib import Path
from typing import NamedTuple

import yaml
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from telemetry import tracer

state_dir = Path(__file__).parent / "state"
state_file = state_dir / "story_state.yaml"

current_story_key = "current_story"
last_poll_message_id_key = "last_poll_message_id"
story_finished_key = "story_finished"
main_idea_key = "main_idea"


class StoryState(NamedTuple):
    """A named tuple to represent the story state."""

    current_story: str
    main_idea: str
    last_poll_message_id: int | None
    story_finished: bool


@tracer.start_as_current_span("load_state")
def load_state() -> StoryState:
    """Load the story state (current_story, last_poll_message_id) from the JSON file."""
    current_span = trace.get_current_span()
    current_span.set_attribute("filename", state_file.name)
    state_dir.mkdir(exist_ok=True)
    if state_file.exists():
        try:
            with open(state_file, encoding="utf-8") as f:
                state = yaml.load(f, Loader=yaml.CLoader)
                current_span.add_event("State loaded")
                current_story = state.get(current_story_key, "")
                main_idea = state.get(main_idea_key, "")
                last_poll_message_id = state.get(last_poll_message_id_key, None)
                story_finished = state.get(story_finished_key, False)
                current_span.set_status(Status(StatusCode.OK))
                return StoryState(
                    current_story,
                    main_idea,
                    last_poll_message_id,
                    story_finished,
                )
        except OSError as e:
            current_span.set_status(Status(StatusCode.ERROR))
            current_span.record_exception(e)
    else:
        current_span.add_event("File not found")
    return StoryState("", "", None, False)


@tracer.start_as_current_span("save_state")
def save_state(
    state: StoryState,
    dry_run: bool = False,
) -> None:
    """Save the story state to the JSON file."""
    current_span = trace.get_current_span()
    current_span.set_attribute("filename", state_file.name)
    state = {
        current_story_key: state.current_story,
        main_idea_key: state.main_idea,
        last_poll_message_id_key: state.last_poll_message_id,
        story_finished_key: state.story_finished,
    }
    if dry_run:
        current_span.add_event("Dry run: not saving to state_file")
        return
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            yaml.dump(state, f, allow_unicode=True)
        current_span.set_status(Status(StatusCode.OK))
    except OSError as e:
        current_span.set_status(Status(StatusCode.ERROR), "Error saving state file")
        current_span.record_exception(e)
