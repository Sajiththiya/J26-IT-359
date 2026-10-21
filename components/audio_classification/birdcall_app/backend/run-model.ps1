$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:DEMO_MODE = 'false'
# Use the app's pinned finalized Wav2Vec2 run, regardless of an old shell setting.
Remove-Item Env:MODEL_PATH -ErrorAction SilentlyContinue
& .\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
