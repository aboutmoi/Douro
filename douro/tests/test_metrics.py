"""
Tests unitaires pour le module metrics de Douro.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime
from prometheus_client.registry import CollectorRegistry

from douro.core.analyzer import DomainInfo
from douro.core.metrics import DouroMetrics


class TestDouroMetrics(unittest.TestCase):
    """Tests pour la classe DouroMetrics."""
    
    def setUp(self):
        """Initialise un registre Prometheus pour les tests."""
        self.registry = CollectorRegistry()
        self.metrics = DouroMetrics(registry=self.registry)
    
    def test_update_metrics_complete(self):
        """Teste la mise à jour des métriques avec des données complètes."""
        # Créer un objet DomainInfo avec toutes les données
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(days=365)
        tls_expiration = now + datetime.timedelta(days=90)
        
        info = DomainInfo(
            domain="example.com",
            dns_resolve_duration=0.5,
            ip_addresses=["1.2.3.4"],
            ns_records=["ns1.example.com"],
            registrar="Example Registrar",
            expiration_date=expiration,
            asn="12345",
            asn_org="Example Org",
            country="US",
            http_status=200,
            server_header="nginx",
            tls_expiration=tls_expiration,
            cdn_detected=False
        )
        
        # Mettre à jour les métriques
        self.metrics.update_metrics([info])
        
        # Vérifier les métriques
        # HTTP status
        http_status = self.metrics.http_status.labels(domain="example.com")._value.get()
        self.assertEqual(http_status, 200)
        
        # DNS resolve duration
        dns_duration = self.metrics.dns_resolve_duration.labels(domain="example.com")._value.get()
        self.assertEqual(dns_duration, 0.5)
        
        # Domain expiration
        domain_exp = self.metrics.domain_expiration.labels(domain="example.com")._value.get()
        self.assertEqual(domain_exp, expiration.timestamp())
        
        # TLS expiration
        tls_exp = self.metrics.tls_expiration.labels(domain="example.com")._value.get()
        self.assertEqual(tls_exp, tls_expiration.timestamp())
        
        # Scrape error
        error_value = self.metrics.scrape_error.labels(domain="example.com", stage="dns")._value.get()
        self.assertEqual(error_value, 0)
    
    def test_update_metrics_with_error(self):
        """Teste la mise à jour des métriques avec des erreurs."""
        # Créer un objet DomainInfo avec erreur
        info = DomainInfo(
            domain="example.com",
            dns_resolve_duration=0.0,
            error={"dns": "DNS resolution failed"}
        )
        
        # Mettre à jour les métriques
        self.metrics.update_metrics([info])
        
        # Vérifier les métriques d'erreur
        dns_error = self.metrics.scrape_error.labels(domain="example.com", stage="dns")._value.get()
        self.assertEqual(dns_error, 1)
        
        https_error = self.metrics.scrape_error.labels(domain="example.com", stage="https")._value.get()
        self.assertEqual(https_error, 0)
    
    def test_update_metrics_multiple_domains(self):
        """Teste la mise à jour des métriques pour plusieurs domaines."""
        # Créer plusieurs objets DomainInfo
        domain1 = DomainInfo(
            domain="example1.com",
            dns_resolve_duration=0.5,
            http_status=200
        )
        
        domain2 = DomainInfo(
            domain="example2.com",
            dns_resolve_duration=1.0,
            http_status=404
        )
        
        # Mettre à jour les métriques
        self.metrics.update_metrics([domain1, domain2])
        
        # Vérifier les métriques pour chaque domaine
        http_status1 = self.metrics.http_status.labels(domain="example1.com")._value.get()
        self.assertEqual(http_status1, 200)
        
        http_status2 = self.metrics.http_status.labels(domain="example2.com")._value.get()
        self.assertEqual(http_status2, 404)
        
        dns_duration1 = self.metrics.dns_resolve_duration.labels(domain="example1.com")._value.get()
        self.assertEqual(dns_duration1, 0.5)
        
        dns_duration2 = self.metrics.dns_resolve_duration.labels(domain="example2.com")._value.get()
        self.assertEqual(dns_duration2, 1.0)


if __name__ == '__main__':
    unittest.main() 