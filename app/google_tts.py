import logging
import google.generativeai as genai
from google.generativeai import types
from google.api_core import exceptions as google_exceptions # For specific error handling

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_audio_from_text(text: str, api_key: str) -> bytes | None:
    """
    Generates audio from text using the Google Generative AI SDK.

    Args:
        text: The text to synthesize.
        api_key: The Google Gemini API key.

    Returns:
        The audio content in bytes if successful, None otherwise.
    """
    try:
        client = genai.Client(api_key=api_key)

        response = client.generate_content(
            model="gemini-2.5-pro-preview-tts", # Using the specified "pro" model
            contents=text,
            generation_config=types.GenerationConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')
                    )
                )
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            if audio_data:
                logging.info(f"Successfully synthesized audio for text: {text[:50]}...")
                return audio_data
            else:
                logging.error("Audio data is missing in the successful response from Generative AI SDK.")
                return None
        else:
            logging.error("No valid candidates or parts found in the response from Generative AI SDK.")
            # Log detailed response if possible and privacy permits
            # logging.debug(f"Full response: {response}")
            return None

    except google_exceptions.GoogleAPIError as e:
        logging.error(f"Google API error during TTS generation: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during TTS generation with Generative AI SDK: {e}")
        return None

if __name__ == '__main__':
    # This is an example of how to use the function.
    # You'll need to set your GEMINI_API_KEY environment variable or pass it directly.
    # Important: This assumes app.config.Config can be imported and initialized.
    # If running this script standalone, you might need to adjust how api_key_to_test is obtained.
    try:
        from app.config import Config 
        config = Config()
        # Note: The task mentioned using config.gemini_api_key, so we use that.
        # The previous version of this file used GOOGLE_TTS_API_KEY for the old API.
        api_key_to_test = config.gemini_api_key 
    except (ImportError, AttributeError, FileNotFoundError):
        logging.warning(
            "Could not load API key from app.config.Config. "
            "Falling back to placeholder. Set GEMINI_API_KEY env var or modify script."
        )
        api_key_to_test = "YOUR_GEMINI_API_KEY_HERE" # IMPORTANT: Replace for testing

    if not api_key_to_test or api_key_to_test == "YOUR_GEMINI_API_KEY_HERE":
        logging.warning(
            "Please set your GEMINI_API_KEY in .env or replace 'YOUR_GEMINI_API_KEY_HERE' "
            "with your actual API key to test the script."
        )
    else:
        sample_text = "Привет, мир! Это тестовое сообщение для проверки синтеза речи с помощью нового SDK."
        logging.info(f"Attempting to synthesize text: '{sample_text}' using Gemini API Key.")
        
        audio_bytes = generate_audio_from_text(sample_text, api_key_to_test)

        if audio_bytes:
            try:
                with open("test_audio_sdk.mp3", "wb") as f:
                    f.write(audio_bytes)
                logging.info("Test audio successfully saved to test_audio_sdk.mp3")
            except IOError as e:
                logging.error(f"Failed to write audio to file: {e}")
        else:
            logging.error("Failed to generate audio for the sample text using SDK.")
    
    logging.info("Note: The main block is for testing and will not run in production if imported.")
