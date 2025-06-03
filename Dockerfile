# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (but not venv/)
COPY . .

# Default command to run your app (edit if needed!)
CMD [ "python", "agent.py", "run-agent" ]