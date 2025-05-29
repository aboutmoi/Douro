"""
Tests unitaires pour le module config.
"""

import json
import pytest
import tempfile
import os
from unittest.mock import patch

from douro.core.config import (
    DouroConfig,
    ExporterConfig,
    MonitoringConfig,
    DomainConfig,
    load_config,
    parse_config,
    save_config
)


class TestDomainConfig:
    """Tests pour DomainConfig."""
    
    def test_default_values(self):
        """Test des valeurs par défaut."""
        domain = DomainConfig(name="example.com")
        assert domain.name == "example.com"
        assert domain.enabled is True
        assert domain.description == ""
    
    def test_custom_values(self):
        """Test avec des valeurs personnalisées."""
        domain = DomainConfig(
            name="test.com",
            enabled=False,
            description="Test domain"
        )
        assert domain.name == "test.com"
        assert domain.enabled is False
        assert domain.description == "Test domain"


class TestExporterConfig:
    """Tests pour ExporterConfig."""
    
    def test_default_values(self):
        """Test des valeurs par défaut."""
        config = ExporterConfig()
        assert config.port == 9105
        assert config.interval_seconds == 300
        assert config.timeout_seconds == 10
    
    def test_custom_values(self):
        """Test avec des valeurs personnalisées."""
        config = ExporterConfig(
            port=8080,
            interval_seconds=600,
            timeout_seconds=30
        )
        assert config.port == 8080
        assert config.interval_seconds == 600
        assert config.timeout_seconds == 30


class TestMonitoringConfig:
    """Tests pour MonitoringConfig."""
    
    def test_default_values(self):
        """Test des valeurs par défaut."""
        config = MonitoringConfig()
        assert config.log_level == "INFO"
        assert config.enable_verbose_logging is False
    
    def test_custom_values(self):
        """Test avec des valeurs personnalisées."""
        config = MonitoringConfig(
            log_level="DEBUG",
            enable_verbose_logging=True
        )
        assert config.log_level == "DEBUG"
        assert config.enable_verbose_logging is True


