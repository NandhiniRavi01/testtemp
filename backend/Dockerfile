FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies + MySQL client + curl for CA bundle
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        default-mysql-client \
    && curl -o /etc/ssl/certs/rds-ca.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
    && chmod 644 /etc/ssl/certs/rds-ca.pem \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==24.2 \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose Flask port
EXPOSE 5000

# Start Flask app
CMD ["python", "app.py"]
