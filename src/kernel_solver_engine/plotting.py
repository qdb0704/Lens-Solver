from __future__ import annotations

import numpy as np


def axis_edges_from_centers(values: np.ndarray) -> np.ndarray:
    centers = np.asarray(values, dtype=np.float64)
    if centers.ndim != 1 or centers.size == 0:
        raise ValueError("axis center coordinates must be a non-empty 1D array")
    if centers.size == 1:
        return np.array([centers[0] - 0.5, centers[0] + 0.5], dtype=np.float64)

    midpoints = 0.5 * (centers[:-1] + centers[1:])
    first_edge = centers[0] - 0.5 * (centers[1] - centers[0])
    last_edge = centers[-1] + 0.5 * (centers[-1] - centers[-2])
    return np.concatenate(([first_edge], midpoints, [last_edge])).astype(np.float64)


def pcolormesh_from_centers(
    ax,
    values: np.ndarray,
    x_centers: np.ndarray,
    y_centers: np.ndarray,
    *,
    invert_y: bool = False,
    **kwargs,
):
    data = np.asarray(values)
    x = np.asarray(x_centers, dtype=np.float64)
    y = np.asarray(y_centers, dtype=np.float64)
    if data.shape != (y.size, x.size):
        raise ValueError("values must have shape (len(y_centers), len(x_centers))")

    x_edges = axis_edges_from_centers(x)
    y_edges = axis_edges_from_centers(y)
    plot_data = data
    plot_y_edges = y_edges
    if invert_y:
        plot_data = np.flipud(plot_data)
        plot_y_edges = y_edges[::-1]
    return ax.pcolormesh(
        x_edges,
        plot_y_edges,
        plot_data,
        shading="flat",
        **kwargs,
    )
