$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $projectRoot '.env'
$originalAsrPath = Join-Path $projectRoot 'models\custom\wav2vec2-xlsr-vi-r3'
$publicAsrPath = Join-Path $projectRoot 'models\custom\wav2vec2-base-vietnamese'
$mtPath = Join-Path $projectRoot 'models\custom\opus-mt-vi-en'

$originalAsrReady = @('config.json', 'model.safetensors', 'vocab.json', 'tokenizer_config.json', 'processor_config.json') |
    ForEach-Object { Test-Path -LiteralPath (Join-Path $originalAsrPath $_) -PathType Leaf } |
    Where-Object { -not $_ }
$asrPath = if (-not $originalAsrReady) {
    $originalAsrPath
} else {
    $publicAsrPath
}
foreach ($path in @(
    (Join-Path $asrPath 'config.json'),
    (Join-Path $asrPath 'model.safetensors'),
    (Join-Path $asrPath 'vocab.json'),
    (Join-Path $asrPath 'tokenizer_config.json'),
    (Join-Path $asrPath $(if ($asrPath -eq $originalAsrPath) { 'processor_config.json' } else { 'preprocessor_config.json' })),
    (Join-Path $mtPath 'config.json'),
    (Join-Path $mtPath 'source.spm'),
    (Join-Path $mtPath 'target.spm')
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing model file: $path. Copy models/custom with the project."
    }
}
if (-not (
    (Test-Path -LiteralPath (Join-Path $mtPath 'model.safetensors') -PathType Leaf) -or
    (Test-Path -LiteralPath (Join-Path $mtPath 'pytorch_model.bin') -PathType Leaf)
)) {
    throw 'Missing MT model weights. Run scripts/bootstrap-models.py first.'
}

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination $envPath
}

$values = [ordered]@{
    DATABASE_MODE = 'sqlite'
    SQLITE_PATH = './data/avrt.sqlite3'
    INFERENCE_MODE = 'inline'
    LOCAL_MODELS_ROOT = './models/custom'
    HF_CACHE_DIR = './models/cache'
    HF_OFFLINE = 'true'
    ASR_VI_SOURCE = 'local'
    ASR_VI_MODEL_ID = if ($asrPath -eq $originalAsrPath) { 'duyhocfpt/wav2vec2-xlsr-vi-r3' } else { 'dragonSwing/wav2vec2-base-vietnamese' }
    ASR_VI_MODEL_REVISION = if ($asrPath -eq $originalAsrPath) { 'e6049c0bd63517aa6d84523d77851ba58c9b513a' } else { '2d658ec1a90820fee04e9d2edc3cf31ededa4886' }
    ASR_VI_LOCAL_PATH = Split-Path $asrPath -Leaf
    ASR_VI_ADAPTER = 'transformers_asr'
    ASR_VI_DEVICE = 'cpu'
    ASR_VI_DTYPE = 'float32'
    ASR_VI_ADAPTER_KWARGS_JSON = '{}'
    MT_VI_EN_SOURCE = 'local'
    MT_VI_EN_MODEL_ID = 'Helsinki-NLP/opus-mt-vi-en'
    MT_VI_EN_LOCAL_PATH = 'opus-mt-vi-en'
    MT_VI_EN_ADAPTER = 'seq2seq'
    MT_VI_EN_DEVICE = 'cpu'
    MT_VI_EN_DTYPE = 'float32'
}

$content = [IO.File]::ReadAllText($envPath)
if ($content -match '(?m)^JWT_SECRET=\s*$') {
    $bytes = New-Object byte[] 48
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $values['JWT_SECRET'] = [Convert]::ToBase64String($bytes)
}
foreach ($entry in $values.GetEnumerator()) {
    $pattern = '(?m)^' + [regex]::Escape($entry.Key) + '=.*$'
    if (-not [regex]::IsMatch($content, $pattern)) {
        if ($entry.Key -eq 'SQLITE_PATH') {
            $content = $content.TrimEnd() + "`r`n# Local persistent database; path is relative to the project root.`r`nSQLITE_PATH=$($entry.Value)`r`n"
            continue
        }
        throw "Missing $($entry.Key) in .env. Refresh it from .env.example."
    }
    $content = [regex]::Replace($content, $pattern, "$($entry.Key)=$($entry.Value)")
}
[IO.File]::WriteAllText($envPath, $content, (New-Object Text.UTF8Encoding($false)))
Write-Host 'Vietnamese ASR and Vietnamese-to-English MT are configured for offline local inference.'
Write-Host 'Run the backend and frontend as described in README.md.'
