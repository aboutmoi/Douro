"""
Module de gestion de la configuration pour Douro.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DomainConfig:
    """Configuration d'un domaine à analyser."""
    name: str
    enabled: bool = True
    description: str = ""


@dataclass
class ExporterConfig:
    """Configuration de l'exporteur Prometheus."""
    port: int = 9105
    interval_seconds: int = 300
    timeout_seconds: int = 10


@dataclass
class MonitoringConfig:
    """Configuration du monitoring et logging."""
    log_level: str = "INFO"
    enable_verbose_logging: bool = False


@dataclass
class DouroConfig:
    """Configuration complète de Douro."""
    exporter: ExporterConfig = field(default_factory=ExporterConfig)
    domains: List[DomainConfig] = field(default_factory=list)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    def get_enabled_domains(self) -> List[str]:
        """Retourne la liste des domaines activés."""
        return [domain.name for domain in self.domains if domain.enabled]
    
    def get_domain_count(self) -> int:
        """Retourne le nombre total de domaines configurés."""
        return len(self.domains)
    
    def get_enabled_domain_count(self) -> int:
        """Retourne le nombre de domaines activés."""
        return len([d for d in self.domains if d.enabled])


def load_config(config_path: str) -> DouroConfig:
    """
    Charge la configuration depuis un fichier JSON avec support des variables d'environnement.
    
    Args:
        config_path: Chemin vers le fichier de configuration JSON
        
    Returns:
        Objet DouroConfig avec la configuration chargée
        
    Raises:
        FileNotFoundError: Si le fichier de configuration n'existe pas
        json.JSONDecodeError: Si le fichier JSON est malformé
        ValueError: Si la configuration est invalide
    """
    # Vérifier si le chemin de config vient d'une variable d'environnement
    config_path = os.environ.get('DOURO_CONFIG', config_path)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Fichier de configuration non trouvé: {config_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Fichier JSON malformé: {e}", e.doc, e.pos)
    
    # Appliquer les variables d'environnement par-dessus la configuration
    config_data = apply_env_overrides(config_data)
    
    return parse_config(config_data)


def apply_env_overrides(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applique les variables d'environnement par-dessus la configuration JSON.
    
    Args:
        config_data: Configuration chargée depuis le JSON
        
    Returns:
        Configuration avec les overrides des variables d'environnement
    """
    # Override des paramètres d'exporteur
    if 'exporter' not in config_data:
        config_data['exporter'] = {}
    
    env_port = os.environ.get('DOURO_EXPORTER_PORT')
    if env_port:
        config_data['exporter']['port'] = int(env_port)
    
    env_interval = os.environ.get('DOURO_EXPORTER_INTERVAL')
    if env_interval:
        config_data['exporter']['interval_seconds'] = int(env_interval)
    
    env_timeout = os.environ.get('DOURO_EXPORTER_TIMEOUT')
    if env_timeout:
        config_data['exporter']['timeout_seconds'] = int(env_timeout)
    
    # Override des paramètres de monitoring
    if 'monitoring' not in config_data:
        config_data['monitoring'] = {}
    
    env_log_level = os.environ.get('DOURO_LOG_LEVEL')
    if env_log_level:
        config_data['monitoring']['log_level'] = env_log_level
    
    env_verbose = os.environ.get('DOURO_ENABLE_VERBOSE_LOGGING')
    if env_verbose:
        config_data['monitoring']['enable_verbose_logging'] = env_verbose.lower() in ('true', '1', 'yes', 'on')
    
    return config_data


def parse_config(config_data: Dict[str, Any]) -> DouroConfig:
    """
    Parse les données de configuration et crée un objet DouroConfig.
    
    Args:
        config_data: Dictionnaire contenant les données de configuration
        
    Returns:
        Objet DouroConfig configuré
        
    Raises:
        ValueError: Si la configuration est invalide
    """
    # Configuration de l'exporteur
    exporter_data = config_data.get('exporter', {})
    exporter = ExporterConfig(
        port=exporter_data.get('port', 9105),
        interval_seconds=exporter_data.get('interval_seconds', 300),
        timeout_seconds=exporter_data.get('timeout_seconds', 10)
    )
    
    # Configuration du monitoring
    monitoring_data = config_data.get('monitoring', {})
    monitoring = MonitoringConfig(
        log_level=monitoring_data.get('log_level', 'INFO'),
        enable_verbose_logging=monitoring_data.get('enable_verbose_logging', False)
    )
    
    # Configuration des domaines
    domains_data = config_data.get('domains', [])
    domains = []
    
    for domain_data in domains_data:
        if not isinstance(domain_data, dict):
            raise ValueError("Chaque domaine doit être un objet JSON")
        
        if 'name' not in domain_data:
            raise ValueError("Chaque domaine doit avoir un champ 'name'")
        
        domain = DomainConfig(
            name=domain_data['name'],
            enabled=domain_data.get('enabled', True),
            description=domain_data.get('description', '')
        )
        domains.append(domain)
    
    if not domains:
        raise ValueError("Au moins un domaine doit être configuré")
    
    # Validation des valeurs
    if exporter.port < 1 or exporter.port > 65535:
        raise ValueError("Le port doit être entre 1 et 65535")
    
    if exporter.interval_seconds < 30:
        raise ValueError("L'intervalle doit être d'au moins 30 secondes")
    
    if exporter.timeout_seconds < 1:
        raise ValueError("Le timeout doit être d'au moins 1 seconde")
    
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if monitoring.log_level not in valid_log_levels:
        raise ValueError(f"Le niveau de log doit être l'un de: {valid_log_levels}")
    
    return DouroConfig(
        exporter=exporter,
        domains=domains,
        monitoring=monitoring
    )


def save_config(config: DouroConfig, config_path: str) -> None:
    """
    Sauvegarde la configuration dans un fichier JSON.
    
    Args:
        config: Configuration à sauvegarder
        config_path: Chemin vers le fichier de configuration
    """
    config_data = {
        'exporter': {
            'port': config.exporter.port,
            'interval_seconds': config.exporter.interval_seconds,
            'timeout_seconds': config.exporter.timeout_seconds
        },
        'domains': [
            {
                'name': domain.name,
                'enabled': domain.enabled,
                'description': domain.description
            }
            for domain in config.domains
        ],
        'monitoring': {
            'log_level': config.monitoring.log_level,
            'enable_verbose_logging': config.monitoring.enable_verbose_logging
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def setup_logging(config: MonitoringConfig) -> None:
    """
    Configure le logging selon la configuration avec support des variables d'environnement.
    
    Args:
        config: Configuration du monitoring
    """
    # Permettre override du niveau de log via variable d'environnement
    log_level_str = os.environ.get('DOURO_LOG_LEVEL', config.log_level)
    log_level = getattr(logging, log_level_str.upper())
    
    # Permettre override du verbose logging via variable d'environnement
    verbose_env = os.environ.get('DOURO_ENABLE_VERBOSE_LOGGING')
    verbose_logging = config.enable_verbose_logging
    if verbose_env:
        verbose_logging = verbose_env.lower() in ('true', '1', 'yes', 'on')
    
    if verbose_logging:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    else:
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configuration des logs vers fichier si spécifié
    log_dir = os.environ.get('DOURO_LOG_DIR')
    handlers = []
    
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'douro.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Toujours ajouter la sortie console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    ) 