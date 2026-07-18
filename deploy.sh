#!/bin/bash
echo "Starting PropBot Pipecat Deployment..."

# Ensure Docker is installed
if ! command -v docker &> /dev/null
then
    echo "Docker could not be found. Please install Docker first."
    exit 1
fi

# Build and run the Pipecat container in the background
echo "Building and spinning up docker containers..."
docker-compose up -d --build

echo "Deployment complete! Pipecat worker is running."
echo "Use 'docker logs -f propbot-pipecat' to monitor the logs."
