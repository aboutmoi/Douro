"""
Module principal d'analyse d'hébergement de sites web pour Douro.
Fournit les fonctions de base pour l'analyse DNS, WHOIS, HTTP et TLS.
"""

import time
import socket
import ssl
import json
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
import datetime
import logging

import dns.resolver
import whois
from ipwhois import IPWhois
import requests

try:
    from .region_detector import RegionDetector
except ImportError:
    # Fallback si le module n'est pas disponible
    RegionDetector = None


@dataclass
class DomainInfo:
    """Classe stockant les informations d'analyse d'un domaine."""
    domain: str
    dns_resolve_duration: float = 0.0
    ip_addresses: List[str] = field(default_factory=list)
    ns_records: List[str] = field(default_factory=list)
    registrar: Optional[str] = None
    expiration_date: Optional[datetime.datetime] = None
    asn: Optional[str] = None
    asn_org: Optional[str] = None
    country: Optional[str] = None
    hosting_provider: Optional[str] = None
    hosting_region: Optional[str] = None
    http_status: int = 0
    server_header: Optional[str] = None
    tls_expiration: Optional[datetime.datetime] = None
    cdn_detected: bool = False
    error: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire."""
        result = asdict(self)
        # Convertir les objets datetime en timestamps Unix
        if self.expiration_date:
            result['expiration_timestamp'] = self.expiration_date.timestamp()
        if self.tls_expiration:
            result['tls_expiration_timestamp'] = self.tls_expiration.timestamp()
        return result
    
    def to_json(self) -> str:
        """Convertit l'objet en chaîne JSON."""
        data = self.to_dict()
        # Convertir les datetime en chaînes ISO pour JSON
        if self.expiration_date:
            data['expiration_date'] = self.expiration_date.isoformat()
        if self.tls_expiration:
            data['tls_expiration'] = self.tls_expiration.isoformat()
        # Supprimer les objets datetime qui ne sont pas sérialisables
        data.pop('expiration_date', None)
        data.pop('tls_expiration', None)
        return json.dumps(data, indent=2)


def resolve_dns(domain: str) -> Tuple[float, List[str], List[str]]:
    """
    Résout les enregistrements DNS pour un domaine.
    
    Args:
        domain: Le nom de domaine à résoudre
        
    Returns:
        Tuple contenant:
        - La durée de résolution en secondes
        - La liste des adresses IP (A et AAAA)
        - La liste des serveurs de noms (NS)
    """
    start_time = time.time()
    ip_addresses = []
    ns_records = []
    
    # Tenter de résoudre les enregistrements A
    try:
        a_records = dns.resolver.resolve(domain, 'A', lifetime=5)
        for record in a_records:
            ip_addresses.append(str(record))
    except dns.exception.DNSException:
        pass
    
    # Si aucun enregistrement A, tenter AAAA
    if not ip_addresses:
        try:
            aaaa_records = dns.resolver.resolve(domain, 'AAAA', lifetime=5)
            for record in aaaa_records:
                ip_addresses.append(str(record))
        except dns.exception.DNSException:
            pass
    
    # Résoudre les enregistrements NS
    try:
        ns_results = dns.resolver.resolve(domain, 'NS', lifetime=5)
        for record in ns_results:
            ns_records.append(str(record).rstrip('.'))
    except dns.exception.DNSException:
        pass
    
    duration = time.time() - start_time
    return duration, ip_addresses, ns_records


def get_whois_info(domain: str) -> Tuple[Optional[str], Optional[datetime.datetime]]:
    """
    Récupère les informations WHOIS pour un domaine.
    
    Args:
        domain: Le nom de domaine à interroger
        
    Returns:
        Tuple contenant:
        - Le registrar
        - La date d'expiration du domaine
    """
    try:
        w = whois.whois(domain)
        
        # Gérer les dates d'expiration multiples ou uniques
        expiration_date = None
        if isinstance(w.expiration_date, list):
            if w.expiration_date:
                expiration_date = w.expiration_date[0]
        else:
            expiration_date = w.expiration_date
            
        return w.registrar, expiration_date
    except Exception:
        return None, None


