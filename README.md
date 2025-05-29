# Douro

Analyseur d'infrastructure d'hébergement de sites Web avec export de métriques Prometheus.

## Fonctionnalités

- Résolution DNS (A, AAAA, CNAME, NS) avec mesure de performance
- WHOIS domaine (registrar, dates d'expiration)
- WHOIS/RDAP IP (ASN, organisation, pays) avec détection améliorée
- Détection CDN intelligente
- Requête HTTPS (code de statut, en-tête Server)
- Informations TLS (date d'expiration du certificat)
- Export des métriques pour Prometheus
- Configuration JSON centralisée
- Mode CLI avec sortie texte ou JSON
- Mode exporteur HTTP pour scrape Prometheus

## Installation

### Depuis les sources

```bash
git clone https://github.com/votre-utilisateur/douro.git
cd douro
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## Configuration

Douro utilise un fichier de configuration JSON pour définir les domaines à analyser et les paramètres de fonctionnement.

### Fichier de configuration

#### Configuration de développement (`config.json`)

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
      "description": "Site d'exemple"
    },
    {
      "name": "wikipedia.org",
      "enabled": true,
      "description": "Encyclopédie en ligne"
    },
    {
      "name": "github.com",
      "enabled": false,
      "description": "Plateforme de développement (désactivé)"
    }
  ],
  "monitoring": {
    "log_level": "INFO",
    "enable_verbose_logging": false
  }
}
```

#### Configuration de production (`config.production.json`)

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
    },
    {
      "name": "cdn.entreprise.com",
      "enabled": true,
      "description": "CDN pour les assets statiques"
    }
  ],
  "monitoring": {
    "log_level": "WARNING",
    "enable_verbose_logging": false
  }
}
```

### Paramètres de configuration

#### Section `exporter`
- `port`: Port HTTP pour l'exposition des métriques (défaut: 9105)
- `interval_seconds`: Intervalle entre les analyses en secondes (défaut: 300)
- `timeout_seconds`: Timeout des requêtes HTTP/DNS en secondes (défaut: 10)

#### Section `domains`
- `name`: Nom de domaine à analyser
- `enabled`: Active/désactive l'analyse de ce domaine
- `description`: Description optionnelle du domaine

#### Section `monitoring`
- `log_level`: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `enable_verbose_logging`: Active les logs détaillés avec fichier/ligne

## Utilisation

### 1. Validation de la configuration

Avant de démarrer l'exporteur, validez votre configuration :

```bash
# Environnement virtuel
source venv/bin/activate

# Validation config de développement
python -m douro.config_validator --config config.json

# Validation config de production
python -m douro.config_validator --config config.production.json
```

### 2. Mode Exporteur Prometheus (Recommandé)

Pour un monitoring continu avec Prometheus :

```bash
# Utiliser le fichier config.json par défaut
python -m douro.douro_exporter

# Spécifier un fichier de configuration
python -m douro.douro_exporter --config config.production.json
```

### 3. Mode CLI (Analyse ponctuelle)

```bash
# Analyse de domaines spécifiés en arguments
python -m douro.douro_analyzer example.com wikipedia.org

# Lecture des domaines depuis un fichier
python -m douro.douro_analyzer --domains-file domains.txt -j -o resultats.json
```

## Configuration Prometheus

Ajoutez la configuration suivante à votre fichier `prometheus.yml` :

```yaml
scrape_configs:
  - job_name: 'douro'
    scrape_interval: 5m
    static_configs:
      - targets: ['localhost:9105']
