FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY ml/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML service code and model
COPY ml/ ./ml/

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:5000/health', timeout=2)" || exit 1

# Run the service
CMD ["uvicorn", "ml.app:app", "--host", "0.0.0.0", "--port", "5000"]
