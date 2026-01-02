FROM python:3.10-slim

WORKDIR /app

# Install dependencies + MySQL 8 client + build tools
RUN apt-get update && apt-get install -y wget lsb-release gnupg build-essential curl \
    && wget https://dev.mysql.com/get/mysql-apt-config_0.8.30-1_all.deb \
    && DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.30-1_all.deb \
    && apt-get update \
    && apt-get install -y mysql-client \
    && curl -o /etc/ssl/certs/rds-ca.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
    && chmod 644 /etc/ssl/certs/rds-ca.pem \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==24.2 \
    && pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Flask port
EXPOSE 5000

# Start app
CMD ["python", "app.py"]
