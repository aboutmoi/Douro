#!/usr/bin/env python3
"""
Validateur de configuration pour Douro.

Usage:
    config_validator.py [--config CONFIG_FILE]
"""

import argparse
import sys
import json
from typing import Dict, Any

from douro.core.config import load_config, DouroConfig


def parse_args() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description='Douro - Validateur de configuration JSON.'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Chemin vers le fichier de configuration JSON (défaut: config.json)'
    )
    
    return parser.parse_args()


def print_config_summary(config: DouroConfig) -> None:
    """
    Affiche un résumé de la configuration.
    
    Args:
        config: Configuration à résumer
    """
    print("📊 Résumé de la configuration Douro:")
    print()
    
    print("🚀 Exporteur:")
    print(f"  - Port HTTP: {config.exporter.port}")
    print(f"  - Intervalle de scrape: {config.exporter.interval_seconds}s")
    print(f"  - Timeout des requêtes: {config.exporter.timeout_seconds}s")
    print()
    
    print("📝 Monitoring:")
    print(f"  - Niveau de log: {config.monitoring.log_level}")
    print(f"  - Logging verbeux: {'Activé' if config.monitoring.enable_verbose_logging else 'Désactivé'}")
    print()
    
    print("🌐 Domaines:")
    print(f"  - Total configurés: {config.get_domain_count()}")
    print(f"  - Activés: {config.get_enabled_domain_count()}")
    print(f"  - Désactivés: {config.get_domain_count() - config.get_enabled_domain_count()}")
    print()
    
    if config.domains:
        print("📋 Liste des domaines:")
        for domain in config.domains:
            status = "✅" if domain.enabled else "❌"
            desc = f" ({domain.description})" if domain.description else ""
            print(f"  {status} {domain.name}{desc}")
        print()
    
    enabled_domains = config.get_enabled_domains()
    if enabled_domains:
        print("🎯 Domaines qui seront analysés:")
        for domain in enabled_domains:
            print(f"  - {domain}")
        print()


def validate_config_file(config_path: str) -> bool:
    """
    Valide un fichier de configuration.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        True si la configuration est valide, False sinon
    """
    try:
        print(f"🔍 Validation du fichier: {config_path}")
        print()
        
        # Charger et valider la configuration
        config = load_config(config_path)
        
        print("✅ Configuration valide!")
        print()
        
        # Afficher le résumé
        print_config_summary(config)
        
        # Vérifications supplémentaires
        warnings = []
        
        if config.exporter.interval_seconds < 300:
            warnings.append(f"⚠️  Intervalle court ({config.exporter.interval_seconds}s) - Attention aux rate-limits WHOIS")
        
        if config.get_enabled_domain_count() > 50:
            warnings.append(f"⚠️  Beaucoup de domaines ({config.get_enabled_domain_count()}) - Considérez un intervalle plus long")
        
        if config.exporter.timeout_seconds < 5:
            warnings.append(f"⚠️  Timeout court ({config.exporter.timeout_seconds}s) - Peut causer des échecs de requête")
        
        if warnings:
            print("⚠️  Avertissements:")
            for warning in warnings:
                print(f"  {warning}")
            print()
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ Fichier non trouvé: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON invalide: {e}")
        return False
    except ValueError as e:
        print(f"❌ Configuration invalide: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False


def main() -> int:
    """Fonction principale."""
    args = parse_args()
    
    if validate_config_file(args.config):
        print("🎉 La configuration est prête à être utilisée!")
        return 0
    else:
        print("💥 La configuration contient des erreurs.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 