param(
    [string]$PythonExe = "..\\python.exe",
    [string]$BackendModule = "lens_gtmm"
)

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$WorkspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot ".."))
$DistDir = Join-Path $RepoRoot "dist"
$ArtifactsRoot = Join-Path $RepoRoot ".artifacts"
$TargetDir = Join-Path $ArtifactsRoot "smoke_install"
$PortableDistDir = Join-Path $ArtifactsRoot "portable_dist"
$TempRoot = Join-Path $ArtifactsRoot "tmp"
$BuildTracker = Join-Path $TempRoot "pip-build-tracker"
$WheelExtract = Join-Path $PSScriptRoot "extract_wheel.py"
$SmokeCheck = Join-Path $PSScriptRoot "smoke_install_check.py"
$PythonCommand = $PythonExe
if (-not [System.IO.Path]::IsPathRooted($PythonCommand)) {
    $PythonCommand = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $PythonCommand))
}

New-Item -ItemType Directory -Force -Path $ArtifactsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
New-Item -ItemType Directory -Force -Path $BuildTracker | Out-Null
$ResolvedTarget = [System.IO.Path]::GetFullPath($TargetDir)
if (-not $ResolvedTarget.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to touch smoke-install directory outside repo root"
}
if (Test-Path -LiteralPath $TargetDir) {
    Remove-Item -LiteralPath $TargetDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

$Wheel = @(
    Get-ChildItem -Path $PortableDistDir -Filter "kernel_solver_engine-*.whl" -ErrorAction SilentlyContinue
    Get-ChildItem -Path $DistDir -Filter "kernel_solver_engine-*.whl" -ErrorAction SilentlyContinue
) | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if (-not $Wheel) {
    throw "No built wheel found in dist/. Run ./scripts/build_wheel.ps1 first."
}

$env:TMP = $TempRoot
$env:TEMP = $TempRoot
$env:TMPDIR = $TempRoot
$env:PIP_BUILD_TRACKER = $BuildTracker
& $PythonCommand $WheelExtract --wheel $Wheel.FullName --target $TargetDir
if ($LASTEXITCODE -ne 0) {
    throw "Wheel extract failed"
}

$env:KERNEL_SOLVER_BACKEND_MODULE = $BackendModule
& $PythonCommand $SmokeCheck --install-root $TargetDir --workspace-root $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
    throw "Installed-wheel smoke check failed"
}
