#!/usr/bin/env python3
"""
FedChecker Setup Script
Fedora Linux Health & Setup Tool by sudo3rs
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README if it exists
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="fedchecker",
    version="1.0.0",
    author="sudo3rs",
    author_email="sudo3rs@example.com",
    description="Fedora Linux Health & Setup Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Masriyan/FedChecks",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.11",
    install_requires=[
        "rich>=13.0.0",
        "reportlab>=4.0.0",
        "matplotlib>=3.7.0",
        "psutil>=5.9.0",
        "distro>=1.8.0",
    ],
    entry_points={
        "console_scripts": [
            "fedchecker=fedchecker.main:main",
        ],
    },
    keywords=[
        "fedora",
        "linux",
        "system",
        "health",
        "check",
        "diagnostic",
        "post-install",
        "setup",
    ],
    project_urls={
        "Bug Reports": "https://github.com/Masriyan/FedChecks/issues",
        "Source": "https://github.com/Masriyan/FedChecks",
    },
)
