Write-Host "=== Spice-GUI Development Setup ==="

# Check prerequisites
try {
    $pyVersion = python --version 2>&1
    Write-Host "Using Python: $pyVersion"
} catch {
    Write-Host "ERROR: Python 3.11+ is required but not found."
    exit 1
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: GitHub CLI (gh) is required. Install from https://cli.github.com/"
    exit 1
}

$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: gh CLI is not authenticated. Run: gh auth login"
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..."
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..."
pip install -r app/requirements.txt
pip install pytest ruff

# Verify
Write-Host "Verifying test collection..."
python -m pytest --co -q 2>$null | Select-Object -Last 1

Write-Host ""
Write-Host "=== Setup complete ==="
Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
