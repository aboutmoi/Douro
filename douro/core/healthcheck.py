"""
Module de healthcheck pour Douro.
Fournit des endpoints pour vérifier l'état de santé de l'application.
"""

import time
import json
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


@dataclass
class HealthStatus:
    """État de santé de l'application."""
    status: str  # "healthy", "unhealthy", "degraded"
    timestamp: float
    uptime_seconds: float
    version: str = "1.0.0"
    environment: str = "production"
    last_scrape_timestamp: Optional[float] = None
    last_scrape_duration: Optional[float] = None
    last_scrape_errors: int = 0
    total_scrapes: int = 0
    total_errors: int = 0
    enabled_domains_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le status en dictionnaire."""
        return asdict(self)


class HealthMonitor:
    """Moniteur de santé de l'application."""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_scrape_timestamp: Optional[float] = None
        self.last_scrape_duration: Optional[float] = None
        self.last_scrape_errors = 0
        self.total_scrapes = 0
        self.total_errors = 0
        self.enabled_domains_count = 0
        self._lock = threading.Lock()
    
    def update_scrape_metrics(self, duration: float, error_count: int, domains_count: int) -> None:
        """
        Met à jour les métriques de scrape.
        
        Args:
            duration: Durée du dernier scrape en secondes
            error_count: Nombre d'erreurs dans le dernier scrape
            domains_count: Nombre de domaines traités
        """
        with self._lock:
            self.last_scrape_timestamp = time.time()
            self.last_scrape_duration = duration
            self.last_scrape_errors = error_count
            self.total_scrapes += 1
            self.total_errors += error_count
            self.enabled_domains_count = domains_count
    
    def get_status(self) -> HealthStatus:
        """
        Retourne l'état de santé actuel.
        
        Returns:
            HealthStatus avec les métriques actuelles
        """
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Déterminer l'état de santé
        status = "healthy"
        
        # Vérifier si on a eu des scrapes récents (dans les 10 dernières minutes)
        if self.last_scrape_timestamp:
            time_since_last_scrape = current_time - self.last_scrape_timestamp
            if time_since_last_scrape > 600:  # 10 minutes
                status = "unhealthy"
            elif self.last_scrape_errors > 0:
                status = "degraded"
        elif uptime > 300:  # Plus de 5 minutes sans scrape
            status = "unhealthy"
        
        return HealthStatus(
            status=status,
            timestamp=current_time,
            uptime_seconds=uptime,
            last_scrape_timestamp=self.last_scrape_timestamp,
            last_scrape_duration=self.last_scrape_duration,
            last_scrape_errors=self.last_scrape_errors,
            total_scrapes=self.total_scrapes,
            total_errors=self.total_errors,
            enabled_domains_count=self.enabled_domains_count
        )


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour les requêtes de healthcheck."""
    
    def __init__(self, health_monitor: HealthMonitor, *args, **kwargs):
        self.health_monitor = health_monitor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Traite les requêtes GET."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            self._handle_health()
        elif parsed_path.path == '/ready':
            self._handle_ready()
        elif parsed_path.path == '/live':
            self._handle_live()
        else:
            self._send_404()
    
    def _handle_health(self):
        """Endpoint de santé complet."""
        status = self.health_monitor.get_status()
        
        if status.status == "healthy":
            self._send_json_response(200, status.to_dict())
        elif status.status == "degraded":
            self._send_json_response(200, status.to_dict())
        else:
            self._send_json_response(503, status.to_dict())
    
    def _handle_ready(self):
        """Endpoint de readiness (prêt à recevoir du trafic)."""
        status = self.health_monitor.get_status()
        
        # Prêt si l'application a fait au moins un scrape ou est démarrée depuis moins de 5 minutes
        is_ready = (status.last_scrape_timestamp is not None or 
                   status.uptime_seconds < 300)
        
        if is_ready:
            self._send_json_response(200, {"status": "ready", "timestamp": status.timestamp})
        else:
            self._send_json_response(503, {"status": "not_ready", "timestamp": status.timestamp})
    
    def _handle_live(self):
        """Endpoint de liveness (application vivante)."""
        status = self.health_monitor.get_status()
        
        # Vivant si l'application répond (toujours true si on arrive ici)
        self._send_json_response(200, {
            "status": "alive", 
            "timestamp": status.timestamp,
            "uptime_seconds": status.uptime_seconds
        })
    
    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        """Envoie une réponse JSON."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        response = json.dumps(data, indent=2)
        self.wfile.write(response.encode('utf-8'))
    
    def _send_404(self):
        """Envoie une erreur 404."""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Supprime les logs HTTP par défaut."""
        pass


def start_health_server(port: int, health_monitor: HealthMonitor) -> threading.Thread:
    """
    Démarre le serveur de healthcheck dans un thread séparé.
    
    Args:
        port: Port pour le serveur de healthcheck
        health_monitor: Instance du moniteur de santé
        
    Returns:
        Thread du serveur de healthcheck
    """
    def create_handler(*args, **kwargs):
        return HealthCheckHandler(health_monitor, *args, **kwargs)
    
    def run_server():
        server = HTTPServer(('', port), create_handler)
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread 