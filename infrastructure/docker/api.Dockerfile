FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv
RUN --mount=type=secret,id=build_ca,mode=0444 \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    if [ -f /run/secrets/build_ca ]; then printf 'Acquire::https::CaInfo "/run/secrets/build_ca";\n' > /tmp/apt-ca.conf; export APT_CONFIG=/tmp/apt-ca.conf; fi; \
    apt-get update -o APT::Update::Error-Mode=any && \
    apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng ca-certificates && \
    rm -rf /var/lib/apt/lists/* /tmp/apt-ca.conf
RUN groupadd --gid 10001 medicare && useradd --uid 10001 --gid medicare --create-home medicare
WORKDIR /app/services/api
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -f /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --frozen --no-dev
COPY services/api/ ./
RUN mkdir -p /data && chown -R medicare:medicare /app /data
USER medicare
ENV LOCAL_DATA_DIR=/data UV_CACHE_DIR=/data/uv-cache
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD ["/app/services/api/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
