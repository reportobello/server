import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger("reportobello")


def setup_otel_tracing(app: FastAPI) -> None:
    trace_endpoint = os.getenv("REPORTOBELLO_OTEL_TRACE_ENDPOINT", "")
    if not trace_endpoint:
        logger.warning(
            "Could not find REPORTOBELLO_OTEL_TRACE_ENDPOINT env var, Open Telemetry trace exporting will be disabled"
        )
        return

    span_exporter = OTLPSpanExporter(endpoint=trace_endpoint)

    resource = Resource(attributes={SERVICE_NAME: "reportobello"})

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)

    FastAPIInstrumentor().instrument_app(app)
