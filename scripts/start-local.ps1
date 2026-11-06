param(
    [switch]$SetupOnly,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Install Python 3.12 or newer, then run this script again.'
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Install Node.js 22 or newer, then run this script again.'
}
python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 or newer is required.' }
$nodeMajor = [int]((node --version).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 22) { throw 'Node.js 22 or newer is required.' }

$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
if (-not $SkipInstall) {
    & $venvPython -m pip install -r backend\requirements-ai.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    if (-not (Test-Path -LiteralPath 'frontend\node_modules\next')) {
        Push-Location frontend
        try {
            & npm.cmd ci
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        } finally {
            Pop-Location
        }
    }
}

$env:PYTHONUTF8 = '1'
& $venvPython .\scripts\bootstrap-models.py
if ($LASTEXITCODE -ne 0) { throw 'Model download failed; rerun to resume.' }
& powershell -ExecutionPolicy Bypass -File .\scripts\setup-vi-en.ps1
if ($LASTEXITCODE -ne 0) { throw 'Local configuration failed.' }
& $venvPython .\scripts\seed-local-account.py
if ($LASTEXITCODE -ne 0) { throw 'Could not create the local test account.' }

$credentials = Join-Path $projectRoot 'data\test-login.txt'
if (Test-Path -LiteralPath $credentials) {
    Get-Content -LiteralPath $credentials
}
if ($SetupOnly) { return }

$env:PYTHONPATH = Join-Path $projectRoot 'backend'
$stdout = Join-Path $projectRoot 'data\backend.stdout.log'
$stderr = Join-Path $projectRoot 'data\backend.stderr.log'
$backend = Start-Process -FilePath $venvPython -ArgumentList @(
    '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'
) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
try {
    $healthy = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        if ($backend.HasExited) { break }
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 2
            if ($health.status -eq 'ok') { $healthy = $true; break }
        } catch {}
    }
    if (-not $healthy) {
        throw "Backend did not start. Check $stderr"
    }
    Write-Host 'AVRT Studio: http://localhost:3000'
    Write-Host 'Press Ctrl+C to stop frontend and backend.'
    Push-Location frontend
    try {
        & npm.cmd run dev
        if ($LASTEXITCODE -ne 0) { throw 'Frontend stopped with an error.' }
    } finally {
        Pop-Location
    }
} finally {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue }
}
