from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

def do_unpack(source: Path, output: Path) -> None:
    import subprocess
    print(f"Unpacking {source} -> {output}")
    result = subprocess.run([
        sys.executable, str(Path(__file__).parent / "converter.py"),
        "unpack", str(source), str(output)
    ])
    if result.returncode == 0:
        print("Unpack complete")
    else:
        print("Unpack failed")


def get_dir_mtime(directory: Path) -> float:
    """Get the most recent modification time of any file in the directory (recursively)."""
    mtimes = [f.stat().st_mtime for f in directory.rglob("*") if f.is_file()]
    if not mtimes:
        return 0.0
    return max(mtimes)

def watch(packed_file: Path, unpacked_dir: Path, interval: float = 1.0, debounce: float = 0.5) -> None:
    running = True

    def _handle(sig, frame):
        nonlocal running
        print(f"Stopping watcher (signal {sig})")
        running = False

    signal.signal(signal.SIGINT, _handle)
    try:
        signal.signal(signal.SIGTERM, _handle)
    except Exception:
        pass

    last_packed_mtime = packed_file.stat().st_mtime if packed_file.exists() else 0.0
    last_unpacked_mtime = get_dir_mtime(unpacked_dir) if unpacked_dir.exists() else 0.0

    # Initial sync: apply the newer version
    if last_packed_mtime > last_unpacked_mtime:
        do_unpack(packed_file, unpacked_dir)
        last_unpacked_mtime = get_dir_mtime(unpacked_dir)
    elif last_unpacked_mtime > last_packed_mtime:
        do_pack(packed_file, unpacked_dir)
        last_packed_mtime = packed_file.stat().st_mtime if packed_file.exists() else 0.0

    while running:
        time.sleep(interval)
        packed_exists = packed_file.exists()
        unpacked_exists = unpacked_dir.exists()
        packed_mtime = packed_file.stat().st_mtime if packed_exists else 0.0
        unpacked_mtime = get_dir_mtime(unpacked_dir) if unpacked_exists else 0.0

        # If packed file changed
        if packed_mtime > last_packed_mtime and packed_mtime >= unpacked_mtime:
            time.sleep(debounce)
            # Recheck after debounce
            packed_mtime2 = packed_file.stat().st_mtime if packed_file.exists() else 0.0
            if packed_mtime2 == packed_mtime:
                do_unpack(packed_file, unpacked_dir)
                last_unpacked_mtime = get_dir_mtime(unpacked_dir)
                last_packed_mtime = packed_mtime2
                continue

        # If unpacked dir changed
        if unpacked_mtime > last_unpacked_mtime and unpacked_mtime > packed_mtime:
            time.sleep(debounce)
            unpacked_mtime2 = get_dir_mtime(unpacked_dir) if unpacked_dir.exists() else 0.0
            if unpacked_mtime2 == unpacked_mtime:
                do_pack(packed_file, unpacked_dir)
                last_packed_mtime = packed_file.stat().st_mtime if packed_file.exists() else 0.0
                last_unpacked_mtime = unpacked_mtime2

def do_pack(packed_file: Path, unpacked_dir: Path) -> None:
    import subprocess
    print(f"Packing {unpacked_dir} -> {packed_file}")
    result = subprocess.run([
        sys.executable, str(Path(__file__).parent / "converter.py"),
        "pack", str(packed_file), str(unpacked_dir)
    ])
    if result.returncode == 0:
        print("Pack complete")
    else:
        print("Pack failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch and sync packed and unpacked PM files, always applying the newer version.")
    parser.add_argument("packed_file", nargs="?", default="input.pmp", help="Path to the packed PM file")
    parser.add_argument("unpacked_dir", nargs="?", default="output", help="Path to the unpacked directory")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds")
    parser.add_argument("--debounce", type=float, default=0.5, help="Debounce time after change (seconds)")
    args = parser.parse_args(argv)

    packed_file = Path(args.packed_file)
    unpacked_dir = Path(args.unpacked_dir)

    print(f"Watching {packed_file} and {unpacked_dir} (interval={args.interval}s, debounce={args.debounce}s)")
    watch(packed_file, unpacked_dir, interval=args.interval, debounce=args.debounce)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
