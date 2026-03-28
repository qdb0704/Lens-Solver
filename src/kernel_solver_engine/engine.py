from __future__ import annotations

from dataclasses import replace
import inspect
import time

import numpy as np

from .backend import load_backend
from .models import OrderValidationReport, SolverKernelRequest, SolverKernelResponse, SolverKernelSummary, SymmetricLensDesign


def _spherical_cap_radius(aperture_radius: float, sag_edge: float) -> float:
    if sag_edge <= 0.0:
        raise ValueError("sag_edge must be positive")
    return (aperture_radius**2 + sag_edge**2) / (2.0 * sag_edge)


def _symmetric_lens_focal_length(refractive_index: float, curvature_radius: float, center_thickness: float) -> float:
    optical_power = (refractive_index - 1.0) * (
        2.0 / curvature_radius
        - ((refractive_index - 1.0) * center_thickness) / (refractive_index * curvature_radius**2)
    )
    if optical_power <= 0.0:
        raise ValueError("lens power must be positive")
    return 1.0 / optical_power


def _build_axis(half_width: float, dx: float) -> np.ndarray:
    half_steps = int(round(half_width / dx))
    return np.linspace(-half_steps * dx, half_steps * dx, 2 * half_steps + 1, dtype=np.float64)


def _gaussian_feed(
    backend,
    x: np.ndarray,
    y: np.ndarray,
    *,
    waist: float,
    lambda0: float,
    phase_radius: float | None,
    polarization: str,
    z_ref: float,
):
    x_mat, y_mat = np.meshgrid(x, y, indexing="xy")
    envelope = np.exp(-(x_mat**2 + y_mat**2) / waist**2)
    if phase_radius is None:
        phase = np.ones_like(envelope, dtype=np.complex128)
        label = f"kernel-gaussian-waist-{polarization}"
    else:
        k0 = 2.0 * np.pi / lambda0
        phase = np.exp(-1j * k0 * (np.sqrt(x_mat**2 + y_mat**2 + phase_radius**2) - phase_radius))
        label = f"kernel-gaussian-spherical-{polarization}"
    ex_xy = np.zeros_like(envelope, dtype=np.complex128)
    ey_xy = np.zeros_like(envelope, dtype=np.complex128)
    if polarization == "x":
        ex_xy[...] = envelope * phase
    else:
        ey_xy[...] = envelope * phase
    return backend.FeedField(ex_xy=ex_xy, ey_xy=ey_xy, z_ref=z_ref, label=label)


def _fwhm_1d(x: np.ndarray, amplitude: np.ndarray) -> float:
    peak = float(np.max(amplitude))
    if peak <= 0.0:
        return float("nan")
    normalized = amplitude / peak
    peak_index = int(np.argmax(normalized))
    half_level = 0.5
    left_candidates = np.where(normalized[: peak_index + 1] < half_level)[0]
    right_candidates = np.where(normalized[peak_index:] < half_level)[0]
    if left_candidates.size == 0 or right_candidates.size == 0:
        return float("nan")
    left_lo = int(left_candidates[-1])
    left_hi = min(left_lo + 1, peak_index)
    right_hi = int(peak_index + right_candidates[0])
    right_lo = max(right_hi - 1, peak_index)
    if left_hi == left_lo or right_hi == right_lo:
        return float("nan")
    x0 = float(x[left_lo])
    x1 = float(x[left_hi])
    y0 = float(normalized[left_lo])
    y1 = float(normalized[left_hi])
    left_cross = 0.5 * (x0 + x1) if np.isclose(y1, y0) else x0 + (half_level - y0) * (x1 - x0) / (y1 - y0)
    x0 = float(x[right_lo])
    x1 = float(x[right_hi])
    y0 = float(normalized[right_lo])
    y1 = float(normalized[right_hi])
    right_cross = 0.5 * (x0 + x1) if np.isclose(y1, y0) else x0 + (half_level - y0) * (x1 - x0) / (y1 - y0)
    return float(right_cross - left_cross)


