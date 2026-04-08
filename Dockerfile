FROM python:3.10-slim

# Set up a new user named "user" with user ID 1000
# Hugging Face enforces running as UID 1000 for security.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the current directory contents into the container at $HOME/app setting the owner to the user
COPY --chown=user . $HOME/app

# Install dependencies
RUN pip install --no-cache-dir \
    openenv-core \
    fastapi \
    uvicorn \
    pydantic \
    openai

# Expose port 7860 for the FastAPI server (Hugging Face default)
EXPOSE 7860

# Start the environment server
CMD ["python", "-m", "server.app"]
