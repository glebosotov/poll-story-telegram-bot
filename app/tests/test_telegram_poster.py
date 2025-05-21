import asyncio
import logging
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call

# Assuming these modules exist and can be imported
from app.telegram_poster import run_story_step
from app.state import StoryState
from app.config import Config # Actual Config to be mocked

# Configure logging for testing
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@pytest.fixture
def mock_config():
    """Fixture for a mocked Config object."""
    config = MagicMock(spec=Config)
    config.bot_token = "fake_bot_token"
    config.channel_id = "fake_channel_id"
    config.openai_api_key = "fake_openai_key"
    config.openai_base_url = "http://fake.openai.url"
    config.gemini_api_key = "fake_gemini_key"
    config.gemini_image_model = "fake_gemini_image_model"
    config.image_prompt_start = "start prompt"
    config.dry_run = False
    config.openai_model = "fake_openai_model"
    config.max_context_chars = 15000
    config.initial_story_idea = "Initial idea."
    config.story_max_sentences = 10 # Lower for testing
    config.poll_question_template = "What next?"
    config.fallback_continue_prompt = "Continue."
    config.end_story_option = "End story."
    config.google_tts_api_key = "fake_google_tts_key" # Default for successful audio
    return config

@pytest.fixture
def mock_openai_client():
    """Fixture for a mocked OpenAI client."""
    return MagicMock()

@pytest.fixture
def mock_story_state():
    """Fixture for a mocked StoryState object."""
    state = MagicMock(spec=StoryState)
    state.current_story = "Initial story part. "
    state.last_poll_message_id = 12345
    state.main_idea = "Original main idea."
    state.story_finished = False
    return state

@pytest.mark.asyncio
@patch('app.telegram_poster.generate_audio_from_text')
@patch('app.telegram_poster.generate_poll_options')
@patch('app.telegram_poster.make_gemini_image')
@patch('app.telegram_poster.generate_imagen_prompt')
@patch('app.telegram_poster.generate_story_continuation')
@patch('app.telegram_poster.Bot')
@patch('app.telegram_poster.save_state')
@patch('app.telegram_poster.load_state')
@patch('app.telegram_poster.get_poll_winner') # Added mock for get_poll_winner
async def test_run_story_step_sends_audio_on_success(
    mock_get_poll_winner,
    mock_load_state, mock_save_state, mock_bot_class,
    mock_generate_story_continuation, mock_generate_imagen_prompt,
    mock_make_gemini_image, mock_generate_poll_options,
    mock_generate_audio_from_text,
    mock_config, mock_openai_client, mock_story_state, caplog
):
    """Test that audio is sent when TTS is successful and API key is present."""
    mock_load_state.return_value = mock_story_state
    mock_get_poll_winner.return_value = "User choice from poll" # Simulate poll winner

    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    
    # Mock send_message to return a message object with an ID
    mock_sent_text_message = MagicMock()
    mock_sent_text_message.id = 78901 # Important for reply_parameters
    mock_sent_text_message.message_id = 78901 # Ensure message_id is also available
    
    # Let the first call to send_message be the story part
    mock_bot_instance.send_message.return_value = mock_sent_text_message
    mock_bot_instance.send_photo.return_value = AsyncMock(id=67890) # if an image is sent first

    new_story_text = "This is the new story part from AI."
    mock_generate_story_continuation.return_value = (new_story_text, "Updated main idea")
    mock_generate_imagen_prompt.return_value = "Generated image prompt."
    mock_make_gemini_image.return_value = b"fake_image_bytes" # Simulate image generation
    mock_generate_poll_options.return_value = ["Option 1", "Option 2"]
    
    fake_audio_data = b"fake_tts_audio_data"
    mock_generate_audio_from_text.return_value = fake_audio_data

    await run_story_step(mock_config, mock_openai_client)

    mock_generate_audio_from_text.assert_called_once_with(
        text=new_story_text, api_key=mock_config.google_tts_api_key
    )
    
    # Check if send_voice was called correctly
    # It should reply to the text message mock_sent_text_message
    # The text message is the one that receives new_story_text
    # The image is sent first, then the text message, then the voice replies to text.
    
    # We need to find the call to send_message that sent the new_story_text
    # and ensure send_voice replied to its ID.
    # The current setup sends image, then message, then poll.
    # The voice should reply to the message.

    # The image is sent, its id is 67890.
    # The text message is sent, replying to image. Its id is 78901.
    # The voice message should reply to text message (id 78901).

    send_voice_called = False
    for call_args in mock_bot_instance.send_voice.call_args_list:
        _, kwargs = call_args
        if kwargs.get('voice') == fake_audio_data and \
           kwargs.get('chat_id') == mock_config.channel_id and \
           kwargs.get('reply_parameters').message_id == mock_sent_text_message.id:
            send_voice_called = True
            break
    assert send_voice_called, "bot.send_voice was not called with correct parameters"

    assert mock_save_state.called # Ensure state is saved
    assert "Voice message sent successfully" in caplog.text


