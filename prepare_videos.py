"""Prepare transparent loop videos for Sia using FFmpeg chromakey."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict


def build_cmd(inp: Path, out: Path, color: str = "white") -> list[str]:
    if color.lower() == "green":
        key = "chromakey=0x00FF00:0.16:0.11"
    else:
        key = "chromakey=white:0.10:0.10"

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(inp),
        "-vf",
        key,
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        str(out),
    ]


def convert(input_name: str, output_name: str, color: str = "white") -> int:
    assets = Path(__file__).resolve().parent / "assets"
    inp = assets / input_name
    out = assets / output_name
    if not inp.exists():
        print(f"Missing input: {inp}")
        return 1
    return convert_path(inp, out, color=color)


def convert_path(input_path: Path, output_path: Path, color: str = "white") -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_cmd(input_path, output_path, color=color)
    print(" ".join(cmd))
    return subprocess.call(cmd)


def process_named_sources(source_map: Dict[str, str], color: str = "white") -> Dict[str, int]:
    """Convert named source files into assets outputs.

    source_map should map output basename -> absolute source path.
    Example: {"idle_transparent.webm": "C:/.../idle.mp4"}
    """
    assets = Path(__file__).resolve().parent / "assets"
    results: Dict[str, int] = {}
    for output_name, source_path in source_map.items():
        inp = Path(source_path)
        out = assets / output_name
        if not inp.exists():
            results[output_name] = 1
            continue
        results[output_name] = convert_path(inp, out, color=color)
    return results


def main() -> int:
    jobs = [
        ("idle.mp4", "idle_transparent.webm"),
        ("talking.mp4", "talking_transparent.webm"),
        ("thinking.mp4", "thinking_transparent.webm"),
        ("greeting.mp4", "greeting_transparent.webm"),
    ]

    code = 0
    for src, dst in jobs:
        rc = convert(src, dst, color="white")
        code = code or rc

    if code == 0:
        print("Video preprocessing completed.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
