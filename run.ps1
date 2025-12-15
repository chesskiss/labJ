# run_all.ps1
# One-click launcher for Windows:
# - Installs Python/Node (via winget) if missing
# - Creates/uses venv and installs Python deps
# - Starts backend (uvicorn) + frontend (npm dev)
# - Opens browser at http://localhost:5173
# - Cleans up background processes on exit

$ErrorActionPreference = "Stop"
cd $PSScriptRoot

$backendProc = $null
$frontendProc = $null

function Cleanup {
    if ($backendProc -and -not $backendProc.HasExited) {
        try { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        try { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
}

try {
    Write-Host "=== Checking for winget ==="
    if (-not (Get-Command "winget" -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: winget is not available. Please install 'App Installer' from the Microsoft Store and rerun this script."
        exit 1
    }

    Write-Host "=== Checking Python installation ==="
    $hasPy      = Get-Command "py" -ErrorAction SilentlyContinue
    $hasPython  = Get-Command "python" -ErrorAction SilentlyContinue

    if (-not $hasPy -and -not $hasPython) {
        Write-Host "Python not found. Installing Python via winget..."
        winget install -e --id Python.Python.3.11 -h
    } else {
        Write-Host "Python already installed."
    }

    Write-Host "=== Checking Node.js installation ==="
    if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
        Write-Host "Node.js not found. Installing Node.js via winget..."
        winget install -e --id OpenJS.NodeJS -h
    } else {
        Write-Host "Node.js already installed."
    }

    Write-Host "=== Audio libs (PortAudio / libsndfile) ==="
    Write-Host "PortAudio/libsndfile are required for audio input. If STT fails, install them via Chocolatey (portaudio, libsndfile) or manually from upstream packages."

    Write-Host "=== Ensuring virtualenv exists ==="
    if (-not (Test-Path ".vlab")) {
        Write-Host "Creating virtualenv..."
        py -m venv .vlab
    }

    Write-Host "Activating virtualenv..."
    . .\.vlab\Scripts\Activate.ps1

    Write-Host "Installing Python requirements..."
    .\.vlab\Scripts\python.exe -m pip install -r requirements.txt

    Write-Host "=== Starting backend (uvicorn) ==="
    $backendProc = Start-Process -PassThru -WorkingDirectory $PSScriptRoot `
        -FilePath ".\.vlab\Scripts\python.exe" `
        -ArgumentList "-m","uvicorn","agents.controller:app","--host","0.0.0.0","--port","8000","--reload"

    Write-Host "=== Preparing frontend (npm install if needed) ==="
    $uiPath = Join-Path $PSScriptRoot "ui"
    if (-not (Test-Path (Join-Path $uiPath "node_modules"))) {
        Push-Location $uiPath
        npm install
        Pop-Location
    } else {
        Write-Host "node_modules present, skipping npm install (delete node_modules to force reinstall)."
    }

    Write-Host "=== Starting frontend (npm run dev) ==="
    $frontendProc = Start-Process -PassThru -WorkingDirectory $uiPath -FilePath "npm" -ArgumentList "run","dev"

    Write-Host "Opening browser at http://localhost:5173 ..."
    Start-Process "http://localhost:5173"

    Write-Host "=== Services running. Press Ctrl+C to stop. ==="
    Wait-Process -Id @($backendProc.Id, $frontendProc.Id)
}
finally {
    Cleanup
}
