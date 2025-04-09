FROM python:3.13.3-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Set Python path environment variable
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=fly_settings_override

# Run the start script
CMD ["./start.sh"]
