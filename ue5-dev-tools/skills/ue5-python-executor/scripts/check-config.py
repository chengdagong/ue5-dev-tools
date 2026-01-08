#!/usr/bin/env python3
"""
UE5 Project Configuration Check & Fix Tool (Wrapper)
Wraps lib.ue5_remote.config for easy execution.
"""

import sys
from pathlib import Path

# Add lib directory to Python path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

from ue5_remote.config import main

if __name__ == "__main__":
    main()