class TestDouroConfig:
    """Tests pour DouroConfig."""
    
    def test_default_values(self):
        """Test des valeurs par défaut."""
        config = DouroConfig()
        assert isinstance(config.exporter, ExporterConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
        assert config.domains == []
    
    def test_get_enabled_domains(self):
        """Test de get_enabled_domains."""
        domains = [
            DomainConfig(name="enabled1.com", enabled=True),
            DomainConfig(name="disabled.com", enabled=False),
            DomainConfig(name="enabled2.com", enabled=True),
        ]
        config = DouroConfig(domains=domains)
        
        enabled = config.get_enabled_domains()
        assert enabled == ["enabled1.com", "enabled2.com"]
    
    def test_get_domain_count(self):
        """Test de get_domain_count."""
        domains = [
            DomainConfig(name="domain1.com"),
            DomainConfig(name="domain2.com"),
        ]
        config = DouroConfig(domains=domains)
        assert config.get_domain_count() == 2
    
    def test_get_enabled_domain_count(self):
        """Test de get_enabled_domain_count."""
        domains = [
            DomainConfig(name="enabled.com", enabled=True),
            DomainConfig(name="disabled.com", enabled=False),
        ]
        config = DouroConfig(domains=domains)
        assert config.get_enabled_domain_count() == 1


class TestParseConfig:
    """Tests pour parse_config."""
    
    def test_valid_config(self):
        """Test avec une configuration valide."""
        config_data = {
            "exporter": {
                "port": 8080,
                "interval_seconds": 600,
                "timeout_seconds": 30
            },
            "domains": [
                {
                    "name": "example.com",
                    "enabled": True,
                    "description": "Test domain"
                }
            ],
            "monitoring": {
                "log_level": "DEBUG",
                "enable_verbose_logging": True
            }
        }
        
        config = parse_config(config_data)
        
        assert config.exporter.port == 8080
        assert config.exporter.interval_seconds == 600
        assert config.exporter.timeout_seconds == 30
        
        assert len(config.domains) == 1
        assert config.domains[0].name == "example.com"
        assert config.domains[0].enabled is True
        assert config.domains[0].description == "Test domain"
        
        assert config.monitoring.log_level == "DEBUG"
        assert config.monitoring.enable_verbose_logging is True
    
    def test_minimal_config(self):
        """Test avec une configuration minimale."""
        config_data = {
            "domains": [
                {"name": "example.com"}
            ]
        }
        
        config = parse_config(config_data)
        
        # Valeurs par défaut
        assert config.exporter.port == 9105
        assert config.monitoring.log_level == "INFO"
        
        # Domaine avec valeurs par défaut
        assert len(config.domains) == 1
        assert config.domains[0].name == "example.com"
        assert config.domains[0].enabled is True
        assert config.domains[0].description == ""
    
    def test_no_domains(self):
        """Test sans domaines configurés."""
        config_data = {"domains": []}
        
        with pytest.raises(ValueError, match="Au moins un domaine doit être configuré"):
            parse_config(config_data)
    
    def test_invalid_domain_format(self):
        """Test avec un format de domaine invalide."""
        config_data = {
            "domains": ["example.com"]  # String au lieu d'objet
        }
        
        with pytest.raises(ValueError, match="Chaque domaine doit être un objet JSON"):
            parse_config(config_data)
    
    def test_domain_without_name(self):
        """Test avec un domaine sans nom."""
        config_data = {
            "domains": [
                {"enabled": True}  # Pas de champ 'name'
            ]
        }
        
        with pytest.raises(ValueError, match="Chaque domaine doit avoir un champ 'name'"):
            parse_config(config_data)
    
    def test_invalid_port(self):
        """Test avec un port invalide."""
        config_data = {
            "exporter": {"port": 70000},
            "domains": [{"name": "example.com"}]
        }
        
        with pytest.raises(ValueError, match="Le port doit être entre 1 et 65535"):
            parse_config(config_data)
    
    def test_invalid_interval(self):
        """Test avec un intervalle invalide."""
        config_data = {
            "exporter": {"interval_seconds": 10},
            "domains": [{"name": "example.com"}]
        }
        
        with pytest.raises(ValueError, match="L'intervalle doit être d'au moins 30 secondes"):
            parse_config(config_data)
    
    def test_invalid_timeout(self):
        """Test avec un timeout invalide."""
        config_data = {
            "exporter": {"timeout_seconds": 0},
            "domains": [{"name": "example.com"}]
        }
        
        with pytest.raises(ValueError, match="Le timeout doit être d'au moins 1 seconde"):
            parse_config(config_data)
    
    def test_invalid_log_level(self):
        """Test avec un niveau de log invalide."""
        config_data = {
            "monitoring": {"log_level": "INVALID"},
            "domains": [{"name": "example.com"}]
        }
        
        with pytest.raises(ValueError, match="Le niveau de log doit être l'un de"):
            parse_config(config_data)


class TestLoadConfig:
    """Tests pour load_config."""
    
    def test_load_valid_config(self):
        """Test de chargement d'un fichier valide."""
        config_data = {
            "domains": [{"name": "example.com"}]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = load_config(config_path)
            assert len(config.domains) == 1
            assert config.domains[0].name == "example.com"
        finally:
            os.unlink(config_path)
    
    def test_file_not_found(self):
        """Test avec un fichier qui n'existe pas."""
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_file.json")
    
    def test_invalid_json(self):
        """Test avec un JSON invalide."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                load_config(config_path)
        finally:
            os.unlink(config_path)


class TestSaveConfig:
    """Tests pour save_config."""
    
    def test_save_config(self):
        """Test de sauvegarde d'une configuration."""
        config = DouroConfig(
            domains=[
                DomainConfig(name="example.com", enabled=True, description="Test")
            ]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            save_config(config, config_path)
            
            # Recharger et vérifier
            loaded_config = load_config(config_path)
            assert len(loaded_config.domains) == 1
            assert loaded_config.domains[0].name == "example.com"
            assert loaded_config.domains[0].enabled is True
            assert loaded_config.domains[0].description == "Test"
        finally:
            os.unlink(config_path) 