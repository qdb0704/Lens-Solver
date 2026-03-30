from __future__ import annotations

from dataclasses import replace

import numpy as np

from .models import KernelPresetName, SamplingSpec, SolverKernelRequest, SolverToggles, SourceSpec, SymmetricLensSpec


def _spherical_cap_radius(aperture_radius_lambda: float, sag_edge_lambda: float) -> float:
    if sag_edge_lambda <= 0.0:
        raise ValueError("sag_edge_lambda must be positive")
    return (aperture_radius_lambda**2 + sag_edge_lambda**2) / (2.0 * sag_edge_lambda)


def _symmetric_lens_focal_length_lambda(
    refractive_index: float,
    curvature_radius_lambda: float,
    center_thickness_lambda: float,
) -> float:
    optical_power = (refractive_index - 1.0) * (
        2.0 / curvature_radius_lambda
        - ((refractive_index - 1.0) * center_thickness_lambda) / (refractive_index * curvature_radius_lambda**2)
    )
    if optical_power <= 0.0:
        raise ValueError("lens power must be positive")
    return 1.0 / optical_power


def make_named_preset(name: KernelPresetName) -> SolverToggles:
    if name == "fast_preview":
        return SolverToggles(
            ordered_interface_subcell_count=0,
            use_lateral_sidewall_trace_projection=False,
        )
    if name == "focus_only_fast":
        return SolverToggles(
            ordered_interface_subcell_count=0,
            use_lateral_sidewall_trace_projection=False,
            use_internal_cavity_correction=False,
        )
    if name == "focus_only_mainline":
        return SolverToggles(
            ordered_interface_subcell_count=4,
            use_lateral_sidewall_trace_projection=True,
            use_internal_cavity_correction=False,
        )
    if name == "external_default":
        return SolverToggles(
            ordered_interface_subcell_count=4,
            use_lateral_sidewall_trace_projection=True,
        )
    if name == "validation_reference":
        return SolverToggles(
            ordered_interface_subcell_count=4,
            use_lateral_sidewall_trace_projection=True,
        )
    if name == "projector_advanced":
        return SolverToggles(
            ordered_interface_subcell_count=4,
            use_lateral_sidewall_trace_projection=True,
        )
    raise ValueError(f"unsupported preset: {name}")


def with_named_preset(request: SolverKernelRequest, name: KernelPresetName) -> SolverKernelRequest:
    return replace(request, toggles=make_named_preset(name))


def make_large_lens_example_request(
    preset: KernelPresetName = "external_default",
) -> SolverKernelRequest:
    request = SolverKernelRequest(
        lens=SymmetricLensSpec(
            diameter_lambda=60.0,
            center_thickness_lambda=10.0,
            edge_thickness_lambda=4.0,
            eps_r=4.0,
            mu_r=1.0,
        ),
        source=SourceSpec(
            waist_lambda=16.0,
            source_to_lens_lambda=28.0,
            source_phase_radius_lambda=80.0,
            lens_to_observation_lambda=50.0,
            polarization="y",
        ),
        sampling=SamplingSpec(
            compute_half_width_lambda=76.0,
            display_half_width_lambda=28.0,
            dx_lambda=0.40,
            dz_lens_lambda=0.50,
            focus_scan_dz_lambda=0.50,
        ),
    )
    return with_named_preset(request, preset)


