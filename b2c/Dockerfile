FROM python:3.13-slim

WORKDIR /app

COPY b2c/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared /tmp/shared

RUN pip install --no-cache-dir /tmp/shared

COPY b2c/src /app/src

COPY b2c/migrations /app/migrations

COPY b2c/alembic.ini /app/alembic.ini

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]