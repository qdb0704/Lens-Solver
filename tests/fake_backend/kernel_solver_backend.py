from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PhysicalConstants:
    eps0: float = 8.854e-12
    mu0: float = 4.0 * np.pi * 1e-7
    c0: float = 3.0e8


@dataclass(frozen=True)
class FFTConvention:
    inverse_input_is_shifted: bool = True


@dataclass(frozen=True)
class FeedField:
    ex_xy: np.ndarray
    ey_xy: np.ndarray
    z_ref: float = 0.0
    label: str = "fake-feed"


@dataclass(frozen=True)
class MaterialTensor:
    eps_r: np.ndarray
    mu_r: np.ndarray

    @classmethod
    def from_relative(
        cls,
        eps_r: np.ndarray,
        mu_r: np.ndarray,
        alpha_r: np.ndarray | None = None,
        beta_r: np.ndarray | None = None,
        constants: PhysicalConstants | None = None,
    ) -> "MaterialTensor":
        del alpha_r, beta_r, constants
        return cls(
            eps_r=np.asarray(eps_r, dtype=np.complex128),
            mu_r=np.asarray(mu_r, dtype=np.complex128),
        )


@dataclass(frozen=True)
class ZSlicedLensConfig:
    radius: float
    z_front_profile: object
    z_back_profile: object | None = None
    thickness_profile: object | None = None
    dz_lens: float | None = None
    z_edges: np.ndarray | None = None
    z_entr_ref: float | None = None
    z_exit_ref: float | None = None
    occupancy_kind: str = "fractional"
    weight_floor: float = 1e-8


@dataclass(frozen=True)
class ZSlicedSolverConfig:
    x: np.ndarray
    y: np.ndarray
    f0: float
    feed: FeedField
    material: MaterialTensor
    lens: ZSlicedLensConfig
    fft_convention: FFTConvention = FFTConvention()
    support_policy: str = "propagating_only"
    ordered_interface_subcell_count: int = 4
    sidewall_ordered_split_kind: str = "local_fractional_interface"
    use_lateral_sidewall_trace_projection: bool = True
    use_internal_cavity_correction: bool = True
    cavity_longitudinal_model: str = "multispectral_oblique_slab"
    sidewall_ordered_split_kind: str = "local_fractional_interface"
    local_slab_localization_kind: str = "hard_mask"
    local_slab_response_blend_kind: str = "continuous_thickness_interp"
    local_slab_response_thickness_alpha: float = 1.0
    local_slab_response_operator_interp_kind: str = "linear_thickness"
    local_slab_depth_anchor_count_max: int = 1
    local_slab_depth_anchor_phase_std_threshold: float = 0.0
    use_local_slab_adaptive_confidence: bool = False
    local_slab_adaptive_confidence_ownership_threshold: float = 0.0
    use_local_slab_lateral_patch_refinement: bool = False
    local_slab_lateral_patch_count_max: int = 1
    local_slab_lateral_patch_x_std_threshold: float = 0.0


@dataclass(frozen=True)
class Grid:
    kz_mat: np.ndarray


@dataclass(frozen=True)
class Geometry:
    z_exit_ref: float


@dataclass(frozen=True)
class Result:
    geometry: Geometry
    exit_xy: np.ndarray
    exit_k: np.ndarray
    grid: Grid
    max_invalid_fraction: float


def _fft_xy_to_k(field_xy: np.ndarray, convention: FFTConvention) -> np.ndarray:
    del convention
    return np.fft.fftshift(np.fft.fft2(np.asarray(field_xy, dtype=np.complex128), axes=(0, 1)), axes=(0, 1)).astype(
        np.complex128
    )


def ifft_k_to_xy(field_k: np.ndarray, convention: FFTConvention) -> np.ndarray:
    values = np.asarray(field_k, dtype=np.complex128)
    if convention.inverse_input_is_shifted:
        values = np.fft.ifftshift(values, axes=(0, 1))
    return np.fft.ifft2(values, axes=(0, 1)).astype(np.complex128)


