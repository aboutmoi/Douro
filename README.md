# 🚀 Douro

Analyseur d'infrastructure d'hébergement de sites Web avec export de métriques Prometheus.

[![GitHub](https://img.shields.io/badge/GitHub-aboutmoi%2FDouro-blue)](https://github.com/aboutmoi/Douro)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://python.org)

## ✨ Fonctionnalités

- **DNS Analysis** : Résolution DNS (A, AAAA, CNAME, NS) avec mesure de performance
- **WHOIS Domain** : Registrar, dates d'expiration
- **WHOIS/RDAP IP** : ASN, organisation, pays avec détection améliorée
- **CDN Detection** : Détection CDN intelligente
- **HTTPS Monitoring** : Code de statut, en-têtes Server
- **TLS Certificates** : Date d'expiration des certificats
- **Prometheus Export** : Métriques pour monitoring
- **Health Checks** : Endpoints de santé intégrés
- **Production Ready** : Service systemd sécurisé
- **DevOps Compliant** : Scripts de déploiement automatisés

## 📦 Installation

### 🚀 Installation en une ligne (Recommandée)

```bash
# Installation automatique depuis GitHub
curl -fsSL https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash
```

### 📋 Installation manuelle

#### 1. Cloner le repository
```bash
git clone https://github.com/aboutmoi/Douro.git
cd Douro
```

#### 2. Installation automatisée
```bash
# Sur Linux avec systemd
./scripts/deploy-vm-safe.sh
```

#### 3. Installation depuis les sources (Développement)
```bash
# Environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# Installation des dépendances
pip install -r requirements.txt

# Validation de la configuration
python -m douro.config_validator --config config.json
```

## 🔧 Configuration

Douro utilise un fichier de configuration JSON pour définir les domaines à analyser.

### Configuration rapide

```json
{
  "exporter": {
    "port": 9105,
    "interval_seconds": 300,
    "timeout_seconds": 10
  },
  "domains": [
    {
      "name": "example.com",
      "enabled": true,
      "description": "Mon site web"
    }
  ],
  "monitoring": {
    "log_level": "INFO",
    "enable_verbose_logging": false
  }
}
```

### Variables d'environnement

```bash
# Configuration
export DOURO_CONFIG="/path/to/config.json"
export DOURO_LOG_LEVEL="INFO"
export DOURO_LOG_DIR="/var/log/douro"

# Exporteur
export DOURO_EXPORTER_PORT="9105"
export DOURO_EXPORTER_INTERVAL="300"

# Health check
export DOURO_HEALTH_PORT="9106"
```

## 🚀 Utilisation

### Mode Production (Service systemd)

```bash
# Vérifier le statut
sudo systemctl status douro

# Voir les logs
sudo journalctl -u douro -f

# Redémarrer
sudo systemctl restart douro
```

### Mode Développement

```bash
# Mode exporteur Prometheus
python -m douro.douro_exporter --config config.json

# Mode CLI (analyse ponctuelle)
python -m douro.douro_analyzer example.com wikipedia.org

# Validation de configuration
python -m douro.config_validator --config config.json
```

## 📊 Endpoints

### Métriques Prometheus
- **URL:** `http://localhost:9105/metrics`
- **Format:** Prometheus metrics

### Health Checks
- **Health:** `http://localhost:9106/health`
- **Ready:** `http://localhost:9106/ready` 
- **Live:** `http://localhost:9106/live`

## 📈 Métriques disponibles

| Métrique | Description |
|----------|-------------|
| `douro_domain_info` | Métadonnées (registrar, provider, ASN, pays) |
| `douro_http_status_code` | Code HTTP (0 = erreur) |
| `douro_dns_resolve_duration_seconds` | Temps de résolution DNS |
| `douro_domain_expiration_timestamp` | Timestamp d'expiration du domaine |
| `douro_tls_cert_expiration_timestamp` | Timestamp d'expiration du certificat TLS |
| `douro_scrape_duration_seconds` | Durée totale du scrape |
| `douro_scrape_error` | Indicateur d'erreur (0 = OK, 1 = erreur) |

### Exemples de métriques

```
douro_domain_info{asn="15169",asn_org="GOOGLE, US",cdn="true",country="US",domain="google.com",registrar="MarkMonitor, Inc."} 1.0
douro_http_status_code{domain="google.com"} 200
douro_dns_resolve_duration_seconds{domain="google.com"} 0.045
```

## 🔍 Configuration Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'douro'
    scrape_interval: 5m
    static_configs:
      - targets: ['localhost:9105']
```

### Requêtes PromQL utiles

```promql
# Disponibilité d'un site
douro_http_status_code{domain="example.com"} != 0

# Jours avant expiration du domaine
(douro_domain_expiration_timestamp{domain="example.com"} - time()) / 86400

# Performance DNS moyenne
avg(douro_dns_resolve_duration_seconds) by (domain)

# Sites par pays
sum by (country) (douro_domain_info{country!="unknown"})
```

## 🛠️ DevOps

### Scripts disponibles

```bash
# Déploiement complet
make install-all

# Gestion du service
make service-start
make service-stop
make service-restart

# Tests et validation
make test
make check-config
make security-check

# Nettoyage
make clean
```

### Architecture de déploiement

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │◄───│     Douro       │◄───│   DNS/WHOIS     │
│   :9090         │    │   :9105/:9106   │    │   Providers     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│    Grafana      │    │    systemd      │
│    :3000        │    │   douro.service │
└─────────────────┘    └─────────────────┘
```

## 🔐 Sécurité

### Configuration systemd sécurisée

- ✅ Utilisateur dédié non-privilégié
- ✅ Restrictions de sécurité (NoNewPrivileges, ProtectSystem)
- ✅ Limites de ressources (Memory, CPU)
- ✅ Journalisation centralisée

### Bonnes pratiques

- **Intervalles** : ≥ 300s pour éviter les rate-limits
- **Monitoring** : Surveillez `douro_scrape_error`
- **Logs** : Utilisez `WARNING` en production
- **Firewall** : Limitez l'accès aux ports métriques

## 🔧 Configuration avancée

### Modifier les domaines surveillés

```bash
# Éditer la configuration
sudo nano /opt/douro/config.production.json

# Redémarrer le service
sudo systemctl restart douro
```

### Exemple de configuration production

```json
{
  "exporter": {
    "port": 9105,
    "interval_seconds": 600,
    "timeout_seconds": 15
  },
  "domains": [
    {
      "name": "site-critique.com",
      "enabled": true,
      "description": "Application principale"
    },
    {
      "name": "api.entreprise.com", 
      "enabled": true,
      "description": "API métier critique"
    }
  ],
  "monitoring": {
    "log_level": "WARNING",
    "enable_verbose_logging": false
  }
}
```

## 🧪 Tests et développement

### Tests

```bash
# Installation développement
git clone https://github.com/aboutmoi/Douro.git
cd Douro
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Lancer les tests
pytest

# Tests avec couverture
pytest --cov=douro
```

### Structure du projet

```
douro/
├── core/                    # Modules principaux
│   ├── analyzer.py          # Analyseur principal
│   ├── metrics.py           # Métriques Prometheus
│   ├── config.py            # Configuration
│   └── healthcheck.py       # Health checks
├── scripts/                 # Scripts DevOps
│   ├── deploy-vm-safe.sh    # Déploiement sécurisé
│   ├── deploy-from-github.sh # Installation GitHub
│   └── install-service.sh   # Installation service
├── systemd/                 # Configuration systemd
├── tests/                   # Tests unitaires
└── configs/                 # Configurations
```

## 📚 Documentation

- **[Installation détaillée](INSTALL.md)** - Guide d'installation complet
- **[Déploiement](DEPLOYMENT.md)** - Guide de déploiement DevOps
- **[Configuration](config.example.json)** - Exemples de configuration

## 🤝 Contribution

1. Fork le projet : https://github.com/aboutmoi/Douro
2. Créez une branche feature (`git checkout -b feature/amelioration`)
3. Commitez vos changements (`git commit -am 'Ajout feature'`)
4. Poussez la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

## 📄 License

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- **Prometheus** - Système de monitoring
- **Python WHOIS** - Bibliothèque WHOIS
- **dnspython** - Résolution DNS
- **Communauté Open Source** - Pour les outils et bibliothèques

---

**🎯 Douro - Monitoring d'infrastructure simple et efficace** 