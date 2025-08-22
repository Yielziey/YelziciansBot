# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port for Railway health checks (optional)
EXPOSE 8080

# Environment variables (can override in Railway)
ENV DISCORD_TOKEN=""
ENV SPOTIFY_CLIENT_ID=""
ENV SPOTIFY_CLIENT_SECRET=""
ENV YOUTUBE_API_KEY=""
ENV YOUTUBE_API_CHANNEL_ID=""

# Command to run the bot
CMD ["python", "bot.py"]
