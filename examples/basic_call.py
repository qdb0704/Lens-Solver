from __future__ import annotations

from pprint import pprint

from kernel_solver_engine import KernelSolverEngine, make_large_lens_example_request


def main() -> None:
    engine = KernelSolverEngine()
    request = make_large_lens_example_request(preset="external_default")
    response = engine.solve(request)
    pprint(response.summary.as_dict(), sort_dicts=False)


if __name__ == "__main__":
    main()
