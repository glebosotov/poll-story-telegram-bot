"""Generate audio from text using the Google Gemini SDK."""

import logging

import ffmpeg
from google import genai
from google.genai import types


def generate_audio_from_text(
    api_key: str,
    model: str,
    prompt: str,
) -> bytes | None:
    """Generate ogg audio from text using the Google Generative AI SDK."""
    try:
        client = genai.Client(api_key=api_key)

        contents = f"Read like a storyteller recording an audiobook: {prompt}"

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Gacrux",
                        ),
                    ),
                    language_code="ru-RU",
                ),
            ),
        )

        data = response.candidates[0].content.parts[0].inline_data.data

        logging.info(f"Gemini returned {len(data)} bytes of audio")

        if data:
            with open("out.wav", "wb") as f:
                f.write(data)
            return raw_bytes_to_ogg_bytes(data)

        raise Exception("Gemini returned None")

    except Exception as e:
        logging.error(f"An unexpected error occurred during TTS generation: {e}")
        return None


def raw_bytes_to_ogg_bytes(
    raw_bytes: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_fmt: str = "s16le",
    codec: str = "libvorbis",
) -> bytes | None:
    """
    Convert WAV audio bytes to OGG audio bytes (Vorbis by default) using ffmpeg-python.

    Returns OGG bytes.
    """
    process = (
        ffmpeg.input("pipe:0", format=sample_fmt, ar=str(sample_rate), ac=channels)
        .output("pipe:1", format="ogg", acodec=codec)
        .overwrite_output()
        .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )
    out, err = process.communicate(raw_bytes)
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {err.decode()}")
    logging.info(f"ffmpeg returned {len(out)} bytes of OGG audio")
    return out
