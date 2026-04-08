"""
Sia launcher with UTF-8 console setup for Windows.
Routes to the maintained desktop entrypoint.
"""

import os
import sys
import argparse


# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

    # Reconfigure stdout/stderr to use UTF-8 where supported.
    if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure") and sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Use the active desktop entrypoint.
from sia_desktop import main


def _parse_args():
    parser = argparse.ArgumentParser(description="Launch Sia desktop assistant")
    parser.add_argument(
        "--smoke",
        nargs="?",
        const="8",
        metavar="SECONDS",
        help="Run startup smoke check and auto-exit cleanly after N seconds (default: 8)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.smoke is not None:
        os.environ["SIA_SMOKE_SECONDS"] = str(args.smoke)
    main()
