#!/bin/bash
# Script de nettoyage complet de Douro

echo "🧹 Nettoyage complet de Douro..."

# Arrêter le service
echo "1. Arrêt du service douro..."
sudo systemctl stop douro 2>/dev/null || true
sudo systemctl disable douro 2>/dev/null || true

# Tuer les processus
echo "2. Arrêt des processus douro..."
sudo pkill -f douro 2>/dev/null || true

# Supprimer les fichiers systemd
echo "3. Suppression des fichiers systemd..."
sudo rm -f /etc/systemd/system/douro.service
sudo systemctl daemon-reload

# Supprimer l'utilisateur douro
echo "4. Suppression de l'utilisateur douro..."
sudo userdel -r douro 2>/dev/null || true

# Supprimer les répertoires
echo "5. Suppression des répertoires..."
sudo rm -rf /opt/douro
sudo rm -rf /var/log/douro

# Nettoyer les fichiers temporaires
echo "6. Nettoyage des fichiers temporaires..."
rm -f /tmp/test_* /tmp/region_detector_new.py

echo "✅ Douro supprimé complètement !"
echo ""
echo "Vérification finale:"
ps aux | grep douro | grep -v grep || echo "  ✓ Aucun processus douro"
sudo systemctl status douro 2>/dev/null || echo "  ✓ Service douro supprimé"
ls -la /opt/ | grep douro || echo "  ✓ Répertoire /opt/douro supprimé" 