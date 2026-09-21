# Stage 1: build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY isg/frontend/package.json ./
RUN npm install --legacy-peer-deps
COPY isg/frontend/ ./
ENV VITE_API_URL=""
ENV VITE_API_TOKEN="isg-demo-token-sih2026"
RUN npm run build

# Stage 2: Python backend (also serves the frontend build)
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && rm -rf /var/lib/apt/lists/*

COPY isg/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY isg/backend/ .

# Place frontend build where main.py expects it: ../frontend/build
COPY --from=frontend-build /frontend/build /frontend/build

ENV DEMO_API_KEY=isg-demo-token-sih2026
ENV ALLOWED_ORIGINS=*
ENV ENVIRONMENT=demo

EXPOSE 8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