```

## Métriques disponibles

- `douro_domain_info` - Métadonnées (registrar, provider, asn, pays)
- `douro_http_status_code` - Code HTTP (0 = erreur)
- `douro_dns_resolve_duration_seconds` - Temps de résolution DNS
- `douro_domain_expiration_timestamp` - Timestamp d'expiration du NDD
- `douro_tls_cert_expiration_timestamp` - Timestamp d'expiration du certificat TLS
- `douro_scrape_duration_seconds` - Durée totale du scrape
- `douro_scrape_error` - Indicateur d'erreur (0 = OK, 1 = erreur)

### Améliorations de détection

#### Détection de pays améliorée
Douro utilise maintenant une détection de pays multi-sources :
1. **RDAP/WHOIS standard** : Champ `network.country`
2. **Analyse des contacts** : Extraction des codes pays depuis les adresses
3. **Réseaux parents** : Recherche dans la hiérarchie des objets réseau
4. **Mapping d'organisations** : Déduction basée sur le nom de l'organisation ASN

#### Exemples de métriques améliorées
```
douro_domain_info_info{asn="15169",asn_org="GOOGLE, US",cdn="true",country="US",domain="google.com",registrar="MarkMonitor, Inc."} 1.0
douro_domain_info_info{asn="36459",asn_org="GITHUB, US",cdn="false",country="US",domain="github.com",registrar="MarkMonitor, Inc."} 1.0
douro_domain_info_info{asn="14907",asn_org="WIKIMEDIA, US",cdn="false",country="NL",domain="wikipedia.org",registrar="MarkMonitor Inc."} 1.0
```

### Exemples de requêtes PromQL

- Disponibilité d'un site :
  ```
  douro_http_status_code{domain="example.com"} != 0
  ```

- Sites par pays :
  ```
  sum by (country) (douro_domain_info{country!="unknown"})
  ```

- Jours avant expiration du domaine :
  ```
  (douro_domain_expiration_timestamp{domain="example.com"} - time()) / 86400
  ```

- Jours avant expiration du certificat TLS :
  ```
  (douro_tls_cert_expiration_timestamp{domain="example.com"} - time()) / 86400
  ```

- Performance DNS :
  ```
  avg(douro_dns_resolve_duration_seconds) by (domain)
  ```

## Service systemd

Pour exécuter Douro comme service système :

```bash
# Créer le fichier de service
sudo tee /etc/systemd/system/douro.service > /dev/null << EOF
[Unit]
Description=Douro Website Hosting Analyzer
After=network.target

[Service]
Type=simple
User=douro
WorkingDirectory=/opt/douro
Environment=PATH=/opt/douro/venv/bin
ExecStart=/opt/douro/venv/bin/python -m douro.douro_exporter --config /opt/douro/config.production.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Activer et démarrer le service
sudo systemctl enable douro
sudo systemctl start douro
sudo systemctl status douro
```

## Bonnes pratiques

### Intervalles de scrape
- **≥ 300s** : Recommandé pour éviter les rate-limits WHOIS
- **≥ 600s** : Si vous analysez > 20 domaines (production)
- **≥ 1800s** : Pour un usage intensif (> 100 domaines)

### Monitoring en production
- Utilisez `log_level: "WARNING"` pour réduire les logs
- Surveillez les métriques `douro_scrape_error` pour détecter les problèmes
- Configurez des alertes sur l'expiration des domaines/certificats
- Activez `enable_verbose_logging: true` uniquement pour le debug

### Sécurité et performance
- Utilisez un utilisateur dédié non-privilégié pour le service
- Limitez l'accès au port des métriques (firewall)
- Surveillez la charge CPU/mémoire sur les gros volumes
- Utilisez des timeouts appropriés selon votre réseau

## Dépannage

### Problèmes courants

#### "Country unknown" dans les métriques
- **Cause** : Certains ASN/IP n'exposent pas d'information de pays
- **Solution** : C'est normal pour certains CDN/providers, les autres champs restent valides

#### Rate-limiting WHOIS
- **Cause** : Trop de requêtes WHOIS rapprochées
- **Solution** : Augmentez `interval_seconds` à 600s ou plus

#### Timeouts DNS/HTTP
- **Cause** : Réseau lent ou sites inaccessibles
- **Solution** : Augmentez `timeout_seconds` ou désactivez les domaines problématiques

## Limitations

- Rate-limits WHOIS : intervalle ≥ 300s recommandé si > 100 domaines.
- CDN : l'IP renvoyée peut être celle d'un CDN, non l'hôte d'origine.
- IPv6 only : fallback sur AAAA si pas de A.
- TLS absent : métrique douro_tls_cert_expiration_timestamp non exposée.
- Détection de pays : dépend de la qualité des données WHOIS/RDAP

## Développement

### Tests

```bash
source venv/bin/activate
pytest
```

### Structure du projet

```
douro/
├── core/
│   ├── analyzer.py          # Module d'analyse principal
│   ├── metrics.py           # Gestion des métriques Prometheus
│   └── config.py            # Gestion de la configuration JSON
├── tests/
│   ├── test_analyzer.py     # Tests du module analyzer
│   ├── test_metrics.py      # Tests du module metrics
│   └── test_config.py       # Tests du module config
├── douro_analyzer.py        # CLI d'analyse
├── douro_exporter.py        # Exporteur Prometheus
└── config_validator.py     # Validateur de configuration
```

### Roadmap

- Implémentation asynchrone (aiodns/aiohttp)
- Cache Redis/SQLite pour WHOIS
- Export CSV/XLSX
- API REST (FastAPI)
- Interface web de gestion
- Alerting intégré
- Support IPv6 natif
- Métriques de performance réseau étendues 