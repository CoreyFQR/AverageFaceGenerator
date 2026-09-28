# Build the smaller single-file EXE that bundles the FP16 gender model
# (models/realistic_gender_fp16.onnx, ~173MB) under models/realistic_gender.onnx.
# Result: dist\AverageFaceGenerator_v1.0.0_lite.exe. The FP32 model is restored
# afterwards so the default development tree keeps the full-precision file.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$fp32File = Join-Path $PSScriptRoot 'models\realistic_gender.onnx'
$fp16File = Join-Path $PSScriptRoot 'models\realistic_gender_fp16.onnx'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Build venv is missing; run build.ps1 once first (or create .venv).' }
if (-not (Test-Path -LiteralPath $fp16File)) { throw 'FP16 gender model missing; run tools/prepare_gender_model.py first.' }
if (-not (Test-Path -LiteralPath $fp32File)) { throw 'FP32 gender model missing; run tools/prepare_gender_model.py first.' }

$backup = Join-Path $env:TEMP ("avgface-fp32-" + [guid]::NewGuid().ToString('N') + ".onnx")
Copy-Item -LiteralPath $fp32File -Destination $backup
try {
    Copy-Item -LiteralPath $fp16File -Destination $fp32File -Force
    & $pythonPath -m PyInstaller --clean --noconfirm AvgFace.spec
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    & $pythonPath tools/build_launcher.py --lite --output (Join-Path $PSScriptRoot 'dist\AverageFaceGenerator_v1.0.0_lite.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Single-file launcher failed.' }
    $out = Join-Path $PSScriptRoot 'dist\AverageFaceGenerator_v1.0.0_lite.exe'
    $h = (Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLower()
    Set-Content -Path "$out.sha256" -Value "$h  AverageFaceGenerator_v1.0.0_lite.exe" -Encoding ascii
    Write-Host ("FP16 EXE SHA-256: " + $h)
} finally {
    Copy-Item -LiteralPath $backup -Destination $fp32File -Force
    Remove-Item -LiteralPath $backup -Force
}
Write-Host 'Ready: dist\AverageFaceGenerator_v1.0.0_lite.exe (FP16 gender model; no runtime downloads)'
