#!/usr/bin/env python3
"""
Script CLI Douro pour analyser l'hébergement d'un ou plusieurs sites web.

Usage:
    douro_analyzer.py [-j] [-o FILE] [-v] domaine [domaine ...]
    douro_analyzer.py [-j] [-o FILE] [-v] --domains-file FILE
    -j, --json       sortie JSON
    -o, --output     écrire dans FILE
    -v, --verbose    traces stderr
    --domains-file   lire les domaines depuis un fichier (un par ligne)
"""

import argparse
import json
import sys
import logging
from typing import List, TextIO

from douro.core.analyzer import analyze_domains


def setup_logging(verbose: bool = False) -> None:
    """Configure le logging."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_domains_from_file(filepath: str) -> List[str]:
    """
    Charge les domaines depuis un fichier texte (un domaine par ligne).
    
    Args:
        filepath: Chemin vers le fichier contenant les domaines
        
    Returns:
        Liste des domaines
    """
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip()
                if domain and not domain.startswith('#'):  # Ignorer les lignes vides et commentaires
                    domains.append(domain)
    except IOError as e:
        logging.error(f"Impossible de lire le fichier de domaines {filepath}: {e}")
        sys.exit(1)
    
    return domains


def parse_args() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description='Douro - Analyse l\'hébergement de sites web.'
    )
    
    # Groupe mutuellement exclusif pour les domaines
    domain_group = parser.add_mutually_exclusive_group(required=True)
    domain_group.add_argument(
        'domains',
        nargs='*',
        help='Liste des domaines à analyser'
    )
    domain_group.add_argument(
        '--domains-file',
        type=str,
        help='Fichier contenant les domaines à analyser (un par ligne)'
    )
    
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Sortie au format JSON'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Fichier de sortie (par défaut: stdout)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mode verbeux (logs détaillés)'
    )
    
    return parser.parse_args()


def output_text(domains_info: List, file: TextIO = sys.stdout) -> None:
    """Affiche les résultats au format texte."""
    for info in domains_info:
        file.write(f"=== {info.domain} ===\n")
        file.write(f"DNS duration: {info.dns_resolve_duration:.3f}s\n")
        file.write(f"IP addresses: {', '.join(info.ip_addresses)}\n")
        file.write(f"NS records: {', '.join(info.ns_records)}\n")
        
        if info.registrar:
            file.write(f"Registrar: {info.registrar}\n")
        
        if info.expiration_date:
            file.write(f"Domain expiration: {info.expiration_date.isoformat()}\n")
        
        if info.asn:
            file.write(f"ASN: {info.asn} ({info.asn_org or 'unknown'})\n")
        
        if info.country:
            file.write(f"Country: {info.country}\n")
        
        file.write(f"CDN detected: {info.cdn_detected}\n")
        file.write(f"HTTP status: {info.http_status}\n")
        
        if info.server_header:
            file.write(f"Server: {info.server_header}\n")
        
        if info.tls_expiration:
            file.write(f"TLS expiration: {info.tls_expiration.isoformat()}\n")
        
        if info.error:
            file.write("Errors:\n")
            for stage, error in info.error.items():
                file.write(f"  - {stage}: {error}\n")
        
        file.write("\n")


def output_json(domains_info: List, file: TextIO = sys.stdout) -> None:
    """Affiche les résultats au format JSON."""
    results = [info.to_dict() for info in domains_info]
    json.dump(results, file, indent=2)
    file.write("\n")


def main() -> int:
    """Fonction principale."""
    args = parse_args()
    setup_logging(args.verbose)
    
    # Déterminer la liste des domaines
    if args.domains_file:
        domains = load_domains_from_file(args.domains_file)
        logging.debug(f"Douro - Domaines chargés depuis {args.domains_file}: {len(domains)} domaines")
    else:
        domains = args.domains
        logging.debug(f"Douro - Domaines en arguments: {domains}")
    
    if not domains:
        logging.error("Aucun domaine à analyser")
        return 1
    
    logging.debug(f"Douro - Analyse des domaines: {domains}")
    domains_info = analyze_domains(domains)
    
    # Ouvrir le fichier de sortie si spécifié
    output_file = sys.stdout
    if args.output:
        try:
            output_file = open(args.output, 'w', encoding='utf-8')
        except IOError as e:
            logging.error(f"Impossible d'ouvrir le fichier de sortie: {e}")
            return 1
    
    try:
        if args.json:
            output_json(domains_info, output_file)
        else:
            output_text(domains_info, output_file)
    finally:
        if output_file is not sys.stdout:
            output_file.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 