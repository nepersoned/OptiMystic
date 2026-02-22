# Python base image
FROM python:3.8-slim

# Install CBC solver for optimization
RUN apt-get update && apt-get install -y \
    coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "optimystic.wsgi"]