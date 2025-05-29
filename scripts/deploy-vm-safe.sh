#!/bin/bash

# Script de déploiement sécurisé pour Douro
# Version améliorée avec plus de vérifications

set -euo pipefail  # Arrêt strict sur toute erreur

# Couleurs
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly INSTALL_DIR="/opt/douro"
readonly LOG_FILE="/tmp/douro-install.log"

# Fonctions de logging
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Gestion des erreurs
error_exit() {
    log_error "$1"
    log_error "Installation échouée. Consultez les logs: $LOG_FILE"
    exit 1
}

# Trap pour nettoyer en cas d'erreur
cleanup() {
    if [[ $? -ne 0 ]]; then
        log_error "Script interrompu ! Consultez les logs: $LOG_FILE"
    fi
}
trap cleanup EXIT

# Vérification de l'utilisateur
check_user() {
    log "Vérification de l'utilisateur..."
    
    if [[ $EUID -eq 0 ]]; then
        error_exit "Ne pas exécuter ce script en tant que root !"
    fi
    
    local current_user=$(whoami)
    log "Utilisateur actuel: $current_user"
    
    # Vérifier les privilèges sudo
    if ! sudo -l >/dev/null 2>&1; then
        error_exit "L'utilisateur $current_user n'a pas les privilèges sudo"
    fi
    
    log "✓ Privilèges sudo confirmés"
}

