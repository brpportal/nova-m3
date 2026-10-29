#!/usr/bin/env python3
"""NOVA M3 launcher — run as: python3 nova.py <command> (or ./nova)."""
import sys

from nova.cli import main

if __name__ == "__main__":
    sys.exit(main())
