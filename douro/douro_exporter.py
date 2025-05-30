#!/usr/bin/env python3
"""
Douro Prometheus exporter for web hosting metrics.

Usage:
python -m douro.douro_exporter
--config    Path to JSON configuration file (default: config.json)
--port      Prometheus exporter port (default: 9105)
--interval  Collection interval in seconds (default: 300)
--debug     Enable debug mode

The exporter collects domain information and exports it as Prometheus metrics.
"""

import argparse
import logging
import signal
import sys
import time
from typing import Dict, Any

from prometheus_client import start_http_server

from .core.config import load_config
from .core.analyzer import analyze_domain
from .core.metrics import DouroMetrics


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Douro - Prometheus exporter for hosting analysis via JSON configuration.'
    )
    
    parser.add_argument(
        '--config', 
        default='config.json',
        help='Path to JSON configuration file (default: config.json)'
    )
    
    return parser.parse_args()


def collect_metrics(domains: list, metrics: DouroMetrics) -> None:
    """
    Collect metrics and update Prometheus metrics.
    
    Args:
        domains: List of domains to analyze
        metrics: DouroMetrics instance to update metrics
    """
    logging.info(f"Douro - Collecting metrics for {len(domains)} domains...")
    
    for domain_config in domains:
        if not domain_config.get('enabled', True):
            continue
            
        domain_name = domain_config['name']
        try:
            # Analyze domain
            domain_info = analyze_domain(domain_name)
            
            # Update Prometheus metrics
            metrics.update_domain_metrics(domain_info)
            
            logging.debug(f"Metrics updated for {domain_name}")
            
        except Exception as e:
            logging.error(f"Error analyzing {domain_name}: {e}")
            # Update error metrics
            metrics.update_error_metrics(domain_name, str(e))
    
    logging.info("Douro - Collection completed, metrics updated.")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_collection_loop(config: Dict[str, Any], metrics: DouroMetrics) -> None:
    """
    Run a metrics collection loop at regular intervals.
    
    Args:
        config: Configuration dictionary
        metrics: DouroMetrics instance to update metrics
    """
    domains = config.get('domains', [])
    interval = config.get('exporter', {}).get('interval_seconds', 300)
    
    logging.info(f"Starting collection loop (interval: {interval}s)")
    
    while True:
        try:
            collect_metrics(domains, metrics)
            time.sleep(interval)
        except KeyboardInterrupt:
            logging.info("Collection interrupted by user")
            break
        except Exception as e:
            logging.error(f"Error in collection loop: {e}")
            time.sleep(60)  # Wait before retrying


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration before startup.
    
    Args:
        config: Configuration to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    domains = config.get('domains', [])
    enabled_domains = [d for d in domains if d.get('enabled', True)]
    if not enabled_domains:
        raise ValueError("No enabled domains in configuration")
    
    logging.info(f"Douro - Configuration validated:")
    logging.info(f"  • Enabled domains: {len(enabled_domains)}")
    logging.info(f"  • Collection interval: {config.get('exporter', {}).get('interval_seconds', 300)}s")


def main():
    """Main function."""
    # Parse arguments
    args = parse_arguments()
    
    # Initial logging setup (will be replaced by config file settings)
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    logging.info(f"Douro - Loading configuration from: {args.config}")
    try:
        config = load_config(args.config)
    except Exception as e:
        logging.error(f"Configuration loading error: {e}")
        sys.exit(1)
    
    # Validate configuration
    try:
        validate_config(config)
    except ValueError as e:
        logging.error(f"Configuration validation error: {e}")
        sys.exit(1)
    
    # Update logging configuration
    log_level = config.get('monitoring', {}).get('log_level', 'INFO')
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    # Create registry and metrics
    try:
        metrics = DouroMetrics()
    except Exception as e:
        logging.error(f"Error creating metrics: {e}")
        sys.exit(1)
    
    # Start HTTP server to expose metrics
    port = config.get('exporter', {}).get('port', 9105)
    start_http_server(port)
    logging.info(f"Douro - Metrics available at http://localhost:{port}/metrics")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        # Health check server
        from .core.healthcheck import start_health_server
        health_port = config.get('monitoring', {}).get('health_port', 9106)
        start_health_server(health_port)
        logging.info(f"Health checks available at http://localhost:{health_port}/health")
        
        # Collect metrics once first
        domains = config.get('domains', [])
        collect_metrics(domains, metrics)
        
        # Start collection loop
        run_collection_loop(config, metrics)
        
    except Exception as e:
        logging.error(f"Runtime error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Douro exporter interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Douro - Invalid configuration: {e}")
        sys.exit(1) 