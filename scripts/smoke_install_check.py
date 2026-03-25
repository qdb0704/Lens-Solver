from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check an installed kernel-solver-engine wheel.")
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--workspace-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    install_root = Path(args.install_root).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    sys.path.insert(0, str(install_root))
    sys.path.insert(0, str(workspace_root))

    from kernel_solver_engine import KernelSolverEngine, SamplingSpec, SolverKernelRequest, SourceSpec, SymmetricLensSpec, make_named_preset

    engine = KernelSolverEngine()
    request = SolverKernelRequest(
        lens=SymmetricLensSpec(
            diameter_lambda=8.0,
            center_thickness_lambda=3.0,
            edge_thickness_lambda=1.2,
        ),
        source=SourceSpec(
            waist_lambda=4.0,
            source_to_lens_lambda=8.0,
            source_phase_radius_lambda=18.0,
            lens_to_observation_lambda=10.0,
        ),
        sampling=SamplingSpec(
            compute_half_width_lambda=10.0,
            display_half_width_lambda=6.0,
            dx_lambda=1.0,
            dz_lens_lambda=1.0,
            focus_scan_dz_lambda=1.0,
        ),
        toggles=make_named_preset("external_default"),
    )
    response = engine.solve(request)
    sys.stdout.write(json.dumps(response.summary.as_dict(), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
