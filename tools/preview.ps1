$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$candidates = @()
if ($env:CPO_PYTHON) { $candidates += $env:CPO_PYTHON }
$foundPython = Get-Command python -ErrorAction SilentlyContinue
if ($foundPython) { $candidates += $foundPython.Source }
$candidates += Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$pythonRuntime = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $pythonRuntime) { throw 'Python not found. Set CPO_PYTHON to your Python executable.' }
& $pythonRuntime (Join-Path $projectRoot 'assets/source/v13/START_PREVIEW.py')
exit $LASTEXITCODE
