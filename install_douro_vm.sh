#!/bin/bash
# Script d'installation Douro pour la VM

set -e

echo "🚀 Installation Douro depuis GitHub..."
echo "======================================"

# Variables
REPO_URL="https://github.com/aboutmoi/Douro.git"
INSTALL_DIR="/opt/douro"
USER="douro"

# 1. Installer les dépendances système
echo "1. Installation des dépendances système..."
apt update
apt install -y python3 python3-pip python3-venv git mtr-tiny traceroute curl

# 2. Créer l'utilisateur douro
echo "2. Création de l'utilisateur douro..."
useradd -r -m -s /bin/bash $USER || true
usermod -aG sudo $USER || true

# 3. Cloner le repository
echo "3. Clonage du repository GitHub..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf $INSTALL_DIR
fi
git clone $REPO_URL $INSTALL_DIR
chown -R $USER:$USER $INSTALL_DIR

# 4. Installation Python
echo "4. Installation de l'environnement Python..."
cd $INSTALL_DIR
sudo -u $USER python3 -m venv venv
sudo -u $USER bash -c "source venv/bin/activate && pip install -r requirements.txt"

# 5. Configuration
echo "5. Configuration..."
if [ ! -f config.production.json ]; then
    cp config.example.json config.production.json
    echo "Configuration de base créée."
fi

# 6. Service systemd
echo "6. Configuration du service systemd..."
cp systemd/douro.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable douro

# 7. Créer les répertoires de logs
echo "7. Création des répertoires de logs..."
mkdir -p /var/log/douro
chown $USER:$USER /var/log/douro

# 8. Démarrer le service
echo "8. Démarrage du service..."
systemctl start douro

echo ""
echo "✅ Installation terminée !"
echo ""
echo "Status du service:"
systemctl status douro --no-pager -l
echo ""
echo "Vérification des ports:"
ss -tlnp | grep -E ':(9105|9106)'
echo ""
echo "Pour voir les logs: journalctl -u douro -f" 