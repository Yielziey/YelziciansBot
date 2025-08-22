# -------------------------
# Base Image
# -------------------------
FROM python:3.12-slim

# -------------------------
# Set environment variables
# -------------------------
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# -------------------------
# Set working directory
# -------------------------
WORKDIR /app

# -------------------------
# Install system dependencies
# -------------------------
RUN apt-get update && \
    apt-get install -y ffmpeg curl git ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -------------------------
# Install Python dependencies
# -------------------------
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -------------------------
# Copy bot code and cookies
# -------------------------
COPY . /app
# Ensure you have cookies.txt in your project root
# Railway allows secret files through Environment Variables if needed

# -------------------------
# Environment variables
# -------------------------
ENV DISCORD_TOKEN=""
ENV SPOTIFY_CLIENT_ID=""
ENV SPOTIFY_CLIENT_SECRET=""

# -------------------------
# Pre-fetch yt-dlp cookies (optional)
# -------------------------
# If you have a cookies.txt, ensure it's in the repo root.
# This allows yt-dlp to bypass YouTube restrictions
# You can also mount cookies via Railway environment secrets if preferred.

# -------------------------
# Run bot
# -------------------------
CMD ["python", "bot.py"]
