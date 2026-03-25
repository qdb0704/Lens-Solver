from __future__ import annotations

import argparse
import sys

from .engine import KernelSolverEngine
from .json_api import dump_json, load_request_json, report_to_dict, response_to_public_dict
from .presets import make_large_lens_example_request


def _build_request(args: argparse.Namespace):
    if args.request_json is not None:
        return load_request_json(args.request_json)
    return make_large_lens_example_request(preset=args.preset)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Public CLI for the kernel solver engine.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="Solve one request.")
    solve_parser.add_argument("--preset", choices=("fast_preview", "external_default", "validation_reference", "projector_advanced"), default="external_default")
    solve_parser.add_argument("--request-json")
    solve_parser.add_argument("--out")
    solve_parser.add_argument("--include-field-arrays", action="store_true")

    compare_parser = subparsers.add_parser("compare-orders", help="Run the 2-vs-4 validation gate.")
    compare_parser.add_argument("--preset", choices=("fast_preview", "external_default", "validation_reference", "projector_advanced"), default="external_default")
    compare_parser.add_argument("--request-json")
    compare_parser.add_argument("--candidate-order", type=int, default=2)
    compare_parser.add_argument("--reference-order", type=int, default=4)
    compare_parser.add_argument("--out")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    engine = KernelSolverEngine()
    request = _build_request(args)
    if args.command == "solve":
        response = engine.solve(request)
        payload = response_to_public_dict(response, include_field_arrays=bool(args.include_field_arrays))
    else:
        report = engine.compare_orders(request, candidate_order=int(args.candidate_order), reference_order=int(args.reference_order))
        payload = report_to_dict(report)
    text = dump_json(payload, args.out)
    if args.out is None:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
