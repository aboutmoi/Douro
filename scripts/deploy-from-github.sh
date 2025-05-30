#!/bin/bash

# Douro deployment script from GitHub
# Usage: curl -fsSL https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash
# Or: wget -qO- https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash

set -euo pipefail

# Configuration
GITHUB_REPO="https://github.com/aboutmoi/Douro.git"
INSTALL_DIR="/tmp/douro-deploy-$(date +%s)"
LOGFILE="/tmp/douro-github-install.log"

# Colors for display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Utility functions
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
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOGFILE"
    echo -e "${RED}Check logs: $LOGFILE${NC}"
    exit 1
}

# Startup banner
show_banner() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "   🚀 DOURO DEPLOYMENT FROM GITHUB"
    echo "=============================================="
    echo -e "${NC}"
    echo "📍 Repository: $GITHUB_REPO"
    echo "📋 Logs: $LOGFILE"
    echo "🕒 Started: $(date)"
    echo ""
}

# Prerequisites check
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check that it's Linux
    if [[ "$(uname)" != "Linux" ]]; then
        error_exit "This script requires Linux"
    fi
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        error_exit "Don't run this script as root"
    fi
    
    # Check sudo
    if ! sudo -n true 2>/dev/null; then
        log_info "Sudo privileges required..."
        sudo true || error_exit "Sudo privileges required"
    fi
    
    # Check git
    if ! command -v git >/dev/null 2>&1; then
        log_info "Installing git..."
        sudo apt update && sudo apt install -y git || error_exit "Cannot install git"
    fi
    
    log "✓ Prerequisites validated"
}

# Repository cloning
clone_repository() {
    log "Cloning Douro repository from GitHub..."
    
    # Clean directory if it exists
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    # Clone repository
    git clone "$GITHUB_REPO" "$INSTALL_DIR" || error_exit "Repository cloning failed"
    
    cd "$INSTALL_DIR" || error_exit "Cannot access cloned directory"
    
    log "✓ Repository cloned to $INSTALL_DIR"
}

# Installation
install_douro() {
    log "Starting Douro automatic installation..."
    
    # Make script executable
    chmod +x scripts/deploy-vm-safe.sh || error_exit "Cannot make script executable"
    
    # Run installation
    ./scripts/deploy-vm-safe.sh || error_exit "Douro installation failed"
    
    log "✓ Douro installation completed"
}

# Cleanup
cleanup() {
    log "Cleaning temporary files..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log "✓ Temporary directory removed"
    fi
}

# Final summary display
show_summary() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo "   ✅ DEPLOYMENT SUCCESSFUL!"
    echo -e "===============================================${NC}"
    echo ""
    echo "🎯 Douro has been installed from GitHub"
    echo "📱 Source: $GITHUB_REPO"
    echo ""
    echo "📊 Monitoring URLs:"
    echo "  • Metrics: http://$(hostname -I | awk '{print $1}'):9105/metrics"
    echo "  • Health:  http://$(hostname -I | awk '{print $1}'):9106/health"
    echo ""
    echo "🔧 Useful commands:"
    echo "  • Status:   sudo systemctl status douro"
    echo "  • Logs:     sudo journalctl -u douro -f"
    echo "  • Restart:  sudo systemctl restart douro"
    echo ""
    echo "📁 Configuration: /opt/douro/config.production.json"
    echo "📋 Installation logs: $LOGFILE"
    echo ""
    echo -e "${BLUE}🎉 Deployment completed successfully!${NC}"
}

# Main function
main() {
    show_banner
    
    # Redirect all logs to file
    exec 1> >(tee -a "$LOGFILE")
    exec 2> >(tee -a "$LOGFILE" >&2)
    
    check_prerequisites
    clone_repository
    install_douro
    cleanup
    show_summary
}

# Signal handling for cleanup
trap cleanup EXIT ERR

# Main script launch
main "$@" 