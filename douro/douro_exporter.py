#!/usr/bin/env python3
"""
Exporteur Prometheus Douro pour les métriques d'hébergement de sites web.

Usage:
    douro_exporter.py [--config CONFIG_FILE]
    --config    Chemin vers le fichier de configuration JSON (défaut: config.json)
"""

import argparse
import logging
import time
import threading
import sys
import os
from typing import List

from prometheus_client import start_http_server
from prometheus_client.registry import CollectorRegistry

from douro.core.analyzer import analyze_domains
from douro.core.metrics import DouroMetrics
from douro.core.config import load_config, setup_logging, DouroConfig
from douro.core.healthcheck import HealthMonitor, start_health_server


def parse_args() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description='Douro - Exporteur Prometheus pour l\'analyse d\'hébergement via configuration JSON.'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Chemin vers le fichier de configuration JSON (défaut: config.json)'
    )
    
    return parser.parse_args()


def collect_metrics(domains: List[str], metrics: DouroMetrics, health_monitor: HealthMonitor) -> None:
    """
    Collecte les métriques et met à jour les métriques Prometheus.
    
    Args:
        domains: Liste des domaines à analyser
        metrics: Instance DouroMetrics pour mettre à jour les métriques
        health_monitor: Instance HealthMonitor pour le suivi de santé
    """
    logging.info(f"Douro - Collecte des métriques pour {len(domains)} domaines...")
    
    start_time = time.time()
    error_count = 0
    
    try:
        domains_info = analyze_domains(domains)
        metrics.update_metrics(domains_info)
        
        # Compter les erreurs
        for info in domains_info:
            if info.error:
                error_count += len(info.error)
                for stage, error in info.error.items():
                    logging.warning(f"Douro - Erreur {stage} pour {info.domain}: {error}")
        
        duration = time.time() - start_time
        health_monitor.update_scrape_metrics(duration, error_count, len(domains))
        
        logging.info("Douro - Collecte terminée, métriques mises à jour.")
                    
    except Exception as e:
        error_count += 1
        duration = time.time() - start_time
        health_monitor.update_scrape_metrics(duration, error_count, len(domains))
        logging.error(f"Douro - Erreur lors de la collecte: {e}")


def start_metrics_collection(
    domains: List[str],
    metrics: DouroMetrics,
    health_monitor: HealthMonitor,
    interval: int
) -> None:
    """
    Lance une boucle de collecte des métriques à intervalles réguliers.
    
    Args:
        domains: Liste des domaines à analyser
        metrics: Instance DouroMetrics pour mettre à jour les métriques
        health_monitor: Instance HealthMonitor pour le suivi de santé
        interval: Intervalle en secondes entre les collectes
    """
    while True:
        try:
            collect_metrics(domains, metrics, health_monitor)
        except Exception as e:
            logging.error(f"Douro - Erreur critique lors de la collecte: {e}")
        
        # Attendre pour la prochaine collecte
        logging.debug(f"Douro - Attente de {interval} secondes avant la prochaine collecte...")
        time.sleep(interval)


def validate_config(config: DouroConfig) -> None:
    """
    Valide la configuration avant le démarrage.
    
    Args:
        config: Configuration à valider
        
    Raises:
        ValueError: Si la configuration est invalide
    """
    enabled_domains = config.get_enabled_domains()
    
    if not enabled_domains:
        raise ValueError("Aucun domaine activé dans la configuration")
    
    logging.info(f"Douro - Configuration validée:")
    logging.info(f"  - Port: {config.exporter.port}")
    logging.info(f"  - Intervalle: {config.exporter.interval_seconds}s")
    logging.info(f"  - Timeout: {config.exporter.timeout_seconds}s")
    logging.info(f"  - Domaines configurés: {config.get_domain_count()}")
    logging.info(f"  - Domaines activés: {config.get_enabled_domain_count()}")
    logging.info(f"  - Domaines: {', '.join(enabled_domains)}")


def main() -> None:
    """Fonction principale."""
    args = parse_args()
    
    # Configuration initiale du logging (sera remplacée par la config du fichier)
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Charger la configuration
        logging.info(f"Douro - Chargement de la configuration depuis: {args.config}")
        config = load_config(args.config)
        
        # Configurer le logging selon le fichier de config
        setup_logging(config.monitoring)
        
        # Valider la configuration
        validate_config(config)
        
        # Récupérer les domaines activés
        domains = config.get_enabled_domains()
        
        logging.info(f"Douro - Démarrage de l'exporteur...")
        
        # Créer le registry et les métriques
        registry = CollectorRegistry()
        metrics = DouroMetrics(registry=registry)
        
        # Créer le moniteur de santé
        health_monitor = HealthMonitor()
        
        # Démarrer le serveur HTTP pour exposer les métriques
        start_http_server(config.exporter.port, registry=registry)
        logging.info(f"Douro - Serveur HTTP démarré sur le port {config.exporter.port}")
        logging.info(f"Douro - Métriques disponibles sur http://localhost:{config.exporter.port}/metrics")
        
        # Démarrer le serveur de healthcheck sur un port différent
        health_port = int(os.environ.get('DOURO_HEALTH_PORT', config.exporter.port + 1))
        start_health_server(health_port, health_monitor)
        logging.info(f"Douro - Healthcheck disponible sur http://localhost:{health_port}/health")
        logging.info(f"Douro - Readiness probe: http://localhost:{health_port}/ready")
        logging.info(f"Douro - Liveness probe: http://localhost:{health_port}/live")
        
        # Collecter les métriques une première fois
        collect_metrics(domains, metrics, health_monitor)
        
        # Démarrer la boucle de collecte dans un thread séparé
        collection_thread = threading.Thread(
            target=start_metrics_collection,
            args=(domains, metrics, health_monitor, config.exporter.interval_seconds),
            daemon=True
        )
        collection_thread.start()
        
        logging.info(f"Douro - Collecte démarrée, intervalle: {config.exporter.interval_seconds}s")
        logging.info("Douro - Exporteur en fonctionnement. Ctrl+C pour arrêter.")
        
        # Boucle principale - garder le programme en vie
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Douro - Arrêt de l'exporteur...")
    
    except FileNotFoundError as e:
        logging.error(f"Douro - {e}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"Douro - Configuration invalide: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Douro - Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 