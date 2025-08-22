# Dockerfile for YelziciansBot

# Base image
FROM python:3.12-slim

# -------------------------
# Environment & Workdir
# -------------------------
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------------------------
# Install system dependencies
# -------------------------
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Copy project files
# -------------------------
COPY . /app

# -------------------------
# Upgrade pip and install Python dependencies
# -------------------------
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

# -------------------------
# Expose any ports if needed
# -------------------------
# EXPOSE 8080

# -------------------------
# Command to run the bot
# -------------------------
CMD ["python", "bot.py"]
