from __future__ import annotations

import base64
import csv
import hashlib
from io import StringIO
from pathlib import Path
import tomllib
import zipfile


def _normalize_dist_name(name: str) -> str:
    return name.replace("-", "_")


def _metadata_text(pyproject: dict[str, object]) -> str:
    project = dict(pyproject["project"])
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project['description']}",
        f"License-Expression: {project['license']}",
        f"Requires-Python: {project['requires-python']}",
    ]
    for author in project.get("authors", []):
        author_dict = dict(author)
        if "name" in author_dict:
            lines.append(f"Author: {author_dict['name']}")
    for dependency in project.get("dependencies", []):
        lines.append(f"Requires-Dist: {dependency}")
    lines.append("")
    return "\n".join(lines)


def _entry_points_text(pyproject: dict[str, object]) -> str:
    project = dict(pyproject["project"])
    scripts = dict(project.get("scripts", {}))
    lines = ["[console_scripts]"]
    for name, target in scripts.items():
        lines.append(f"{name} = {target}")
    lines.append("")
    return "\n".join(lines)


def _wheel_text() -> str:
    return "\n".join(
        (
            "Wheel-Version: 1.0",
            "Generator: build_portable_wheel.py",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        )
    )


def _record_row(path_name: str, payload: bytes) -> tuple[str, str, str]:
    digest = hashlib.sha256(payload).digest()
    digest_b64 = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return (path_name, f"sha256={digest_b64}", str(len(payload)))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    project = dict(pyproject["project"])
    dist_name = _normalize_dist_name(str(project["name"]))
    version = str(project["version"])
    wheel_name = f"{dist_name}-{version}-py3-none-any.whl"
    dist_info_dir = f"{dist_name}-{version}.dist-info"
    source_root = repo_root / "src" / "kernel_solver_engine"
    portable_dist = repo_root / ".artifacts" / "portable_dist"
    portable_dist.mkdir(parents=True, exist_ok=True)
    wheel_path = portable_dist / wheel_name

    file_payloads: list[tuple[str, bytes]] = []
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(repo_root / "src").as_posix()
        file_payloads.append((relative, path.read_bytes()))

    metadata_files = [
        (f"{dist_info_dir}/METADATA", _metadata_text(pyproject).encode("utf-8")),
        (f"{dist_info_dir}/WHEEL", _wheel_text().encode("utf-8")),
        (f"{dist_info_dir}/entry_points.txt", _entry_points_text(pyproject).encode("utf-8")),
        (f"{dist_info_dir}/top_level.txt", b"kernel_solver_engine\n"),
        (f"{dist_info_dir}/licenses/LICENSE", (repo_root / "LICENSE").read_bytes()),
    ]
    file_payloads.extend(metadata_files)

    record_rows = [_record_row(path_name, payload) for path_name, payload in file_payloads]
    record_buffer = StringIO()
    writer = csv.writer(record_buffer, lineterminator="\n")
    for row in record_rows:
        writer.writerow(row)
    writer.writerow((f"{dist_info_dir}/RECORD", "", ""))
    record_bytes = record_buffer.getvalue().encode("utf-8")
    file_payloads.append((f"{dist_info_dir}/RECORD", record_bytes))

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path_name, payload in file_payloads:
            archive.writestr(path_name, payload)

    print(wheel_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
