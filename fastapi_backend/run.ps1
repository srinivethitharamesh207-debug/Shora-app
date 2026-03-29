$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

python -m uvicorn app:app --reload --port 8000