@pytest.mark.asyncio
@patch('app.telegram_poster.generate_audio_from_text')
@patch('app.telegram_poster.generate_poll_options')
@patch('app.telegram_poster.make_gemini_image')
@patch('app.telegram_poster.generate_imagen_prompt')
@patch('app.telegram_poster.generate_story_continuation')
@patch('app.telegram_poster.Bot')
@patch('app.telegram_poster.save_state')
@patch('app.telegram_poster.load_state')
@patch('app.telegram_poster.get_poll_winner')
async def test_run_story_step_no_audio_on_tts_failure(
    mock_get_poll_winner,
    mock_load_state, mock_save_state, mock_bot_class,
    mock_generate_story_continuation, mock_generate_imagen_prompt,
    mock_make_gemini_image, mock_generate_poll_options,
    mock_generate_audio_from_text,
    mock_config, mock_openai_client, mock_story_state, caplog
):
    """Test that audio is NOT sent if TTS generation fails."""
    mock_load_state.return_value = mock_story_state
    mock_get_poll_winner.return_value = "User choice"

    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_sent_text_message = MagicMock(id=78902, message_id=78902)
    mock_bot_instance.send_message.return_value = mock_sent_text_message
    mock_bot_instance.send_photo.return_value = AsyncMock(id=67891)


    new_story_text = "Another story part."
    mock_generate_story_continuation.return_value = (new_story_text, "Idea")
    mock_make_gemini_image.return_value = b"fake_image_bytes"
    mock_generate_poll_options.return_value = ["Opt A", "Opt B"]
    
    mock_generate_audio_from_text.return_value = None # Simulate TTS failure

    await run_story_step(mock_config, mock_openai_client)

    mock_generate_audio_from_text.assert_called_once_with(
        text=new_story_text, api_key=mock_config.google_tts_api_key
    )
    mock_bot_instance.send_voice.assert_not_called()
    assert "Audio generation failed. Skipping voice message." in caplog.text
    assert mock_save_state.called

@pytest.mark.asyncio
@patch('app.telegram_poster.generate_audio_from_text')
@patch('app.telegram_poster.generate_poll_options')
@patch('app.telegram_poster.make_gemini_image')
@patch('app.telegram_poster.generate_imagen_prompt')
@patch('app.telegram_poster.generate_story_continuation')
@patch('app.telegram_poster.Bot')
@patch('app.telegram_poster.save_state')
@patch('app.telegram_poster.load_state')
@patch('app.telegram_poster.get_poll_winner')
async def test_run_story_step_no_audio_if_key_missing(
    mock_get_poll_winner,
    mock_load_state, mock_save_state, mock_bot_class,
    mock_generate_story_continuation, mock_generate_imagen_prompt,
    mock_make_gemini_image, mock_generate_poll_options,
    mock_generate_audio_from_text,
    mock_config, mock_openai_client, mock_story_state, caplog
):
    """Test that audio is NOT generated or sent if the TTS API key is missing."""
    mock_config.google_tts_api_key = None # Key is missing
    mock_load_state.return_value = mock_story_state
    mock_get_poll_winner.return_value = "User choice"
    
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_sent_text_message = MagicMock(id=78903, message_id=78903)
    mock_bot_instance.send_message.return_value = mock_sent_text_message
    mock_bot_instance.send_photo.return_value = AsyncMock(id=67892)

    mock_generate_story_continuation.return_value = ("Story part without key.", "Idea")
    mock_make_gemini_image.return_value = b"fake_image_bytes"
    mock_generate_poll_options.return_value = ["Go on", "Stop"]

    await run_story_step(mock_config, mock_openai_client)

    mock_generate_audio_from_text.assert_not_called()
    mock_bot_instance.send_voice.assert_not_called()
    assert "Google TTS API key not configured. Skipping audio generation." in caplog.text
    assert mock_save_state.called

