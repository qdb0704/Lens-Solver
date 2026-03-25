from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from types import ModuleType


DEFAULT_BACKEND_MODULE = "lens_gtmm"
BACKEND_ENV_VAR = "KERNEL_SOLVER_BACKEND_MODULE"


class BackendUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackendAPI:
    module_name: str
    adapter_module_name: str | None
    FFTConvention: type
    FeedField: type
    MaterialTensor: type
    ZSlicedLensConfig: type
    ZSlicedSolverConfig: type
    solve_lens_zmarching_bulk: object
    PhysicalConstants: type
    ifft_k_to_xy: object
    propagate_spectrum: object


def _coerce_backend_api(api: object, *, module_name: str, adapter_module_name: str | None) -> BackendAPI:
    required_fields = (
        "FFTConvention",
        "FeedField",
        "MaterialTensor",
        "ZSlicedLensConfig",
        "ZSlicedSolverConfig",
        "solve_lens_zmarching_bulk",
        "PhysicalConstants",
        "ifft_k_to_xy",
        "propagate_spectrum",
    )
    missing = [name for name in required_fields if not hasattr(api, name)]
    if missing:
        joined = ", ".join(missing)
        raise BackendUnavailableError(
            f"Backend API from '{module_name}' is missing required attributes: {joined}"
        )
    return BackendAPI(
        module_name=module_name,
        adapter_module_name=adapter_module_name,
        FFTConvention=getattr(api, "FFTConvention"),
        FeedField=getattr(api, "FeedField"),
        MaterialTensor=getattr(api, "MaterialTensor"),
        ZSlicedLensConfig=getattr(api, "ZSlicedLensConfig"),
        ZSlicedSolverConfig=getattr(api, "ZSlicedSolverConfig"),
        solve_lens_zmarching_bulk=getattr(api, "solve_lens_zmarching_bulk"),
        PhysicalConstants=getattr(api, "PhysicalConstants"),
        ifft_k_to_xy=getattr(api, "ifft_k_to_xy"),
        propagate_spectrum=getattr(api, "propagate_spectrum"),
    )


def _import_optional_submodule(module_name: str, submodule_name: str) -> ModuleType | None:
    full_name = f"{module_name}.{submodule_name}"
    try:
        return importlib.import_module(full_name)
    except ModuleNotFoundError as exc:
        if exc.name == full_name:
            return None
        raise BackendUnavailableError(
            f"Backend adapter import for '{full_name}' failed while importing dependency '{exc.name}'."
        ) from exc
    except ImportError as exc:
        raise BackendUnavailableError(
            f"Backend adapter import for '{full_name}' failed."
        ) from exc


def load_backend() -> BackendAPI:
    module_name = os.environ.get(BACKEND_ENV_VAR, DEFAULT_BACKEND_MODULE)
    adapter_module = _import_optional_submodule(module_name, "kernel_solver_backend")
    if adapter_module is not None:
        factory = getattr(adapter_module, "create_backend_api", None)
        if factory is None or not callable(factory):
            raise BackendUnavailableError(
                f"Backend adapter module '{module_name}.kernel_solver_backend' does not expose create_backend_api()."
            )
        return _coerce_backend_api(
            factory(module_name=module_name),
            module_name=module_name,
            adapter_module_name=f"{module_name}.kernel_solver_backend",
        )

    try:
        backend_module = importlib.import_module(module_name)
    except ImportError as exc:
        raise BackendUnavailableError(
            f"Unable to import proprietary backend module '{module_name}'. "
            f"Install the private backend and/or set {BACKEND_ENV_VAR}."
        ) from exc

    try:
        common_module = importlib.import_module(f"{module_name}.common")
    except ImportError as exc:
        raise BackendUnavailableError(
            f"Backend module '{module_name}' does not expose the expected '.common' API."
        ) from exc

    return _coerce_backend_api(
        type(
            "LegacyBackendAPI",
            (),
            {
                "FFTConvention": backend_module.FFTConvention,
                "FeedField": backend_module.FeedField,
                "MaterialTensor": backend_module.MaterialTensor,
                "ZSlicedLensConfig": backend_module.ZSlicedLensConfig,
                "ZSlicedSolverConfig": backend_module.ZSlicedSolverConfig,
                "solve_lens_zmarching_bulk": backend_module.solve_lens_zmarching_bulk,
                "PhysicalConstants": common_module.PhysicalConstants,
                "ifft_k_to_xy": common_module.ifft_k_to_xy,
                "propagate_spectrum": common_module.propagate_spectrum,
            },
        )(),
        module_name=module_name,
        adapter_module_name=None,
    )
