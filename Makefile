# Makefile for Douro
# Automation of development, testing and deployment tasks

# Variables
PYTHON = python3
PIP = pip3
VENV = venv
VENV_BIN = $(VENV)/bin
SERVICE_NAME = douro
INSTALL_DIR = /opt/douro
CONFIG_DIR = /etc/douro
LOG_DIR = /var/log/douro

# Colors for display
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help install dev test lint clean build deploy service-install service-start service-stop service-status health check-config

# Default help
help:
	@echo "$(GREEN)Makefile for Douro - Infrastructure Analyzer$(NC)"
	@echo ""
	@echo "$(YELLOW)Development commands:$(NC)"
	@echo "  install          - Initial installation with virtual environment"
	@echo "  dev              - Install development dependencies"
	@echo "  test             - Run tests"
	@echo "  lint             - Code verification with flake8 and mypy"
	@echo "  clean            - Clean temporary files"
	@echo ""
	@echo "$(YELLOW)Build and packaging commands:$(NC)"
	@echo "  build            - Build Python package"
	@echo "  check-config     - Configuration validation"
	@echo ""
	@echo "$(YELLOW)Deployment commands:$(NC)"
	@echo "  deploy           - Complete deployment on server"
	@echo "  service-install  - Install systemd service (requires sudo)"
	@echo "  service-start    - Start service"
	@echo "  service-stop     - Stop service"
	@echo "  service-status   - Service status"
	@echo "  health           - Health check"

# Initial installation
install:
	@echo "$(GREEN)Installing Douro...$(NC)"
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	$(VENV_BIN)/pip install -e .
	@echo "$(GREEN)Installation completed!$(NC)"
	@echo "Activate environment with: source $(VENV)/bin/activate"

# Development dependencies installation
dev: install
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(VENV_BIN)/pip install flake8 mypy black isort pytest-cov
	@echo "$(GREEN)Development environment configured!$(NC)"

# Tests
test:
	@echo "$(GREEN)Running tests...$(NC)"
	$(VENV_BIN)/python -m pytest douro/tests/ -v
	@echo "$(GREEN)Tests completed!$(NC)"

# Tests with coverage
test-cov:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(VENV_BIN)/python -m pytest douro/tests/ -v --cov=douro --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

# Linting
lint:
	@echo "$(GREEN)Code verification...$(NC)"
	$(VENV_BIN)/flake8 douro/ --max-line-length=120 --ignore=E501,W503
	$(VENV_BIN)/mypy douro/ --ignore-missing-imports
	@echo "$(GREEN)Verification completed!$(NC)"

# Code formatting
format:
	@echo "$(GREEN)Code formatting...$(NC)"
	$(VENV_BIN)/black douro/ --line-length=120
	$(VENV_BIN)/isort douro/
	@echo "$(GREEN)Formatting completed!$(NC)"

# Cleanup
clean:
	@echo "$(GREEN)Cleaning...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/ .coverage .pytest_cache/ .mypy_cache/
	@echo "$(GREEN)Cleanup completed!$(NC)"

# Package build
build: clean
	@echo "$(GREEN)Building package...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		$(VENV_BIN)/pip install --upgrade pip; \
		$(VENV_BIN)/pip install wheel setuptools; \
	fi
	$(VENV_BIN)/python setup.py sdist bdist_wheel
	@echo "$(GREEN)Package built in dist/$(NC)"

# Configuration validation
check-config:
	@echo "$(GREEN)Configuration validation...$(NC)"
	@if [ -f "config.json" ]; then \
		$(PYTHON) -c "import json; json.load(open('config.json'))" && echo "config.json: OK"; \
	else \
		echo "config.json: File not found (optional)"; \
	fi
	@if [ -f "config.production.json" ]; then \
		$(PYTHON) -c "import json; json.load(open('config.production.json'))" && echo "config.production.json: OK"; \
	else \
		echo "config.production.json: File not found (optional)"; \
	fi
	@echo "$(GREEN)Configuration validated!$(NC)"

