#!/usr/bin/env python3
"""
Script de debug pour tester la détection de région sur les IPs problématiques
"""

import socket
import subprocess
import sys
sys.path.append('/opt/douro')

from douro.core.region_detector import RegionDetector

# Domaines problématiques
domains = [
    'www.ovhcloud.com',
    'aws.amazon.com', 
    'azure.microsoft.com',
    'www.linode.com',
    'www.hetzner.com'
]

def get_ip(domain):
    """Résoudre l'IP d'un domaine"""
    try:
        return socket.gethostbyname(domain)
    except:
        return None

def test_domain(domain):
    """Tester la détection pour un domaine"""
    print(f"\n🔍 TEST: {domain}")
    print("=" * 50)
    
    # Résolution IP
    ip = get_ip(domain)
    if not ip:
        print(f"❌ Impossible de résoudre {domain}")
        return
    
    print(f"📍 IP: {ip}")
    
    # Test détection région
    try:
        detector = RegionDetector()
        provider, region, hostnames = detector.detect_hosting_region(ip)
        print(f"🏢 Provider: {provider}")
        print(f"🌍 Region: {region}")
        print(f"🖥️  Hostnames: {len(hostnames) if hostnames else 0}")
        if hostnames:
            print(f"    Exemples: {hostnames[:3]}")
    except Exception as e:
        print(f"❌ Erreur détection: {e}")

if __name__ == "__main__":
    print("🚀 DEBUG - Détection région domaines problématiques")
    
    for domain in domains:
        test_domain(domain)
    
    print(f"\n✅ Tests terminés") 