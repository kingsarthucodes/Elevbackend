# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies and librdkafka
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    curl \
    librdkafka-dev \
    && apt-get clean

# Copy the current directory contents into the container
COPY . /app

# Add the wait-for-it script to the container and make it executable
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask's port
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

# Command to run the Flask application
ENTRYPOINT ["/wait-for-it.sh", "kafka:9092", "--", "flask", "run", "--host=0.0.0.0", "--port=5000"]