# Vérification du système
check_system() {
    log "Vérification du système..."
    
    # Vérifier que c'est Linux
    if [[ "$(uname)" != "Linux" ]]; then
        error_exit "Ce script nécessite Linux"
    fi
    
    # Vérifier Python 3
    if ! command -v python3 >/dev/null 2>&1; then
        log_warn "Python 3 non trouvé, installation en cours..."
        install_dependencies
    fi
    
    # Vérifier la version Python avec une méthode plus robuste
    local python_version_check=$(python3 -c "
import sys
major, minor = sys.version_info[:2]
if major >= 3 and minor >= 7:
    print('OK')
else:
    print(f'{major}.{minor}')
    exit(1)
" 2>/dev/null)
    
    if [[ "$python_version_check" != "OK" ]]; then
        error_exit "Python 3.7+ requis, trouvé: $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    fi
    
    log "✓ Système compatible ($(uname -a | cut -d' ' -f1-3))"
    log "✓ Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') détecté"
}

# Installation des dépendances
install_dependencies() {
    log "Installation des dépendances système..."
    
    # Détecter la distribution
    if [[ -f /etc/debian_version ]]; then
        log_info "Distribution: Debian/Ubuntu détectée"
        sudo apt update || error_exit "Échec de apt update"
        sudo apt install -y python3 python3-venv python3-pip curl make git || error_exit "Échec d'installation des paquets"
    elif [[ -f /etc/redhat-release ]]; then
        log_info "Distribution: RedHat/CentOS détectée"
        sudo yum update -y || error_exit "Échec de yum update"
        sudo yum install -y python3 python3-pip curl make git || error_exit "Échec d'installation des paquets"
    else
        error_exit "Distribution non supportée"
    fi
    
    log "✓ Dépendances installées"
}

# Vérification des fichiers du projet
check_project_files() {
    log "Vérification des fichiers du projet..."
    
    # Aller dans le répertoire du projet
    cd "$PROJECT_ROOT" || error_exit "Impossible d'accéder à $PROJECT_ROOT"
    
    # Vérifier les fichiers essentiels
    local required_files=("Makefile" "requirements.txt" "setup.py")
    local required_dirs=("douro" "systemd" "scripts")
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error_exit "Fichier manquant: $file"
        fi
    done
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            error_exit "Répertoire manquant: $dir"
        fi
    done
    
    log "✓ Structure du projet validée"
    pwd
}

# Test de la configuration
test_config() {
    log "Test de la configuration..."
    
    # Tester la création d'un environnement virtuel
    local test_venv="/tmp/test-douro-venv"
    python3 -m venv "$test_venv" || error_exit "Impossible de créer un environnement virtuel"
    rm -rf "$test_venv"
    
    # Vérifier que make est fonctionnel
    if ! make --version >/dev/null 2>&1; then
        error_exit "Make non fonctionnel"
    fi
    
    log "✓ Configuration système OK"
}

# Installation de Douro étape par étape
install_douro_step_by_step() {
    log "=== DÉBUT DE L'INSTALLATION DOURO ==="
    
    # Étape 1: Installation du service systemd
    log "Étape 1/5: Installation du service systemd et création utilisateur douro..."
    if ! sudo make service-install; then
        error_exit "Échec de l'installation du service systemd"
    fi
    log "✓ Service systemd installé"
    
    # Vérifier que l'utilisateur douro a été créé
    if ! id douro >/dev/null 2>&1; then
        error_exit "Utilisateur douro non créé"
    fi
    log "✓ Utilisateur douro créé"
    
    # Étape 2: Déploiement du code
    log "Étape 2/5: Déploiement du code..."
    if ! make deploy; then
        error_exit "Échec du déploiement"
    fi
    log "✓ Code déployé"
    
    # Étape 3: Configuration
    log "Étape 3/5: Configuration..."
    configure_production_settings
    
    # Étape 4: Validation
    log "Étape 4/5: Validation de la configuration..."
    if ! make check-config; then
        error_exit "Configuration invalide"
    fi
    log "✓ Configuration validée"
    
    # Étape 5: Démarrage
    log "Étape 5/5: Démarrage du service..."
    if ! sudo systemctl start douro; then
        error_exit "Échec du démarrage du service"
    fi
    
    # Vérifier que le service est actif
    sleep 5
    if ! sudo systemctl is-active --quiet douro; then
        log_error "Service non actif"
        sudo systemctl status douro --no-pager -l
        error_exit "Service douro inactif"
    fi
    
    log "✓ Service démarré avec succès"
}

# Configuration pour la production
configure_production_settings() {
    log "Configuration des paramètres de production..."
    
    # Créer une configuration de test sécurisée
    local config_file="$INSTALL_DIR/config.production.json"
    
    sudo tee "$config_file" > /dev/null << 'EOF'
{
  "exporter": {
    "port": 9105,
    "interval_seconds": 300,
    "timeout_seconds": 15
  },
  "domains": [
    {
      "name": "google.com",
      "enabled": true,
      "description": "Test de connectivité - Google"
    },
    {
      "name": "github.com",
      "enabled": true,
      "description": "Test de connectivité - GitHub"
    }
  ],
  "monitoring": {
    "log_level": "INFO",
    "enable_verbose_logging": false
  }
}
EOF
    
    sudo chown douro:douro "$config_file" || error_exit "Impossible de changer les permissions du fichier config"
    log "✓ Configuration de production créée"
}

# Tests complets de fonctionnement
run_comprehensive_tests() {
    log "Tests complets de fonctionnement..."
    
    # Test 1: Service actif
    if ! sudo systemctl is-active --quiet douro; then
        error_exit "Service douro non actif"
    fi
    log "✓ Service actif"
    
    # Test 2: Attendre que l'application soit prête
    local max_attempts=60
    local attempt=1
    
    log "Attente du démarrage complet de l'application..."
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s --connect-timeout 5 http://localhost:9106/ready >/dev/null 2>&1; then
            log "✓ Application prête après $attempt tentatives"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error_exit "Application non prête après $max_attempts tentatives"
        fi
        
        log_info "Tentative $attempt/$max_attempts..."
        sleep 3
        ((attempt++))
    done
    
    # Test 3: Endpoints
    local endpoints=("metrics:9105" "health:9106" "ready:9106" "live:9106")
    
    for endpoint in "${endpoints[@]}"; do
        local name="${endpoint%:*}"
        local port="${endpoint#*:}"
        local path=""
        
        if [[ "$name" == "metrics" ]]; then
            path="/metrics"
        else
            path="/$name"
        fi
        
        if curl -s --connect-timeout 10 "http://localhost:$port$path" >/dev/null; then
            log "✓ Endpoint $name OK"
        else
            log_warn "✗ Endpoint $name KO"
        fi
    done
    
    log "✓ Tests de fonctionnement terminés"
}

# Configuration du firewall (optionnel)
configure_firewall() {
    log "Configuration du firewall..."
    
    if command -v ufw >/dev/null 2>&1; then
        if sudo ufw status | grep -q "Status: active"; then
            sudo ufw allow 9105/tcp comment "Douro Prometheus metrics" || log_warn "Échec config firewall port 9105"
            sudo ufw allow 9106/tcp comment "Douro health checks" || log_warn "Échec config firewall port 9106"
            log "✓ Règles UFW ajoutées"
        else
            log_info "UFW non actif, pas de configuration firewall"
        fi
    elif command -v firewall-cmd >/dev/null 2>&1; then
        if systemctl is-active --quiet firewalld; then
            sudo firewall-cmd --permanent --add-port=9105/tcp || log_warn "Échec config firewall port 9105"
            sudo firewall-cmd --permanent --add-port=9106/tcp || log_warn "Échec config firewall port 9106"
            sudo firewall-cmd --reload || log_warn "Échec reload firewall"
            log "✓ Règles firewalld ajoutées"
        else
            log_info "Firewalld non actif, pas de configuration firewall"
        fi
    else
        log_info "Aucun firewall détecté"
    fi
}

# Résumé final
show_final_summary() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}   ✅ INSTALLATION RÉUSSIE !${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    echo -e "\n${GREEN}🎯 Douro est maintenant installé et fonctionnel${NC}"
    echo -e "${GREEN}👤 Utilisateur 'douro' créé${NC}"
    echo -e "${GREEN}🔧 Service systemd configuré${NC}"
    echo -e "${GREEN}🚀 Application démarrée${NC}"
    
    echo -e "\n${YELLOW}📊 URLs de monitoring :${NC}"
    echo -e "  • Métriques Prometheus: ${BLUE}http://$(hostname -I | awk '{print $1}'):9105/metrics${NC}"
    echo -e "  • Health check:         ${BLUE}http://$(hostname -I | awk '{print $1}'):9106/health${NC}"
    echo -e "  • Readiness probe:      ${BLUE}http://$(hostname -I | awk '{print $1}'):9106/ready${NC}"
    echo -e "  • Liveness probe:       ${BLUE}http://$(hostname -I | awk '{print $1}'):9106/live${NC}"
    
    echo -e "\n${YELLOW}🔧 Commandes de gestion :${NC}"
    echo -e "  • Statut:       ${BLUE}sudo systemctl status douro${NC}"
    echo -e "  • Logs:         ${BLUE}sudo journalctl -u douro -f${NC}"
    echo -e "  • Redémarrer:   ${BLUE}sudo systemctl restart douro${NC}"
    echo -e "  • Arrêter:      ${BLUE}sudo systemctl stop douro${NC}"
    
    echo -e "\n${YELLOW}📁 Fichiers importants :${NC}"
    echo -e "  • Configuration: ${BLUE}/opt/douro/config.production.json${NC}"
    echo -e "  • Logs:          ${BLUE}/var/log/douro/douro.log${NC}"
    echo -e "  • Code source:   ${BLUE}/opt/douro/douro/${NC}"
    
    echo -e "\n${GREEN}🔧 Pour configurer vos domaines :${NC}"
    echo -e "   1. ${BLUE}sudo nano /opt/douro/config.production.json${NC}"
    echo -e "   2. ${BLUE}sudo systemctl restart douro${NC}"
    
    echo -e "\n${YELLOW}📋 Logs d'installation: ${BLUE}$LOG_FILE${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Fonction principale
main() {
    # Initialisation
    log "🚀 Démarrage de l'installation sécurisée de Douro..."
    log "📋 Logs sauvegardés dans: $LOG_FILE"
    
    # Vérifications préliminaires
    check_user
    check_system
    check_project_files
    test_config
    
    # Installation
    install_douro_step_by_step
    
    # Configuration optionnelle
    configure_firewall
    
    # Tests finaux
    run_comprehensive_tests
    
    # Résumé
    show_final_summary
    
    log "🎉 Installation terminée avec succès !"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 