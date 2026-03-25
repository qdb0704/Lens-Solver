from __future__ import annotations

from pprint import pprint

from kernel_solver_engine import KernelSolverEngine, make_large_lens_example_request


def main() -> None:
    engine = KernelSolverEngine()
    request = make_large_lens_example_request(preset="external_default")
    report = engine.compare_orders(request, candidate_order=2, reference_order=4)
    pprint(report.as_dict(), sort_dicts=False)


if __name__ == "__main__":
    main()
