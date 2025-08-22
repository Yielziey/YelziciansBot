# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all bot files
COPY . .

# Set environment variable to flush stdout (optional but useful for logs)
ENV PYTHONUNBUFFERED=1

# Expose port if needed (e.g., for webhooks or health checks)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]