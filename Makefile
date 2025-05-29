# Makefile pour Douro
# Automatisation des tâches de développement, test et déploiement

# Variables
PYTHON = python3
PIP = pip3
VENV = venv
VENV_BIN = $(VENV)/bin
SERVICE_NAME = douro
INSTALL_DIR = /opt/douro
CONFIG_DIR = /etc/douro
LOG_DIR = /var/log/douro

# Couleurs pour l'affichage
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help install dev test lint clean build deploy service-install service-start service-stop service-status health check-config

# Aide par défaut
help:
	@echo "$(GREEN)Makefile pour Douro - Analyseur d'infrastructure$(NC)"
	@echo ""
	@echo "$(YELLOW)Commandes de développement:$(NC)"
	@echo "  install          - Installation initiale avec environnement virtuel"
	@echo "  dev              - Installation des dépendances de développement"
	@echo "  test             - Exécution des tests"
	@echo "  lint             - Vérification du code avec flake8 et mypy"
	@echo "  clean            - Nettoyage des fichiers temporaires"
	@echo ""
	@echo "$(YELLOW)Commandes de build et packaging:$(NC)"
	@echo "  build            - Construction du package Python"
	@echo "  check-config     - Validation de la configuration"
	@echo ""
	@echo "$(YELLOW)Commandes de déploiement:$(NC)"
	@echo "  deploy           - Déploiement complet sur le serveur"
	@echo "  service-install  - Installation du service systemd (nécessite sudo)"
	@echo "  service-start    - Démarrage du service"
	@echo "  service-stop     - Arrêt du service"
	@echo "  service-status   - Statut du service"
	@echo "  health           - Vérification de l'état de santé"

# Installation initiale
install:
	@echo "$(GREEN)Installation de Douro...$(NC)"
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	$(VENV_BIN)/pip install -e .
	@echo "$(GREEN)Installation terminée!$(NC)"
	@echo "Activez l'environnement avec: source $(VENV)/bin/activate"

# Installation des dépendances de développement
dev: install
	@echo "$(GREEN)Installation des dépendances de développement...$(NC)"
	$(VENV_BIN)/pip install flake8 mypy black isort pytest-cov
	@echo "$(GREEN)Environnement de développement configuré!$(NC)"

# Tests
test:
	@echo "$(GREEN)Exécution des tests...$(NC)"
	$(VENV_BIN)/python -m pytest douro/tests/ -v
	@echo "$(GREEN)Tests terminés!$(NC)"

# Tests avec couverture
test-cov:
	@echo "$(GREEN)Exécution des tests avec couverture...$(NC)"
	$(VENV_BIN)/python -m pytest douro/tests/ -v --cov=douro --cov-report=html --cov-report=term
	@echo "$(GREEN)Rapport de couverture généré dans htmlcov/$(NC)"

# Linting
lint:
	@echo "$(GREEN)Vérification du code...$(NC)"
	$(VENV_BIN)/flake8 douro/ --max-line-length=120 --ignore=E501,W503
	$(VENV_BIN)/mypy douro/ --ignore-missing-imports
	@echo "$(GREEN)Vérification terminée!$(NC)"

# Formatage du code
format:
	@echo "$(GREEN)Formatage du code...$(NC)"
	$(VENV_BIN)/black douro/ --line-length=120
	$(VENV_BIN)/isort douro/
	@echo "$(GREEN)Formatage terminé!$(NC)"

# Nettoyage
clean:
	@echo "$(GREEN)Nettoyage...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ htmlcov/ .coverage .pytest_cache/ .mypy_cache/
	@echo "$(GREEN)Nettoyage terminé!$(NC)"

# Build du package
build: clean
	@echo "$(GREEN)Construction du package...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "Création de l'environnement virtuel..."; \
		$(PYTHON) -m venv $(VENV); \
		$(VENV_BIN)/pip install --upgrade pip; \
		$(VENV_BIN)/pip install wheel setuptools; \
	fi
	$(VENV_BIN)/python setup.py sdist bdist_wheel
	@echo "$(GREEN)Package construit dans dist/$(NC)"

