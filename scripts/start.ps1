$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    $bytes = New-Object byte[] 48
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes)
    $content = (Get-Content .env -Raw).Replace('JWT_SECRET=', "JWT_SECRET=$secret")
    [IO.File]::WriteAllText((Join-Path (Get-Location) '.env'), $content, (New-Object Text.UTF8Encoding($false)))
}
$composeFiles = @('-f', 'compose.yaml')
if (Select-String -Path .env -Pattern '^(ASR|MT|TTS)_[A-Z_]+_SOURCE=(local|hf_hub|hf_remote)$' -Quiet) {
    $composeFiles += @('-f', 'compose.ai.yaml')
}
docker compose @composeFiles up --build -d
if ($LASTEXITCODE -ne 0) { throw 'Docker failed. Open Docker Desktop with WSL2 and retry.' }
Write-Host 'AVRT Studio: http://localhost:3000'
