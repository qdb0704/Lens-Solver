from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from .models import OrderValidationReport, SamplingSpec, SolverKernelRequest, SolverKernelResponse, SolverKernelSummary, SolverToggles, SourceSpec, SymmetricLensSpec


def request_to_dict(request: SolverKernelRequest) -> dict[str, object]:
    return asdict(request)


def request_from_dict(data: dict[str, object]) -> SolverKernelRequest:
    lens_data = dict(data.get("lens", {}))
    source_data = dict(data.get("source", {}))
    sampling_data = dict(data.get("sampling", {}))
    toggles_data = dict(data.get("toggles", {}))
    return SolverKernelRequest(
        f0_hz=float(data.get("f0_hz", 10.0e9)),
        lens=SymmetricLensSpec(**lens_data),
        source=SourceSpec(**source_data),
        sampling=SamplingSpec(**sampling_data),
        toggles=SolverToggles(**toggles_data),
    )


def summary_to_dict(summary: SolverKernelSummary) -> dict[str, object]:
    return summary.as_dict()


def report_to_dict(report: OrderValidationReport) -> dict[str, object]:
    return report.as_dict()


def _complex_array_to_dict(values: np.ndarray) -> dict[str, object]:
    values_use = np.asarray(values, dtype=np.complex128)
    return {"shape": list(values_use.shape), "real": values_use.real.tolist(), "imag": values_use.imag.tolist()}


def response_to_public_dict(response: SolverKernelResponse, *, include_field_arrays: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "request": request_to_dict(response.request),
        "design": asdict(response.design),
        "summary": summary_to_dict(response.summary),
        "best_focus_z": response.best_focus_z,
    }
    if include_field_arrays:
        payload["best_focus_ey_xy"] = _complex_array_to_dict(response.best_focus_ey_xy)
        payload["observation_ey_xy"] = _complex_array_to_dict(response.observation_ey_xy)
    return payload


def load_request_json(path: str | Path) -> SolverKernelRequest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("request JSON must contain an object at the top level")
    return request_from_dict(data)


def dump_json(payload: dict[str, object], path: str | Path | None = None) -> str:
    text = json.dumps(payload, indent=2, sort_keys=False)
    if path is not None:
        Path(path).write_text(text + "\n", encoding="utf-8")
    return text
