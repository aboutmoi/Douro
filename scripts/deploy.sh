#!/bin/bash
set -e

# Script de déploiement automatisé pour Douro
# Usage: ./scripts/deploy.sh [--dev|--prod] [--restart-service]

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables par défaut
ENVIRONMENT="prod"
RESTART_SERVICE=false
BACKUP_DIR="/opt/douro/backups"
INSTALL_DIR="/opt/douro"
SERVICE_NAME="douro"

# Fonction d'aide
show_help() {
    echo "Script de déploiement automatisé pour Douro"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev              Déploiement en mode développement"
    echo "  --prod             Déploiement en mode production (défaut)"
    echo "  --restart-service  Redémarre le service après déploiement"
    echo "  --help             Affiche cette aide"
    echo ""
}

# Parse des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            ENVIRONMENT="dev"
            shift
            ;;
        --prod)
            ENVIRONMENT="prod"
            shift
            ;;
        --restart-service)
            RESTART_SERVICE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Option inconnue: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Fonction de log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Vérifications préliminaires
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier si on est root pour certaines opérations
    if [[ $EUID -ne 0 ]]; then
        log_warn "Ce script nécessite les privilèges sudo pour certaines opérations"
    fi
    
    # Vérifier si le répertoire d'installation existe
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_error "Répertoire d'installation $INSTALL_DIR n'existe pas!"
        log "Exécutez d'abord: sudo make service-install"
        exit 1
    fi
    
    # Vérifier si le service existe
    if ! systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
        log_warn "Service $SERVICE_NAME non installé. Installation recommandée."
    fi
    
    log "Prérequis OK"
}

# Créer une sauvegarde
create_backup() {
    log "Création d'une sauvegarde..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"
    
    sudo mkdir -p "$backup_path"
    
    if [[ -d "$INSTALL_DIR/douro" ]]; then
        sudo cp -r "$INSTALL_DIR/douro" "$backup_path/"
        log "Sauvegarde créée: $backup_path"
    else
        log_warn "Aucune installation précédente trouvée"
    fi
}

# Validation de la configuration
validate_config() {
    log "Validation de la configuration..."
    
    local config_file
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        config_file="config.json"
    else
        config_file="config.production.json"
    fi
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Fichier de configuration $config_file non trouvé!"
        exit 1
    fi
    
    # Valider avec l'outil intégré
    python3 -m douro.config_validator --config "$config_file"
    log "Configuration validée"
}

# Déploiement des fichiers
deploy_files() {
    log "Déploiement des fichiers..."
    
    # Arrêter le service temporairement si il tourne
    local service_was_running=false
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Arrêt temporaire du service..."
        sudo systemctl stop "$SERVICE_NAME"
        service_was_running=true
    fi
    
    # Copier les fichiers
    sudo cp -r douro/ "$INSTALL_DIR/"
    sudo cp requirements.txt "$INSTALL_DIR/"
    sudo cp setup.py "$INSTALL_DIR/"
    
    # Copier la bonne configuration
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        sudo cp config.json "$INSTALL_DIR/"
    else
        sudo cp config.production.json "$INSTALL_DIR/"
    fi
    
    # Installer les dépendances
    log "Mise à jour des dépendances..."
    cd "$INSTALL_DIR"
    sudo -u douro "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    sudo -u douro "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt
    sudo -u douro "$INSTALL_DIR/venv/bin/pip" install -e .
    
    # Restaurer les permissions
    sudo chown -R douro:douro "$INSTALL_DIR"
    
    # Redémarrer le service si il était en cours d'exécution
    if [[ "$service_was_running" == true ]] || [[ "$RESTART_SERVICE" == true ]]; then
        log "Redémarrage du service..."
        sudo systemctl start "$SERVICE_NAME"
        sleep 3
        
        # Vérifier le statut
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log "Service redémarré avec succès"
        else
            log_error "Échec du redémarrage du service"
            sudo systemctl status "$SERVICE_NAME" --no-pager -l
            exit 1
        fi
    fi
    
    log "Déploiement des fichiers terminé"
}

# Configuration du monitoring
setup_monitoring() {
    log "Configuration du monitoring..."
    
    # Installer logrotate si nécessaire
    if [[ -f "configs/logrotate.conf" ]]; then
        sudo cp configs/logrotate.conf /etc/logrotate.d/douro
        log "Configuration logrotate installée"
    fi
    
    # Créer les répertoires de logs si nécessaire
    sudo mkdir -p /var/log/douro
    sudo chown douro:douro /var/log/douro
    
    log "Monitoring configuré"
}

# Test de santé
health_check() {
    log "Vérification de l'état de santé..."
    
    # Attendre que le service soit prêt
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:9106/ready >/dev/null 2>&1; then
            log "Service prêt!"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Service non prêt après $max_attempts tentatives"
            return 1
        fi
        
        log "Tentative $attempt/$max_attempts - En attente..."
        sleep 2
        ((attempt++))
    done
    
    # Tester les endpoints
    log "Test des endpoints..."
    
    if curl -s http://localhost:9105/metrics >/dev/null; then
        log "✓ Endpoint métriques OK"
    else
        log_warn "✗ Endpoint métriques KO"
    fi
    
    if curl -s http://localhost:9106/health >/dev/null; then
        log "✓ Endpoint health OK"
    else
        log_warn "✗ Endpoint health KO"
    fi
    
    log "Tests de santé terminés"
}

# Afficher le résumé
show_summary() {
    log "=== Résumé du déploiement ==="
    log "Environnement: $ENVIRONMENT"
    log "Répertoire: $INSTALL_DIR"
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Service: ✓ Actif"
    else
        log "Service: ✗ Inactif"
    fi
    
    log ""
    log "URLs de monitoring:"
    log "  Métriques: http://localhost:9105/metrics"
    log "  Health:    http://localhost:9106/health"
    log "  Ready:     http://localhost:9106/ready"
    log "  Live:      http://localhost:9106/live"
    log ""
    log "Commandes utiles:"
    log "  Statut: sudo systemctl status douro"
    log "  Logs:   sudo journalctl -u douro -f"
    log "  Health: curl http://localhost:9106/health"
}

# Fonction principale
main() {
    log "=== Déploiement Douro - Environnement: $ENVIRONMENT ==="
    
    check_prerequisites
    validate_config
    create_backup
    deploy_files
    setup_monitoring
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        health_check
    fi
    
    show_summary
    log "=== Déploiement terminé avec succès! ==="
}

# Exécution du script principal
main "$@" 