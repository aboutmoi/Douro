# 🚀 Installation Douro depuis GitHub

## Installation en une ligne

### Option 1 : avec curl
```bash
curl -fsSL https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash
```

### Option 2 : avec wget
```bash
wget -qO- https://raw.githubusercontent.com/aboutmoi/Douro/main/scripts/deploy-from-github.sh | bash
```

## Installation manuelle

### 1. Cloner le repository
```bash
git clone https://github.com/aboutmoi/Douro.git
cd Douro
```

### 2. Lancer l'installation
```bash
./scripts/deploy-vm-safe.sh
```

## Post-installation

### Vérifier le statut
```bash
sudo systemctl status douro
```

### Voir les métriques
```bash
curl http://localhost:9105/metrics
```

### Modifier la configuration
```bash
sudo nano /opt/douro/config.production.json
sudo systemctl restart douro
```

## URLs importantes

- **Métriques Prometheus:** `http://VOTRE_IP:9105/metrics`
- **Health check:** `http://VOTRE_IP:9106/health`
- **Readiness probe:** `http://VOTRE_IP:9106/ready`
- **Liveness probe:** `http://VOTRE_IP:9106/live`

## Configuration des domaines

Éditez `/opt/douro/config.production.json` :

```json
{
  "domains": [
    {
      "name": "votre-site.com",
      "enabled": true,
      "description": "Site principal"
    }
  ]
}
```

Puis redémarrez : `sudo systemctl restart douro` 