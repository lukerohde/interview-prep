.PHONY: run-server build test npm-dev npm-build docker-up docker-down docker-restart

# Default target
all: build run-server

# Start the development server with all dependencies
run-server: npm-build
	docker-compose exec app python manage.py runserver 0.0.0.0:3000

# Run database migrations
migrate: docker-up
	docker-compose exec app python manage.py makemigrations
	docker-compose exec app python manage.py migrate

make dev: 
	make npm-dev & make run-server

# Docker restart
docker-restart: docker-down docker-up

# Start npm development mode in background (depends on docker being up)
npm-build: docker-up
	docker-compose exec app npm run build

# Build the Docker containers
build:
	docker-compose build

# Run the test suite
test: docker-up
	docker-compose exec app pytest

# Run playwright tests in headed mode
test-headed: docker-up
	docker-compose exec app pytest --headed

# Build npm assets
npm-dev: docker-up
	docker-compose exec app npm run dev

# Start Docker containers
docker-up:
	docker-compose up -d

# Stop Docker containers
docker-down:
	docker-compose down

# Clean up Docker resources
clean: docker-down
	docker system prune -f

kill:
	docker kill $(docker ps -q)

# Show help
help:
	@echo "Available targets:"
	@echo "  all         - Run everything (docker build and run-server)"
	@echo "  run-server  - Start just development server with all dependencies"
	@echo "  dev         - Start npm in devlopment mode plus the development server"
	@echo "  migrate     - Run database migrations"
	@echo "  build       - Build Docker containers"
	@echo "  test        - Run test suite"
	@echo "  test-headed - Run playwright tests in headed mode"
	@echo "  npm-dev     - Start npm in development mode"
	@echo "  npm-build   - Build npm assets"
	@echo "  docker-up   - Start Docker containers"
	@echo "  docker-down - Stop Docker containers"
	@echo "  docker-restart - Restart Docker containers"
	@echo "  clean       - Clean up all Docker resources"
	@echo "  kill        - Kill all Docker containers"
	@echo "  help        - Show this help message"
