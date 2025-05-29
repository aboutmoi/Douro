#!/usr/bin/env python3
"""
Script de test pour la détection de région d'hébergement.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'douro'))

from douro.core.region_detector import RegionDetector

def test_region_detection():
    """Test la détection de région."""
    
    detector = RegionDetector()
    
    # Domaines de test
    test_domains = [
        "example.com",
        "wikipedia.org", 
        "github.com",
        "google.com",
        "stackoverflow.com",
        "aws.amazon.com"
    ]
    
    print("Test de détection de région d'hébergement")
    print("=" * 50)
    
    for domain in test_domains:
        print(f"\n🌐 Domaine: {domain}")
        
        try:
            # Résolution de l'IP
            import socket
            ip = socket.gethostbyname(domain)
            print(f"📍 IP: {ip}")
            
            # Détection de région
            provider, region, hostnames = detector.detect_hosting_region(ip)
            
            if provider and region:
                print(f"☁️  Provider: {provider}")
                print(f"🗺️  Région: {region}")
                print("✅ Région détectée avec succès")
            elif provider:
                print(f"☁️  Provider: {provider}")
                print(f"🗺️  Région: Non détectée")
                print("⚠️  Provider détecté, mais pas la région")
            else:
                print("❌ Aucune région détectée")
            
            if hostnames:
                print(f"🔍 Traceroute: {len(hostnames)} sauts")
                print(f"🛤️  Exemples: {hostnames[:3]}")
            else:
                print("🚫 Traceroute échoué")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_region_detection() 