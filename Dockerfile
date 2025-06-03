# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get install -y locales fonts-dejavu-core \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

# Copy the rest of the application code (but not venv/)
COPY . .

COPY entrypoint.py /entrypoint.py

ENV TERM=xterm-256color
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENTRYPOINT ["python", "/entrypoint.py"]