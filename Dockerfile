# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set environment variables to avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Copy the project files to the work directory
COPY . .

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on (if needed)
EXPOSE 8000

# Command to run the bot
CMD ["python", "main.py"]
