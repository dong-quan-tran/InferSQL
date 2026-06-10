# app/core/observability.py
from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

SERVICE_NAME = "infersql-backend"

_resource = Resource.create({"service.name": SERVICE_NAME})

_tracer_provider = TracerProvider(resource=_resource)
_tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_tracer_provider)

_meter_provider = MeterProvider(resource=_resource)
metrics.set_meter_provider(_meter_provider)

tracer = trace.get_tracer(SERVICE_NAME)
meter = metrics.get_meter(SERVICE_NAME)

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