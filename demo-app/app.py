import logging
import os
import random
import time
from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from opentelemetry import _logs, metrics
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "demo-api")
OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://otel-gateway-collector.observability.svc.cluster.local:4317"
)
POD_NAME = os.getenv("POD_NAME", "unknown")
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "unknown")

resource = Resource.create(
    {
        "service.name": SERVICE_NAME,
        "service.version": "0.1.0",
        "deployment.environment.name": "kind-lab",
        "k8s.pod.name": POD_NAME,
        "k8s.namespace.name": POD_NAMESPACE,
    }
)

# Native OTLP metrics
metric_exporter = OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True)
metric_reader = PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=5000,
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("demo-api", "0.1.0")
otel_request_counter = meter.create_counter(
    "demo.otel.requests",
    unit="{requests}",
    description="Requests counted by the OpenTelemetry SDK",
)
otel_work_histogram = meter.create_histogram(
    "demo.otel.work.duration",
    unit="s",
    description="Synthetic work duration",
)

# Native OTLP logs plus stdout. stdout is deliberately retained so the
# filelog receiver can collect the same application's container logs.
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True))
)
_logs.set_logger_provider(logger_provider)
logger = logging.getLogger("demo-api")
logger.setLevel(logging.INFO)
logger.propagate = False
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(
    logging.Formatter(
        '{"timestamp":"%(asctime)s","severity":"%(levelname)s",'
        '"service":"demo-api","message":"%(message)s"}'
    )
)
logger.addHandler(stdout_handler)
logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

# Prometheus exposition metrics.
prom_requests = Counter(
    "demo_http_requests_total",
    "HTTP requests exposed for Prometheus scraping",
    ["method", "path", "status"],
)
prom_latency = Histogram(
    "demo_http_request_duration_seconds",
    "HTTP request latency exposed for Prometheus scraping",
    ["method", "path"],
)

app = Flask(__name__)

def record(path: str, status: int, started: float) -> None:
    elapsed = time.monotonic() - started
    method = request.method
    prom_requests.labels(method=method, path=path, status=str(status)).inc()
    prom_latency.labels(method=method, path=path).observe(elapsed)
    otel_request_counter.add(
        1,
        {
            "http.request.method": method,
            "http.route": path,
            "http.response.status_code": status,
        },
    )
    otel_work_histogram.record(elapsed, {"http.route": path})
    level = logging.ERROR if status >= 500 else logging.INFO
    logger.log(level, "request completed path=%s status=%s duration_seconds=%.4f", path, status, elapsed)

@app.get("/")
def index():
    started = time.monotonic()
    record("/", 200, started)
    return jsonify(service=SERVICE_NAME, pod=POD_NAME, status="ok")

@app.get("/work")
def work():
    started = time.monotonic()
    time.sleep(random.uniform(0.02, 0.20))
    record("/work", 200, started)
    return jsonify(result="work-complete", pod=POD_NAME)

@app.get("/error")
def error():
    started = time.monotonic()
    time.sleep(random.uniform(0.01, 0.05))
    record("/error", 500, started)
    return jsonify(error="synthetic failure", pod=POD_NAME), 500

@app.get("/healthz")
def healthz():
    return jsonify(status="healthy")

@app.get("/metrics")
def prometheus_metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    logger.info("application starting pod=%s namespace=%s otlp_endpoint=%s", POD_NAME, POD_NAMESPACE, OTLP_ENDPOINT)
    app.run(host="0.0.0.0", port=8080, threaded=True)