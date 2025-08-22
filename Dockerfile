# --------------------------
# Base image
# --------------------------
FROM python:3.12-slim

# --------------------------
# Environment variables
# --------------------------
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SPOTIPY_CLIENT_ID=your_spotify_client_id \
    SPOTIPY_CLIENT_SECRET=your_spotify_client_secret

# --------------------------
# Install system dependencies
# --------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# Set working directory
# --------------------------
WORKDIR /app

# --------------------------
# Copy files
# --------------------------
COPY requirements.txt .
COPY . .

# --------------------------
# Install Python dependencies
# --------------------------
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --------------------------
# Expose port (not strictly needed for Discord bot)
# --------------------------
EXPOSE 8080

# --------------------------
# Start the bot
# --------------------------
CMD ["python", "bot.py"]