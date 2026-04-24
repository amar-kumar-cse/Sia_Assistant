"""Setup utility: install rembg and generate transparent Sia avatar."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def ensure_rembg() -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rembg"])


def remove_background(input_path: Path, output_path: Path) -> None:
    from rembg import remove

    input_data = input_path.read_bytes()
    output_data = remove(input_data)
    output_path.write_bytes(output_data)


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "assets" / "sia_idle.png"
    dst = root / "assets" / "sia_idle_transparent.png"

    if not src.exists():
        print(f"Input image not found: {src}")
        return 1

    try:
        ensure_rembg()
        remove_background(src, dst)
    except Exception as exc:
        print(f"Setup failed: {exc}")
        return 1

    print(f"Done. Transparent avatar created: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