def _relative_l2(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.linalg.norm(candidate - reference) / (np.linalg.norm(reference) + 1e-30))


def _callable_accepts_kwarg(callable_obj: object, kwarg_name: str) -> bool:
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return False
    if kwarg_name in signature.parameters:
        return True
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())


def _inject_supported_solver_baseline_kwargs(
    config_type: object,
    kwargs: dict[str, object],
    *,
    lambda0: float | None = None,
) -> dict[str, object]:
    merged = dict(kwargs)
    supported = set(getattr(config_type, "__dataclass_fields__", {}).keys())
    baseline_kwargs = {
        "sidewall_ordered_split_kind": "none",
        "local_slab_localization_kind": "smooth_partition",
        "local_slab_response_blend_kind": "partitioned_drive",
        "local_slab_response_thickness_alpha": 0.0,
        "local_slab_response_operator_interp_kind": "none",
        "local_slab_depth_anchor_count_max": 4,
        "local_slab_depth_anchor_phase_std_threshold": 0.75,
        "use_local_slab_adaptive_confidence": True,
        "local_slab_adaptive_confidence_ownership_threshold": 0.01,
        "use_local_slab_lateral_patch_refinement": True,
        "local_slab_lateral_patch_count_max": 4,
    }
    if lambda0 is not None:
        baseline_kwargs["local_slab_lateral_patch_x_std_threshold"] = 6.0 * float(lambda0)
    for key, value in baseline_kwargs.items():
        if key in supported or _callable_accepts_kwarg(config_type, key):
            merged.setdefault(key, value)
    return merged


