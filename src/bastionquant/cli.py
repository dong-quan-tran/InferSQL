from __future__ import annotations

import argparse

from bastionquant.ingestion.build_panel import build_panel
from bastionquant.settings import load_config


def main() -> None:
    parser = argparse.ArgumentParser(prog="bastionquant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Download and build the initial market+macro panel.",
    )
    ingest_parser.add_argument("--config", required=True, help="Path to YAML config file.")

    args = parser.parse_args()

    if args.command == "ingest":
        config = load_config(args.config)
        outputs = build_panel(config)
        for name, path in outputs.items():
            print(f"{name}: {path}")