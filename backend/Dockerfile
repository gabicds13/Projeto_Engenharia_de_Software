# BFF do ms-dashboard
FROM python:3.12-slim

WORKDIR /app

# Copiamos o projeto e o pacote antes de instalar: o pyproject declara
# packages = ["app"], então o diretório app/ precisa existir no momento do build.
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

ENV PORT=8006
EXPOSE 8006

CMD ["sh", "-c", "if [ -n \"$DATABASE_URL\" ]; then alembic upgrade head; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
