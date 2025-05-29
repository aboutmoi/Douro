# Guide de Déploiement Douro

Guide complet pour le déploiement et l'administration de l'application Douro en production sur Linux.

## 📋 Table des matières

- [Prérequis](#prérequis)
- [Installation rapide](#installation-rapide)
- [Installation manuelle](#installation-manuelle)
- [Configuration](#configuration)
- [Monitoring et observabilité](#monitoring-et-observabilité)
- [Maintenance](#maintenance)
- [Dépannage](#dépannage)

## 🔧 Prérequis

### Système d'exploitation
- Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- Python 3.9 ou supérieur
- systemd (pour la gestion des services)

### Dépendances système
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-pip curl make

# CentOS/RHEL
sudo yum install python3 python3-pip curl make
```

### Ports réseau
- **9105** : Métriques Prometheus (configurable)
- **9106** : Healthcheck endpoints (configurable)

## 🚀 Installation rapide

### Option 1 : Installation complète automatisée
```bash
# Clone du projet
git clone https://github.com/votre-utilisateur/douro.git
cd douro

# Installation complète (dev + service)
make install-all
```

### Option 2 : Installation production uniquement
```bash
# Installation du service systemd
sudo make service-install

# Déploiement
make deploy

# Démarrage
make service-start
```

### Option 3 : Script de déploiement
```bash
# Déploiement production avec redémarrage
./scripts/deploy.sh --prod --restart-service

# Déploiement développement
./scripts/deploy.sh --dev
```

## 🔨 Installation manuelle

### 1. Préparation de l'environnement
```bash
# Créer l'utilisateur système
sudo useradd --system --home-dir /opt/douro --shell /bin/false douro

# Créer les répertoires
sudo mkdir -p /opt/douro /var/log/douro /etc/douro
sudo chown douro:douro /opt/douro /var/log/douro
```

### 2. Installation de l'application
```bash
# Copier les fichiers
sudo cp -r douro/ /opt/douro/
sudo cp requirements.txt setup.py /opt/douro/
sudo cp config.production.json /opt/douro/

# Créer l'environnement virtuel
cd /opt/douro
sudo -u douro python3 -m venv venv
sudo -u douro venv/bin/pip install --upgrade pip
sudo -u douro venv/bin/pip install -r requirements.txt
sudo -u douro venv/bin/pip install -e .
```

### 3. Configuration du service systemd
```bash
# Copier le fichier de service
sudo cp systemd/douro.service /etc/systemd/system/

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable douro.service
sudo systemctl start douro.service
```

## ⚙️ Configuration

### Variables d'environnement

Copiez `env.example` vers `/opt/douro/.env` et adaptez selon vos besoins :

```bash
# Configuration principale
DOURO_CONFIG=/opt/douro/config.production.json
DOURO_LOG_LEVEL=INFO
DOURO_LOG_DIR=/var/log/douro

# Ports
DOURO_EXPORTER_PORT=9105
DOURO_HEALTH_PORT=9106

# Intervalles
DOURO_EXPORTER_INTERVAL=600
DOURO_EXPORTER_TIMEOUT=15
```

### Fichiers de configuration

#### Production (`config.production.json`)
```json
{
  "exporter": {
    "port": 9105,
    "interval_seconds": 600,
    "timeout_seconds": 15
  },
  "domains": [
    {
      "name": "votre-site.com",
      "enabled": true,
      "description": "Site principal"
    }
  ],
  "monitoring": {
    "log_level": "WARNING",
    "enable_verbose_logging": false
  }
}
```

#### Validation de la configuration
```bash
# Validation avant déploiement
python3 -m douro.config_validator --config config.production.json

# Avec Make
make check-config
```

### Rotation des logs

La configuration logrotate est automatiquement installée dans `/etc/logrotate.d/douro` :

```bash
# Test manuel de la rotation
sudo logrotate -d /etc/logrotate.d/douro

# Forcer la rotation
sudo logrotate -f /etc/logrotate.d/douro
```

## 📊 Monitoring et observabilité

### Endpoints de santé

| Endpoint | Description | Usage |
|----------|-------------|-------|
| `/health` | État de santé complet | Monitoring général |
| `/ready` | Readiness probe | Kubernetes readiness |
| `/live` | Liveness probe | Kubernetes liveness |

```bash
# Vérification manuelle
curl http://localhost:9106/health | jq
curl http://localhost:9106/ready
curl http://localhost:9106/live
```

### Métriques Prometheus

Les métriques sont exposées sur `http://localhost:9105/metrics` :

```bash
# Test des métriques
curl http://localhost:9105/metrics

# Avec Make
make health
```

### Configuration Prometheus

Ajoutez dans votre `prometheus.yml` :

```yaml
scrape_configs:
  - job_name: 'douro'
    scrape_interval: 5m
    static_configs:
      - targets: ['votre-serveur:9105']
    metrics_path: '/metrics'
    
  # Healthcheck séparé
  - job_name: 'douro-health'
    scrape_interval: 30s
    static_configs:
      - targets: ['votre-serveur:9106']
    metrics_path: '/health'
```

### Alertes recommandées

```yaml
# alertmanager rules
groups:
- name: douro
  rules:
  - alert: DouroDown
    expr: up{job="douro"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Douro exporter is down"
      
  - alert: DouroUnhealthy
    expr: douro_scrape_error == 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Douro is experiencing errors"
```

## 🔧 Maintenance

### Commandes utiles

```bash
# Statut du service
sudo systemctl status douro
make service-status

# Logs en temps réel
sudo journalctl -u douro -f
make service-logs

# Redémarrage
sudo systemctl restart douro
make service-restart

# Tests de santé
make health
curl -s http://localhost:9106/health | jq
```

### Mise à jour

```bash
# Méthode 1 : Makefile
make update

# Méthode 2 : Script de déploiement
./scripts/deploy.sh --prod --restart-service

# Méthode 3 : Manuelle
make deploy
make service-restart
```

### Sauvegarde

Les sauvegardes automatiques sont créées dans `/opt/douro/backups/` lors des déploiements.

```bash
# Sauvegarde manuelle
sudo mkdir -p /opt/douro/backups/$(date +%Y%m%d_%H%M%S)
sudo cp -r /opt/douro/douro /opt/douro/backups/$(date +%Y%m%d_%H%M%S)/
```

### Nettoyage

```bash
# Nettoyage des fichiers temporaires
make clean

# Nettoyage des logs anciens (fait automatiquement par logrotate)
sudo find /var/log/douro -name "*.log.*.gz" -mtime +30 -delete
```

## 🔍 Dépannage

### Problèmes courants

#### 1. Service ne démarre pas
```bash
# Vérifier les logs
sudo journalctl -u douro -n 50

# Vérifier les permissions
sudo ls -la /opt/douro/
sudo ls -la /var/log/douro/

# Tester manuellement
sudo -u douro /opt/douro/venv/bin/python -m douro.douro_exporter --config /opt/douro/config.production.json
```

#### 2. Endpoints non accessibles
```bash
# Vérifier les ports
sudo netstat -tlnp | grep -E ':(9105|9106)'

# Vérifier le firewall
sudo ufw status
sudo firewall-cmd --list-ports  # CentOS/RHEL
```

#### 3. Erreurs de configuration
```bash
# Valider la configuration
python3 -m douro.config_validator --config /opt/douro/config.production.json

# Vérifier les variables d'environnement
sudo -u douro env | grep DOURO
```

#### 4. Problèmes de permissions
```bash
# Réparer les permissions
sudo chown -R douro:douro /opt/douro
sudo chown -R douro:douro /var/log/douro
sudo chmod 755 /opt/douro
sudo chmod 755 /var/log/douro
```

### Logs de diagnostic

```bash
# Logs applicatifs
sudo tail -f /var/log/douro/douro.log

# Logs système
sudo journalctl -u douro -f

# Logs avec plus de détails
sudo systemctl edit douro.service
# Ajouter:
# [Service]
# Environment="DOURO_LOG_LEVEL=DEBUG"
# Environment="DOURO_ENABLE_VERBOSE_LOGGING=true"
```

### Mode debug

```bash
# Arrêter le service
sudo systemctl stop douro

# Lancer en mode debug
sudo -u douro DOURO_LOG_LEVEL=DEBUG DOURO_ENABLE_VERBOSE_LOGGING=true \
  /opt/douro/venv/bin/python -m douro.douro_exporter \
  --config /opt/douro/config.production.json
```

## 📋 Checklist de production

### Avant la mise en production
- [ ] Configuration validée (`make check-config`)
- [ ] Tests passés (`make test`)
- [ ] Analyse de sécurité (`make security`)
- [ ] Domaines de production configurés
- [ ] Variables d'environnement définies
- [ ] Monitoring Prometheus configuré
- [ ] Alertes configurées

### Après la mise en production
- [ ] Service actif (`make service-status`)
- [ ] Endpoints accessibles (`make health`)
- [ ] Métriques collectées
- [ ] Logs fonctionnels
- [ ] Rotation des logs configurée
- [ ] Sauvegardes planifiées

## 🔐 Sécurité

### Bonnes pratiques appliquées

1. **Utilisateur dédié** : Service tournant sous l'utilisateur `douro`
2. **Permissions restreintes** : Accès minimal aux ressources système
3. **Isolation réseau** : Restrictions systemd sur les accès réseau
4. **Logs sécurisés** : Rotation automatique et permissions appropriées
5. **Variables d'environnement** : Configuration sensible externalisée

### Vérification de sécurité

```bash
# Analyse des dépendances
make security

# Vérification des permissions
sudo systemd-analyze security douro.service
```

---

Pour plus d'informations, consultez le [README.md](README.md) principal du projet. 