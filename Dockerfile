FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code is baked into the image; data, figures and report are mounted by
# docker-compose.yml so results persist on the host.
COPY code/ ./code/

# API keys (MISTRAL_API_KEY, ANTHROPIC_API_KEY) are passed in at run time.
WORKDIR /app/code
CMD ["/bin/bash"]
