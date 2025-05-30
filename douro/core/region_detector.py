"""
Hosting region detection module via traceroute analysis and IP geolocation.
"""

import re
import subprocess
import logging
import socket
import requests
from typing import Optional, List, Tuple, Dict
from ipwhois import IPWhois


class RegionDetector:
    """Hosting region detection based on traceroute analysis and IP geolocation."""
    
    def __init__(self):
        """Initialise the detector with region mappings."""
        # Patterns for region detection based on hostnames
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
                'gra7': [r'gra\d*', r'gravelines', r'gra7', r'\.gra-', r'gra-g\d+', r'be\d+\.gra-g\d+', r'gra-g\d+-nc\d+', r'\.gra\.', r'-gra\.', r'lil\d*-gra\d*', r'\.lil\d*-gra\d*-'],
                'gra9': [r'gra9', r'gravelines9'],
                'rbx8': [r'rbx\d*', r'roubaix', r'rbx8', r'\.rbx-', r'rbx-g\d+', r'\.rbx\.', r'-rbx\.', r'lil\d*-rbx\d*', r'\.lil\d*-rbx\d*-'],
                'sbg5': [r'sbg\d*', r'strasbourg', r'sbg5', r'\.sbg-', r'sbg-g\d+', r'\.sbg\.', r'-sbg\.', r'lil\d*-sbg\d*', r'\.lil\d*-sbg\d*-'],
                'bhs5': [r'bhs\d*', r'beauharnois', r'montreal', r'bhs5', r'\.bhs-', r'bhs-g\d+', r'\.bhs\.', r'-bhs\.', r'lil\d*-bhs\d*', r'\.lil\d*-bhs\d*-'],
                'waw1': [r'waw\d*', r'warsaw', r'poland', r'waw1', r'\.waw-', r'waw-g\d+', r'\.waw\.', r'-waw\.', r'lil\d*-waw\d*', r'\.lil\d*-waw\d*-'],
                'lon1': [r'lon\d*', r'london', r'lon1', r'\.lon-', r'lon-g\d+', r'\.lon\.', r'-lon\.', r'lil\d*-lon\d*', r'\.lil\d*-lon\d*-'],
                'fra1': [r'fra\d*', r'frankfurt', r'fra1', r'\.fra-', r'fra-g\d+', r'\.fra\.', r'-fra\.', r'lil\d*-fra\d*', r'\.lil\d*-fra\d*-'],
                'sin1': [r'sin\d*', r'singapore', r'sin1', r'\.sin-', r'sin-g\d+', r'\.sin\.', r'-sin\.', r'lil\d*-sin\d*', r'\.lil\d*-sin\d*-'],
                'syd1': [r'syd\d*', r'sydney', r'australia', r'syd1', r'\.syd-', r'syd-g\d+', r'\.syd\.', r'-syd\.', r'lil\d*-syd\d*', r'\.lil\d*-syd\d*-'],
            },
            # Cloudflare - improved with IATA codes and IP patterns
            'cloudflare': {
                'ams': [r'ams\d*', r'amsterdam', r'\.ams\.', r'-ams\.', r'ams\d+\.cloudflare'],
                'atl': [r'atl\d*', r'atlanta', r'\.atl\.', r'-atl\.', r'atl\d+\.cloudflare'],
                'bom': [r'bom\d*', r'mumbai', r'\.bom\.', r'-bom\.', r'bom\d+\.cloudflare'],
                'cdg': [r'cdg\d*', r'paris', r'\.cdg\.', r'-cdg\.', r'cdg\d+\.cloudflare'],
                'dfw': [r'dfw\d*', r'dallas', r'\.dfw\.', r'-dfw\.', r'dfw\d+\.cloudflare'],
                'fra': [r'fra\d*', r'frankfurt', r'\.fra\.', r'-fra\.', r'fra\d+\.cloudflare'],
                'iad': [r'iad\d*', r'washington', r'ashburn', r'\.iad\.', r'-iad\.', r'iad\d+\.cloudflare'],
                'lax': [r'lax\d*', r'los.angeles', r'\.lax\.', r'-lax\.', r'lax\d+\.cloudflare'],
                'lhr': [r'lhr\d*', r'london', r'\.lhr\.', r'-lhr\.', r'lhr\d+\.cloudflare'],
                'nrt': [r'nrt\d*', r'tokyo', r'\.nrt\.', r'-nrt\.', r'nrt\d+\.cloudflare'],
                'ord': [r'ord\d*', r'chicago', r'\.ord\.', r'-ord\.', r'ord\d+\.cloudflare'],
                'sea': [r'sea\d*', r'seattle', r'\.sea\.', r'-sea\.', r'sea\d+\.cloudflare'],
                'sin': [r'sin\d*', r'singapore', r'\.sin\.', r'-sin\.', r'sin\d+\.cloudflare'],
                'syd': [r'syd\d*', r'sydney', r'\.syd\.', r'-syd\.', r'syd\d+\.cloudflare'],
            },
            # Akamai - improved with Akamai domain patterns
            'akamai': {
                'ams': [r'ams\d*', r'amsterdam', r'\.ams\.', r'-ams\.', r'ams\d+\.akamai', r'\.akam\.net.*ams'],
                'atl': [r'atl\d*', r'atlanta', r'\.atl\.', r'-atl\.', r'atl\d+\.akamai', r'\.akam\.net.*atl'],
                'bos': [r'bos\d*', r'boston', r'\.bos\.', r'-bos\.', r'bos\d+\.akamai', r'\.akam\.net.*bos'],
                'cdg': [r'cdg\d*', r'paris', r'\.cdg\.', r'-cdg\.', r'cdg\d+\.akamai', r'\.akam\.net.*cdg'],
                'dfw': [r'dfw\d*', r'dallas', r'\.dfw\.', r'-dfw\.', r'dfw\d+\.akamai', r'\.akam\.net.*dfw'],
                'fra': [r'fra\d*', r'frankfurt', r'\.fra\.', r'-fra\.', r'fra\d+\.akamai', r'\.akam\.net.*fra'],
                'lax': [r'lax\d*', r'los.angeles', r'\.lax\.', r'-lax\.', r'lax\d+\.akamai', r'\.akam\.net.*lax'],
                'lhr': [r'lhr\d*', r'london', r'\.lhr\.', r'-lhr\.', r'lhr\d+\.akamai', r'\.akam\.net.*lhr'],
                'mia': [r'mia\d*', r'miami', r'\.mia\.', r'-mia\.', r'mia\d+\.akamai', r'\.akam\.net.*mia'],
                'nrt': [r'nrt\d*', r'tokyo', r'\.nrt\.', r'-nrt\.', r'nrt\d+\.akamai', r'\.akam\.net.*nrt'],
                'ord': [r'ord\d*', r'chicago', r'\.ord\.', r'-ord\.', r'ord\d+\.akamai', r'\.akam\.net.*ord'],
                'sea': [r'sea\d*', r'seattle', r'\.sea\.', r'-sea\.', r'sea\d+\.akamai', r'\.akam\.net.*sea'],
                'sin': [r'sin\d*', r'singapore', r'\.sin\.', r'-sin\.', r'sin\d+\.akamai', r'\.akam\.net.*sin'],
                'syd': [r'syd\d*', r'sydney', r'\.syd\.', r'-syd\.', r'syd\d+\.akamai', r'\.akam\.net.*syd'],
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
            # GitHub (hosted on Azure)
            'github': {
                'fra': [r'fra', r'frankfurt', r'de-cix\.fra', r'\.fra\.github', r'-fra\.github'],
                'sea': [r'sea', r'seattle'],
                'iad': [r'iad', r'ashburn', r'washington'],
                'sjc': [r'sjc', r'san-jose'],
                'lhr': [r'lhr', r'london'],
                'sin': [r'sin', r'singapore'],
            }
        }
        
        # Mapping of country codes to probable regions
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
                'FR': 'gra7',  # Gravelines (default France)
                'DE': 'fra1',  # Frankfurt  
                'GB': 'lon1',  # London
                'CA': 'bhs5',  # Beauharnois
                'PL': 'waw1',  # Warsaw
                'SG': 'sin1',  # Singapore
                'AU': 'syd1',  # Sydney
                'US': 'us-east-va-1',  # Virginia
            },
            'digitalocean': {
                'US': 'nyc1',     # New York (default US)
                'NL': 'ams3',     # Amsterdam
                'GB': 'lon1',     # London
                'DE': 'fra1',     # Frankfurt
                'SG': 'sgp1',     # Singapore
                'CA': 'tor1',     # Toronto
                'IN': 'blr1',     # Bangalore
            },
            'hetzner': {
                'DE': 'fsn1',     # Falkenstein (default)
                'FI': 'hel1',     # Helsinki
                'US': 'ash',      # Ashburn
            },
            'cloudflare': {
                'US': 'iad',      # Washington DC (default global)
                'GB': 'lhr',      # London
                'DE': 'fra',      # Frankfurt
                'SG': 'sin',      # Singapore
                'FR': 'cdg',      # Paris
                'NL': 'ams',      # Amsterdam
                'JP': 'nrt',      # Tokyo
            }
        }
    
    def detect_via_ip_geolocation(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect provider and region via IP geolocation and WHOIS.
        Faster but less accurate than MTR.
        """
        try:
            # Resolve IP if it's a domain name
            if not self._is_ip_address(target):
                ip = socket.gethostbyname(target)
            else:
                ip = target
            
            # Use ipwhois to get information
            obj = IPWhois(ip)
            
            try:
                results = obj.lookup_rdap()
            except Exception:
                try:
                    results = obj.lookup_whois()
                except Exception:
                    return None, None
            
            asn = results.get('asn')
            asn_org = results.get('asn_description', '').lower()
            country = results.get('country')
            
            # If no direct country, try to extract from organization
            if not country and asn_org:
                # Common patterns: "OVH, FR", "Amazon, US", "Microsoft, US", etc.
                if ', fr' in asn_org or ' fr' in asn_org:
                    country = 'FR'
                elif ', us' in asn_org or ' us' in asn_org:
                    country = 'US'
                elif ', de' in asn_org or ' de' in asn_org:
                    country = 'DE'
                elif ', gb' in asn_org or ' gb' in asn_org:
                    country = 'GB'
                elif ', ca' in asn_org or ' ca' in asn_org:
                    country = 'CA'
                elif ', sg' in asn_org or ' sg' in asn_org:
                    country = 'SG'
                elif ', jp' in asn_org or ' jp' in asn_org:
                    country = 'JP'
                elif ', au' in asn_org or ' au' in asn_org:
                    country = 'AU'
                elif ', nl' in asn_org or ' nl' in asn_org:
                    country = 'NL'
                elif ', be' in asn_org or ' be' in asn_org:
                    country = 'BE'
                elif ', ie' in asn_org or ' ie' in asn_org:
                    country = 'IE'
            
            # Detect provider based on ASN and organization
            provider = None
            region = None
            
            # AWS
            if '16509' in str(asn) or 'amazon' in asn_org or 'aws' in asn_org:
                provider = 'aws'
                if country in self.country_to_region_mapping.get('aws', {}):
                    region = self.country_to_region_mapping['aws'][country]
            
            # Google Cloud
            elif '15169' in str(asn) or 'google' in asn_org:
                provider = 'gcp'
                if country in self.country_to_region_mapping.get('gcp', {}):
                    region = self.country_to_region_mapping['gcp'][country]
            
            # Microsoft Azure
            elif '8075' in str(asn) or 'microsoft' in asn_org:
                provider = 'azure'
                if country in self.country_to_region_mapping.get('azure', {}):
                    region = self.country_to_region_mapping['azure'][country]
            
            # OVH - improvement with IP range detection
            elif '16276' in str(asn) or 'ovh' in asn_org:
                provider = 'ovh'
                # Improved logic for OVH
                if country == 'FR':
                    # For France, analyze IP range to distinguish GRA/RBX/SBG
                    ip_parts = ip.split('.')
                    if len(ip_parts) == 4:
                        try:
                            first_octet = int(ip_parts[0])
                            second_octet = int(ip_parts[1])
                            
                            # Approximate OVH ranges (to be refined based on experience)
                            # 54.39.x.x seems to be typically GRA
                            if first_octet == 54 and second_octet == 39:
                                region = 'gra7'  # Gravelines default for this range
                            # 151.80.x.x typically RBX
                            elif first_octet == 151 and second_octet == 80:
                                region = 'rbx8'
                            # 51.38.x.x typically SBG
                            elif first_octet == 51 and second_octet == 38:
                                region = 'sbg5'
                            else:
                                region = 'gra7'  # Default France
                        except ValueError:
                            region = 'gra7'
                elif country == 'CA':
                    region = 'bhs5'
                elif country == 'GB':
                    region = 'lon1'
                elif country == 'DE':
                    region = 'fra1'
                elif country == 'PL':
                    region = 'waw1'
                elif country == 'SG':
                    region = 'sin1'
                elif country == 'AU':
                    region = 'syd1'
                else:
                    region = None
            
            # Cloudflare
            elif '13335' in str(asn) or 'cloudflare' in asn_org:
                provider = 'cloudflare'
                # For Cloudflare, no specific region via IP alone
                region = None
            
            # Akamai
            elif any(akamai_asn in str(asn) for akamai_asn in ['16625', '20940', '21342', '16702', '18717', '18680', '20189']) or 'akamai' in asn_org:
                provider = 'akamai'
                # For Akamai, no specific region via IP alone
                region = None
            
            # Hetzner
            elif '24940' in str(asn) or 'hetzner' in asn_org:
                provider = 'hetzner'
                if country == 'DE':
                    region = 'fsn'  # Falkenstein default
                elif country == 'FI':
                    region = 'hel'
                elif country == 'US':
                    region = 'ash'  # Ashburn
                else:
                    region = None
            
            # DigitalOcean
            elif '14061' in str(asn) or 'digitalocean' in asn_org:
                provider = 'digitalocean'
                if country in self.country_to_region_mapping.get('digitalocean', {}):
                    region = self.country_to_region_mapping['digitalocean'][country]
            
            logging.info(f"DEBUG GEO: {target} -> ASN={asn}, Org={asn_org}, Country={country}, Provider={provider}, Region={region}")
            return provider, region
            
        except Exception as e:
            logging.debug(f"Error in geolocation for {target}: {e}")
            return None, None
    
    def _identify_provider_from_org(self, org_text: str) -> Optional[str]:
        """Identify provider from organization information."""
        org_lower = org_text.lower()
        
        provider_indicators = {
            'aws': ['amazon', 'aws', 'ec2', 'cloudfront'],
            'gcp': ['google', 'gcp', 'googlers'],
            'azure': ['microsoft', 'azure', 'msft'],
            'ovh': ['ovh.net', 'ovh.com', 'kimsufi.com', 'soyoustart.com', 'ovh.fr', '.fr.eu', 'gra-g', 'rbx-', 'sbg-', 'bhs-', 'be102.gra-g', 'be103.gra-g', 'be104.gra-g', 'gra-g1-nc', 'gra-g2-nc', 'gra-g3-nc', 'rbx-g1-nc', 'be103.lil', 'be102.lil', 'be104.lil', 'lil1-rbx', 'lil1-gra', 'lil1-sbg', 'lil1-bhs', '-sbb1-nc', '-sbb2-nc'],
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
        """Deduce region based on geographical location."""
        location_text = f"{region_name} {city}".lower()
        
        # Mapping of cities/regions to cloud regions
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
        Execute MTR to target for detailed routing information.
        MTR is more accurate than classic traceroute.
        
        Args:
            target: Target IP or domain name
            max_hops: Maximum number of hops
            
        Returns:
            List of hostnames encountered in the MTR
        """
        hostnames = []
        
        # Try IPv4 first, then IPv6 if IPv4 fails
        for ip_version in ['-4', '-6']:
            try:
                # Try MTR (My Traceroute) - with sudo only if the user is douro
                import getpass
                current_user = getpass.getuser()
                
                if current_user == 'douro':
                    cmd = [
                        'sudo', 'mtr', 
                        ip_version,  # IPv4 or IPv6
                        '--report', 
                        '--report-cycles', '10',  # 10 cycles for more accuracy as requested
                        '--max-ttl', str(max_hops),
                        '-b',  # Show both hostnames and IPs
                        target  # With DNS for having hostnames - NO --no-dns
                    ]
                else:
                    # Fallback without sudo for tests
                    cmd = [
                        'mtr', 
                        ip_version,  # IPv4 or IPv6
                        '--report', 
                        '--report-cycles', '10',  # 10 cycles for more accuracy
                        '--max-ttl', str(max_hops),
                        '-b',  # Show both hostnames and IPs
                        target  # With DNS for having hostnames
                    ]
                
                logging.info(f"DEBUG MTR: Command for {target} ({ip_version}): {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60  # Increase timeout for 10 cycles
                )
                
                logging.info(f"DEBUG MTR: Return code for {target} ({ip_version}): {result.returncode}")
                logging.info(f"DEBUG MTR: Stdout length for {target}: {len(result.stdout)} chars")
                
                if result.returncode == 0 and result.stdout.strip():
                    logging.info(f"DEBUG MTR: Stdout sample for {target}: {result.stdout[:300]}")
                    parsed_hostnames = self._parse_mtr_output_enhanced(result.stdout)
                    logging.info(f"DEBUG MTR: Parsed hostnames for {target} ({ip_version}): {parsed_hostnames}")
                    
                    if parsed_hostnames:
                        hostnames.extend(parsed_hostnames)
                        # If hostnames found, stop trying other IP versions
                        break
                    
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
                logging.debug(f"MTR failure {ip_version} to {target}: {e}")
                continue
        
        # If MTR gave no result, fallback on traceroute
        if not hostnames:
            logging.debug(f"MTR failed, fallback on traceroute for {target}")
            return self.run_traceroute_fallback(target, max_hops)
        
        return hostnames

    def _parse_mtr_output_enhanced(self, output: str) -> List[str]:
        """
        Improved parsing of MTR output to extract hostnames and IPs.
        Handles IPv4, IPv6 and different MTR output formats.
        """
        hostnames = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or 'HOST:' in line or 'Start:' in line or 'Keys:' in line:
                continue
                
            # Possible MTR formats:
            # IPv4: "  1.|-- hostname.com (192.168.1.1)   0.0%     3    1.0   1.0   1.0   1.0   0.0"
            # IPv4: "  1.|-- 192.168.1.1                 0.0%     3    1.0   1.0   1.0   1.0   0.0"
            # IPv6: "  1.|-- 2001:db8::1                 0.0%     3    1.0   1.0   1.0   1.0   0.0"
            # New format: "  1. hostname.com           0.0%     3    1.0   1.0   1.0   1.0   0.0"
            # Format with ???: "  2.|-- ???                       100.0     1    0.0   0.0   0.0   0.0   0.0"
            
            # Pattern to capture hostname or IP after the hop number
            patterns = [
                # Classic format: "1.|-- hostname.com (IP)" or "1.|-- IP"
                r'\s*\d+\.\|\-\-\s+([^\s\(]+)(?:\s+\([^)]+\))?',
                # Modern format: "1. hostname.com"
                r'\s*\d+\.\s+([^\s]+)',
            ]
            
            hostname_or_ip = None
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    hostname_or_ip = match.group(1)
                    break
            
            if not hostname_or_ip:
                continue
                
            # Ignore empty entries, timeouts and wildcards
            if hostname_or_ip in ['???', '*', '0.0.0.0', '(waiting', 'waiting', 'reply)']:
                continue
            
            # Ignore local/private addresses not interesting
            if hostname_or_ip.startswith(('192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', 'bbox.lan')):
                continue
            
            # IP vs hostname processing
            if self._is_ip_address(hostname_or_ip):
                # It's an IP, try reverse DNS resolution
                try:
                    reversed_name = socket.gethostbyaddr(hostname_or_ip)[0]
                    if reversed_name and '.' in reversed_name and len(reversed_name) > 5:
                        hostnames.append(reversed_name.lower())
                        logging.debug(f"DEBUG: Reverse resolution {hostname_or_ip} -> {reversed_name}")
                except (socket.herror, socket.gaierror, socket.timeout):
                    # No reverse resolution, keep IP for further analysis
                    hostnames.append(hostname_or_ip)
            else:
                # It's already a hostname
                if '.' in hostname_or_ip and len(hostname_or_ip) > 3:
                    hostnames.append(hostname_or_ip.lower())
        
        # Deduplicate while keeping order
        seen = set()
        deduplicated = []
        for h in hostnames:
            if h not in seen:
                seen.add(h)
                deduplicated.append(h)
        
        return deduplicated

    def _is_ip_address(self, addr: str) -> bool:
        """Check if a string is an IP (IPv4 or IPv6)."""
        # IPv4
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', addr):
            return True
        # IPv6 (simplified pattern)
        if re.match(r'^[0-9a-fA-F:]+$', addr) and '::' in addr or addr.count(':') >= 2:
            return True
        return False

    def run_traceroute_fallback(self, target: str, max_hops: int = 15) -> List[str]:
        """
        Fallback on classic traceroute if MTR fails.
        """
        hostnames = []
        
        try:
            # Try traceroute on Unix/Linux/macOS
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
                # Fallback on tracert Windows
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
            logging.debug(f"Traceroute fallback failure to {target}")
        
        return hostnames
    
    def run_traceroute(self, target: str, max_hops: int = 15) -> List[str]:
        """
        Execute a traceroute to target.
        
        Args:
            target: Target IP or domain name
            max_hops: Maximum number of hops
            
        Returns:
            List of hostnames encountered in the traceroute
        """
        hostnames = []
        
        try:
            # Try traceroute on Unix/Linux/macOS
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
                # Fallback on tracert Windows
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
            logging.debug(f"Traceroute failure to {target}")
        
        return hostnames
    
    def _parse_traceroute_unix(self, output: str) -> List[str]:
        """Parse the output of a Unix/Linux/macOS traceroute."""
        hostnames = []
        
        for line in output.split('\n'):
            if line.strip():
                # Search for hostnames in each line
                # Typical format: " 3  router.example.com (1.2.3.4)  10.123 ms"
                hostname_match = re.search(r'\s+\d+\s+([a-zA-Z0-9\-\.]+)\s+\(', line)
                if hostname_match:
                    hostname = hostname_match.group(1)
                    if hostname != '*' and '.' in hostname:
                        hostnames.append(hostname.lower())
        
        return hostnames
    
    def _parse_traceroute_windows(self, output: str) -> List[str]:
        """Parse the output of a tracert Windows."""
        hostnames = []
        
        for line in output.split('\n'):
            if line.strip() and re.match(r'\s*\d+', line):
                # Typical format: "  3    10 ms     9 ms    10 ms  router.example.com [1.2.3.4]"
                hostname_match = re.search(r'\s+([a-zA-Z0-9\-\.]+)\s+\[', line)
                if hostname_match:
                    hostname = hostname_match.group(1)
                    if hostname != '*' and '.' in hostname:
                        hostnames.append(hostname.lower())
        
        return hostnames
    
    def _analyze_ip_ranges(self, hostnames: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Analyze IP ranges for identifying provider and region.
        Useful for Cloudflare and Akamai which use a lot of direct IPs.
        """
        for hostname_or_ip in hostnames:
            # Cloudflare IPv6 ranges
            if hostname_or_ip.startswith('2606:4700'):
                logging.info(f"DEBUG: Cloudflare IPv6 detected: {hostname_or_ip}")
                
                # Analyze IPv6 patterns to deduce region
                # Cloudflare IPs sometimes contain geographical indices
                
                # Pattern 2606:4700:10::6816:xxxx often Europe (CDG/AMS/LHR)
                if '2606:4700:10::' in hostname_or_ip:
                    # Heuristic based on last octets
                    last_part = hostname_or_ip.split(':')[-1]
                    try:
                        last_int = int(last_part, 16)
                        # These patterns are empirical and may need adjustments
                        if 0x1400 <= last_int <= 0x14ff:  # 1400-14ff range often CDG
                            return 'cloudflare', 'cdg'
                        elif 0x1500 <= last_int <= 0x15ff:  # 1500-15ff range often AMS
                            return 'cloudflare', 'ams'
                        elif 0x1600 <= last_int <= 0x16ff:  # 1600-16ff range often LHR
                            return 'cloudflare', 'lhr'
                    except ValueError:
                        pass
                    return 'cloudflare', 'cdg'  # Default Europe
                
                # Pattern 2606:4700::68xx:xxxx often US/Global
                elif '2606:4700::68' in hostname_or_ip:
                    last_part = hostname_or_ip.split(':')[-1]
                    try:
                        last_int = int(last_part, 16)
                        if 0x8500 <= last_int <= 0x85ff:  # 85xx range often IAD
                            return 'cloudflare', 'iad'
                        elif 0x8600 <= last_int <= 0x86ff:  # 86xx range often LAX
                            return 'cloudflare', 'lax'
                    except ValueError:
                        pass
                    return 'cloudflare', 'iad'  # Default US East
                
                # Other patterns
                return 'cloudflare', None
            
            # Cloudflare IPv4 ranges
            if any(hostname_or_ip.startswith(prefix) for prefix in ['104.16.', '104.17.', '104.18.', '104.19.', '104.20.', '104.21.', '104.22.', '104.23.', '104.24.', '104.25.', '104.26.', '104.27.', '104.28.', '104.29.', '104.30.', '104.31.', '172.64.', '172.65.', '172.66.', '172.67.']):
                logging.info(f"DEBUG: Cloudflare IPv4 detected: {hostname_or_ip}")
                return 'cloudflare', None
            
            # Akamai patterns in IPs or hostnames
            if 'akamaitechnologies.com' in hostname_or_ip or 'akamaiedge.net' in hostname_or_ip:
                logging.info(f"DEBUG: Akamai detected: {hostname_or_ip}")
                # Search for region codes in hostname
                if re.search(r'\.([a-z]{3})\d*\.', hostname_or_ip):
                    region_match = re.search(r'\.([a-z]{3})\d*\.', hostname_or_ip)
                    region_code = region_match.group(1)
                    if region_code in ['ams', 'fra', 'lhr', 'cdg', 'sin', 'nrt', 'lax', 'ord', 'sea', 'dfw', 'atl', 'bos', 'mia', 'syd']:
                        return 'akamai', region_code
                return 'akamai', None
            
            # Akamai IPv6 patterns - improvement for linode.com
            if hostname_or_ip.startswith('2a02:26f0:'):
                logging.info(f"DEBUG: Akamai IPv6 detected: {hostname_or_ip}")
                # Pattern 2a02:26f0:2b80 often Europe
                if '2a02:26f0:2b80:' in hostname_or_ip:
                    return 'akamai', 'ams'  # Default Amsterdam for Europe
                return 'akamai', None
        
        return None, None

    def detect_provider_and_region(self, hostnames: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect provider and region based on hostnames.
        
        Args:
            hostnames: List of hostnames from traceroute
            
        Returns:
            Tuple (provider, region) or (None, None) if not detected
        """
        logging.info(f"DEBUG: Analyzing {len(hostnames)} hostnames: {hostnames[:5]}")
        
        # Check each hostname against patterns
        for hostname in hostnames:
            hostname_lower = hostname.lower()
            
            # Identify provider first
            provider = self._identify_provider(hostname_lower)
            logging.info(f"DEBUG: Hostname '{hostname_lower}' -> provider: {provider}")
            if provider:
                # Search for region for this provider
                region = self._identify_region(hostname_lower, provider)
                logging.info(f"DEBUG: Hostname '{hostname_lower}' -> region: {region}")
                if region:
                    return provider, region
        
        # If not found by hostnames, try IP analysis
        logging.info(f"DEBUG: IP ranges analysis for {len(hostnames)} entries")
        provider, region = self._analyze_ip_ranges(hostnames)
        if provider:
            logging.info(f"DEBUG: IP ranges -> provider: {provider}, region: {region}")
            return provider, region
        
        return None, None
    
    def _identify_provider(self, hostname: str) -> Optional[str]:
        """Identify provider based on hostname."""
        provider_indicators = {
            'aws': ['amazonaws.com', 'aws.com', 'ec2', 'cloudfront', 'amazon.com'],
            'gcp': ['googleapis.com', 'google.com', 'gcp', 'googlers.com', '1e100.net', 'googleusercontent.com'],
            'azure': ['azure.com', 'microsoft.com', 'azureedge.net', 'msft.net'],
            'ovh': ['ovh.net', 'ovh.com', 'kimsufi.com', 'soyoustart.com', 'ovh.fr', '.fr.eu', 'gra-g', 'rbx-', 'sbg-', 'bhs-', 'be102.gra-g', 'be103.gra-g', 'be104.gra-g', 'gra-g1-nc', 'gra-g2-nc', 'gra-g3-nc', 'rbx-g1-nc', 'be103.lil', 'be102.lil', 'be104.lil', 'lil1-rbx', 'lil1-gra', 'lil1-sbg', 'lil1-bhs', '-sbb1-nc', '-sbb2-nc'],
            'cloudflare': ['cloudflare.com', 'cloudflare.net', 'cf-dns.com', '2606:4700', '172.64.', '172.65.', '172.66.', '172.67.', '104.16.', '104.17.', '104.18.', '104.19.', '104.20.', '104.21.', '104.22.', '104.23.', '104.24.', '104.25.', '104.26.', '104.27.', '104.28.', '104.29.', '104.30.', '104.31.'],
            'akamai': ['akamai.com', 'akamai.net', 'akamaitechnologies.com', 'akam.net', 'akamaiedge.net', 'akamai-staging.net', 'deploy.static.akamaitechnologies.com', 'deploy.akamaitechnologies.com', 'g2a02-26f0', 'a248.e.akamai.net', 'e.akamai.net'],
            'hetzner': ['hetzner.de', 'hetzner.com', 'your-server.de'],
            'digitalocean': ['digitalocean.com', 'do.co', 'nyc.co'],
            'github': ['github.com', 'github.io', 'githubassets.com', 'githubusercontent.com']
        }
        
        for provider, indicators in provider_indicators.items():
            for indicator in indicators:
                if indicator in hostname:
                    logging.debug(f"DEBUG: Provider '{provider}' détecté via pattern '{indicator}' dans '{hostname}'")
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
        
        # Méthode 1: Géolocalisation IP (plus fiable pour les providers)
        provider_geo, region_geo = self.detect_via_ip_geolocation(target)
        logging.info(f"DEBUG REGION: Géolocalisation pour {target}: provider={provider_geo}, region={region_geo}")
        
        # Méthode 2: Analyse des plages IP pour providers spéciaux (Cloudflare, Akamai)
        # Faire cette analyse tôt pour les IPs directs
        provider_ip, region_ip = self._analyze_ip_ranges([target])
        logging.info(f"DEBUG REGION: Analyse IP pour {target}: provider={provider_ip}, region={region_ip}")
        
        # Si on a trouvé une région via IP ranges, privilégier cela
        if provider_ip and region_ip:
            logging.info(f"DEBUG REGION: Succès IP ranges pour {target}: {provider_ip}->{region_ip}")
            return provider_ip, region_ip, []
        
        # Si géolocalisation a trouvé provider ET région, l'utiliser
        if provider_geo and region_geo:
            logging.info(f"DEBUG REGION: Succès géolocalisation pour {target}: {provider_geo}->{region_geo}")
            return provider_geo, region_geo, []
        
        # Méthode 3: MTR (My Traceroute) - plus précis que traceroute classique
        # PRIORITAIRE pour OVH/Cloudflare/Akamai même si géolocalisation a trouvé le provider sans région
        logging.info(f"DEBUG REGION: Tentative MTR pour {target}")
        hostnames = self.run_mtr(target)
        logging.info(f"DEBUG REGION: MTR pour {target}: {len(hostnames)} hostnames trouvés: {hostnames[:3]}")
        
        if hostnames:
            provider_tr, region_tr = self.detect_provider_and_region(hostnames)
            logging.info(f"DEBUG REGION: Analyse hostnames pour {target}: provider={provider_tr}, region={region_tr}")
            if provider_tr and region_tr:
                logging.info(f"DEBUG REGION: Succès MTR pour {target}: {provider_tr}->{region_tr}")
                return provider_tr, region_tr, hostnames
            
            # Essayer l'analyse IP ranges sur les hostnames trouvés
            provider_ip_hostnames, region_ip_hostnames = self._analyze_ip_ranges(hostnames)
            if provider_ip_hostnames and region_ip_hostnames:
                logging.info(f"DEBUG REGION: Succès IP ranges hostnames pour {target}: {provider_ip_hostnames}->{region_ip_hostnames}")
                return provider_ip_hostnames, region_ip_hostnames, hostnames
        
        # Retourner ce qu'on a trouvé via géolocalisation ou IP ranges même sans région
        if provider_ip:
            logging.info(f"DEBUG REGION: Provider IP final pour {target}: {provider_ip}")
            return provider_ip, region_ip, hostnames
        elif provider_geo:
            logging.info(f"DEBUG REGION: Provider géo final pour {target}: {provider_geo}")
            return provider_geo, region_geo, hostnames
        
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