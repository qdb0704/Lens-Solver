from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np


KernelPresetName = Literal[
    "fast_preview",
    "focus_only_fast",
    "focus_only_mainline",
    "external_default",
    "validation_reference",
    "projector_advanced",
]


@dataclass(frozen=True)
class SamplingSpec:
    compute_half_width_lambda: float = 40.0
    display_half_width_lambda: float = 18.0
    dx_lambda: float = 0.25
    dz_lens_lambda: float = 0.50
    focus_scan_dz_lambda: float = 0.50


@dataclass(frozen=True)
class SymmetricLensSpec:
    diameter_lambda: float = 20.0
    center_thickness_lambda: float = 6.0
    edge_thickness_lambda: float = 2.5
    eps_r: float = 4.0
    mu_r: float = 1.0


@dataclass(frozen=True)
class SourceSpec:
    waist_lambda: float = 8.0
    source_to_lens_lambda: float = 20.0
    source_phase_radius_lambda: float | None = 36.0
    lens_to_observation_lambda: float = 30.0
    polarization: Literal["x", "y"] = "y"


@dataclass(frozen=True)
class SolverToggles:
    ordered_interface_subcell_count: int = 4
    use_lateral_sidewall_trace_projection: bool = True
    use_internal_cavity_correction: bool = True
    cavity_longitudinal_model: Literal[
        "normal_incidence",
        "multispectral_oblique_slab",
        "multispectral_gtmm_slab",
    ] = "multispectral_oblique_slab"


@dataclass(frozen=True)
class SolverKernelRequest:
    f0_hz: float = 10.0e9
    lens: SymmetricLensSpec = field(default_factory=SymmetricLensSpec)
    source: SourceSpec = field(default_factory=SourceSpec)
    sampling: SamplingSpec = field(default_factory=SamplingSpec)
    toggles: SolverToggles = field(default_factory=SolverToggles)


@dataclass(frozen=True)
class SymmetricLensDesign:
    lambda0: float
    f0_hz: float
    lens_radius: float
    compute_half_width: float
    display_half_width: float
    dx: float
    dz_lens: float
    focus_scan_dz: float
    center_thickness: float
    edge_thickness: float
    refractive_index: float
    eta_rel: float
    curvature_radius: float
    effective_focal_length_lambda: float
    z_source: float
    z_lens_front: float
    z_observation_end: float
    waist: float
    source_phase_radius: float | None
    polarization: Literal["x", "y"]


@dataclass(frozen=True)
class SolverKernelSummary:
    runtime_seconds: float
    grid_shape: tuple[int, int]
    ordered_interface_subcell_count: int
    use_lateral_sidewall_trace_projection: bool
    best_focus_z_lambda: float
    focus_fwhm_lambda: float
    focus_center_amp: float
    observation_center_amp: float
    max_invalid_fraction: float
    effective_focal_length_lambda: float

    def as_dict(self) -> dict[str, float | int | bool | tuple[int, int]]:
        return {
            "runtime_seconds": self.runtime_seconds,
            "grid_shape": self.grid_shape,
            "ordered_interface_subcell_count": self.ordered_interface_subcell_count,
            "use_lateral_sidewall_trace_projection": self.use_lateral_sidewall_trace_projection,
            "best_focus_z_lambda": self.best_focus_z_lambda,
            "focus_fwhm_lambda": self.focus_fwhm_lambda,
            "focus_center_amp": self.focus_center_amp,
            "observation_center_amp": self.observation_center_amp,
            "max_invalid_fraction": self.max_invalid_fraction,
            "effective_focal_length_lambda": self.effective_focal_length_lambda,
        }


@dataclass(frozen=True)
class SolverKernelResponse:
    request: SolverKernelRequest
    design: SymmetricLensDesign
    best_focus_ey_xy: np.ndarray
    best_focus_z: float
    observation_ey_xy: np.ndarray
    summary: SolverKernelSummary


@dataclass(frozen=True)
class OrderValidationReport:
    candidate_order: int
    reference_order: int
    candidate_summary: SolverKernelSummary
    reference_summary: SolverKernelSummary
    focus_plane_rel_l2: float
    focus_centerline_rel_l2: float
    observation_plane_rel_l2: float
    focus_center_amp_delta: float
    focus_fwhm_delta_lambda: float
    runtime_ratio_vs_reference: float

    def as_dict(self) -> dict[str, float | int | dict[str, float | int | bool | tuple[int, int]]]:
        return {
            "candidate_order": self.candidate_order,
            "reference_order": self.reference_order,
            "focus_plane_rel_l2": self.focus_plane_rel_l2,
            "focus_centerline_rel_l2": self.focus_centerline_rel_l2,
            "observation_plane_rel_l2": self.observation_plane_rel_l2,
            "focus_center_amp_delta": self.focus_center_amp_delta,
            "focus_fwhm_delta_lambda": self.focus_fwhm_delta_lambda,
            "runtime_ratio_vs_reference": self.runtime_ratio_vs_reference,
            "candidate_summary": self.candidate_summary.as_dict(),
            "reference_summary": self.reference_summary.as_dict(),
        }
