# Use official Python slim image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# system deps - include netcat-openbsd for wait loop
RUN apt-get update \
    && apt-get install -y build-essential libpq-dev gcc netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# copy and install python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# copy project
COPY . .

# make entrypoint executable (note: bind mount can mask this; ensure host file is executable)
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "agrovet_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]