$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 x64 is required on the build machine.' }
}
& $pythonPath -m pip install --disable-pip-version-check --no-input -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $pythonPath tools/prepare_alternatives.py
if ($LASTEXITCODE -ne 0) { throw 'Model preparation failed.' }
& $pythonPath tools/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
& $pythonPath tools/prepare_font.py
if ($LASTEXITCODE -ne 0) { throw 'Font preparation failed.' }
$testRoot = Join-Path $PSScriptRoot 'artifacts'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$pytestTemp = Join-Path $testRoot ('build-pytest-' + [guid]::NewGuid().ToString('N'))
& $pythonPath -m pytest -q --basetemp $pytestTemp
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $pythonPath -m PyInstaller --clean --noconfirm AvgFace.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
& $pythonPath tools/build_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Single-file launcher failed.' }
Write-Host 'Ready: dist\AverageFaceGenerator_v1.0.0.exe (models included; no runtime downloads)'
