FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask gunicorn python-dotenv requests

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY miniapp_api.py weather_app.py bot.py storage.py ./

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "miniapp_api:app"]
