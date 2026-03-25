from __future__ import annotations

from dataclasses import replace

from .models import KernelPresetName, SamplingSpec, SolverKernelRequest, SolverToggles, SourceSpec, SymmetricLensSpec


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
            ordered_interface_subcell_count=2,
            use_lateral_sidewall_trace_projection=False,
            use_internal_cavity_correction=False,
        )
    if name == "external_default":
        return SolverToggles(
            ordered_interface_subcell_count=2,
            use_lateral_sidewall_trace_projection=False,
        )
    if name == "validation_reference":
        return SolverToggles(
            ordered_interface_subcell_count=4,
            use_lateral_sidewall_trace_projection=False,
        )
    if name == "projector_advanced":
        return SolverToggles(
            ordered_interface_subcell_count=2,
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
