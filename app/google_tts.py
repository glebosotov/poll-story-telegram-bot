import base64
import json
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_ENDPOINT = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"

def generate_audio_from_text(text: str, api_key: str, model_name: str = "gemini-1.5-flash-001") -> bytes | None:
    """
    Generates audio from text using Google Text-to-Speech API.

    Args:
        text: The text to synthesize.
        api_key: The Google Cloud API key.
        model_name: The name of the model to use for synthesis.

    Returns:
        The audio content in bytes if successful, None otherwise.
    """
    headers = {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "ru-RU", "name": "ru-RU-Standard-D"},
        "audioConfig": {"audioEncoding": "MP3"},
        "model": model_name,
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            response_json = response.json()
            audio_content_base64 = response_json.get("audioContent")
            if audio_content_base64:
                logging.info(f"Successfully synthesized audio for text: {text[:50]}...")
                return base64.b64decode(audio_content_base64)
            else:
                logging.error("Audio content is missing in the successful response.")
                return None
        else:
            logging.error(
                f"Failed to synthesize audio. Status: {response.status_code}, Response: {response.text}"
            )
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Google TTS API failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response from Google TTS API: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    # This is an example of how to use the function.
    # You'll need to set your GOOGLE_TTS_API_KEY environment variable or pass it directly.
    # from app.config import Config # Assuming your Config class can load this key
    # config = Config()
    # api_key_to_test = config.google_tts_api_key

    # Replace with your actual API key for testing if not using Config
    api_key_to_test = "YOUR_API_KEY_HERE" # IMPORTANT: Replace before testing if not using Config

    if api_key_to_test == "YOUR_API_KEY_HERE":
        logging.warning("Please replace 'YOUR_API_KEY_HERE' with your actual API key to test the script.")
    else:
        sample_text = "Привет, мир! Это тестовое сообщение для проверки синтеза речи."
        logging.info(f"Attempting to synthesize text: '{sample_text}'")
        audio_bytes = generate_audio_from_text(sample_text, api_key_to_test)

        if audio_bytes:
            try:
                with open("test_audio.mp3", "wb") as f:
                    f.write(audio_bytes)
                logging.info("Test audio successfully saved to test_audio.mp3")
            except IOError as e:
                logging.error(f"Failed to write audio to file: {e}")
        else:
            logging.error("Failed to generate audio for the sample text.")

    # Example with a different voice (if you want to explore)
    # payload_custom_voice = {
    #     "input": {"text": text},
    #     "voice": {"languageCode": "ru-RU", "name": "ru-RU-Wavenet-A"}, # Example Wavenet voice
    #     "audioConfig": {"audioEncoding": "MP3"},
    #     "model": model_name,
    # }
    # You would need to modify the function to accept voice parameters or create a new one.
    # logging.info("Note: The main block is for testing and will not run in production.")
