"""Generate an image using the Gemini API."""

from google import genai
from google.genai import types
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from telemetry import tracer


@tracer.start_as_current_span("make_gemini_image")
def make_gemini_image(
    model: str,
    prompt: str,
) -> bytes | None:
    """Generate an image using the Gemini API."""
    current_span = trace.get_current_span()
    client = genai.Client()

    current_span.add_event(
        "Making image with prompt",
        {"prompt": prompt, "model": model},
    )

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
        current_span.set_status(Status(StatusCode.ERROR))
        current_span.record_exception(e)
        return None
