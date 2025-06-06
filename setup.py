#!/usr/bin/env python3
"""
Configuration for Douro package installation.
"""

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="douro",
    version="0.1.0",
    description="Douro - Web hosting infrastructure analyzer with Prometheus metrics export",
    author="Baptiste",
    author_email="baptiste@example.com",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'douro-analyzer=douro.douro_analyzer:main',
            'douro-exporter=douro.douro_exporter:main',
            'douro-config-validator=douro.config_validator:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
) 