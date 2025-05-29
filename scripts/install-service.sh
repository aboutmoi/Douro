#!/bin/bash
set -e

# Script d'installation du service Douro pour systemd
# Usage: sudo ./scripts/install-service.sh

echo "=== Installation du service Douro ==="

# Vérifier les privilèges
if [[ $EUID -ne 0 ]]; then
   echo "Ce script doit être exécuté en tant que root (sudo)" 
   exit 1
fi

# Variables
SERVICE_NAME="douro"
SERVICE_USER="douro"
SERVICE_GROUP="douro"
INSTALL_DIR="/opt/douro"
LOG_DIR="/var/log/douro"
CONFIG_DIR="/etc/douro"

echo "Création de l'utilisateur et groupe ${SERVICE_USER}..."
if ! id "${SERVICE_USER}" &>/dev/null; then
    useradd --system --home-dir ${INSTALL_DIR} --shell /bin/false ${SERVICE_USER}
    echo "Utilisateur ${SERVICE_USER} créé"
else
    echo "Utilisateur ${SERVICE_USER} existe déjà"
fi

echo "Création des répertoires..."
mkdir -p ${INSTALL_DIR}
mkdir -p ${LOG_DIR}
mkdir -p ${CONFIG_DIR}
mkdir -p ${INSTALL_DIR}/logs

echo "Configuration des permissions..."
chown -R ${SERVICE_USER}:${SERVICE_GROUP} ${INSTALL_DIR}
chown -R ${SERVICE_USER}:${SERVICE_GROUP} ${LOG_DIR}
chmod 755 ${INSTALL_DIR}
chmod 755 ${LOG_DIR}
chmod 750 ${CONFIG_DIR}

echo "Copie des fichiers de service..."
cp systemd/douro.service /etc/systemd/system/
chmod 644 /etc/systemd/system/douro.service

echo "Rechargement de systemd..."
systemctl daemon-reload

echo "Activation du service..."
systemctl enable douro.service

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Pour déployer l'application :"
echo "1. Copiez les fichiers de l'application dans ${INSTALL_DIR}"
echo "2. Créez un environnement virtuel : python3 -m venv ${INSTALL_DIR}/venv"
echo "3. Installez les dépendances : ${INSTALL_DIR}/venv/bin/pip install -r requirements.txt"
echo "4. Copiez la configuration : cp config.production.json ${INSTALL_DIR}/"
echo "5. Démarrez le service : systemctl start douro"
echo ""
echo "Commandes utiles :"
echo "- Statut : systemctl status douro"
echo "- Logs : journalctl -u douro -f"
echo "- Redémarrage : systemctl restart douro"
echo "- Arrêt : systemctl stop douro" 