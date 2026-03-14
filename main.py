#!/usr/bin/env python3
"""
メルカリ自動運営ツール v1.0
- 批量上架
- 自动调价
- 自动回复
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import main

if __name__ == "__main__":
    main()
