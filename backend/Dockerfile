FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

# One worker is used because the demo's JWT logout blocklist is in-memory.
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "app:create_app()"]
