#!/bin/bash
set -e

# Script de déploiement automatique Douro pour VM
# Usage: ./scripts/auto-deploy-vm.sh

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
VM_IP="192.168.1.40"
VM_USER="grafana"
PROJECT_DIR="/home/grafana/douro"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  DOURO - DÉPLOIEMENT AUTOMATIQUE${NC}"
echo -e "${BLUE}  VM: $VM_IP${NC}"
echo -e "${BLUE}  User: $VM_USER${NC}"
echo -e "${BLUE}================================${NC}"

# Fonction de log
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
}

# Vérifier si on est sur la VM ou sur la machine locale
if [[ $(hostname -I | grep -c "192.168.1.40") -gt 0 ]] || [[ "$1" == "--local" ]]; then
    echo -e "${GREEN}Exécution locale sur la VM${NC}"
    LOCAL_INSTALL=true
else
    log_error "Ce script doit être exécuté directement sur la VM"
    log "Copiez ce script sur votre VM et exécutez-le là-bas :"
    log "scp scripts/auto-deploy-vm.sh grafana@192.168.1.40:/home/grafana/"
    log "ssh grafana@192.168.1.40"
    log "chmod +x auto-deploy-vm.sh"
    log "./auto-deploy-vm.sh --local"
    exit 1
fi

# Vérification des privilèges sudo
check_sudo() {
    log "Vérification des privilèges sudo..."
    if sudo -n true 2>/dev/null; then
        log "✓ Privilèges sudo OK"
    else
        log_warn "Configuration sudo nécessaire..."
        log "Exécution de: sudo -v"
        sudo -v
    fi
}

# Installation des dépendances système
install_dependencies() {
    log "Installation des dépendances système..."
    
    # Détecter la distribution
    if command -v apt-get &> /dev/null; then
        PACKAGE_MANAGER="apt"
        log "Distribution: Ubuntu/Debian détectée"
        sudo apt update
        sudo apt install -y python3 python3-venv python3-pip curl make git jq
    elif command -v yum &> /dev/null; then
        PACKAGE_MANAGER="yum"
        log "Distribution: CentOS/RHEL détectée"
        sudo yum update -y
        sudo yum install -y python3 python3-pip curl make git jq
    else
        log_error "Gestionnaire de paquets non supporté"
        exit 1
    fi
    
    log "✓ Dépendances installées"
}

# Vérifier si douro est déjà dans le répertoire courant
check_douro_files() {
    log "Vérification des fichiers Douro..."
    
    if [[ -f "Makefile" ]] && [[ -f "requirements.txt" ]] && [[ -d "douro" ]]; then
        log "✓ Fichiers Douro détectés dans le répertoire courant"
        DOURO_DIR="."
    elif [[ -f "/home/grafana/douro/Makefile" ]]; then
        log "✓ Fichiers Douro trouvés dans /home/grafana/douro"
        DOURO_DIR="/home/grafana/douro"
        cd "$DOURO_DIR"
    else
        log_error "Fichiers Douro non trouvés !"
        log "Assurez-vous que les fichiers sont dans le répertoire courant ou dans /home/grafana/douro"
        log "Structure attendue :"
        log "  - Makefile"
        log "  - requirements.txt"
        log "  - douro/ (dossier)"
        log "  - systemd/ (dossier)"
        log "  - scripts/ (dossier)"
        exit 1
    fi
}

