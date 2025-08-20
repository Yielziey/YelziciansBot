# Gamitin ang official Python 3.12 image
FROM python:3.12.7-slim

# Gumawa ng working directory sa loob ng container
WORKDIR /app

# Kopyahin lahat ng project files papunta sa container
COPY . .

# Install dependencies mula sa requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Command na magpapatakbo ng bot
CMD ["python", "bot.py"]
