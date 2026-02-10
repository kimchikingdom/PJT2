FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "flask --app manage.py init-db && gunicorn --bind 0.0.0.0:8000 'app:create_app()'"]
