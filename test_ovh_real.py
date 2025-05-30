#!/usr/bin/env python3
"""
Test direct de l'IP réelle OVH 198.27.92.14
"""

import subprocess
import socket

def test_ovh_real():
    """Test la vraie IP OVH"""
    
    # Vérifier l'IP actuelle
    try:
        ip = socket.gethostbyname('www.ovhcloud.com')
        print(f"🔍 IP actuelle de www.ovhcloud.com: {ip}")
    except Exception as e:
        print(f"❌ Erreur résolution: {e}")
        return
    
    # Test MTR rapide (3 cycles pour test)
    print(f"\n🚀 Test MTR vers {ip}:")
    try:
        cmd = ['mtr', '-4', '--report', '--report-cycles', '3', '--max-ttl', '15', '-b', ip]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print(f"📊 MTR Return code: {result.returncode}")
        if result.stdout:
            print("📋 MTR Output:")
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not any(skip in line for skip in ['HOST:', 'Keys:', 'Start:']):
                    print(f"  {i:2d}: {line}")
        
        if result.stderr:
            print(f"⚠️  MTR Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Erreur MTR: {e}")
    
    # Test traceroute pour comparaison
    print(f"\n🔍 Test traceroute vers {ip}:")
    try:
        cmd = ['traceroute', '-m', '12', ip]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.stdout:
            print("📋 Traceroute Output:")
            lines = result.stdout.split('\n')[:8]  # Premiers sauts seulement
            for line in lines:
                if line.strip():
                    print(f"  {line}")
                    
    except Exception as e:
        print(f"❌ Erreur traceroute: {e}")

if __name__ == "__main__":
    test_ovh_real() 