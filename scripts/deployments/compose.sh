#!/bin/bash

compose_up() {
    echo "Starting services with Docker Compose..."
    docker-compose up -d "$@"
}

compose_down() {
    echo "Stopping services..."
    docker-compose down "$@"
}

compose_logs() {
    echo "Showing logs..."
    docker-compose logs "$@"
}