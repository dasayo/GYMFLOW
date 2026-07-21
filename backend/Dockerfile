# GymFlow backend — FastAPI + SQLAlchemy + Alembic, dependencias con Pipenv

FROM python:3.13-slim AS base

# Dependencias del sistema necesarias para psycopg2 (driver de Postgres) y compilación de paquetes nativos.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pipenv fijo (no "el que sea más nuevo") para builds reproducibles.
RUN pip install --no-cache-dir pipenv==2024.0.1

# Copiamos solo los manifiestos primero para aprovechar la cache de Docker:
# si el código cambia pero Pipfile no, este paso no se vuelve a ejecutar.
COPY Pipfile Pipfile.lock ./
# Pipfile.lock ya se regeneró con Python 3.13 real, así que "--deploy"
# (falla si el lock no matchea exacto el Pipfile) es seguro de exigir aquí.
RUN pipenv install --system --deploy

COPY . .

EXPOSE 8000

# El entrypoint corre las migraciones antes de levantar el server —
# así "docker compose up" deja la base al día sin un paso manual aparte.
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
