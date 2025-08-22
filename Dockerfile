# Base image
FROM python:3.12-slim

# Environment
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    wget \
    git \
    build-essential \
    libffi-dev \
    python3-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy YouTube cookies if exists
COPY cookies.txt /app/cookies.txt

# Entrypoint
CMD ["python", "bot.py"]