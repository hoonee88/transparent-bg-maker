FROM node:24-slim AS frontend

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY index.html tsconfig.json ./
COPY src ./src
RUN npm run build

FROM python:3.13-slim AS app

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV U2NET_HOME=/app/models
ENV MAX_UPLOAD_MB=12
ENV MAX_IMAGE_MEGAPIXELS=12
ENV INFERENCE_CONCURRENCY=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends libgomp1 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py ./
COPY scripts ./scripts
COPY --from=frontend /app/dist ./dist

ARG PREFETCH_MODELS=1
ARG PREFETCH_MODELS_LIST=u2netp
ENV PREFETCH_MODELS_LIST=${PREFETCH_MODELS_LIST}
RUN if [ "$PREFETCH_MODELS" = "1" ]; then python scripts/prefetch_models.py; fi

EXPOSE 8080
CMD ["sh", "-c", "python -m uvicorn backend:app --host 0.0.0.0 --port ${PORT:-8080}"]
