FROM python:3.12-slim

RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Prague
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IS_DOCKER=True

WORKDIR /app

COPY src/requirements.txt .
# Append tzdata to requirements only for the Docker build
RUN echo "tzdata" >> requirements.txt && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x src/start.sh

EXPOSE 80

WORKDIR /app/src

CMD ["./start.sh"]
