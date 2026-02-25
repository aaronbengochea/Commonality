FROM python:3.12-slim

WORKDIR /app

# LiveKit Python SDK requires GLib for its native FFI library
RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 libgstreamer1.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml .
COPY app/ app/
RUN pip install --no-cache-dir ".[dev]"

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
