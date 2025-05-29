"""
Module de gestion des métriques Prometheus pour Douro.
"""

from typing import Dict, List, Optional
import time

from prometheus_client import Info, Gauge, Counter
from prometheus_client.registry import CollectorRegistry

from douro.core.analyzer import DomainInfo


class DouroMetrics:
    """Classe de gestion des métriques Prometheus pour l'analyse d'hébergement Douro."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialise les métriques Prometheus.
        
        Args:
            registry: Registre Prometheus personnalisé (optionnel)
        """
        self.registry = registry
        
        # Métrique info domaine (métadonnées statiques)
        self.domain_info = Info(
            'douro_domain_info',
            'Informations statiques sur le domaine',
            ['domain'],
            registry=self.registry
        )
        
        # Métriques gauge
        self.http_status = Gauge(
            'douro_http_status_code',
            'Code de statut HTTP ou 0 si erreur',
            ['domain'],
            registry=self.registry
        )
        
        self.dns_resolve_duration = Gauge(
            'douro_dns_resolve_duration_seconds',
            'Temps de résolution DNS en secondes',
            ['domain'],
            registry=self.registry
        )
        
        self.domain_expiration = Gauge(
            'douro_domain_expiration_timestamp',
            'Timestamp Unix d\'expiration du nom de domaine',
            ['domain'],
            registry=self.registry
        )
        
        self.tls_expiration = Gauge(
            'douro_tls_cert_expiration_timestamp',
            'Timestamp Unix d\'expiration du certificat TLS',
            ['domain'],
            registry=self.registry
        )
        
        self.scrape_duration = Gauge(
            'douro_scrape_duration_seconds',
            'Durée totale d\'un scrape en secondes',
            registry=self.registry
        )
        
        self.scrape_error = Gauge(
            'douro_scrape_error',
            'Indicateur d\'erreur (0=OK, 1=erreur)',
            ['domain', 'stage'],
            registry=self.registry
        )
    
    def update_metrics(self, domain_infos: List[DomainInfo]) -> None:
        """
        Met à jour toutes les métriques à partir des infos de domaines.
        
        Args:
            domain_infos: Liste des objets DomainInfo à exposer
        """
        start_time = time.time()
        
        for info in domain_infos:
            # Métrique info avec les nouvelles informations de région
            info_labels = {
                'registrar': info.registrar or 'unknown',
                'asn': info.asn or 'unknown',
                'asn_org': info.asn_org or 'unknown',
                'country': info.country or 'unknown',
                'hosting_provider': info.hosting_provider or 'unknown',
                'hosting_region': info.hosting_region or 'unknown',
                'cdn': str(info.cdn_detected).lower(),
            }
            self.domain_info.labels(domain=info.domain).info(info_labels)
            
            # Métriques gauge
            self.http_status.labels(domain=info.domain).set(info.http_status)
            self.dns_resolve_duration.labels(domain=info.domain).set(info.dns_resolve_duration)
            
            # Date d'expiration du domaine
            if info.expiration_date:
                self.domain_expiration.labels(domain=info.domain).set(
                    info.expiration_date.timestamp()
                )
            
            # Date d'expiration TLS
            if info.tls_expiration:
                self.tls_expiration.labels(domain=info.domain).set(
                    info.tls_expiration.timestamp()
                )
            
            # Erreurs par étape (y compris détection de région)
            for stage in ['dns', 'whois_domain', 'whois_ip', 'https', 'region_detection']:
                value = 1 if stage in info.error else 0
                self.scrape_error.labels(domain=info.domain, stage=stage).set(value)
        
        # Durée totale du scrape
        self.scrape_duration.set(time.time() - start_time) 