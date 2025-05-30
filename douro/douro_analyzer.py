#!/usr/bin/env python3
"""
Douro CLI script for analyzing hosting of one or more websites.

Usage:
    python -m douro.douro_analyzer example.com
    python -m douro.douro_analyzer example.com wikipedia.org
    python -m douro.douro_analyzer --config config.json

Performs complete analysis of domains including DNS, WHOIS, hosting detection, etc.
"""

import argparse
import json
import sys
import logging
from typing import List, TextIO

from douro.core.analyzer import analyze_domains


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_domains_from_file(filepath: str) -> List[str]:
    """
    Load domains from a text file (one domain per line).
    
    Args:
        filepath: Path to file containing domains
        
    Returns:
        List of domains
    """
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip()
                if domain and not domain.startswith('#'):  # Ignore empty lines and comments
                    domains.append(domain)
    except IOError as e:
        logging.error(f"Cannot read domains file {filepath}: {e}")
        sys.exit(1)
    
    return domains


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Douro - Analyze web hosting infrastructure.'
    )
    
    # Mutually exclusive group for domains
    domain_group = parser.add_mutually_exclusive_group(required=True)
    domain_group.add_argument(
        'domains',
        nargs='*',
        help='List of domains to analyze'
    )
    domain_group.add_argument(
        '--domains-file',
        type=str,
        help='File containing domains to analyze (one per line)'
    )
    
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='JSON output format'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose mode (detailed logs)'
    )
    
    return parser.parse_args()


def output_text(domains_info: List, file: TextIO = sys.stdout) -> None:
    """Display results in text format."""
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
    """Display results in JSON format."""
    results = [info.to_dict() for info in domains_info]
    json.dump(results, file, indent=2)
    file.write("\n")


def main() -> int:
    """Main function."""
    args = parse_args()
    setup_logging(args.verbose)
    
    # Determine domain list
    if args.domains_file:
        domains = load_domains_from_file(args.domains_file)
        logging.debug(f"Douro - Domains loaded from {args.domains_file}: {len(domains)} domains")
    else:
        domains = args.domains
        logging.debug(f"Douro - Domains from arguments: {domains}")
    
    if not domains:
        logging.error("No domains to analyze")
        return 1
    
    logging.debug(f"Douro - Analyzing domains: {domains}")
    domains_info = analyze_domains(domains)
    
    # Open output file if specified
    output_file = sys.stdout
    if args.output:
        try:
            output_file = open(args.output, 'w', encoding='utf-8')
        except IOError as e:
            logging.error(f"Cannot open output file: {e}")
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