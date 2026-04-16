from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from pm_converter.converter import unpack_project


def do_unpack(source: Path, output: Path) -> None:
    logging.info("Unpacking %s -> %s", source, output)
    try:
        unpack_project(source, output)
        logging.info("Unpack complete")
    except Exception:
        logging.exception("Unpack failed")


def watch(source: Path, output: Path, interval: float = 1.0, debounce: float = 0.5) -> None:
    last_mtime = None
    running = True

    def _handle(sig, frame):
        nonlocal running
        logging.info("Stopping watcher (signal %s)", sig)
        running = False

    signal.signal(signal.SIGINT, _handle)
    try:
        signal.signal(signal.SIGTERM, _handle)
    except Exception:
        # Windows may not have SIGTERM available in the same way
        pass

    while running:
        try:
            stat = source.stat()
        except FileNotFoundError:
            logging.debug("Source %s not found, waiting...", source)
            time.sleep(interval)
            continue

        mtime = stat.st_mtime
        if last_mtime is None:
            # First time seeing the file: run an initial unpack immediately
            do_unpack(source, output)
            last_mtime = mtime
        elif mtime != last_mtime:
            # wait a short debounce period to allow writers to finish
            time.sleep(debounce)
            try:
                new_mtime = source.stat().st_mtime
            except FileNotFoundError:
                logging.debug("Source disappeared after change, skipping")
                last_mtime = None
                time.sleep(interval)
                continue

            if new_mtime == mtime:
                do_unpack(source, output)
                last_mtime = new_mtime
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch a PM input file and unpack on changes")
    parser.add_argument("source_file", nargs="?", default="input.pmp", help="Path to the source save file")
    parser.add_argument("output_dir", nargs="?", default="output", help="Path to the output directory")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds")
    parser.add_argument("--debounce", type=float, default=0.5, help="Debounce time after change (seconds)")
    parser.add_argument("--once", action="store_true", help="Run a single unpack and exit")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    source = Path(args.source_file)
    output = Path(args.output_dir)

    if args.once:
        if not source.exists():
            logging.error("Source file does not exist: %s", source)
            return 2
        do_unpack(source, output)
        return 0

    logging.info("Watching %s (interval=%ss, debounce=%ss)", source, args.interval, args.debounce)
    watch(source, output, interval=args.interval, debounce=args.debounce)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
