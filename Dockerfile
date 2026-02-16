# Use Python 3.12 slim image as base
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry==2.2.1

# Copy dependency files
COPY pyproject.toml ./

# Configure Poetry to not create virtual environment (not needed in container)
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application source code
COPY src/ ./src/

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Expose application port (default: 3000)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:3000/api/v1/health', timeout=2.0)" || exit 1

# Run the application
CMD ["python", "-m", "main"]
