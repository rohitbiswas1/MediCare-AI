FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY ml/pyproject.toml ml/uv.lock ./ml/
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -f /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --frozen --project ml
COPY ml ./ml
COPY services/inference ./services/inference
RUN useradd --uid 10001 --create-home inference
USER inference
ENV ALLOW_RESEARCH_INFERENCE=false UV_CACHE_DIR=/tmp/uv-cache
EXPOSE 8001
CMD ["uv", "run", "--frozen", "--project", "ml", "uvicorn", "services.inference.main:app", "--host", "0.0.0.0", "--port", "8001"]
