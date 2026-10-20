FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000 NDAKU_HTTPS=1
VOLUME /app/instance
CMD ["sh", "-c", "python seed.py; gunicorn -w 2 -b 0.0.0.0:${PORT} 'app:create_app()'"]
