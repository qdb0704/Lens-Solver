from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract a wheel into a target directory without pip.")
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--target", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wheel_path = Path(args.wheel).resolve()
    target_path = Path(args.target).resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel_path) as archive:
        archive.extractall(target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
