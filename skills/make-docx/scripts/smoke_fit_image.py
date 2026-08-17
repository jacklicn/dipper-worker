#!/usr/bin/env python3
"""Smoke fit_image.py with a tiny generated PNG (shared by docx/pptx/pdf skills)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow missing; skip fit_image smoke", file=sys.stderr)
        return 0

    fit = SCRIPT_DIR / "fit_image.py"
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "probe.png"
        Image.new("RGB", (800, 450), color=(47, 93, 80)).save(png)
        proc = subprocess.run(
            [
                sys.executable,
                str(fit),
                str(png),
                "--max-w",
                "5.5",
                "--max-h",
                "3.5",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            return proc.returncode
        if '"width"' not in proc.stdout or '"height"' not in proc.stdout:
            print("fit_image smoke: missing width/height in JSON", file=sys.stderr)
            return 1
    print("fit_image smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
