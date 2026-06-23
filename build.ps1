$ErrorActionPreference = "Stop"

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --clean .\ai-login-switcher.spec

Write-Host "Built:"
Get-ChildItem .\dist\
