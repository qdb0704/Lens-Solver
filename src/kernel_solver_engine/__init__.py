from .backend import BACKEND_ENV_VAR, DEFAULT_BACKEND_MODULE, BackendUnavailableError
from .engine import KernelSolverEngine
from .json_api import (
    dump_json,
    load_request_json,
    report_to_dict,
    request_from_dict,
    request_to_dict,
    response_to_public_dict,
    summary_to_dict,
)
from .models import (
    KernelPresetName,
    OrderValidationReport,
    SamplingSpec,
    SolverKernelRequest,
    SolverKernelResponse,
    SolverKernelSummary,
    SolverToggles,
    SourceSpec,
    SymmetricLensDesign,
    SymmetricLensSpec,
)
from .presets import make_large_lens_example_request, make_named_preset, with_named_preset

__all__ = [
    "BACKEND_ENV_VAR",
    "DEFAULT_BACKEND_MODULE",
    "BackendUnavailableError",
    "KernelPresetName",
    "KernelSolverEngine",
    "OrderValidationReport",
    "SamplingSpec",
    "SolverKernelRequest",
    "SolverKernelResponse",
    "SolverKernelSummary",
    "SolverToggles",
    "SourceSpec",
    "SymmetricLensDesign",
    "SymmetricLensSpec",
    "dump_json",
    "load_request_json",
    "make_large_lens_example_request",
    "make_named_preset",
    "report_to_dict",
    "request_from_dict",
    "request_to_dict",
    "response_to_public_dict",
    "summary_to_dict",
    "with_named_preset",
]