def make_frozen_f_lens_f_request(
    preset: KernelPresetName = "external_default",
) -> SolverKernelRequest:
    lens = SymmetricLensSpec(
        diameter_lambda=50.0,
        center_thickness_lambda=10.024,
        edge_thickness_lambda=3.5,
        eps_r=4.0,
        mu_r=1.0,
    )
    refractive_index = float(np.sqrt(float(lens.eps_r) * float(lens.mu_r)))
    sag_edge_lambda = 0.5 * (float(lens.center_thickness_lambda) - float(lens.edge_thickness_lambda))
    curvature_radius_lambda = _spherical_cap_radius(0.5 * float(lens.diameter_lambda), sag_edge_lambda)
    f_lambda = _symmetric_lens_focal_length_lambda(
        refractive_index,
        curvature_radius_lambda,
        float(lens.center_thickness_lambda),
    )
    request = SolverKernelRequest(
        lens=lens,
        source=SourceSpec(
            waist_lambda=3.0,
            source_phase_radius_lambda=None,
            source_to_lens_lambda=f_lambda,
            lens_to_observation_lambda=f_lambda,
            polarization="y",
        ),
        sampling=SamplingSpec(
            compute_half_width_lambda=64.0,
            display_half_width_lambda=30.0,
            dx_lambda=0.40,
            dz_lens_lambda=0.50,
            focus_scan_dz_lambda=0.50,
        ),
    )
    return with_named_preset(request, preset)


def make_plane_wave_focus_request(
    preset: KernelPresetName = "external_default",
) -> SolverKernelRequest:
    lens = SymmetricLensSpec(
        diameter_lambda=50.0,
        center_thickness_lambda=10.024,
        edge_thickness_lambda=3.5,
        eps_r=4.0,
        mu_r=1.0,
    )
    refractive_index = float(np.sqrt(float(lens.eps_r) * float(lens.mu_r)))
    sag_edge_lambda = 0.5 * (float(lens.center_thickness_lambda) - float(lens.edge_thickness_lambda))
    curvature_radius_lambda = _spherical_cap_radius(0.5 * float(lens.diameter_lambda), sag_edge_lambda)
    f_lambda = _symmetric_lens_focal_length_lambda(
        refractive_index,
        curvature_radius_lambda,
        float(lens.center_thickness_lambda),
    )
    request = SolverKernelRequest(
        lens=lens,
        source=SourceSpec(
            source_kind="plane_wave",
            waist_lambda=3.0,
            source_phase_radius_lambda=None,
            source_to_lens_lambda=f_lambda,
            lens_to_observation_lambda=f_lambda,
            polarization="y",
        ),
        sampling=SamplingSpec(
            compute_half_width_lambda=64.0,
            display_half_width_lambda=30.0,
            dx_lambda=0.40,
            dz_lens_lambda=0.50,
            focus_scan_dz_lambda=0.50,
        ),
    )
    return with_named_preset(request, preset)


def make_offaxis_2f_imaging_request(
    preset: KernelPresetName = "external_default",
) -> SolverKernelRequest:
    lens = SymmetricLensSpec(
        diameter_lambda=50.0,
        center_thickness_lambda=10.024,
        edge_thickness_lambda=3.5,
        eps_r=4.0,
        mu_r=1.0,
    )
    refractive_index = float(np.sqrt(float(lens.eps_r) * float(lens.mu_r)))
    sag_edge_lambda = 0.5 * (float(lens.center_thickness_lambda) - float(lens.edge_thickness_lambda))
    curvature_radius_lambda = _spherical_cap_radius(0.5 * float(lens.diameter_lambda), sag_edge_lambda)
    f_lambda = _symmetric_lens_focal_length_lambda(
        refractive_index,
        curvature_radius_lambda,
        float(lens.center_thickness_lambda),
    )
    principal_shift_lambda = f_lambda * (refractive_index - 1.0) * float(lens.center_thickness_lambda) / (
        refractive_index * curvature_radius_lambda
    )
    object_distance_lambda = 2.0 * f_lambda - principal_shift_lambda
    request = SolverKernelRequest(
        lens=lens,
        source=SourceSpec(
            source_kind="gaussian",
            waist_lambda=1.5,
            source_x_offset_lambda=6.0,
            source_y_offset_lambda=0.0,
            source_phase_radius_lambda=None,
            source_to_lens_lambda=object_distance_lambda,
            lens_to_observation_lambda=object_distance_lambda,
            polarization="y",
        ),
        sampling=SamplingSpec(
            compute_half_width_lambda=64.0,
            display_half_width_lambda=30.0,
            dx_lambda=0.40,
            dz_lens_lambda=0.50,
            focus_scan_dz_lambda=0.50,
        ),
    )
    return with_named_preset(request, preset)
