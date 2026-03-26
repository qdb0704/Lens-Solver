# Kernel Solver Engine

`kernel-solver-engine` is the public interface layer for a proprietary
finite-lens solver kernel.

This repository intentionally exposes:

- a stable request/response API
- named presets
- a CLI
- JSON input/output helpers
- a practical `2 vs 4` validation gate
- a wheel-friendly packaging layout and smoke-install scripts

It intentionally does **not** include the proprietary backend implementation.

## Backend Boundary

The public package expects the proprietary backend to be installed separately.
By default it tries to import a private backend module named `lens_gtmm`.

If your private backend uses a different module name, set:

```text
KERNEL_SOLVER_BACKEND_MODULE=your_private_backend_module_name
```

When a private backend provides an explicit adapter module at
`<backend_module>.kernel_solver_backend`, the public package uses that adapter
first. This keeps the public layer pinned to one small backend contract instead
of depending on a broader internal package surface.

## Current Public Defaults

- `external_default`
  `ordered_interface_subcell_count = 2`
  `use_lateral_sidewall_trace_projection = False`
- `focus_only_mainline`
  `ordered_interface_subcell_count = 2`
  `use_lateral_sidewall_trace_projection = False`
  `use_internal_cavity_correction = False`
- `validation_reference`
  `ordered_interface_subcell_count = 4`
  `use_lateral_sidewall_trace_projection = False`
- `fast_preview`
  `ordered_interface_subcell_count = 0`
  `use_lateral_sidewall_trace_projection = False`
- `focus_only_fast`
  `ordered_interface_subcell_count = 0`
  `use_lateral_sidewall_trace_projection = False`
  `use_internal_cavity_correction = False`
- `projector_advanced`
  `ordered_interface_subcell_count = 2`
  `use_lateral_sidewall_trace_projection = True`

## Minimal Python Usage

```python
from kernel_solver_engine import KernelSolverEngine, make_large_lens_example_request

engine = KernelSolverEngine()
request = make_large_lens_example_request(preset="external_default")
response = engine.solve(request)

print(response.summary.as_dict())
```

## Validation Gate Usage

```python
from kernel_solver_engine import KernelSolverEngine, make_large_lens_example_request

engine = KernelSolverEngine()
request = make_large_lens_example_request(preset="external_default")
report = engine.compare_orders(request, candidate_order=2, reference_order=4)

print(report.as_dict())
```

## Nonuniform Panorama Rendering

Private-backend diagnostics may save panorama arrays on a nonuniform `z` grid,
for example when air-side slices, lens slices, and post-lens scans use
different step sizes. In that case, do not render `z_all_lambda` with `imshow`,
because `imshow` assumes uniform pixel spacing and can visibly misalign the
drawn lens outline and field map.

Use the exported helper:

```python
from kernel_solver_engine import pcolormesh_from_centers
```

or the example script:

```powershell
python examples/render_nonuniform_panorama_npz.py --npz path\to\run.npz
```

The script expects the private diagnostic `.npz` to contain at least:

- `x_lambda`
- `z_all_lambda`
- `centerline_ey_xz`

and will overlay `front_curve_lambda`, `back_curve_lambda`, `front_edge_lambda`,
`back_edge_lambda`, and `lens_radius_lambda` when present.

## CLI Usage

```bash
kernel-solver-engine solve --preset external_default
kernel-solver-engine solve --preset focus_only_mainline
kernel-solver-engine compare-orders --preset external_default --candidate-order 2 --reference-order 4
```

## Build A Wheel

From the repo root:

```powershell
./scripts/build_wheel.ps1
```

That script prefers `python -m build` when available and falls back to
`python -m pip wheel` for a wheel-only build. For local Windows smoke checks it
also emits a readable portable wheel under `.artifacts/portable_dist/`.

## Smoke-Install Against A Private Backend

After building a wheel, run:

```powershell
./scripts/smoke_install.ps1
```

By default this expects a private backend module named `lens_gtmm` to be
importable from the parent workspace. Override with `-BackendModule` if your
private package uses a different module name.

## Test Strategy

The public repo test suite uses a lightweight fake backend under
`tests.fake_backend` so public CI does not require the proprietary solver.
Real end-to-end private-backend verification is handled by the local
smoke-install path above.

## Scope Boundary

This package does not claim:

- exact or full-wave equivalence
- universal convergence of `ordered = 2`
- release of the proprietary backend internals

This package does provide:

- a stable public calling interface
- a practical product-facing default stack
- a reproducible `2 vs 4` validation protocol
- a clean adapter seam for a separately installed private backend
