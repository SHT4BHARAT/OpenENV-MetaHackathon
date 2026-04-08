FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    openenv-core \
    fastapi \
    uvicorn \
    pydantic \
    openai

# Copy source code
COPY . .

# Expose port 7860 for the FastAPI server (Hugging Face default)
EXPOSE 7860

# Start the environment server
CMD ["python", "-m", "server.app"]
