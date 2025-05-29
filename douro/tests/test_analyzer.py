"""
Tests unitaires pour le module analyzer de Douro.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime

from douro.core.analyzer import (
    DomainInfo,
    resolve_dns,
    get_whois_info,
    is_cdn_ip,
    analyze_domain
)


class TestDomainInfo(unittest.TestCase):
    """Tests pour la classe DomainInfo."""
    
    def test_to_dict(self):
        """Teste la conversion en dictionnaire."""
        now = datetime.datetime.now()
        info = DomainInfo(
            domain="example.com",
            dns_resolve_duration=0.5,
            ip_addresses=["1.2.3.4"],
            registrar="Example Registrar",
            expiration_date=now,
            tls_expiration=now
        )
        
        result = info.to_dict()
        self.assertEqual(result["domain"], "example.com")
        self.assertEqual(result["dns_resolve_duration"], 0.5)
        self.assertEqual(result["ip_addresses"], ["1.2.3.4"])
        self.assertEqual(result["registrar"], "Example Registrar")
        self.assertIn("expiration_timestamp", result)
        self.assertIn("tls_expiration_timestamp", result)
    
    def test_to_json(self):
        """Teste la conversion en JSON."""
        info = DomainInfo(domain="example.com")
        json_str = info.to_json()
        self.assertIn('"domain": "example.com"', json_str)


class TestCDNDetection(unittest.TestCase):
    """Tests pour la détection de CDN."""
    
    def test_cloudflare_detection(self):
        """Teste la détection de Cloudflare."""
        self.assertTrue(is_cdn_ip("13335", "Cloudflare Inc"))
        
    def test_aws_detection(self):
        """Teste la détection d'AWS."""
        self.assertTrue(is_cdn_ip("16509", "Amazon.com, Inc."))
        
    def test_non_cdn(self):
        """Teste la non-détection pour un ASN non CDN."""
        self.assertFalse(is_cdn_ip("12345", "Some Regular Hosting"))


@patch('douro.core.analyzer.resolve_dns')
@patch('douro.core.analyzer.get_whois_info')
@patch('douro.core.analyzer.get_ip_whois')
@patch('douro.core.analyzer.check_https')
class TestAnalyzeDomain(unittest.TestCase):
    """Tests pour la fonction analyze_domain."""
    
    def test_analyze_domain_complete(self, mock_check_https, mock_get_ip_whois, 
                                     mock_get_whois_info, mock_resolve_dns):
        """Teste l'analyse complète d'un domaine."""
        # Configurer les mocks
        mock_resolve_dns.return_value = (0.5, ["1.2.3.4"], ["ns1.example.com"])
        
        expiration_date = datetime.datetime.now() + datetime.timedelta(days=365)
        mock_get_whois_info.return_value = ("Example Registrar", expiration_date)
        
        mock_get_ip_whois.return_value = ("12345", "Some Org", "US")
        
        tls_expiration = datetime.datetime.now() + datetime.timedelta(days=90)
        mock_check_https.return_value = (200, "nginx", tls_expiration)
        
        # Appeler la fonction
        result = analyze_domain("example.com")
        
        # Vérifier les résultats
        self.assertEqual(result.domain, "example.com")
        self.assertEqual(result.dns_resolve_duration, 0.5)
        self.assertEqual(result.ip_addresses, ["1.2.3.4"])
        self.assertEqual(result.ns_records, ["ns1.example.com"])
        self.assertEqual(result.registrar, "Example Registrar")
        self.assertEqual(result.expiration_date, expiration_date)
        self.assertEqual(result.asn, "12345")
        self.assertEqual(result.asn_org, "Some Org")
        self.assertEqual(result.country, "US")
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.server_header, "nginx")
        self.assertEqual(result.tls_expiration, tls_expiration)
        self.assertFalse(result.cdn_detected)
        
    def test_analyze_domain_with_errors(self, mock_check_https, mock_get_ip_whois, 
                                       mock_get_whois_info, mock_resolve_dns):
        """Teste l'analyse d'un domaine avec des erreurs."""
        # Configurer les mocks
        mock_resolve_dns.return_value = (0.5, ["1.2.3.4"], [])
        mock_get_whois_info.side_effect = Exception("WHOIS error")
        mock_get_ip_whois.return_value = (None, None, None)
        mock_check_https.return_value = (0, None, None)
        
        # Appeler la fonction
        result = analyze_domain("example.com")
        
        # Vérifier les résultats
        self.assertEqual(result.domain, "example.com")
        self.assertIn("whois_domain", result.error)


if __name__ == '__main__':
    unittest.main() 