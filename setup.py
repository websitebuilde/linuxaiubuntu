#!/usr/bin/env python3
"""
Setup script for AI System Assistant.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="ai-system-assistant",
    version="1.0.0",
    author="AI System Assistant Team",
    author_email="contact@example.com",
    description="Local AI assistant for Ubuntu system management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai-system-assistant/ai-system-assistant",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-assistant=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
    ],
    keywords="ai assistant ubuntu linux system management ollama",
)
