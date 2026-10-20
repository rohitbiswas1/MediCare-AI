# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; \
    npm ci --no-audit --no-fund
COPY apps/web apps/web
COPY packages packages
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_DEMO_MODE=true API_INTERNAL_URL=http://127.0.0.1:8000
RUN npm run build

FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv
COPY --from=web /usr/local/bin/node /usr/local/bin/node
RUN --mount=type=secret,id=build_ca,mode=0444 \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    if [ -f /run/secrets/build_ca ]; then printf 'Acquire::https::CaInfo "/run/secrets/build_ca";\n' > /tmp/apt-ca.conf; export APT_CONFIG=/tmp/apt-ca.conf; fi; \
    apt-get update -o APT::Update::Error-Mode=any && \
    apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng fonts-dejavu-core ca-certificates libstdc++6 && \
    rm -rf /var/lib/apt/lists/* /tmp/apt-ca.conf
RUN groupadd --gid 10001 medicare && useradd --uid 10001 --gid medicare --create-home medicare
WORKDIR /app/services/api
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -f /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --frozen --no-dev
COPY services/api/ ./
COPY --from=web /app/apps/web/.next/standalone /app/web
COPY --from=web /app/apps/web/.next/static /app/web/apps/web/.next/static
COPY apps/web/public /app/web/apps/web/public
COPY scripts/render_start.py scripts/local_start.py scripts/generate_demo_samples.py /app/scripts/
RUN .venv/bin/python /app/scripts/generate_demo_samples.py /app/web/apps/web/public/demo && \
    mkdir -p /var/data/medicare && chown -R medicare:medicare /app /var/data
USER medicare
ENV APP_MODE=demo AUTH_PROVIDER=local STORAGE_PROVIDER=local \
    NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 LOCAL_DATA_DIR=/var/data/medicare \
    PORT=10000 PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["/app/services/api/.venv/bin/python", "/app/scripts/render_start.py"]
