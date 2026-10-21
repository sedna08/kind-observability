FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    'Flask>=3.1,<4' \
    'prometheus-client>=0.22,<1' \
    'opentelemetry-sdk>=1.38,<2' \
    'opentelemetry-exporter-otlp-proto-grpc>=1.38,<2'

WORKDIR /app
COPY app.py /app/app.py
USER 65532:65532
EXPOSE 8080
CMD ["python", "/app/app.py"]