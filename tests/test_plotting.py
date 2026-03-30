from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kernel_solver_engine.plotting import axis_edges_from_centers, pcolormesh_from_centers  # noqa: E402


class _FakeAxis:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def pcolormesh(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "mesh"


class PublicPlottingTests(unittest.TestCase):
    def test_axis_edges_from_centers_handles_nonuniform_grid(self) -> None:
        centers = np.array([0.0, 1.0, 3.0], dtype=np.float64)
        edges = axis_edges_from_centers(centers)
        np.testing.assert_allclose(edges, np.array([-0.5, 0.5, 2.0, 4.0], dtype=np.float64))

    def test_axis_edges_from_centers_handles_single_value(self) -> None:
        centers = np.array([2.5], dtype=np.float64)
        edges = axis_edges_from_centers(centers)
        np.testing.assert_allclose(edges, np.array([2.0, 3.0], dtype=np.float64))

    def test_pcolormesh_from_centers_flips_data_for_inverted_y(self) -> None:
        ax = _FakeAxis()
        values = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        x = np.array([0.0, 2.0], dtype=np.float64)
        y = np.array([10.0, 11.0], dtype=np.float64)

        mesh = pcolormesh_from_centers(ax, values, x, y, invert_y=True, cmap="magma")

        self.assertEqual(mesh, "mesh")
        self.assertEqual(len(ax.calls), 1)
        args, kwargs = ax.calls[0]
        np.testing.assert_allclose(args[0], np.array([-1.0, 1.0, 3.0], dtype=np.float64))
        np.testing.assert_allclose(args[1], np.array([11.5, 10.5, 9.5], dtype=np.float64))
        np.testing.assert_allclose(args[2], np.array([[3.0, 4.0], [1.0, 2.0]], dtype=np.float64))
        self.assertEqual(kwargs["shading"], "flat")
        self.assertEqual(kwargs["cmap"], "magma")

    def test_pcolormesh_from_centers_rejects_shape_mismatch(self) -> None:
        ax = _FakeAxis()
        with self.assertRaises(ValueError):
            pcolormesh_from_centers(
                ax,
                np.ones((2, 3), dtype=np.float64),
                np.array([0.0, 1.0], dtype=np.float64),
                np.array([0.0, 1.0], dtype=np.float64),
            )


if __name__ == "__main__":
    unittest.main()
