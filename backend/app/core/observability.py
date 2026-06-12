# app/core/observability.py
from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.settings import get_settings


settings = get_settings()

_resource = Resource.create({"service.name": settings.service_name})

_tracer_provider = TracerProvider(resource=_resource)
if settings.console_span_exporter_enabled:
    _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_tracer_provider)

_meter_provider = MeterProvider(resource=_resource)
metrics.set_meter_provider(_meter_provider)

tracer = trace.get_tracer(settings.service_name)
meter = metrics.get_meter(settings.service_name)

http_request_duration_histogram = meter.create_histogram(
    "infersql.http.request.duration.ms",
    description="End-to-end HTTP request duration in milliseconds",
    unit="ms",
)

query_counter = meter.create_counter(
    "infersql.query.requests",
    description="Count of query API requests",
)

query_failure_counter = meter.create_counter(
    "infersql.query.failures",
    description="Count of failed query API requests",
)

query_duration_histogram = meter.create_histogram(
    "infersql.query.duration.ms",
    description="End-to-end query request duration in milliseconds",
    unit="ms",
)

query_phase_duration_histogram = meter.create_histogram(
    "infersql.query.phase.duration.ms",
    description="Duration of individual query phases in milliseconds",
    unit="ms",
)

query_rows_histogram = meter.create_histogram(
    "infersql.query.rows_returned",
    description="Distribution of rows returned by executed queries",
)