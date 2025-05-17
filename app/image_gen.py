"""Generate an image using the Gemini API."""

import logging

from google import genai
from google.genai import types


def make_gemini_image(
    api_key: str,
    model: str,
    prompt: str,
) -> bytes | None:
    """Generate an image using the Gemini API."""
    client = genai.Client(api_key=api_key)

    logging.info(f"Making an image with prompt: {prompt}...")

    try:
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )

        return response.generated_images[0].image.image_bytes
    except Exception as e:
        logging.error(f"Error generating image: {e}")
        return None