# Security analysis
security:
	@echo "$(GREEN)Security analysis...$(NC)"
	$(VENV_BIN)/pip install safety bandit
	$(VENV_BIN)/safety check
	$(VENV_BIN)/bandit -r douro/ -f json -o security-report.json || true
	@echo "$(GREEN)Security analysis completed!$(NC)"

# Complete deployment
deploy: check-config
	@echo "$(GREEN)Deploying Douro...$(NC)"
	@if [ ! -d "$(INSTALL_DIR)" ]; then \
		echo "$(RED)Error: Installation directory $(INSTALL_DIR) does not exist!$(NC)"; \
		echo "Run first: sudo make service-install"; \
		exit 1; \
	fi
	sudo cp -r douro/ $(INSTALL_DIR)/
	sudo cp requirements.txt $(INSTALL_DIR)/
	sudo cp -f config.production.json $(INSTALL_DIR)/ || echo "No config.production.json"
	sudo chown -R douro:douro $(INSTALL_DIR)
	cd $(INSTALL_DIR) && sudo -u douro python3 -m venv venv
	cd $(INSTALL_DIR) && sudo -u douro venv/bin/pip install --upgrade pip
	cd $(INSTALL_DIR) && sudo -u douro venv/bin/pip install -r requirements.txt
	@echo "$(GREEN)Deployment completed!$(NC)"

# Systemd service installation
service-install:
	@echo "$(GREEN)Installing systemd service...$(NC)"
	sudo ./scripts/install-service.sh
	@echo "$(GREEN)Service installed!$(NC)"

# Start service
service-start:
	@echo "$(GREEN)Starting $(SERVICE_NAME) service...$(NC)"
	sudo systemctl start $(SERVICE_NAME)
	sudo systemctl status $(SERVICE_NAME) --no-pager -l
	@echo "$(GREEN)Service started!$(NC)"

# Stop service
service-stop:
	@echo "$(YELLOW)Stopping $(SERVICE_NAME) service...$(NC)"
	sudo systemctl stop $(SERVICE_NAME)
	@echo "$(GREEN)Service stopped!$(NC)"

# Restart service
service-restart:
	@echo "$(GREEN)Restarting $(SERVICE_NAME) service...$(NC)"
	sudo systemctl restart $(SERVICE_NAME)
	sudo systemctl status $(SERVICE_NAME) --no-pager -l
	@echo "$(GREEN)Service restarted!$(NC)"

# Service status
service-status:
	@echo "$(GREEN)$(SERVICE_NAME) service status:$(NC)"
	sudo systemctl status $(SERVICE_NAME) --no-pager -l

# Service logs
service-logs:
	@echo "$(GREEN)$(SERVICE_NAME) service logs:$(NC)"
	sudo journalctl -u $(SERVICE_NAME) -f

# Health check
health:
	@echo "$(GREEN)Health check...$(NC)"
	@curl -s http://localhost:9106/health | python3 -m json.tool || echo "$(RED)Service not accessible$(NC)"
	@echo ""
	@curl -s http://localhost:9106/ready | python3 -m json.tool || echo "$(RED)Service not ready$(NC)"

# Monitoring configuration
monitoring:
	@echo "$(GREEN)Monitoring URLs:$(NC)"
	@echo "Prometheus metrics: http://localhost:9105/metrics"
	@echo "Health check:       http://localhost:9106/health"
	@echo "Readiness probe:    http://localhost:9106/ready"
	@echo "Liveness probe:     http://localhost:9106/live"

# Complete installation (dev + service)
install-all: dev service-install deploy service-start
	@echo "$(GREEN)Complete installation completed!$(NC)"
	make monitoring

# Service update
update: deploy service-restart
	@echo "$(GREEN)Service update completed!$(NC)"
	sleep 3
	make health 