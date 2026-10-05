"""
Seed test data for local development.

Run from the repository root:
    python scripts/seed_test_data.py

The script is idempotent: it updates existing seed rows by stable keys
instead of inserting duplicates.
"""

import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.seed_data.runner import seed


if __name__ == "__main__":
    asyncio.run(seed())
