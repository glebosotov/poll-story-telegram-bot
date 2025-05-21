import pytest
import logging
from unittest.mock import patch
from app.config import Config

# To capture log messages
@pytest.fixture
def caplog_fixture(caplog):
    caplog.set_level(logging.ERROR)
    return caplog

class TestConfigValidation:

    def get_base_env_vars(self):
        return {
            "BOT_TOKEN": "fake_bot_token",
            "CHANNEL_ID": "fake_channel_id",
            "OPENAI_API_KEY": "fake_openai_key",
            "OPENAI_BASE_URL": "http://fake.openai.url",
            "GEMINI_API_KEY": "fake_gemini_key", # Essential key
            "GEMINI_IMAGE_MODEL": "fake_gemini_image_model",
            "IMAGE_PROMPT_START": "start prompt",
            "INITIAL_STORY_IDEA": "Initial idea.",
            # GOOGLE_TTS_API_KEY is intentionally omitted as it's no longer used
        }

    def test_valid_config(self, caplog_fixture):
        """Test that a valid configuration passes validation."""
        env_vars = self.get_base_env_vars()
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]): # Mock .env files
                config = Config()
                assert config.validate() is True
                assert not caplog_fixture.records # No error logs

    def test_valid_config_with_old_google_tts_key_present(self, caplog_fixture):
        """Test that config is still valid if old GOOGLE_TTS_API_KEY is somehow present (it should be ignored)."""
        env_vars = self.get_base_env_vars()
        env_vars["GOOGLE_TTS_API_KEY"] = "old_fake_key_should_be_ignored" # Old key
        
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is True # Should still be valid
                # Ensure no error log related to GOOGLE_TTS_API_KEY
                assert not any("GOOGLE_TTS_API_KEY" in record.message for record in caplog_fixture.records)


    def test_invalid_config_missing_bot_token(self, caplog_fixture):
        env_vars = self.get_base_env_vars()
        del env_vars["BOT_TOKEN"]
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("BOT_TOKEN is not set correctly." in record.message for record in caplog_fixture.records)

    def test_invalid_config_missing_gemini_api_key(self, caplog_fixture):
        """Test that missing GEMINI_API_KEY (used for images and now TTS) fails validation."""
        env_vars = self.get_base_env_vars()
        del env_vars["GEMINI_API_KEY"] # GEMINI_API_KEY is critical
        
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("GEMINI_API_KEY and GEMINI_IMAGE_MODEL" in record.message for record in caplog_fixture.records)

    def test_initial_story_idea_validation(self, caplog_fixture):
        """Test that INITIAL_STORY_IDEA is validated."""
        env_vars = self.get_base_env_vars()
        del env_vars["INITIAL_STORY_IDEA"]
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("INITIAL_STORY_IDEA cannot be empty." in record.message for record in caplog_fixture.records)

    def test_openai_details_validation(self, caplog_fixture):
        """Test that OpenAI API key and base URL are validated."""
        env_vars = self.get_base_env_vars()
        del env_vars["OPENAI_API_KEY"]
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("Missing OpenAI API key or base URL." in record.message for record in caplog_fixture.records)
                
        env_vars_2 = self.get_base_env_vars()
        del env_vars_2["OPENAI_BASE_URL"]
        with patch.dict('os.environ', env_vars_2, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("Missing OpenAI API key or base URL." in record.message for record in caplog_fixture.records)

    def test_gemini_image_model_validation(self, caplog_fixture):
        """Test that GEMINI_IMAGE_MODEL is validated along with GEMINI_API_KEY."""
        env_vars = self.get_base_env_vars()
        del env_vars["GEMINI_IMAGE_MODEL"]
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("GEMINI_API_KEY and GEMINI_IMAGE_MODEL" in record.message for record in caplog_fixture.records)

    def test_image_prompt_start_validation(self, caplog_fixture):
        """Test that IMAGE_PROMPT_START is validated."""
        env_vars = self.get_base_env_vars()
        del env_vars["IMAGE_PROMPT_START"]
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('app.config.dotenv_values', side_effect=[{}, {}]):
                config = Config()
                assert config.validate() is False
                assert any("IMAGE_PROMPT_START cannot be empty" in record.message for record in caplog_fixture.records) # The actual message might vary slightly based on how it's grouped.

```
