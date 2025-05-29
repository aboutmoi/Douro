#!/bin/bash

# Script de déploiement Douro depuis GitHub
# Usage: curl -fsSL https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash
# Ou: wget -qO- https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash

set -euo pipefail

# Configuration
GITHUB_REPO="https://github.com/aboutmoi/Douro.git"
INSTALL_DIR="/tmp/douro-deploy-$(date +%s)"
LOGFILE="/tmp/douro-github-install.log"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOGFILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOGFILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOGFILE"
}

error_exit() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERREUR:${NC} $1" | tee -a "$LOGFILE"
    echo -e "${RED}Consultez les logs: $LOGFILE${NC}"
    exit 1
}

# Bannière de démarrage
show_banner() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "   🚀 DÉPLOIEMENT DOURO DEPUIS GITHUB"
    echo "=============================================="
    echo -e "${NC}"
    echo "📍 Repository: $GITHUB_REPO"
    echo "📋 Logs: $LOGFILE"
    echo "🕒 Démarrage: $(date)"
    echo ""
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier que c'est Linux
    if [[ "$(uname)" != "Linux" ]]; then
        error_exit "Ce script nécessite Linux"
    fi
    
    # Vérifier si on est root
    if [[ $EUID -eq 0 ]]; then
        error_exit "Ne pas exécuter ce script en tant que root"
    fi
    
    # Vérifier sudo
    if ! sudo -n true 2>/dev/null; then
        log_info "Privilèges sudo requis..."
        sudo true || error_exit "Privilèges sudo requis"
    fi
    
    # Vérifier git
    if ! command -v git >/dev/null 2>&1; then
        log_info "Installation de git..."
        sudo apt update && sudo apt install -y git || error_exit "Impossible d'installer git"
    fi
    
    log "✓ Prérequis validés"
}

# Clonage du repository
clone_repository() {
    log "Clonage du repository Douro depuis GitHub..."
    
    # Nettoyer le répertoire s'il existe
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    # Cloner le repository
    git clone "$GITHUB_REPO" "$INSTALL_DIR" || error_exit "Échec du clonage du repository"
    
    cd "$INSTALL_DIR" || error_exit "Impossible d'accéder au répertoire cloné"
    
    log "✓ Repository cloné dans $INSTALL_DIR"
}

# Installation
install_douro() {
    log "Lancement de l'installation automatique de Douro..."
    
    # Rendre le script exécutable
    chmod +x scripts/deploy-vm-safe.sh || error_exit "Impossible de rendre le script exécutable"
    
    # Lancer l'installation
    ./scripts/deploy-vm-safe.sh || error_exit "Échec de l'installation Douro"
    
    log "✓ Installation Douro terminée"
}

# Nettoyage
cleanup() {
    log "Nettoyage des fichiers temporaires..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log "✓ Répertoire temporaire supprimé"
    fi
}

# Affichage du résumé final
show_summary() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo "   ✅ DÉPLOIEMENT RÉUSSI !"
    echo -e "===============================================${NC}"
    echo ""
    echo "🎯 Douro a été installé depuis GitHub"
    echo "📱 Source: $GITHUB_REPO"
    echo ""
    echo "📊 URLs de monitoring :"
    echo "  • Métriques: http://$(hostname -I | awk '{print $1}'):9105/metrics"
    echo "  • Health:    http://$(hostname -I | awk '{print $1}'):9106/health"
    echo ""
    echo "🔧 Commandes utiles :"
    echo "  • Statut:     sudo systemctl status douro"
    echo "  • Logs:       sudo journalctl -u douro -f"
    echo "  • Redémarrer: sudo systemctl restart douro"
    echo ""
    echo "📁 Configuration: /opt/douro/config.production.json"
    echo "📋 Logs d'installation: $LOGFILE"
    echo ""
    echo -e "${BLUE}🎉 Déploiement terminé avec succès !${NC}"
}

# Fonction principale
main() {
    show_banner
    
    # Rediriger tous les logs vers le fichier
    exec 1> >(tee -a "$LOGFILE")
    exec 2> >(tee -a "$LOGFILE" >&2)
    
    check_prerequisites
    clone_repository
    install_douro
    cleanup
    show_summary
}

# Gestion des signaux pour le nettoyage
trap cleanup EXIT ERR

# Lancement du script principal
main "$@" 