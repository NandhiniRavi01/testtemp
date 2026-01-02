FROM python:3.10-slim

WORKDIR /app

# Install system dependencies + curl + MySQL server
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    default-mysql-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==24.2 \
    && pip install --no-cache-dir -r requirements.txt --index-url https://pypi.org/simple

# Copy backend code
COPY . .

# Expose Flask port
EXPOSE 5000
EXPOSE 3306  # Expose MySQL port

# Start MySQL + Flask together (simplest way for testing)
CMD service mysql start && python app.py
