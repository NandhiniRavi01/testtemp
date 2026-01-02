FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==24.2 \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Download RDS CA bundle inside container
RUN curl -o /app/rds-ca.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# Expose Flask port
EXPOSE 5000

# Start Flask app
CMD ["python", "app.py"]
