from __future__ import annotations

import os
import math
from pathlib import Path
import sys
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
WORKSPACE_ROOT = REPO_ROOT.parent

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_solver_engine import (  # noqa: E402
    BACKEND_ENV_VAR,
    KernelSolverEngine,
    SamplingSpec,
    SolverKernelRequest,
    SourceSpec,
    SymmetricLensSpec,
    make_large_lens_example_request,
    make_named_preset,
    request_from_dict,
    request_to_dict,
)
from kernel_solver_engine.backend import load_backend  # noqa: E402
from kernel_solver_engine.engine import _inject_supported_solver_baseline_kwargs  # noqa: E402


class PublicKernelSolverEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_backend = os.environ.get(BACKEND_ENV_VAR)
        os.environ[BACKEND_ENV_VAR] = "tests.fake_backend"

    def tearDown(self) -> None:
        if self._previous_backend is None:
            os.environ.pop(BACKEND_ENV_VAR, None)
        else:
            os.environ[BACKEND_ENV_VAR] = self._previous_backend

    def test_large_lens_example_uses_external_default_preset(self) -> None:
        request = make_large_lens_example_request(preset="external_default")
        self.assertEqual(request.toggles.ordered_interface_subcell_count, 4)
        self.assertTrue(request.toggles.use_lateral_sidewall_trace_projection)

    def test_focus_only_mainline_turns_off_internal_cavity(self) -> None:
        request = make_large_lens_example_request(preset="focus_only_mainline")
        self.assertEqual(request.toggles.ordered_interface_subcell_count, 4)
        self.assertTrue(request.toggles.use_lateral_sidewall_trace_projection)
        self.assertFalse(request.toggles.use_internal_cavity_correction)

    def test_public_loader_uses_explicit_adapter_contract(self) -> None:
        backend = load_backend()
        self.assertEqual(backend.module_name, "tests.fake_backend")
        self.assertEqual(backend.adapter_module_name, "tests.fake_backend.kernel_solver_backend")

    def test_request_round_trip(self) -> None:
        original = make_large_lens_example_request(preset="projector_advanced")
        rebuilt = request_from_dict(request_to_dict(original))
        self.assertEqual(original, rebuilt)

    def test_engine_solves_small_smoke_case(self) -> None:
        engine = KernelSolverEngine()
        request = SolverKernelRequest(
            lens=SymmetricLensSpec(
                diameter_lambda=6.0,
                center_thickness_lambda=2.5,
                edge_thickness_lambda=1.0,
            ),
            source=SourceSpec(
                waist_lambda=3.0,
                source_to_lens_lambda=6.0,
                source_phase_radius_lambda=12.0,
                lens_to_observation_lambda=8.0,
            ),
            sampling=SamplingSpec(
                compute_half_width_lambda=8.0,
                display_half_width_lambda=5.0,
                dx_lambda=1.0,
                dz_lens_lambda=1.0,
                focus_scan_dz_lambda=1.0,
            ),
            toggles=make_named_preset("fast_preview"),
        )

        response = engine.solve(request)
        self.assertEqual(response.summary.grid_shape, (17, 17))
        self.assertFalse(response.summary.use_lateral_sidewall_trace_projection)
        self.assertEqual(response.summary.ordered_interface_subcell_count, 0)
        self.assertTrue(math.isfinite(response.summary.best_focus_z_lambda))
        self.assertTrue(math.isfinite(response.summary.focus_center_amp))
        self.assertGreaterEqual(response.summary.focus_center_amp, 0.0)
        self.assertEqual(response.best_focus_ey_xy.shape, (17, 17))
        self.assertEqual(response.observation_ey_xy.shape, (17, 17))

    def test_engine_pins_internal_corrected_baseline_when_backend_supports_it(self) -> None:
        engine = KernelSolverEngine()
        request = make_large_lens_example_request(preset="external_default")
        _, design, cfg = engine.build_backend_config(request)
        self.assertEqual(cfg.sidewall_ordered_split_kind, "none")
        self.assertEqual(cfg.local_slab_localization_kind, "smooth_partition")
        self.assertEqual(cfg.local_slab_response_blend_kind, "partitioned_drive")
        self.assertEqual(cfg.local_slab_response_operator_interp_kind, "none")
        self.assertAlmostEqual(cfg.local_slab_response_thickness_alpha, 0.0)
        self.assertEqual(cfg.local_slab_depth_anchor_count_max, 4)
        self.assertAlmostEqual(cfg.local_slab_depth_anchor_phase_std_threshold, 0.75)
        self.assertTrue(cfg.use_local_slab_adaptive_confidence)
        self.assertAlmostEqual(cfg.local_slab_adaptive_confidence_ownership_threshold, 0.01)
        self.assertTrue(cfg.use_local_slab_lateral_patch_refinement)
        self.assertEqual(cfg.local_slab_lateral_patch_count_max, 4)
        self.assertAlmostEqual(cfg.local_slab_lateral_patch_x_std_threshold, 6.0 * design.lambda0)

    def test_baseline_kwarg_injection_supports_non_dataclass_constructor_signature(self) -> None:
        class NonDataclassConfig:
            def __init__(
                self,
                *,
                x: object | None = None,
                local_slab_localization_kind: str = "hard_mask",
                local_slab_response_blend_kind: str = "continuous_thickness_interp",
                local_slab_response_thickness_alpha: float = 1.0,
                local_slab_response_operator_interp_kind: str = "linear_thickness",
                local_slab_depth_anchor_count_max: int = 1,
                local_slab_depth_anchor_phase_std_threshold: float = 0.0,
                sidewall_ordered_split_kind: str = "local_fractional_interface",
                use_local_slab_adaptive_confidence: bool = False,
                local_slab_adaptive_confidence_ownership_threshold: float = 0.0,
                use_local_slab_lateral_patch_refinement: bool = False,
                local_slab_lateral_patch_count_max: int = 1,
                local_slab_lateral_patch_x_std_threshold: float = 0.0,
            ) -> None:
                del x
                del local_slab_localization_kind
                del local_slab_response_blend_kind
                del local_slab_response_thickness_alpha
                del local_slab_response_operator_interp_kind
                del local_slab_depth_anchor_count_max
                del local_slab_depth_anchor_phase_std_threshold
                del sidewall_ordered_split_kind
                del use_local_slab_adaptive_confidence
                del local_slab_adaptive_confidence_ownership_threshold
                del use_local_slab_lateral_patch_refinement
                del local_slab_lateral_patch_count_max
                del local_slab_lateral_patch_x_std_threshold

        merged = _inject_supported_solver_baseline_kwargs(NonDataclassConfig, {"x": object()}, lambda0=0.03)
        self.assertEqual(merged["sidewall_ordered_split_kind"], "none")
        self.assertEqual(merged["local_slab_localization_kind"], "smooth_partition")
        self.assertEqual(merged["local_slab_response_blend_kind"], "partitioned_drive")
        self.assertEqual(merged["local_slab_response_operator_interp_kind"], "none")
        self.assertAlmostEqual(merged["local_slab_response_thickness_alpha"], 0.0)
        self.assertEqual(merged["local_slab_depth_anchor_count_max"], 4)
        self.assertAlmostEqual(merged["local_slab_depth_anchor_phase_std_threshold"], 0.75)
        self.assertTrue(merged["use_local_slab_adaptive_confidence"])
        self.assertAlmostEqual(merged["local_slab_adaptive_confidence_ownership_threshold"], 0.01)
        self.assertTrue(merged["use_local_slab_lateral_patch_refinement"])
        self.assertEqual(merged["local_slab_lateral_patch_count_max"], 4)
        self.assertAlmostEqual(merged["local_slab_lateral_patch_x_std_threshold"], 0.18)

    def test_compare_orders_returns_finite_report(self) -> None:
        engine = KernelSolverEngine()
        request = SolverKernelRequest(
            lens=SymmetricLensSpec(
                diameter_lambda=6.0,
                center_thickness_lambda=2.5,
                edge_thickness_lambda=1.0,
            ),
            source=SourceSpec(
                waist_lambda=3.0,
                source_to_lens_lambda=6.0,
                source_phase_radius_lambda=12.0,
                lens_to_observation_lambda=8.0,
            ),
            sampling=SamplingSpec(
                compute_half_width_lambda=8.0,
                display_half_width_lambda=5.0,
                dx_lambda=1.0,
                dz_lens_lambda=1.0,
                focus_scan_dz_lambda=1.0,
            ),
            toggles=make_named_preset("external_default"),
        )

        report = engine.compare_orders(request, candidate_order=2, reference_order=4)
        self.assertEqual(report.candidate_order, 2)
        self.assertEqual(report.reference_order, 4)
        self.assertTrue(math.isfinite(report.focus_plane_rel_l2))
        self.assertTrue(math.isfinite(report.focus_centerline_rel_l2))
        self.assertTrue(math.isfinite(report.observation_plane_rel_l2))
        self.assertTrue(math.isfinite(report.runtime_ratio_vs_reference))

    def test_private_backend_adapter_is_discoverable_when_available(self) -> None:
        if str(WORKSPACE_ROOT) not in sys.path:
            sys.path.insert(0, str(WORKSPACE_ROOT))
        try:
            __import__("lens_gtmm")
        except ImportError:
            self.skipTest("private backend not available in this checkout")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(BACKEND_ENV_VAR, None)
            backend = load_backend()
        self.assertEqual(backend.module_name, "lens_gtmm")
        self.assertEqual(backend.adapter_module_name, "lens_gtmm.kernel_solver_backend")


if __name__ == "__main__":
    unittest.main()
