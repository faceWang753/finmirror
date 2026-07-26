FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

COPY benchmark ./benchmark
ENTRYPOINT ["finmirror"]
CMD ["validate", "benchmark/v0.1"]

