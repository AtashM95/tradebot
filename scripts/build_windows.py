from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def build() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "src" / "ui"
    data_sep = ";" if os.name == "nt" else ":"
    add_data = f"{ui_dir}{data_sep}src/ui"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name",
        "ultimate_trading_bot_v2",
        "--add-data",
        add_data,
        str(root / "src" / "app" / "main.py"),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    build()
