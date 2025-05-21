import logging
import pytest
from unittest.mock import patch, MagicMock
from app.google_tts import generate_audio_from_text
from google.generativeai import types as genai_types # Renamed to avoid conflict
from google.api_core import exceptions as google_exceptions

# Configure logging for testing
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TestGoogleTTSWithSDK:
    @patch('app.google_tts.genai.Client')
    def test_generate_audio_from_text_success(self, mock_genai_client_class, caplog):
        """Test successful audio generation using the Generative AI SDK."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance

        fake_audio_bytes = b"fake_sdk_audio_bytes_content"
        
        # Constructing the mock response structure based on SDK
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data.data = fake_audio_bytes
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        
        mock_client_instance.generate_content.return_value = mock_response

        api_key = "fake_gemini_api_key_success"
        text_to_synthesize = "This is a test text for SDK TTS."

        result = generate_audio_from_text(text_to_synthesize, api_key)

        assert result == fake_audio_bytes
        mock_genai_client_class.assert_called_once_with(api_key=api_key)
        
        # Assert that generate_content was called correctly
        mock_client_instance.generate_content.assert_called_once()
        args, kwargs = mock_client_instance.generate_content.call_args
        
        assert kwargs.get('model') == "gemini-2.5-pro-preview-tts"
        assert kwargs.get('contents') == text_to_synthesize
        
        generation_config = kwargs.get('generation_config')
        assert isinstance(generation_config, genai_types.GenerationConfig)
        assert generation_config.response_modalities == ["AUDIO"]
        
        speech_config = generation_config.speech_config
        assert isinstance(speech_config, genai_types.SpeechConfig)
        assert isinstance(speech_config.voice_config, genai_types.VoiceConfig)
        assert isinstance(speech_config.voice_config.prebuilt_voice_config, genai_types.PrebuiltVoiceConfig)
        assert speech_config.voice_config.prebuilt_voice_config.voice_name == 'Kore'
            
        assert any(record.levelno == logging.INFO and f"Successfully synthesized audio for text: {text_to_synthesize[:50]}" in record.message for record in caplog.records)

    @patch('app.google_tts.genai.Client')
    def test_generate_audio_from_text_sdk_api_error(self, mock_genai_client_class, caplog):
        """Test handling of GoogleAPIError from the SDK."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance
        
        # Simulate an API error
        mock_client_instance.generate_content.side_effect = google_exceptions.GoogleAPIError("SDK API Error")

        api_key = "fake_gemini_api_key_sdk_error"
        text_to_synthesize = "Test text for SDK API error."

        result = generate_audio_from_text(text_to_synthesize, api_key)

        assert result is None
        mock_genai_client_class.assert_called_once_with(api_key=api_key)
        mock_client_instance.generate_content.assert_called_once() # Ensure it was called
        assert any(record.levelno == logging.ERROR and "Google API error during TTS generation: SDK API Error" in record.message for record in caplog.records)

    @patch('app.google_tts.genai.Client')
    def test_generate_audio_from_text_sdk_unexpected_exception(self, mock_genai_client_class, caplog):
        """Test handling of an unexpected exception during SDK operation."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance
        
        mock_client_instance.generate_content.side_effect = Exception("Unexpected SDK problem")

        api_key = "fake_gemini_api_key_unexpected_error"
        text_to_synthesize = "Test text for unexpected SDK error."

        result = generate_audio_from_text(text_to_synthesize, api_key)

        assert result is None
        mock_genai_client_class.assert_called_once_with(api_key=api_key)
        mock_client_instance.generate_content.assert_called_once()
        assert any(record.levelno == logging.ERROR and "An unexpected error occurred during TTS generation with Generative AI SDK: Unexpected SDK problem" in record.message for record in caplog.records)

    @patch('app.google_tts.genai.Client')
    def test_generate_audio_from_text_sdk_no_candidates(self, mock_genai_client_class, caplog):
        """Test handling when SDK response has no candidates."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.candidates = [] # No candidates
        mock_client_instance.generate_content.return_value = mock_response

        api_key = "fake_gemini_api_key_no_candidates"
        text_to_synthesize = "Test text for no candidates."

        result = generate_audio_from_text(text_to_synthesize, api_key)

        assert result is None
        assert any(record.levelno == logging.ERROR and "No valid candidates or parts found" in record.message for record in caplog.records)

    @patch('app.google_tts.genai.Client')
    def test_generate_audio_from_text_sdk_no_parts(self, mock_genai_client_class, caplog):
        """Test handling when SDK response candidate has no parts."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [] # No parts
        mock_response.candidates = [mock_candidate]
        mock_client_instance.generate_content.return_value = mock_response
        
        api_key = "fake_gemini_api_key_no_parts"
        text_to_synthesize = "Test text for no parts in candidate."

        result = generate_audio_from_text(text_to_synthesize, api_key)
        
        assert result is None
        assert any(record.levelno == logging.ERROR and "No valid candidates or parts found" in record.message for record in caplog.records)


    @patch('app.google_tts.genai.Client')
    def test_generate_audio_from_text_sdk_missing_audio_data(self, mock_genai_client_class, caplog):
        """Test handling when audio data is missing in a successful SDK response structure."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data.data = None # Audio data is None
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        mock_client_instance.generate_content.return_value = mock_response

        api_key = "fake_gemini_api_key_missing_data"
        text_to_synthesize = "Test text for missing audio data in SDK."

        result = generate_audio_from_text(text_to_synthesize, api_key)

        assert result is None
        assert any(record.levelno == logging.ERROR and "Audio data is missing in the successful response" in record.message for record in caplog.records)
