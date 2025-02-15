.PHONY: run migrate build test npm-dev npm-build up down restart

# Default target
all: build run

# Start the development server with all dependencies
run: npm-build
	docker-compose exec app python manage.py runserver 0.0.0.0:3000

# Run database migrations
migrate: up
	docker-compose exec app python manage.py makemigrations
	docker-compose exec app python manage.py migrate

# Docker restart
restart: down up

# Build npm assets
npm-build: up
	docker-compose exec app npm run build

# Start npm development mode in background (depends on docker being up)
dev: up
	docker-compose exec app npm run dev

# Build the Docker containers
build:
	docker-compose build

# Run the test suite
# Usage: make test TEST_ARGS="-v -k test_name"
test: up
	docker-compose exec app pytest $(TEST_ARGS)

# Run playwright tests in headed mode
test-headed: up
	docker-compose exec app pytest -s --headed $(TEST_ARGS)

# Run playwright tests in headed mode
test-debug: up
	docker-compose exec -e PWDEBUG=1 app pytest -s --headed $(TEST_ARGS)

# Start Docker containers
up:
	docker-compose up -d

# Stop Docker containers
down:
	docker-compose down

# Clean up Docker resources
clean: down
	docker system prune -f

kill:
	docker kill $(docker ps -q)

# Show help
help:
	@echo "Available targets:"
	@echo "  all         - Run everything (docker build and run)"
	@echo "  run      - Start just development server with all dependencies"
	@echo "  dev         - Start npm in devlopment mode plus the development server"
	@echo "  migrate     - Run database migrations"
	@echo "  build       - Build Docker containers"
	@echo "  test        - Run test suite"
	@echo "  test-headed - Run playwright tests in headed mode"
	@echo "  npm-dev     - Start npm in development mode"
	@echo "  npm-build   - Build npm assets"
	@echo "  up          - Start Docker containers"
	@echo "  down        - Stop Docker containers"
	@echo "  restart     - Restart Docker containers"
	@echo "  clean       - Clean up all Docker resources"
	@echo "  kill        - Kill all Docker containers"
	@echo "  help        - Show this help message"
