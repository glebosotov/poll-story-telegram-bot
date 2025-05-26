"""Telemetry configuration."""

import logging

from opentelemetry import metrics, trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor

if not HTTPXClientInstrumentor().is_instrumented_by_opentelemetry:
    HTTPXClientInstrumentor().instrument()
if not OpenAIInstrumentor().is_instrumented_by_opentelemetry:
    OpenAIInstrumentor().instrument()
logging.basicConfig(level=logging.INFO)
if LoggingInstrumentor().is_instrumented_by_opentelemetry:
    LoggingInstrumentor().uninstrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

tracer = trace.get_tracer("main.tracer")
meter = metrics.get_meter("main.meter")
