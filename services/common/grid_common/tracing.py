# This project was developed with assistance from AI tools.

"""OpenTelemetry setup with Kafka header trace propagation."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from grid_common.settings import OtelSettings


def setup_tracing(settings: OtelSettings) -> trace.Tracer:
    """Initialize OTel tracing with OTLP export and return a tracer."""
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(settings.otel_service_name)


def extract_trace_id(traceparent: str | None) -> str | None:
    """Extract the trace ID from a W3C traceparent header value."""
    if not traceparent:
        return None
    parts = traceparent.split("-")
    if len(parts) >= 2:
        return parts[1]
    return None
