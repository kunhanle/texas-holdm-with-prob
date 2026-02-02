FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (PORT will be set at runtime)
EXPOSE 8000

# Start application using PORT environment variable
# We use shell form to ensure any environment variables are handled correctly
CMD sh -c "gunicorn app:app --bind 0.0.0.0:${PORT:-8000}"
