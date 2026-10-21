import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

from .config import get_settings

REQUESTS = Counter("customerops_requests_total", "Requests", ["method", "route", "status"])
LATENCY = Histogram("customerops_request_seconds", "Request latency", ["route"])
AGENT_RUNS = Counter("customerops_agent_runs_total", "Agent runs", ["mode", "status"])
tracer = trace.get_tracer("customerops")


def configure_tracing():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    endpoint = get_settings().otel_endpoint
    if endpoint and not isinstance(trace.get_tracer_provider(), TracerProvider):
        provider = TracerProvider(resource=Resource.create({"service.name": "customerops-api"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)


def instrument(app):
    configure_tracing()
    FastAPIInstrumentor.instrument_app(app)
