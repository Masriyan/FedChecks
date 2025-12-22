#!/usr/bin/env python3
"""
FedChecker Launcher
Fedora Linux Health & Setup Tool by sudo3rs

Run this script to start FedChecker:
    python run.py
    or
    ./run.py
"""

import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fedchecker.main import main

if __name__ == "__main__":
    main()
