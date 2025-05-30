#!/usr/bin/env python3
"""
Test rapide des nouveaux patterns OVH
"""

import sys
import re
sys.path.append('/opt/douro')

# Test des nouveaux patterns
test_hostnames = [
    'be103.lil1-rbx1-sbb1-nc5.',  # Nouveau format trouvé
    'be103.lil1-rbx1-sbb1-nc5.fr.eu',  # Complet
    'be102.gra-g1-nc5.fr.eu',  # Ancien format
    'rbx-g1-nc2.ovh.net',
    'gra-g3-nc1.ovh.fr'
]

# Test patterns provider
provider_patterns = ['be103.lil', 'lil1-rbx', '-sbb1-nc']
region_patterns = {
    'rbx8': [r'lil\d*-rbx\d*'],
    'gra7': [r'lil\d*-gra\d*']
}

print("🔍 Test nouveaux patterns OVH")
print("=" * 40)

for hostname in test_hostnames:
    print(f"\n📍 Test: {hostname}")
    
    # Test provider
    provider_found = False
    for pattern in provider_patterns:
        if pattern in hostname:
            print(f"  ✅ Provider pattern '{pattern}' → OVH")
            provider_found = True
            break
    if not provider_found:
        print(f"  ❌ Aucun provider pattern")
    
    # Test région
    region_found = False  
    for region, patterns in region_patterns.items():
        for pattern in patterns:
            if re.search(pattern, hostname):
                print(f"  ✅ Region pattern '{pattern}' → {region}")
                region_found = True
                break
        if region_found:
            break
    if not region_found:
        print(f"  ❌ Aucune région pattern") 