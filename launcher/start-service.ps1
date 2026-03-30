# Start BIT-Nav Service
param([int]$Port = 8501)

$ProjectDir = Split-Path -Parent $PSScriptRoot

# Check if already running on this port
$portInUse = netstat -ano | findstr ":$Port" | findstr "LISTENING"
if ($portInUse) {
    Write-Host "Port $Port is already in use!" -ForegroundColor Yellow
    exit 0
}

# Start service
Write-Host "Starting BIT-Nav service on port $Port..." -ForegroundColor Yellow
cd $ProjectDir
python -m streamlit run app.py --server.headless true --server.port $Port
