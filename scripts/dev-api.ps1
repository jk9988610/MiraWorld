# MiraWorld local API (rapid mode) — Windows
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Server = Join-Path $Root "server"
$VenvPy = Join-Path $Server ".venv\Scripts\python.exe"
$Db = Join-Path $Root "data\miraworld.db"

if (-not (Test-Path $VenvPy)) {
  Write-Host "Creating venv + installing deps..."
  python -m venv (Join-Path $Server ".venv")
  & $VenvPy -m pip install -U pip
  & $VenvPy -m pip install -r (Join-Path $Server "requirements.txt")
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "data") | Out-Null

$env:MIRAWORLD_DB = $Db
if (-not $env:MIRAWORLD_JWT_SECRET) {
  $env:MIRAWORLD_JWT_SECRET = "dev-secret-change-me"
}
$env:MIRAWORLD_COOKIE_PATH = "/"

Write-Host "API  http://127.0.0.1:8787"
Write-Host "DB   $Db"
Write-Host "Cookie path = /  (local docs:dev)"
Set-Location $Server
& $VenvPy -m uvicorn app:app --reload --port 8787
