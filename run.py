"""启动脚本：从项目根目录运行。

    python run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.main import run

if __name__ == "__main__":
    run()