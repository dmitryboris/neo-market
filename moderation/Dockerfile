FROM python:3.13-slim

WORKDIR /app

COPY moderation/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared /tmp/shared

RUN pip install --no-cache-dir /tmp/shared

COPY moderation/src /app/src

COPY moderation/migrations /app/migrations

COPY moderation/alembic.ini /app/alembic.ini

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]