def propagate_spectrum(field_k: np.ndarray, kz_mat: np.ndarray, distance: float) -> np.ndarray:
    phase = np.exp(1j * np.asarray(kz_mat, dtype=np.complex128) * float(distance))
    return np.asarray(field_k, dtype=np.complex128) * phase[..., None]


def _profile_sample(profile: object, radius: float) -> float:
    if profile is None:
        return 0.0
    if callable(profile):
        sample = np.asarray(profile(np.array([radius], dtype=np.float64)), dtype=np.float64)
        return float(sample.reshape(-1)[0])
    return float(np.asarray(profile, dtype=np.float64).reshape(-1)[0])


def solve_lens_zmarching_bulk(cfg: ZSlicedSolverConfig) -> Result:
    x_mat, y_mat = np.meshgrid(np.asarray(cfg.x, dtype=np.float64), np.asarray(cfg.y, dtype=np.float64), indexing="xy")
    radius_sq = x_mat**2 + y_mat**2
    const = PhysicalConstants()
    lambda0 = const.c0 / float(cfg.f0)
    lens_radius = max(float(cfg.lens.radius), 1e-12)
    order = max(int(cfg.ordered_interface_subcell_count), 0)
    sigma = max(0.18 * lens_radius + 0.65 * lambda0 / (1.0 + 0.15 * order), 0.75 * lambda0)
    amplitude_gain = 1.0 + 0.03 * order + (0.05 if cfg.use_lateral_sidewall_trace_projection else 0.0)
    phase_curvature = 0.08 + 0.02 * order
    if cfg.use_internal_cavity_correction:
        phase_curvature *= 1.05
    amplitude = amplitude_gain * np.exp(-radius_sq / (sigma**2 + 1e-30))
    phase = np.exp(1j * phase_curvature * radius_sq / (lens_radius**2 + lambda0**2))
    ey_xy = (amplitude * phase).astype(np.complex128)
    if cfg.use_lateral_sidewall_trace_projection:
        ey_xy *= (1.0 + 0.02 * np.cos(2.0 * np.pi * x_mat / (lens_radius + lambda0)))
    ex_xy = np.zeros_like(ey_xy)
    exit_xy = np.stack((ex_xy, ey_xy), axis=-1).astype(np.complex128)
    kz_value = complex(2.0 * np.pi / lambda0, 0.0)
    kz_mat = np.full((cfg.y.size, cfg.x.size), kz_value, dtype=np.complex128)
    z_exit_ref = _profile_sample(cfg.lens.z_back_profile, 0.0)
    return Result(
        geometry=Geometry(z_exit_ref=z_exit_ref),
        exit_xy=exit_xy,
        exit_k=_fft_xy_to_k(exit_xy, cfg.fft_convention),
        grid=Grid(kz_mat=kz_mat),
        max_invalid_fraction=max(0.0, 0.01 / (1.0 + order)),
    )


@dataclass(frozen=True)
class KernelSolverBackendAPI:
    module_name: str
    adapter_module_name: str
    FFTConvention: type = FFTConvention
    FeedField: type = FeedField
    MaterialTensor: type = MaterialTensor
    ZSlicedLensConfig: type = ZSlicedLensConfig
    ZSlicedSolverConfig: type = ZSlicedSolverConfig
    solve_lens_zmarching_bulk: object = solve_lens_zmarching_bulk
    PhysicalConstants: type = PhysicalConstants
    ifft_k_to_xy: object = ifft_k_to_xy
    propagate_spectrum: object = propagate_spectrum


def create_backend_api(module_name: str = "tests.fake_backend") -> KernelSolverBackendAPI:
    return KernelSolverBackendAPI(
        module_name=module_name,
        adapter_module_name=f"{module_name}.kernel_solver_backend",
    )
