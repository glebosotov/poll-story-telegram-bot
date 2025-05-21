import base64
import json
import logging
import pytest
from unittest.mock import patch, MagicMock

import requests # Import the actual requests library for requests.exceptions.RequestException

from app.google_tts import generate_audio_from_text, API_ENDPOINT

# Configure logging for testing (e.g., to check caplog)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TestGoogleTTS:
    def test_generate_audio_from_text_success(self, caplog):
        """Test successful audio generation."""
        fake_audio_bytes = b"fake_audio_bytes_content"
        encoded_audio = base64.b64encode(fake_audio_bytes).decode('utf-8')
        mock_response_data = {"audioContent": encoded_audio}

        with patch('app.google_tts.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            api_key = "fake_api_key_success"
            text_to_synthesize = "This is a test text for TTS."
            model_name = "test-model-001"

            result = generate_audio_from_text(text_to_synthesize, api_key, model_name)

            assert result == fake_audio_bytes

            expected_headers = {
                "X-Goog-Api-Key": api_key,
                "Content-Type": "application/json; charset=utf-8",
            }
            expected_payload = {
                "input": {"text": text_to_synthesize},
                "voice": {"languageCode": "ru-RU", "name": "ru-RU-Standard-D"},
                "audioConfig": {"audioEncoding": "MP3"},
                "model": model_name,
            }

            mock_post.assert_called_once_with(
                API_ENDPOINT,
                headers=expected_headers,
                data=json.dumps(expected_payload)
            )
            
            assert any(record.levelno == logging.INFO and f"Successfully synthesized audio for text: {text_to_synthesize[:50]}" in record.message for record in caplog.records)


    def test_generate_audio_from_text_api_error(self, caplog):
        """Test handling of API error (e.g., 500 status code)."""
        with patch('app.google_tts.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            api_key = "fake_api_key_api_error"
            text_to_synthesize = "Test text for API error."

            result = generate_audio_from_text(text_to_synthesize, api_key)

            assert result is None
            mock_post.assert_called_once()
            # Check that an error was logged
            assert any(record.levelno == logging.ERROR and "Failed to synthesize audio. Status: 500" in record.message for record in caplog.records)

    def test_generate_audio_from_text_request_exception(self, caplog):
        """Test handling of a requests.exceptions.RequestException."""
        with patch('app.google_tts.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Network error")

            api_key = "fake_api_key_request_exception"
            text_to_synthesize = "Test text for request exception."

            result = generate_audio_from_text(text_to_synthesize, api_key)

            assert result is None
            mock_post.assert_called_once()
            # Check that an error was logged
            assert any(record.levelno == logging.ERROR and "Request to Google TTS API failed: Network error" in record.message for record in caplog.records)

    def test_generate_audio_from_text_json_decode_error(self, caplog):
        """Test handling of JSONDecodeError when parsing API response."""
        with patch('app.google_tts.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Configure json.loads to raise JSONDecodeError
            mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
            mock_post.return_value = mock_response

            api_key = "fake_api_key_json_error"
            text_to_synthesize = "Test text for JSON decode error."

            result = generate_audio_from_text(text_to_synthesize, api_key)

            assert result is None
            mock_post.assert_called_once()
            assert any(record.levelno == logging.ERROR and "Failed to decode JSON response" in record.message for record in caplog.records)

    def test_generate_audio_from_text_missing_audio_content(self, caplog):
        """Test handling when 'audioContent' is missing in a successful response."""
        with patch('app.google_tts.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"notAudioContent": "some_value"} # Missing 'audioContent'
            mock_post.return_value = mock_response

            api_key = "fake_api_key_missing_content"
            text_to_synthesize = "Test text for missing audio content."

            result = generate_audio_from_text(text_to_synthesize, api_key)

            assert result is None
            mock_post.assert_called_once()
            assert any(record.levelno == logging.ERROR and "Audio content is missing" in record.message for record in caplog.records)
