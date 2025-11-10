# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional: git, curl, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file if you have one
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port (Railway requires it, even if using long polling)
EXPOSE 8080

# Environment variables (Railway will inject these)
# BOT_TOKEN, MONGO_URI, OWNER_ID, etc.

# Run the bot
CMD ["python", "RiddleBot.py"]
