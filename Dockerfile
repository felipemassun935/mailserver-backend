# Build de dos etapas para terminar en UN solo contenedor (FastAPI sirve
# tanto la API como los estáticos del build de React). El contexto de build
# debe ser el directorio PADRE que contiene tanto mailserver-backend/ como
# mailserver-frontend/ como carpetas hermanas (ver docker-compose.yml).

FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY mailserver-frontend/package*.json ./
RUN npm ci
COPY mailserver-frontend/. .
RUN npm run build

FROM python:3.12-slim AS backend
WORKDIR /app

COPY mailserver-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mailserver-backend/app ./app
COPY --from=frontend-builder /frontend/dist ./static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
