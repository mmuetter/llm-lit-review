FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy code and data
COPY code/ ./code/
COPY data/ ./data/

# Set environment for Mistral API key (user provides via docker run -e)
ENV MISTRAL_API_KEY_FILE=/root/.mistral_key

# Default command
CMD ["/bin/bash"]