@pytest.mark.asyncio
@patch('app.telegram_poster.generate_audio_from_text')
@patch('app.telegram_poster.generate_poll_options')
@patch('app.telegram_poster.make_gemini_image')
@patch('app.telegram_poster.generate_imagen_prompt')
@patch('app.telegram_poster.generate_story_continuation')
@patch('app.telegram_poster.Bot')
@patch('app.telegram_poster.save_state')
@patch('app.telegram_poster.load_state')
@patch('app.telegram_poster.get_poll_winner')
async def test_run_story_step_no_audio_if_story_part_missing(
    mock_get_poll_winner,
    mock_load_state, mock_save_state, mock_bot_class,
    mock_generate_story_continuation, mock_generate_imagen_prompt,
    mock_make_gemini_image, mock_generate_poll_options,
    mock_generate_audio_from_text,
    mock_config, mock_openai_client, mock_story_state, caplog
):
    """Test that audio is NOT generated if the story part is empty or None."""
    mock_load_state.return_value = mock_story_state
    mock_get_poll_winner.return_value = "User choice leads to empty story"

    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    # send_message won't be called with the main story part if it's empty
    # but other messages (like errors or polls) might still be.
    # For this test, we focus on generate_audio_from_text not being called.

    # Simulate generate_story_continuation returning an empty or None story part
    mock_generate_story_continuation.return_value = (None, "Updated main idea") # Or ("", "Updated main idea")
    mock_make_gemini_image.return_value = None # No image if story part is problematic

    # We expect run_story_step to raise a RuntimeError in this case, or log an error.
    # The current implementation of run_story_step raises RuntimeError.
    with pytest.raises(RuntimeError, match="Failed to generate story continuation."):
        await run_story_step(mock_config, mock_openai_client)

    mock_generate_audio_from_text.assert_not_called()
    mock_bot_instance.send_voice.assert_not_called()
    
    # Check for the specific error log from run_story_step
    assert any(
        "Story continuation failed or returned empty." in record.message and record.levelno == logging.ERROR
        for record in caplog.records
    )
    # save_state should not be called if there's a critical error like this
    mock_save_state.assert_not_called()
    
@pytest.mark.asyncio
@patch('app.telegram_poster.generate_audio_from_text')
@patch('app.telegram_poster.generate_poll_options')
@patch('app.telegram_poster.make_gemini_image')
@patch('app.telegram_poster.generate_imagen_prompt')
@patch('app.telegram_poster.generate_story_continuation')
@patch('app.telegram_poster.Bot')
@patch('app.telegram_poster.save_state')
@patch('app.telegram_poster.load_state')
@patch('app.telegram_poster.get_poll_winner')
async def test_run_story_step_initial_post_no_audio(
    mock_get_poll_winner,
    mock_load_state, mock_save_state, mock_bot_class,
    mock_generate_story_continuation, mock_generate_imagen_prompt,
    mock_make_gemini_image, mock_generate_poll_options,
    mock_generate_audio_from_text,
    mock_config, mock_openai_client, mock_story_state, caplog
):
    """Test that audio is NOT generated for the initial story post (no new_story_part)."""
    # Simulate the initial run where current_story is None
    mock_story_state.current_story = None 
    mock_story_state.last_poll_message_id = None # No previous poll
    mock_load_state.return_value = mock_story_state
    
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    
    # This will be the initial message
    mock_initial_message = MagicMock(id=11111, message_id=11111)
    
    # generate_story_continuation is called for the main idea, not the initial post text
    mock_generate_story_continuation.return_value = (None, "Generated main idea from initial idea")
    
    # The first bot.send_message will be the initial_story_idea
    # The second bot.send_message (if any for story parts) is what we're testing against for audio
    async def send_message_side_effect(*args, **kwargs):
        if kwargs.get('text') == mock_config.initial_story_idea:
            return mock_initial_message
        # For poll message
        mock_poll_message = MagicMock(id=22222, message_id=22222)
        return mock_poll_message

    mock_bot_instance.send_message.side_effect = send_message_side_effect
    mock_generate_poll_options.return_value = ["Option X", "Option Y"]

    await run_story_step(mock_config, mock_openai_client)

    # generate_audio_from_text should not be called because new_story_part is not generated
    # in the "initial post" branch of run_story_step.
    mock_generate_audio_from_text.assert_not_called()
    mock_bot_instance.send_voice.assert_not_called()
    
    # Check that the initial story idea was sent
    assert call(chat_id=mock_config.channel_id, text=mock_config.initial_story_idea) in mock_bot_instance.send_message.call_args_list
    
    assert "No existing story found. Posting initial idea." in caplog.text
    assert mock_save_state.called # State should still be saved
    assert "Voice message sent successfully" not in caplog.text # Ensure no accidental audio success log

```
