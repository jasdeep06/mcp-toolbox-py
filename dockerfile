# Dockerfile
FROM python:3.12.6-slim

ENV PYTHONPATH="/plugins:${PYTHONPATH}"

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8002

# Default command
CMD ["python", "-m", "cli", "serve", "--tools-file", "tools.yaml", "--host", "0.0.0.0", "--port", "8002"]