def get_ip_whois(ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Récupère les informations WHOIS/RDAP pour une adresse IP.
    
    Args:
        ip: L'adresse IP à interroger
        
    Returns:
        Tuple contenant:
        - Le numéro ASN
        - L'organisation associée à l'ASN
        - Le pays
    """
    try:
        obj = IPWhois(ip)
        
        # Essayer d'abord RDAP
        try:
            results = obj.lookup_rdap()
        except Exception:
            # Si RDAP échoue, essayer whois classique
            try:
                results = obj.lookup_whois()
            except Exception:
                return None, None, None
        
        asn = results.get('asn')
        asn_org = results.get('asn_description')
        country = None
        
        # Essayer différentes sources pour le pays
        # 1. Depuis network.country
        if 'network' in results and 'country' in results['network']:
            country = results['network']['country']
        
        # 2. Si pas de pays dans network, essayer dans objects
        if not country and 'objects' in results:
            for obj_key, obj_data in results['objects'].items():
                if isinstance(obj_data, dict) and 'contact' in obj_data:
                    contact = obj_data['contact']
                    if isinstance(contact, dict) and 'address' in contact:
                        address = contact['address']
                        if isinstance(address, list):
                            for addr_item in address:
                                if isinstance(addr_item, dict) and 'value' in addr_item:
                                    # Chercher un code de pays (2 lettres majuscules)
                                    value = addr_item['value']
                                    if isinstance(value, str):
                                        # Chercher code pays à la fin de l'adresse
                                        country_match = re.search(r'\b([A-Z]{2})\b\s*$', value)
                                        if country_match:
                                            country = country_match.group(1)
                                            break
                                if country:
                                    break
                    if country:
                        break
        
        # 3. Si toujours pas de pays, essayer dans les réseaux parents
        if not country and 'network' in results and 'parent_handle' in results['network']:
            parent_handle = results['network']['parent_handle']
            if parent_handle and 'objects' in results and parent_handle in results['objects']:
                parent_obj = results['objects'][parent_handle]
                if isinstance(parent_obj, dict) and 'contact' in parent_obj:
                    # Chercher dans les contacts du parent
                    contact = parent_obj['contact']
                    if isinstance(contact, dict) and 'address' in contact:
                        address = contact['address']
                        if isinstance(address, list):
                            for addr_item in address:
                                if isinstance(addr_item, dict) and 'value' in addr_item:
                                    value = addr_item['value']
                                    if isinstance(value, str):
                                        country_match = re.search(r'\b([A-Z]{2})\b\s*$', value)
                                        if country_match:
                                            country = country_match.group(1)
                                            break
        
        # 4. Déduction basée sur l'organisation
        if not country and asn_org:
            org_lower = asn_org.lower()
            # Mapping des organisations connues vers les pays
            org_country_mapping = {
                'us': ['united states', 'usa', ', us'],
                'gb': ['united kingdom', 'uk', ', gb'],
                'de': ['germany', 'deutschland', ', de'],
                'fr': ['france', ', fr'],
                'nl': ['netherlands', 'holland', ', nl'],
                'ca': ['canada', ', ca'],
                'au': ['australia', ', au'],
                'jp': ['japan', ', jp'],
                'cn': ['china', ', cn'],
                'in': ['india', ', in'],
                'br': ['brazil', ', br'],
                'ru': ['russia', ', ru'],
                'kr': ['korea', ', kr'],
                'sg': ['singapore', ', sg'],
                'it': ['italy', ', it'],
                'es': ['spain', ', es'],
                'ch': ['switzerland', ', ch'],
                'se': ['sweden', ', se'],
                'no': ['norway', ', no'],
                'dk': ['denmark', ', dk'],
                'fi': ['finland', ', fi'],
                'ie': ['ireland', ', ie'],
                'at': ['austria', ', at'],
                'be': ['belgium', ', be'],
                'pt': ['portugal', ', pt'],
                'gr': ['greece', ', gr'],
                'cz': ['czech', ', cz'],
                'pl': ['poland', ', pl'],
                'hu': ['hungary', ', hu'],
                'ro': ['romania', ', ro'],
                'bg': ['bulgaria', ', bg'],
                'hr': ['croatia', ', hr'],
                'si': ['slovenia', ', si'],
                'sk': ['slovakia', ', sk'],
                'lt': ['lithuania', ', lt'],
                'lv': ['latvia', ', lv'],
                'ee': ['estonia', ', ee'],
            }
            
            for country_code, patterns in org_country_mapping.items():
                for pattern in patterns:
                    if pattern in org_lower:
                        country = country_code.upper()
                        break
                if country:
                    break
            
        return asn, asn_org, country
    except Exception:
        return None, None, None


def is_cdn_ip(asn: Optional[str], org: Optional[str]) -> bool:
    """
    Détecte si une adresse IP appartient à un CDN basé sur son ASN/organisation.
    
    Args:
        asn: Le numéro ASN
        org: L'organisation associée à l'ASN
        
    Returns:
        True si l'IP appartient probablement à un CDN
    """
    if not asn or not org:
        return False
        
    cdn_keywords = [
        'cloudflare', 'akamai', 'fastly', 'cdn', 'amazon', 'aws', 
        'microsoft', 'azure', 'google', 'gcp', 'limelight', 'edgecast',
        'stackpath', 'keycdn', 'cloudfront'
    ]
    
    org_lower = org.lower()
    for keyword in cdn_keywords:
        if keyword in org_lower:
            return True
            
    # ASNs connus pour les CDNs
    cdn_asns = [
        '13335',  # Cloudflare
        '16625',  # Akamai
        '54113',  # Fastly
        '16509',  # AWS
        '8075',   # Microsoft
        '15169',  # Google
    ]
    
    return asn in cdn_asns


def check_https(domain: str) -> Tuple[int, Optional[str], Optional[datetime.datetime]]:
    """
    Effectue une requête HTTPS et extrait les informations du certificat TLS.
    
    Args:
        domain: Le domaine à interroger
        
    Returns:
        Tuple contenant:
        - Le code de statut HTTP (0 si erreur)
        - L'en-tête Server (si présent)
        - La date d'expiration du certificat TLS
    """
    try:
        response = requests.get(f'https://{domain}', timeout=10)
        status_code = response.status_code
        server_header = response.headers.get('Server')
        
        # Extraire la date d'expiration du certificat TLS
        hostname = domain
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                not_after = cert.get('notAfter')
                if not_after:
                    # Format: 'May 30 00:00:00 2023 GMT'
                    tls_expiration = datetime.datetime.strptime(
                        not_after, '%b %d %H:%M:%S %Y %Z'
                    )
                    return status_code, server_header, tls_expiration
                return status_code, server_header, None
    except Exception:
        return 0, None, None


def analyze_domain(domain: str) -> DomainInfo:
    """
    Analyse complète d'un domaine.
    
    Args:
        domain: Le domaine à analyser
        
    Returns:
        Un objet DomainInfo contenant toutes les informations d'analyse
    """
    result = DomainInfo(domain=domain)
    
    # Résolution DNS
    try:
        dns_duration, ip_addresses, ns_records = resolve_dns(domain)
        result.dns_resolve_duration = dns_duration
        result.ip_addresses = ip_addresses
        result.ns_records = ns_records
    except Exception as e:
        result.error['dns'] = str(e)
    
    # Si pas d'IP, on ne peut pas continuer certaines analyses
    if not result.ip_addresses:
        return result
    
    # WHOIS domaine
    try:
        registrar, expiration_date = get_whois_info(domain)
        result.registrar = registrar
        result.expiration_date = expiration_date
    except Exception as e:
        result.error['whois_domain'] = str(e)
    
    # WHOIS/RDAP IP (première IP seulement)
    try:
        ip = result.ip_addresses[0]
        asn, asn_org, country = get_ip_whois(ip)
        result.asn = asn
        result.asn_org = asn_org
        result.country = country
        
        # Détection CDN
        result.cdn_detected = is_cdn_ip(asn, asn_org)
        
        # Détection de région d'hébergement via traceroute
        try:
            if RegionDetector:
                logging.info(f"DEBUG: Détection région pour {ip} (domaine: {domain})")
                detector = RegionDetector()
                hosting_provider, hosting_region, hostnames = detector.detect_hosting_region(ip)
                logging.info(f"DEBUG: Résultat pour {domain}: provider={hosting_provider}, region={hosting_region}, hostnames={len(hostnames) if hostnames else 0}")
                result.hosting_provider = hosting_provider
                result.hosting_region = hosting_region
            else:
                logging.warning(f"DEBUG: RegionDetector est None pour {domain}")
                result.hosting_provider = None
                result.hosting_region = None
        except Exception as e:
            logging.error(f"DEBUG: Exception région pour {domain}: {e}")
            result.error['region_detection'] = str(e)
            
    except Exception as e:
        result.error['whois_ip'] = str(e)
    
    # Vérification HTTPS
    try:
        status_code, server_header, tls_expiration = check_https(domain)
        result.http_status = status_code
        result.server_header = server_header
        result.tls_expiration = tls_expiration
    except Exception as e:
        result.error['https'] = str(e)
    
    return result


def analyze_domains(domains: List[str]) -> List[DomainInfo]:
    """
    Analyse une liste de domaines.
    
    Args:
        domains: Liste des domaines à analyser
        
    Returns:
        Liste d'objets DomainInfo
    """
    results = []
    for domain in domains:
        results.append(analyze_domain(domain))
    return results 