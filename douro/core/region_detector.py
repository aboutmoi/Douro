"""
Module de détection de région d'hébergement via analyse de traceroute et géolocalisation IP.
"""

import re
import subprocess
import logging
import socket
import requests
from typing import Optional, List, Tuple, Dict


class RegionDetector:
    """Détecteur de région d'hébergement basé sur l'analyse de traceroute et géolocalisation."""
    
    def __init__(self):
        """Initialise le détecteur avec les mappings de régions."""
        # Patterns de détection de région basés sur les noms d'hôtes
        self.region_patterns = {
            # AWS
            'aws': {
                'us-east-1': [r'us-east-1', r'iad\d*', r'virginia', r'use1'],
                'us-east-2': [r'us-east-2', r'cmh\d*', r'ohio', r'use2'],
                'us-west-1': [r'us-west-1', r'sfo\d*', r'california', r'usw1'],
                'us-west-2': [r'us-west-2', r'pdx\d*', r'oregon', r'usw2'],
                'eu-west-1': [r'eu-west-1', r'dub\d*', r'ireland', r'euw1'],
                'eu-west-2': [r'eu-west-2', r'lhr\d*', r'london', r'euw2'],
                'eu-west-3': [r'eu-west-3', r'cdg\d*', r'paris', r'euw3'],
                'eu-central-1': [r'eu-central-1', r'fra\d*', r'frankfurt', r'euc1'],
                'ap-southeast-1': [r'ap-southeast-1', r'sin\d*', r'singapore', r'apse1'],
                'ap-northeast-1': [r'ap-northeast-1', r'nrt\d*', r'tokyo', r'apne1'],
            },
            # Google Cloud Platform
            'gcp': {
                'us-central1': [r'us-central1', r'uc1', r'iowa', r'central'],
                'us-east1': [r'us-east1', r'ue1', r'south.carolina', r'eastern'],
                'us-west1': [r'us-west1', r'uw1', r'oregon', r'western'],
                'us-west2': [r'us-west2', r'uw2', r'los.angeles'],
                'us-west3': [r'us-west3', r'uw3', r'salt.lake'],
                'us-west4': [r'us-west4', r'uw4', r'las.vegas'],
                'europe-west1': [r'europe-west1', r'ew1', r'belgium', r'st.ghislain'],
                'europe-west2': [r'europe-west2', r'ew2', r'london', r'lhr\d*'],
                'europe-west3': [r'europe-west3', r'ew3', r'frankfurt', r'fra\d*'],
                'europe-west4': [r'europe-west4', r'ew4', r'netherlands', r'eemshaven', r'ams\d*'],
                'europe-west9': [r'europe-west9', r'ew9', r'paris', r'par\d+s\d+', r'cdg\d*'],
                'asia-southeast1': [r'asia-southeast1', r'as1', r'singapore', r'sin\d*'],
                'asia-northeast1': [r'asia-northeast1', r'an1', r'tokyo', r'nrt\d*'],
            },
            # Microsoft Azure
            'azure': {
                'eastus': [r'eastus', r'east.us', r'virginia'],
                'eastus2': [r'eastus2', r'east.us.2', r'virginia2'],
                'westus': [r'westus', r'west.us', r'california'],
                'westus2': [r'westus2', r'west.us.2', r'washington'],
                'northeurope': [r'northeurope', r'north.europe', r'ireland'],
                'westeurope': [r'westeurope', r'west.europe', r'netherlands'],
                'francecentral': [r'francecentral', r'france.central', r'paris'],
                'germanywestcentral': [r'germanywestcentral', r'germany.west', r'frankfurt'],
                'eastasia': [r'eastasia', r'east.asia', r'hong.kong'],
                'southeastasia': [r'southeastasia', r'southeast.asia', r'singapore'],
            },
            # OVH
            'ovh': {
                'gra7': [r'gra\d*', r'gravelines', r'gra7', r'\.gra-', r'gra-g\d+'],
                'gra9': [r'gra9', r'gravelines9'],
                'rbx8': [r'rbx\d*', r'roubaix', r'rbx8', r'\.rbx-'],
                'sbg5': [r'sbg\d*', r'strasbourg', r'sbg5', r'\.sbg-'],
                'bhs5': [r'bhs\d*', r'beauharnois', r'montreal', r'bhs5', r'\.bhs-'],
                'waw1': [r'waw\d*', r'warsaw', r'poland', r'waw1', r'\.waw-'],
                'lon1': [r'lon\d*', r'london', r'lon1', r'\.lon-'],
                'fra1': [r'fra\d*', r'frankfurt', r'fra1', r'\.fra-'],
                'sin1': [r'sin\d*', r'singapore', r'sin1', r'\.sin-'],
                'syd1': [r'syd\d*', r'sydney', r'australia', r'syd1', r'\.syd-'],
            },
            # Cloudflare
            'cloudflare': {
                'ams': [r'ams\d*', r'amsterdam'],
                'atl': [r'atl\d*', r'atlanta'],
                'bom': [r'bom\d*', r'mumbai'],
                'cdg': [r'cdg\d*', r'paris'],
                'dfw': [r'dfw\d*', r'dallas'],
                'fra': [r'fra\d*', r'frankfurt'],
                'iad': [r'iad\d*', r'washington', r'ashburn'],
                'lax': [r'lax\d*', r'los.angeles'],
                'lhr': [r'lhr\d*', r'london'],
                'nrt': [r'nrt\d*', r'tokyo'],
                'ord': [r'ord\d*', r'chicago'],
                'sea': [r'sea\d*', r'seattle'],
                'sin': [r'sin\d*', r'singapore'],
                'syd': [r'syd\d*', r'sydney'],
            },
            # Akamai
            'akamai': {
                'ams': [r'ams\d*', r'amsterdam'],
                'atl': [r'atl\d*', r'atlanta'],
                'bos': [r'bos\d*', r'boston'],
                'cdg': [r'cdg\d*', r'paris'],
                'dfw': [r'dfw\d*', r'dallas'],
                'fra': [r'fra\d*', r'frankfurt'],
                'lax': [r'lax\d*', r'los.angeles'],
                'lhr': [r'lhr\d*', r'london'],
                'mia': [r'mia\d*', r'miami'],
                'nrt': [r'nrt\d*', r'tokyo'],
                'ord': [r'ord\d*', r'chicago'],
                'sea': [r'sea\d*', r'seattle'],
                'sin': [r'sin\d*', r'singapore'],
                'syd': [r'syd\d*', r'sydney'],
            },
            # Hetzner
            'hetzner': {
                'fsn': [r'fsn\d*', r'falkenstein'],
                'nbg': [r'nbg\d*', r'nuremberg'],
                'hel': [r'hel\d*', r'helsinki'],
                'ash': [r'ash\d*', r'ashburn'],
                'hil': [r'hil\d*', r'hillsboro'],
            },
            # DigitalOcean
            'digitalocean': {
                'nyc': [r'nyc\d*', r'new-york'],
                'sfo': [r'sfo\d*', r'san-francisco'],
                'ams': [r'ams\d*', r'amsterdam'],
                'sgp': [r'sgp\d*', r'singapore'],
                'lon': [r'lon\d*', r'london'],
                'fra': [r'fra\d*', r'frankfurt'],
                'tor': [r'tor\d*', r'toronto'],
                'blr': [r'blr\d*', r'bangalore'],
            },
            # GitHub (hébergé sur Azure)
            'github': {
                'fra': [r'fra', r'frankfurt', r'de-cix\.fra', r'\.fra\.github', r'-fra\.github'],
                'sea': [r'sea', r'seattle'],
                'iad': [r'iad', r'ashburn', r'washington'],
                'sjc': [r'sjc', r'san-jose'],
                'lhr': [r'lhr', r'london'],
                'sin': [r'sin', r'singapore'],
            }
        }
        
        # Mapping des codes de pays vers des régions probables
        self.country_to_region_mapping = {
            'aws': {
                'US': 'us-east-1',
                'IE': 'eu-west-1',
                'GB': 'eu-west-2',
                'FR': 'eu-west-3',
                'DE': 'eu-central-1',
                'SG': 'ap-southeast-1',
                'JP': 'ap-northeast-1',
                'CA': 'ca-central-1',
                'AU': 'ap-southeast-2',
                'BR': 'sa-east-1',
                'KR': 'ap-northeast-2',
                'IN': 'ap-south-1',
            },
            'gcp': {
                'US': 'us-central1',
                'BE': 'europe-west1',
                'GB': 'europe-west2',
                'DE': 'europe-west3',
                'NL': 'europe-west4',
                'SG': 'asia-southeast1',
                'JP': 'asia-northeast1',
                'CA': 'northamerica-northeast1',
                'AU': 'australia-southeast1',
                'BR': 'southamerica-east1',
                'KR': 'asia-northeast3',
                'IN': 'asia-south1',
                'FR': 'europe-west9',
            },
            'azure': {
                'US': 'eastus',
                'IE': 'northeurope',
                'NL': 'westeurope',
                'FR': 'francecentral',
                'DE': 'germanywestcentral',
                'HK': 'eastasia',
                'SG': 'southeastasia',
                'GB': 'uksouth',
                'CA': 'canadacentral',
                'AU': 'australiaeast',
                'BR': 'brazilsouth',
                'KR': 'koreacentral',
                'IN': 'centralindia',
                'JP': 'japaneast',
            },
            'ovh': {
                'FR': 'gra7',  # Gravelines (défaut France)
                'DE': 'fra1',  # Frankfurt  
                'GB': 'lon1',  # London
                'CA': 'bhs5',  # Beauharnois
                'PL': 'waw1',  # Warsaw
                'SG': 'sin1',  # Singapore
                'AU': 'syd1',  # Sydney
                'US': 'us-east-va-1',  # Virginia
            },
            'digitalocean': {
                'US': 'nyc1',     # New York (défaut US)
                'NL': 'ams3',     # Amsterdam
                'GB': 'lon1',     # London
                'DE': 'fra1',     # Frankfurt
                'SG': 'sgp1',     # Singapore
                'CA': 'tor1',     # Toronto
                'IN': 'blr1',     # Bangalore
            },
            'hetzner': {
                'DE': 'fsn1',     # Falkenstein (défaut)
                'FI': 'hel1',     # Helsinki
                'US': 'ash',      # Ashburn
            },
            'cloudflare': {
                'US': 'iad',      # Washington DC (défaut global)
                'GB': 'lhr',      # London
                'DE': 'fra',      # Frankfurt
                'SG': 'sin',      # Singapore
                'FR': 'cdg',      # Paris
                'NL': 'ams',      # Amsterdam
                'JP': 'nrt',      # Tokyo
            }
        }
    
    def detect_via_ip_geolocation(self, ip: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Détecte la région via géolocalisation IP (ip-api.com).
        
        Args:
            ip: Adresse IP à analyser
            
        Returns:
            Tuple (provider, region) basé sur la géolocalisation
        """
        try:
            # Utiliser l'API gratuite ip-api.com
            response = requests.get(
                f"http://ip-api.com/json/{ip}?fields=status,org,isp,as,country,countryCode,regionName,city",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    org = data.get('org', '').lower()
                    isp = data.get('isp', '').lower()
                    as_info = data.get('as', '').lower()
                    country_code = data.get('countryCode', '')
                    region_name = data.get('regionName', '')
                    city = data.get('city', '')
                    
                    # Identifier le provider
                    provider = self._identify_provider_from_org(org + ' ' + isp + ' ' + as_info)
                    
                    if provider:
                        # Essayer de déduire la région
                        region = self._deduce_region_from_location(provider, country_code, region_name, city)
                        if region:
                            return provider, region
                        
                        # Fallback sur le mapping pays -> région
                        if provider in self.country_to_region_mapping and country_code in self.country_to_region_mapping[provider]:
                            return provider, self.country_to_region_mapping[provider][country_code]
                    
                    return provider, None
        except Exception as e:
            logging.debug(f"Géolocalisation IP échouée pour {ip}: {e}")
        
        return None, None
    
    def _identify_provider_from_org(self, org_text: str) -> Optional[str]:
        """Identifie le provider depuis les informations d'organisation."""
        org_lower = org_text.lower()
        
        provider_indicators = {
            'aws': ['amazon', 'aws', 'ec2', 'cloudfront'],
            'gcp': ['google', 'gcp', 'googlers'],
            'azure': ['microsoft', 'azure', 'msft'],
            'ovh': ['ovh', 'kimsufi', 'soyoustart'],
            'cloudflare': ['cloudflare'],
            'akamai': ['akamai', 'akamai-asn1', 'akamai technologies'],
            'hetzner': ['hetzner'],
            'digitalocean': ['digitalocean', 'digital ocean']
        }
        
        for provider, indicators in provider_indicators.items():
            for indicator in indicators:
                if indicator in org_lower:
                    return provider
        
        return None
    
    def _deduce_region_from_location(self, provider: str, country_code: str, region_name: str, city: str) -> Optional[str]:
        """Déduit la région basée sur la localisation géographique."""
        location_text = f"{region_name} {city}".lower()
        
        # Mapping des villes/régions vers des régions cloud
        location_mappings = {
            'aws': {
                'virginia': 'us-east-1',
                'ohio': 'us-east-2',
                'california': 'us-west-1',
                'oregon': 'us-west-2',
                'ireland': 'eu-west-1',
                'london': 'eu-west-2',
                'paris': 'eu-west-3',
                'frankfurt': 'eu-central-1',
                'singapore': 'ap-southeast-1',
                'tokyo': 'ap-northeast-1',
                'sydney': 'ap-southeast-2',
                'seoul': 'ap-northeast-2',
                'mumbai': 'ap-south-1',
                'canada': 'ca-central-1',
                'toronto': 'ca-central-1',
                'são paulo': 'sa-east-1',
                'sao paulo': 'sa-east-1',
            },
            'gcp': {
                'iowa': 'us-central1',
                'south carolina': 'us-east1',
                'oregon': 'us-west1',
                'los angeles': 'us-west2',
                'salt lake': 'us-west3',
                'las vegas': 'us-west4',
                'belgium': 'europe-west1',
                'london': 'europe-west2',
                'frankfurt': 'europe-west3',
                'netherlands': 'europe-west4',
                'eemshaven': 'europe-west4',
                'zurich': 'europe-west6',
                'paris': 'europe-west9',
                'singapore': 'asia-southeast1',
                'tokyo': 'asia-northeast1',
                'osaka': 'asia-northeast2',
                'seoul': 'asia-northeast3',
                'mumbai': 'asia-south1',
                'sydney': 'australia-southeast1',
                'montreal': 'northamerica-northeast1',
                'são paulo': 'southamerica-east1',
                'sao paulo': 'southamerica-east1',
            },
            'azure': {
                'virginia': 'eastus',
                'east us': 'eastus',
                'virginia 2': 'eastus2',
                'central us': 'centralus',
                'north central us': 'northcentralus',
                'south central us': 'southcentralus',
                'west central us': 'westcentralus',
                'west us': 'westus',
                'west us 2': 'westus2',
                'ireland': 'northeurope',
                'netherlands': 'westeurope',
                'london': 'uksouth',
                'uk south': 'uksouth',
                'uk west': 'ukwest',
                'france central': 'francecentral',
                'paris': 'francecentral',
                'france south': 'francesouth',
                'germany west central': 'germanywestcentral',
                'frankfurt': 'germanywestcentral',
                'singapore': 'southeastasia',
                'hong kong': 'eastasia',
                'tokyo': 'japaneast',
                'osaka': 'japanwest',
                'seoul': 'koreacentral',
                'mumbai': 'centralindia',
                'sydney': 'australiaeast',
                'toronto': 'canadacentral',
                'são paulo': 'brazilsouth',
                'sao paulo': 'brazilsouth',
            },
            'ovh': {
                'gravelines': 'gra7',
                'roubaix': 'rbx8',
                'strasbourg': 'sbg5',
                'beauharnois': 'bhs5',
                'montreal': 'bhs5',
                'warsaw': 'waw1',
                'london': 'lon1',
                'frankfurt': 'fra1',
                'singapore': 'sin1',
                'sydney': 'syd1',
                'virginia': 'us-east-va-1',
                'ashburn': 'us-east-va-1',
            },
            'digitalocean': {
                'new york': 'nyc1',
                'san francisco': 'sfo3',
                'amsterdam': 'ams3',
                'singapore': 'sgp1',
                'london': 'lon1',
                'frankfurt': 'fra1',
                'toronto': 'tor1',
                'bangalore': 'blr1',
                'mumbai': 'blr1',
            },
            'hetzner': {
                'falkenstein': 'fsn1',
                'nuremberg': 'nbg1',
                'helsinki': 'hel1',
                'ashburn': 'ash',
                'hillsboro': 'hil',
            },
            'cloudflare': {
                'amsterdam': 'ams',
                'atlanta': 'atl',
                'mumbai': 'bom',
                'paris': 'cdg',
                'dallas': 'dfw',
                'frankfurt': 'fra',
                'washington': 'iad',
                'ashburn': 'iad',
                'los angeles': 'lax',
                'london': 'lhr',
                'tokyo': 'nrt',
                'chicago': 'ord',
                'seattle': 'sea',
                'singapore': 'sin',
                'sydney': 'syd',
            }
        }
        
        if provider in location_mappings:
            for location, region in location_mappings[provider].items():
                if location in location_text:
                    return region
        
        return None
    
    def run_mtr(self, target: str, max_hops: int = 12) -> List[str]:
        """
        Exécute MTR vers la cible pour obtenir des informations détaillées sur le routage.
        MTR est plus précis que traceroute classique.
        
        Args:
            target: Adresse IP ou nom de domaine cible
            max_hops: Nombre maximum de sauts
            
        Returns:
            Liste des noms d'hôtes rencontrés dans le MTR
        """
        hostnames = []
        
        try:
            # Essayer MTR (My Traceroute) - avec sudo maintenant que douro a les droits
            cmd = [
                'sudo', 'mtr', 
                '-4',  # Force IPv4
                '--report', 
                '--report-cycles', '2', 
                '--max-ttl', str(max_hops),
                '-b',  # Show both hostnames and IPs
                target
            ]
            
            logging.info(f"DEBUG MTR: Commande pour {target}: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=45
            )
            
            logging.info(f"DEBUG MTR: Return code pour {target}: {result.returncode}")
            logging.info(f"DEBUG MTR: Stdout length pour {target}: {len(result.stdout)} chars")
            logging.info(f"DEBUG MTR: Stderr pour {target}: {result.stderr[:200]}")
            
            if result.returncode == 0:
                logging.info(f"DEBUG MTR: Stdout échantillon pour {target}: {result.stdout[:300]}")
                hostnames.extend(self._parse_mtr_output(result.stdout))
                logging.info(f"DEBUG MTR: Hostnames parsés pour {target}: {hostnames}")
            else:
                # Fallback sur traceroute classique directement
                logging.debug(f"MTR a échoué, fallback sur traceroute pour {target}")
                return self.run_traceroute_fallback(target, max_hops)
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.debug(f"Échec de MTR vers {target}: {e}")
            # Fallback sur traceroute classique
            return self.run_traceroute_fallback(target, max_hops)
        
        return hostnames

    def _parse_mtr_output(self, output: str) -> List[str]:
        """
        Parse la sortie de MTR pour extraire les noms d'hôtes.
        
        Format typique MTR:
        HOST: hostname                    Loss%   Snt   Last   Avg  Best  Wrst StDev
          1.|-- router.example.com        0.0%     2    1.0   1.0   1.0   1.0   0.0
          2.|-- 192.168.1.1              0.0%     2    5.0   5.0   5.0   5.0   0.0
        """
        hostnames = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or 'HOST:' in line or 'Start:' in line:
                continue
                
            # Format MTR: "  1.|-- hostname/IP   Loss%   ..."
            match = re.match(r'\s*\d+\.\|\-\-\s+([^\s]+)', line)
            if match:
                hostname_or_ip = match.group(1)
                
                # Ignorer les entrées vides ou les timeouts
                if hostname_or_ip in ['???', '*', '0.0.0.0']:
                    continue
                
                # Si c'est une IP, faire une résolution DNS inverse
                if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname_or_ip):
                    try:
                        reversed_name = socket.gethostbyaddr(hostname_or_ip)[0]
                        if reversed_name and '.' in reversed_name:
                            hostnames.append(reversed_name.lower())
                    except (socket.herror, socket.gaierror):
                        # Pas de résolution inverse, on garde l'IP pour analyse
                        hostnames.append(hostname_or_ip)
                else:
                    # C'est déjà un hostname
                    if '.' in hostname_or_ip:
                        hostnames.append(hostname_or_ip.lower())
        
        return hostnames

    def run_traceroute_fallback(self, target: str, max_hops: int = 15) -> List[str]:
        """
        Fallback sur traceroute classique si MTR ne fonctionne pas.
        """
        hostnames = []
        
        try:
            # Essayer traceroute sur Unix/Linux/macOS
            cmd = ['traceroute', '-m', str(max_hops), '-w', '3', target]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                hostnames.extend(self._parse_traceroute_unix(result.stdout))
            else:
                # Fallback sur tracert Windows
                cmd = ['tracert', '-h', str(max_hops), '-w', '3000', target]
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                if result.returncode == 0:
                    hostnames.extend(self._parse_traceroute_windows(result.stdout))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logging.debug(f"Échec du traceroute fallback vers {target}")
        
        return hostnames
    
    def run_traceroute(self, target: str, max_hops: int = 15) -> List[str]:
        """
        Exécute un traceroute vers la cible.
        
        Args:
            target: Adresse IP ou nom de domaine cible
            max_hops: Nombre maximum de sauts
            
        Returns:
            Liste des noms d'hôtes rencontrés dans le traceroute
        """
        hostnames = []
        
        try:
            # Essayer traceroute sur Unix/Linux/macOS
            cmd = ['traceroute', '-m', str(max_hops), '-w', '2', target]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                hostnames.extend(self._parse_traceroute_unix(result.stdout))
            else:
                # Fallback sur tracert Windows
                cmd = ['tracert', '-h', str(max_hops), '-w', '2000', target]
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                if result.returncode == 0:
                    hostnames.extend(self._parse_traceroute_windows(result.stdout))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logging.debug(f"Échec du traceroute vers {target}")
        
        return hostnames
    
    def _parse_traceroute_unix(self, output: str) -> List[str]:
        """Parse la sortie d'un traceroute Unix/Linux/macOS."""
        hostnames = []
        
        for line in output.split('\n'):
            if line.strip():
                # Chercher les noms d'hôtes dans chaque ligne
                # Format typique: " 3  router.example.com (1.2.3.4)  10.123 ms"
                hostname_match = re.search(r'\s+\d+\s+([a-zA-Z0-9\-\.]+)\s+\(', line)
                if hostname_match:
                    hostname = hostname_match.group(1)
                    if hostname != '*' and '.' in hostname:
                        hostnames.append(hostname.lower())
        
        return hostnames
    
    def _parse_traceroute_windows(self, output: str) -> List[str]:
        """Parse la sortie d'un tracert Windows."""
        hostnames = []
        
        for line in output.split('\n'):
            if line.strip() and re.match(r'\s*\d+', line):
                # Format typique: "  3    10 ms     9 ms    10 ms  router.example.com [1.2.3.4]"
                hostname_match = re.search(r'\s+([a-zA-Z0-9\-\.]+)\s+\[', line)
                if hostname_match:
                    hostname = hostname_match.group(1)
                    if hostname != '*' and '.' in hostname:
                        hostnames.append(hostname.lower())
        
        return hostnames
    
    def detect_provider_and_region(self, hostnames: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Détecte le fournisseur et la région basé sur les noms d'hôtes.
        
        Args:
            hostnames: Liste des noms d'hôtes du traceroute
            
        Returns:
            Tuple (provider, region) ou (None, None) si non détecté
        """
        # Vérifier chaque hostname contre les patterns
        for hostname in hostnames:
            hostname_lower = hostname.lower()
            
            # Identifier le provider d'abord
            provider = self._identify_provider(hostname_lower)
            if provider:
                # Chercher la région pour ce provider
                region = self._identify_region(hostname_lower, provider)
                if region:
                    return provider, region
        
        return None, None
    
    def _identify_provider(self, hostname: str) -> Optional[str]:
        """Identifie le fournisseur basé sur le nom d'hôte."""
        provider_indicators = {
            'aws': ['amazonaws.com', 'aws.com', 'ec2', 'cloudfront'],
            'gcp': ['googleapis.com', 'google.com', 'gcp', 'googlers.com', '1e100.net', 'googleusercontent.com'],
            'azure': ['azure.com', 'microsoft.com', 'azureedge.net'],
            'ovh': ['ovh.net', 'ovh.com', 'kimsufi.com', 'soyoustart.com', 'ovh.fr', '.fr.eu', 'gra-g', 'rbx-', 'sbg-', 'bhs-'],
            'cloudflare': ['cloudflare.com', 'cloudflare.net', 'cf-dns.com'],
            'akamai': ['akamai.com', 'akamai.net', 'akamaitechnologies.com', 'akam.net'],
            'hetzner': ['hetzner.de', 'hetzner.com', 'your-server.de'],
            'digitalocean': ['digitalocean.com', 'do.co', 'nyc.co'],
            'github': ['github.com', 'github.io', 'githubassets.com']
        }
        
        for provider, indicators in provider_indicators.items():
            for indicator in indicators:
                if indicator in hostname:
                    return provider
        
        return None
    
    def _identify_region(self, hostname: str, provider: str) -> Optional[str]:
        """Identifie la région pour un provider donné."""
        if provider not in self.region_patterns:
            return None
        
        provider_regions = self.region_patterns[provider]
        
        for region, patterns in provider_regions.items():
            for pattern in patterns:
                if re.search(pattern, hostname):
                    return region
        
        return None
    
    def detect_hosting_region(self, target: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Détecte la région d'hébergement d'une cible.
        
        Args:
            target: Adresse IP ou nom de domaine
            
        Returns:
            Tuple (provider, region, hostnames) ou (None, None, []) si échec
        """
        logging.info(f"DEBUG REGION: Début détection pour {target}")
        
        # Méthode 1: Géolocalisation IP (plus fiable)
        provider, region = self.detect_via_ip_geolocation(target)
        logging.info(f"DEBUG REGION: Géolocalisation pour {target}: provider={provider}, region={region}")
        if provider and region:
            logging.info(f"DEBUG REGION: Succès géolocalisation pour {target}: {provider}->{region}")
            return provider, region, []
        
        # Méthode 2: MTR (My Traceroute) - plus précis que traceroute classique
        logging.info(f"DEBUG REGION: Tentative MTR pour {target}")
        hostnames = self.run_mtr(target)
        logging.info(f"DEBUG REGION: MTR pour {target}: {len(hostnames)} hostnames trouvés: {hostnames[:3]}")
        
        if hostnames:
            provider_tr, region_tr = self.detect_provider_and_region(hostnames)
            logging.info(f"DEBUG REGION: Analyse hostnames pour {target}: provider={provider_tr}, region={region_tr}")
            if provider_tr and region_tr:
                logging.info(f"DEBUG REGION: Succès MTR pour {target}: {provider_tr}->{region_tr}")
                return provider_tr, region_tr, hostnames
            # Si on a trouvé un provider via géolocalisation mais pas via MTR
            elif provider and provider_tr:
                logging.info(f"DEBUG REGION: Provider géo seulement pour {target}: {provider}")
                return provider, None, hostnames
        
        # Retourner ce qu'on a trouvé via géolocalisation même sans région
        if provider:
            logging.info(f"DEBUG REGION: Provider géo final pour {target}: {provider}")
            return provider, None, hostnames
        
        logging.info(f"DEBUG REGION: Échec complet pour {target}")
        return None, None, hostnames


def detect_region(target: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fonction utilitaire pour détecter la région d'hébergement.
    
    Args:
        target: Adresse IP ou nom de domaine
        
    Returns:
        Tuple (provider, region) ou (None, None) si non détecté
    """
    detector = RegionDetector()
    provider, region, _ = detector.detect_hosting_region(target)
    return provider, region 