# Installation complète de Douro
install_douro() {
    log "Installation de Douro..."
    
    # Rendre les scripts exécutables
    chmod +x scripts/*.sh 2>/dev/null || true
    
    # Installation du service systemd et utilisateur douro
    log "Étape 1/4: Installation du service systemd..."
    sudo make service-install
    
    # Déploiement du code
    log "Étape 2/4: Déploiement du code..."
    make deploy
    
    # Configuration par défaut (vous pourrez la modifier après)
    log "Étape 3/4: Configuration par défaut..."
    configure_default_domains
    
    # Validation de la configuration
    log "Validation de la configuration..."
    make check-config
    
    # Démarrage du service
    log "Étape 4/4: Démarrage du service..."
    make service-start
    
    log "✓ Installation de Douro terminée"
}

# Configuration des domaines par défaut
configure_default_domains() {
    log "Configuration des domaines par défaut..."
    
    # Créer une configuration de base
    sudo tee /opt/douro/config.production.json > /dev/null << 'EOF'
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
      "description": "Test domain - Google"
    },
    {
      "name": "github.com",
      "enabled": true,
      "description": "Test domain - GitHub"
    },
    {
      "name": "stackoverflow.com",
      "enabled": true,
      "description": "Test domain - StackOverflow"
    }
  ],
  "monitoring": {
    "log_level": "INFO",
    "enable_verbose_logging": false
  }
}
EOF
    
    sudo chown douro:douro /opt/douro/config.production.json
    log "✓ Configuration par défaut créée"
}

# Configuration du firewall
configure_firewall() {
    log "Configuration du firewall..."
    
    if command -v ufw &> /dev/null; then
        sudo ufw allow 9105/tcp comment "Douro Prometheus metrics"
        sudo ufw allow 9106/tcp comment "Douro health check"
        log "✓ Firewall UFW configuré"
    elif command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-port=9105/tcp
        sudo firewall-cmd --permanent --add-port=9106/tcp
        sudo firewall-cmd --reload
        log "✓ Firewall firewalld configuré"
    else
        log_warn "Aucun firewall détecté, configuration manuelle nécessaire"
    fi
}

# Tests de fonctionnement
run_tests() {
    log "Tests de fonctionnement..."
    
    # Attendre que le service soit prêt
    log "Attente du démarrage du service..."
    sleep 10
    
    # Test de statut du service
    if sudo systemctl is-active --quiet douro; then
        log "✓ Service douro actif"
    else
        log_error "✗ Service douro inactif"
        sudo systemctl status douro --no-pager -l
        return 1
    fi
    
    # Test des endpoints
    log "Test des endpoints..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:9106/ready >/dev/null 2>&1; then
            log "✓ Service prêt !"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "✗ Service non prêt après $max_attempts tentatives"
            return 1
        fi
        
        log "Tentative $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    # Tests des endpoints
    if curl -s http://localhost:9105/metrics | head -5 >/dev/null; then
        log "✓ Endpoint métriques OK"
    else
        log_warn "✗ Endpoint métriques KO"
    fi
    
    if curl -s http://localhost:9106/health >/dev/null; then
        log "✓ Endpoint health OK"
    else
        log_warn "✗ Endpoint health KO"
    fi
}

# Affichage du résumé final
show_summary() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}   INSTALLATION TERMINÉE !${NC}"
    echo -e "${BLUE}================================${NC}"
    
    echo -e "\n${GREEN}🎯 Service Douro installé et actif${NC}"
    echo -e "${GREEN}📊 Utilisateur 'douro' créé${NC}"
    echo -e "${GREEN}🔧 Service systemd configuré${NC}"
    
    echo -e "\n${YELLOW}📡 URLs de monitoring :${NC}"
    echo -e "  • Métriques Prometheus: ${BLUE}http://192.168.1.40:9105/metrics${NC}"
    echo -e "  • Health check:         ${BLUE}http://192.168.1.40:9106/health${NC}"
    echo -e "  • Readiness probe:      ${BLUE}http://192.168.1.40:9106/ready${NC}"
    echo -e "  • Liveness probe:       ${BLUE}http://192.168.1.40:9106/live${NC}"
    
    echo -e "\n${YELLOW}🔧 Commandes utiles :${NC}"
    echo -e "  • Statut:     ${BLUE}sudo systemctl status douro${NC}"
    echo -e "  • Logs:       ${BLUE}sudo journalctl -u douro -f${NC}"
    echo -e "  • Redémarrer: ${BLUE}sudo systemctl restart douro${NC}"
    echo -e "  • Health:     ${BLUE}curl http://localhost:9106/health${NC}"
    
    echo -e "\n${YELLOW}📝 Configuration :${NC}"
    echo -e "  • Fichier config: ${BLUE}/opt/douro/config.production.json${NC}"
    echo -e "  • Logs:          ${BLUE}/var/log/douro/douro.log${NC}"
    echo -e "  • Code source:   ${BLUE}/opt/douro/douro/${NC}"
    
    echo -e "\n${GREEN}✅ Pour configurer vos domaines :${NC}"
    echo -e "   ${BLUE}sudo nano /opt/douro/config.production.json${NC}"
    echo -e "   ${BLUE}sudo systemctl restart douro${NC}"
    
    echo -e "\n${BLUE}================================${NC}"
}

# Fonction principale
main() {
    log "Démarrage de l'installation automatique de Douro..."
    
    check_sudo
    install_dependencies
    check_douro_files
    install_douro
    configure_firewall
    run_tests
    show_summary
    
    log "🎉 Installation complète terminée avec succès !"
}

# Gestion des erreurs
trap 'log_error "Installation interrompue ! Vérifiez les logs ci-dessus."' ERR

# Exécution
main "$@" 