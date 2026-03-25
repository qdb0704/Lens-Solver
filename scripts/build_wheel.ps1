param(
    [string]$PythonExe = "..\\python.exe"
)

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$DistDir = Join-Path $RepoRoot "dist"
$ArtifactsRoot = Join-Path $RepoRoot ".artifacts"
$TempRoot = Join-Path $ArtifactsRoot "tmp"
$BuildTracker = Join-Path $TempRoot "pip-build-tracker"
$PortableWheelBuilder = Join-Path $PSScriptRoot "build_portable_wheel.py"
$PythonCommand = $PythonExe
if (-not [System.IO.Path]::IsPathRooted($PythonCommand)) {
    $PythonCommand = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $PythonCommand))
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $ArtifactsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
New-Item -ItemType Directory -Force -Path $BuildTracker | Out-Null
Push-Location $RepoRoot
try {
    $env:TMP = $TempRoot
    $env:TEMP = $TempRoot
    $env:TMPDIR = $TempRoot
    $env:PIP_BUILD_TRACKER = $BuildTracker
    & $PythonCommand -m build --version *> $null
    if ($LASTEXITCODE -eq 0) {
        & $PythonCommand -m build --no-isolation --sdist --wheel --outdir $DistDir
        if ($LASTEXITCODE -ne 0) {
            & $PythonCommand -m pip wheel . --no-deps --no-build-isolation --wheel-dir $DistDir
            if ($LASTEXITCODE -ne 0) {
                & $PythonCommand setup.py sdist bdist_wheel
                if ($LASTEXITCODE -ne 0) {
                    throw "setup.py sdist bdist_wheel failed"
                }
            }
        }
    }
    else {
        & $PythonCommand -m pip wheel . --no-deps --no-build-isolation --wheel-dir $DistDir
        if ($LASTEXITCODE -ne 0) {
            & $PythonCommand setup.py sdist bdist_wheel
            if ($LASTEXITCODE -ne 0) {
                throw "setup.py sdist bdist_wheel failed"
            }
        }
    }
    & $PythonCommand $PortableWheelBuilder
    if ($LASTEXITCODE -ne 0) {
        throw "portable wheel build failed"
    }
}
finally {
    Pop-Location
}