class KernelSolverEngine:
    def build_design(self, request: SolverKernelRequest) -> SymmetricLensDesign:
        backend = load_backend()
        const = backend.PhysicalConstants()
        lambda0 = const.c0 / float(request.f0_hz)
        lens_radius = 0.5 * float(request.lens.diameter_lambda) * lambda0
        compute_half_width = float(request.sampling.compute_half_width_lambda) * lambda0
        display_half_width = float(request.sampling.display_half_width_lambda) * lambda0
        dx = float(request.sampling.dx_lambda) * lambda0
        dz_lens = float(request.sampling.dz_lens_lambda) * lambda0
        focus_scan_dz = float(request.sampling.focus_scan_dz_lambda) * lambda0
        center_thickness = float(request.lens.center_thickness_lambda) * lambda0
        edge_thickness = float(request.lens.edge_thickness_lambda) * lambda0
        if center_thickness <= edge_thickness:
            raise ValueError("center_thickness_lambda must exceed edge_thickness_lambda")
        if dx <= 0.0 or dz_lens <= 0.0 or focus_scan_dz <= 0.0:
            raise ValueError("dx_lambda, dz_lens_lambda, and focus_scan_dz_lambda must be positive")
        if display_half_width > compute_half_width + 1e-15:
            raise ValueError("display_half_width_lambda must not exceed compute_half_width_lambda")

        refractive_index = float(np.sqrt(float(request.lens.eps_r) * float(request.lens.mu_r)))
        eta_rel = float(np.sqrt(float(request.lens.mu_r) / float(request.lens.eps_r)))
        sag_edge = 0.5 * (center_thickness - edge_thickness)
        curvature_radius = _spherical_cap_radius(lens_radius, sag_edge)
        effective_focal_length = _symmetric_lens_focal_length(refractive_index, curvature_radius, center_thickness)
        z_source = 0.0
        z_lens_front = z_source + float(request.source.source_to_lens_lambda) * lambda0
        z_observation_end = z_lens_front + center_thickness + float(request.source.lens_to_observation_lambda) * lambda0
        waist = float(request.source.waist_lambda) * lambda0
        source_phase_radius = (
            None
            if request.source.source_phase_radius_lambda is None
            else float(request.source.source_phase_radius_lambda) * lambda0
        )
        return SymmetricLensDesign(
            lambda0=lambda0,
            f0_hz=float(request.f0_hz),
            lens_radius=lens_radius,
            compute_half_width=compute_half_width,
            display_half_width=display_half_width,
            dx=dx,
            dz_lens=dz_lens,
            focus_scan_dz=focus_scan_dz,
            center_thickness=center_thickness,
            edge_thickness=edge_thickness,
            refractive_index=refractive_index,
            eta_rel=eta_rel,
            curvature_radius=curvature_radius,
            effective_focal_length_lambda=effective_focal_length / lambda0,
            z_source=z_source,
            z_lens_front=z_lens_front,
            z_observation_end=z_observation_end,
            waist=waist,
            source_phase_radius=source_phase_radius,
            polarization=request.source.polarization,
        )

    def build_backend_config(self, request: SolverKernelRequest):
        backend = load_backend()
        design = self.build_design(request)
        x = _build_axis(design.compute_half_width, design.dx)
        y = x.copy()
        feed = _gaussian_feed(
            backend,
            x,
            y,
            waist=design.waist,
            lambda0=design.lambda0,
            phase_radius=design.source_phase_radius,
            polarization=design.polarization,
            z_ref=design.z_source,
        )
        z_front_vertex = design.z_lens_front
        z_back_vertex = design.z_lens_front + design.center_thickness
        curvature_radius = design.curvature_radius

        def sag_profile(r_mat: np.ndarray) -> np.ndarray:
            rho = np.minimum(r_mat, design.lens_radius)
            inside = np.maximum(curvature_radius**2 - rho**2, 0.0)
            return curvature_radius - np.sqrt(inside)

        def z_front_profile(r_mat: np.ndarray) -> np.ndarray:
            return z_front_vertex + sag_profile(r_mat)

        def z_back_profile(r_mat: np.ndarray) -> np.ndarray:
            return z_back_vertex - sag_profile(r_mat)

        cfg_kwargs = dict(
            x=x,
            y=y,
            f0=design.f0_hz,
            feed=feed,
            material=backend.MaterialTensor.from_relative(
                np.eye(3) * float(request.lens.eps_r),
                np.eye(3) * float(request.lens.mu_r),
            ),
            lens=backend.ZSlicedLensConfig(
                radius=design.lens_radius,
                z_front_profile=z_front_profile,
                z_back_profile=z_back_profile,
                dz_lens=design.dz_lens,
                occupancy_kind="fractional",
            ),
            fft_convention=backend.FFTConvention(inverse_input_is_shifted=True),
            support_policy="propagating_only",
            ordered_interface_subcell_count=int(request.toggles.ordered_interface_subcell_count),
            use_lateral_sidewall_trace_projection=bool(request.toggles.use_lateral_sidewall_trace_projection),
            use_internal_cavity_correction=bool(request.toggles.use_internal_cavity_correction),
            cavity_longitudinal_model=str(request.toggles.cavity_longitudinal_model),
        )
        cfg_kwargs = _inject_supported_solver_baseline_kwargs(backend.ZSlicedSolverConfig, cfg_kwargs, lambda0=design.lambda0)
        cfg = backend.ZSlicedSolverConfig(**cfg_kwargs)
        return backend, design, cfg

    def solve(self, request: SolverKernelRequest) -> SolverKernelResponse:
        backend, design, cfg = self.build_backend_config(request)
        started = time.perf_counter()
        result = backend.solve_lens_zmarching_bulk(cfg)
        runtime_seconds = time.perf_counter() - started
        center_y = cfg.y.size // 2
        center_x = cfg.x.size // 2
        best_focus_z = float(result.geometry.z_exit_ref)
        best_focus_ey_xy = np.asarray(result.exit_xy[..., 1], dtype=np.complex128)
        best_focus_amp = float(np.abs(best_focus_ey_xy[center_y, center_x]))

        z_values = np.arange(
            result.geometry.z_exit_ref + design.focus_scan_dz,
            design.z_observation_end + 0.5 * design.focus_scan_dz,
            design.focus_scan_dz,
            dtype=np.float64,
        )
        observation_ey_xy = np.asarray(best_focus_ey_xy, dtype=np.complex128)
        for z_value in z_values:
            plane_k = backend.propagate_spectrum(result.exit_k, result.grid.kz_mat, float(z_value - result.geometry.z_exit_ref))
            plane_xy = backend.ifft_k_to_xy(plane_k, cfg.fft_convention)
            ey_plane = np.asarray(plane_xy[..., 1], dtype=np.complex128)
            if z_value >= design.z_observation_end - 0.5 * design.focus_scan_dz:
                observation_ey_xy = ey_plane
            on_axis_amp = float(np.abs(ey_plane[center_y, center_x]))
            if on_axis_amp > best_focus_amp:
                best_focus_amp = on_axis_amp
                best_focus_z = float(z_value)
                best_focus_ey_xy = ey_plane

        focus_line = np.abs(best_focus_ey_xy[center_y, :])
        focus_fwhm = _fwhm_1d(cfg.x / design.lambda0, focus_line)
        summary = SolverKernelSummary(
            runtime_seconds=float(runtime_seconds),
            grid_shape=(int(cfg.y.size), int(cfg.x.size)),
            ordered_interface_subcell_count=int(cfg.ordered_interface_subcell_count),
            use_lateral_sidewall_trace_projection=bool(cfg.use_lateral_sidewall_trace_projection),
            best_focus_z_lambda=best_focus_z / design.lambda0,
            focus_fwhm_lambda=focus_fwhm,
            focus_center_amp=float(np.abs(best_focus_ey_xy[center_y, center_x])),
            observation_center_amp=float(np.abs(observation_ey_xy[center_y, center_x])),
            max_invalid_fraction=float(result.max_invalid_fraction),
            effective_focal_length_lambda=float(design.effective_focal_length_lambda),
        )
        return SolverKernelResponse(
            request=request,
            design=design,
            best_focus_ey_xy=best_focus_ey_xy,
            best_focus_z=best_focus_z,
            observation_ey_xy=observation_ey_xy,
            summary=summary,
        )

    def compare_orders(self, request: SolverKernelRequest, *, candidate_order: int = 2, reference_order: int = 4) -> OrderValidationReport:
        candidate_request = replace(request, toggles=replace(request.toggles, ordered_interface_subcell_count=int(candidate_order)))
        reference_request = replace(request, toggles=replace(request.toggles, ordered_interface_subcell_count=int(reference_order)))
        candidate = self.solve(candidate_request)
        reference = self.solve(reference_request)
        candidate_center_y = candidate.best_focus_ey_xy.shape[0] // 2
        reference_center_y = reference.best_focus_ey_xy.shape[0] // 2
        candidate_centerline = np.asarray(candidate.best_focus_ey_xy[candidate_center_y, :], dtype=np.complex128)
        reference_centerline = np.asarray(reference.best_focus_ey_xy[reference_center_y, :], dtype=np.complex128)
        runtime_ratio = float(candidate.summary.runtime_seconds / reference.summary.runtime_seconds) if reference.summary.runtime_seconds > 1e-30 else float("inf")
        return OrderValidationReport(
            candidate_order=int(candidate_order),
            reference_order=int(reference_order),
            candidate_summary=candidate.summary,
            reference_summary=reference.summary,
            focus_plane_rel_l2=_relative_l2(reference.best_focus_ey_xy, candidate.best_focus_ey_xy),
            focus_centerline_rel_l2=_relative_l2(reference_centerline, candidate_centerline),
            observation_plane_rel_l2=_relative_l2(reference.observation_ey_xy, candidate.observation_ey_xy),
            focus_center_amp_delta=float(candidate.summary.focus_center_amp - reference.summary.focus_center_amp),
            focus_fwhm_delta_lambda=float(candidate.summary.focus_fwhm_lambda - reference.summary.focus_fwhm_lambda),
            runtime_ratio_vs_reference=runtime_ratio,
        )
