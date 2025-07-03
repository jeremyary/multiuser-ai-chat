# Multi-User AI Chat System - Simplified Makefile
# =================================================

# Configuration
PROJECT_NAME := ai-chat-system
COMPOSE_FILE := docker-compose.yml
COMPOSE_PROD_FILE := docker-compose.prod.yml
COMPOSE_REGISTRY_FILE := docker-compose.registry.yml
AI_MODEL_URL := http://10.0.0.38:1234

# Docker settings
DOCKER_REGISTRY ?= quay.io/jary
TAG ?= latest
BACKEND_IMAGE := $(DOCKER_REGISTRY)/$(PROJECT_NAME)-backend:$(TAG)
WEBCLIENT_IMAGE := $(DOCKER_REGISTRY)/$(PROJECT_NAME)-webclient:$(TAG)

# Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
CYAN := \033[36m
RESET := \033[0m

.PHONY: help build build-backend build-webclient deploy clean logs restart setup health status pull push dev prod

# Default target
help: ## Show this help message
	@echo "$(CYAN)Multi-User AI Chat System$(RESET)"
	@echo "==============================="
	@echo ""
	@echo "$(YELLOW)Available commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Configuration:$(RESET)"
	@echo "  AI Model URL: $(CYAN)$(AI_MODEL_URL)$(RESET)"
	@echo "  Registry: $(CYAN)$(DOCKER_REGISTRY)$(RESET)"

setup: ## Initial setup - create necessary files and directories
	@echo "$(BLUE)🚀 Setting up Multi-User AI Chat System...$(RESET)"
	@mkdir -p logs data/redis
	@if [ ! -f .env ]; then \
		cp env.example .env && \
		echo "$(GREEN)✅ Created .env file$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  .env file already exists$(RESET)"; \
	fi
	@echo "$(GREEN)✅ Setup completed!$(RESET)"

build: build-backend build-webclient ## Build all Docker images
	@echo "$(GREEN)✅ All images built successfully!$(RESET)"

build-backend: ## Build the backend Docker image
	@echo "$(BLUE)🔨 Building backend image...$(RESET)"
	@docker build -f Dockerfile.backend -t $(BACKEND_IMAGE) .
	@docker tag $(BACKEND_IMAGE) $(PROJECT_NAME)-backend:latest
	@echo "$(GREEN)✅ Backend image built$(RESET)"

build-webclient: ## Build the web client Docker image
	@echo "$(BLUE)🔨 Building webclient image...$(RESET)"
	@docker build -f Dockerfile.webclient -t $(WEBCLIENT_IMAGE) .
	@docker tag $(WEBCLIENT_IMAGE) $(PROJECT_NAME)-webclient:latest
	@echo "$(GREEN)✅ Webclient image built$(RESET)"

deploy: build ## Deploy the full stack using Docker Compose
	@echo "$(BLUE)🚀 Deploying $(PROJECT_NAME) stack...$(RESET)"
	@docker-compose -f $(COMPOSE_PROD_FILE) up -d
	@echo "$(GREEN)✅ Stack deployed successfully!$(RESET)"

dev: ## Start development environment
	@echo "$(BLUE)🛠️  Starting development environment...$(RESET)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Development environment started!$(RESET)"

stop: ## Stop all services
	@echo "$(YELLOW)⏹️  Stopping all services...$(RESET)"
	@docker-compose -f $(COMPOSE_PROD_FILE) down 2>/dev/null || true
	@docker-compose -f $(COMPOSE_REGISTRY_FILE) down 2>/dev/null || true
	@docker-compose -f $(COMPOSE_FILE) down 2>/dev/null || true
	@echo "$(GREEN)✅ All services stopped$(RESET)"

restart: stop deploy ## Restart all services

clean: stop ## Remove containers, images, and volumes
	@echo "$(RED)🧹 Cleaning up containers and images...$(RESET)"
	@docker-compose -f $(COMPOSE_PROD_FILE) down -v --remove-orphans 2>/dev/null || true
	@docker-compose -f $(COMPOSE_REGISTRY_FILE) down -v --remove-orphans 2>/dev/null || true
	@docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans 2>/dev/null || true
	@docker rmi $(BACKEND_IMAGE) $(WEBCLIENT_IMAGE) 2>/dev/null || true
	@docker rmi $(PROJECT_NAME)-backend:latest $(PROJECT_NAME)-webclient:latest 2>/dev/null || true
	@docker system prune -f
	@echo "$(GREEN)✅ Cleanup completed$(RESET)"

logs: ## Show logs from all services
	@echo "$(BLUE)�� Showing logs from all services...$(RESET)"
	@docker-compose -f $(COMPOSE_PROD_FILE) logs -f --tail=100 2>/dev/null || \
	docker-compose -f $(COMPOSE_FILE) logs -f --tail=100

logs-backend: ## Show backend logs only
	@docker-compose -f $(COMPOSE_PROD_FILE) logs -f backend 2>/dev/null || \
	docker-compose -f $(COMPOSE_FILE) logs -f backend

logs-redis: ## Show Redis logs only
	@docker-compose -f $(COMPOSE_PROD_FILE) logs -f redis 2>/dev/null || \
	docker-compose -f $(COMPOSE_FILE) logs -f redis

status: ## Check status of all services
	@echo "$(BLUE)📊 Service Status:$(RESET)"
	@docker-compose -f $(COMPOSE_PROD_FILE) ps 2>/dev/null || docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)🔍 Health Checks:$(RESET)"
	@echo -n "Backend API: "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null | \
		awk '{if($$1=="200") print "$(GREEN)✅ Healthy$(RESET)"; else print "$(RED)❌ Unhealthy$(RESET)"}'
	@echo -n "AI Model: "
	@curl -s -o /dev/null -w "%{http_code}" $(AI_MODEL_URL)/v1/models 2>/dev/null | \
		awk '{if($$1=="200") print "$(GREEN)✅ Healthy$(RESET)"; else print "$(RED)❌ Unhealthy$(RESET)"}'

health: status ## Alias for status command

install: ## Install backend dependencies  
	@echo "$(BLUE)📦 Installing backend dependencies...$(RESET)"
	@pip install -r requirements.txt
	@echo "$(GREEN)✅ Backend dependencies installed$(RESET)"

push: build ## Push images to registry
	@echo "$(BLUE)📤 Pushing images to registry...$(RESET)"
	@docker push $(BACKEND_IMAGE)
	@docker push $(WEBCLIENT_IMAGE)
	@echo "$(GREEN)✅ All images pushed successfully$(RESET)"

pull: ## Pull images from registry
	@echo "$(BLUE)📥 Pulling images from registry...$(RESET)"
	@docker pull $(BACKEND_IMAGE)
	@docker pull $(WEBCLIENT_IMAGE)
	@echo "$(GREEN)✅ Images pulled successfully$(RESET)"

prod: deploy ## Alias for deploy command

all: setup build deploy status ## Run complete setup and deployment