# Validation de la configuration
check-config:
	@echo "$(GREEN)Validation de la configuration...$(NC)"
	@if [ -f "config.json" ]; then \
		$(PYTHON) -c "import json; json.load(open('config.json'))" && echo "config.json: OK"; \
	else \
		echo "config.json: Fichier non trouvé (optionnel)"; \
	fi
	@if [ -f "config.production.json" ]; then \
		$(PYTHON) -c "import json; json.load(open('config.production.json'))" && echo "config.production.json: OK"; \
	else \
		echo "config.production.json: Fichier non trouvé (optionnel)"; \
	fi
	@echo "$(GREEN)Configuration validée!$(NC)"

# Analyse de sécurité
security:
	@echo "$(GREEN)Analyse de sécurité...$(NC)"
	$(VENV_BIN)/pip install safety bandit
	$(VENV_BIN)/safety check
	$(VENV_BIN)/bandit -r douro/ -f json -o security-report.json || true
	@echo "$(GREEN)Analyse de sécurité terminée!$(NC)"

# Déploiement complet
deploy: check-config
	@echo "$(GREEN)Déploiement de Douro...$(NC)"
	@if [ ! -d "$(INSTALL_DIR)" ]; then \
		echo "$(RED)Erreur: Répertoire d'installation $(INSTALL_DIR) n'existe pas!$(NC)"; \
		echo "Exécutez d'abord: sudo make service-install"; \
		exit 1; \
	fi
	sudo cp -r douro/ $(INSTALL_DIR)/
	sudo cp requirements.txt $(INSTALL_DIR)/
	sudo cp -f config.production.json $(INSTALL_DIR)/ || echo "Pas de config.production.json"
	sudo chown -R douro:douro $(INSTALL_DIR)
	cd $(INSTALL_DIR) && sudo -u douro python3 -m venv venv
	cd $(INSTALL_DIR) && sudo -u douro venv/bin/pip install --upgrade pip
	cd $(INSTALL_DIR) && sudo -u douro venv/bin/pip install -r requirements.txt
	@echo "$(GREEN)Déploiement terminé!$(NC)"

# Installation du service systemd
service-install:
	@echo "$(GREEN)Installation du service systemd...$(NC)"
	sudo ./scripts/install-service.sh
	@echo "$(GREEN)Service installé!$(NC)"

# Démarrage du service
service-start:
	@echo "$(GREEN)Démarrage du service $(SERVICE_NAME)...$(NC)"
	sudo systemctl start $(SERVICE_NAME)
	sudo systemctl status $(SERVICE_NAME) --no-pager -l
	@echo "$(GREEN)Service démarré!$(NC)"

# Arrêt du service
service-stop:
	@echo "$(YELLOW)Arrêt du service $(SERVICE_NAME)...$(NC)"
	sudo systemctl stop $(SERVICE_NAME)
	@echo "$(GREEN)Service arrêté!$(NC)"

# Redémarrage du service
service-restart:
	@echo "$(GREEN)Redémarrage du service $(SERVICE_NAME)...$(NC)"
	sudo systemctl restart $(SERVICE_NAME)
	sudo systemctl status $(SERVICE_NAME) --no-pager -l
	@echo "$(GREEN)Service redémarré!$(NC)"

# Statut du service
service-status:
	@echo "$(GREEN)Statut du service $(SERVICE_NAME):$(NC)"
	sudo systemctl status $(SERVICE_NAME) --no-pager -l

# Logs du service
service-logs:
	@echo "$(GREEN)Logs du service $(SERVICE_NAME):$(NC)"
	sudo journalctl -u $(SERVICE_NAME) -f

# Vérification de l'état de santé
health:
	@echo "$(GREEN)Vérification de l'état de santé...$(NC)"
	@curl -s http://localhost:9106/health | python3 -m json.tool || echo "$(RED)Service non accessible$(NC)"
	@echo ""
	@curl -s http://localhost:9106/ready | python3 -m json.tool || echo "$(RED)Service pas prêt$(NC)"

# Configuration de monitoring
monitoring:
	@echo "$(GREEN)URLs de monitoring:$(NC)"
	@echo "Métriques Prometheus: http://localhost:9105/metrics"
	@echo "Health check:        http://localhost:9106/health"
	@echo "Readiness probe:     http://localhost:9106/ready"
	@echo "Liveness probe:      http://localhost:9106/live"

# Installation complète (dev + service)
install-all: dev service-install deploy service-start
	@echo "$(GREEN)Installation complète terminée!$(NC)"
	make monitoring

# Mise à jour du service
update: deploy service-restart
	@echo "$(GREEN)Mise à jour terminée!$(NC)"
	sleep 3
	make health 