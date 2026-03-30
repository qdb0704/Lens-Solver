from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kernel_solver_engine.plotting import pcolormesh_from_centers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a nonuniform panorama NPZ with cell-edge-aware coordinates.")
    parser.add_argument("--npz", type=Path, required=True, help="Path to a private diagnostic NPZ file.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output image path. Defaults to <npz stem>_pcolormesh.png next to the NPZ.",
    )
    parser.add_argument("--db-floor", type=float, default=-45.0, help="Lower dB clip level.")
    parser.add_argument("--x-limit", type=float, default=None, help="Optional symmetric x-limit in lambda.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    npz_path = args.npz.resolve()
    if not npz_path.exists():
        raise FileNotFoundError(f"npz not found: {npz_path}")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError("matplotlib is required; install kernel-solver-engine[plotting] or matplotlib directly") from exc

    data = np.load(npz_path)
    x_lambda = np.asarray(data["x_lambda"], dtype=np.float64)
    z_lambda = np.asarray(data["z_all_lambda"], dtype=np.float64)
    field_xz = np.asarray(data["centerline_ey_xz"], dtype=np.complex128)
    amplitude = np.abs(field_xz)
    amplitude_db = 20.0 * np.log10(np.maximum(amplitude / (np.max(amplitude) + 1e-30), 1e-6))

    out_path = args.out.resolve() if args.out is not None else npz_path.with_name(f"{npz_path.stem}_pcolormesh.png")

    fig, ax = plt.subplots(figsize=(8.6, 7.6), dpi=180)
    image = pcolormesh_from_centers(
        ax,
        amplitude_db,
        x_lambda,
        z_lambda,
        invert_y=True,
        cmap="magma",
        vmin=float(args.db_floor),
        vmax=0.0,
    )
    ax.set_aspect("auto")

    if "front_curve_lambda" in data and "back_curve_lambda" in data:
        ax.plot(np.asarray(x_lambda, dtype=np.float64), np.asarray(data["front_curve_lambda"], dtype=np.float64), color="#7be0ff", linewidth=1.2)
        ax.plot(np.asarray(x_lambda, dtype=np.float64), np.asarray(data["back_curve_lambda"], dtype=np.float64), color="#dff8ff", linewidth=1.2)
    if all(key in data for key in ("lens_radius_lambda", "front_edge_lambda", "back_edge_lambda")):
        lens_radius = float(data["lens_radius_lambda"])
        front_edge = float(data["front_edge_lambda"])
        back_edge = float(data["back_edge_lambda"])
        ax.plot([-lens_radius, -lens_radius], [front_edge, back_edge], color="#dff8ff", linewidth=1.0)
        ax.plot([lens_radius, lens_radius], [front_edge, back_edge], color="#dff8ff", linewidth=1.0)

    ax.set_title("Nonuniform panorama rendered with cell-edge-aware coordinates")
    ax.set_xlabel("x / lambda")
    ax.set_ylabel("z / lambda")
    if args.x_limit is not None:
        ax.set_xlim(-float(args.x_limit), float(args.x_limit))
    colorbar = fig.colorbar(image, ax=ax, pad=0.01)
    colorbar.set_label("dB re. panorama max")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(out_path)


if __name__ == "__main__":
    main()
