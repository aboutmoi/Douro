#!/usr/bin/env python3
"""
Test rapide pour comprendre pourquoi OVH ne marche pas
"""

import sys
import socket
import logging
sys.path.append('/opt/douro')

# Activer les logs debug
logging.basicConfig(level=logging.INFO)

try:
    from douro.core.region_detector import RegionDetector
    
    print("🔍 Test détection OVH")
    print("=" * 40)
    
    # 1. Résolution IP
    domain = 'www.ovhcloud.com'
    ip = socket.gethostbyname(domain)
    print(f"Domain: {domain}")
    print(f"IP: {ip}")
    
    # 2. Test détection complète
    detector = RegionDetector()
    provider, region, hostnames = detector.detect_hosting_region(domain)
    
    print(f"\nRésultats:")
    print(f"Provider: {provider}")
    print(f"Region: {region}")
    print(f"Hostnames: {len(hostnames) if hostnames else 0}")
    if hostnames:
        print("Exemples hostnames:")
        for i, h in enumerate(hostnames[:5]):
            print(f"  {i+1}: {h}")
            
    # 3. Test patterns OVH
    print(f"\nTest patterns OVH:")
    test_hostnames = [
        'be103.lil1-rbx1-sbb1-nc5.fr.eu',
        'be102.gra-g1-nc5.fr.eu', 
        'rbx-g1-nc2.ovh.net',
        'gra-g3-nc1.ovh.fr'
    ]
    
    for hostname in test_hostnames:
        provider_test = detector._identify_provider(hostname)
        if provider_test == 'ovh':
            region_test = detector._identify_region(hostname, 'ovh')
            print(f"  ✅ {hostname} -> {provider_test}/{region_test}")
        else:
            print(f"  ❌ {hostname} -> {provider_test}")
            
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc() 