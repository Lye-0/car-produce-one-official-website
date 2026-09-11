param([string]$Action='menu',[string]$Profile='both',[string]$Job='all')
$ErrorActionPreference='Stop'
$renderRoot=Split-Path $PSScriptRoot
$blenderPath='C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$pythonPath=$env:CPO_PYTHON
if(-not $pythonPath){
 $bundled=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
 if(Test-Path -LiteralPath $bundled){$pythonPath=$bundled}
 else{$pythonPath=(Get-Command python -ErrorAction Stop).Source}
}
function Invoke-Packager([string]$Mode){
 & $pythonPath (Join-Path $PSScriptRoot 'package_media.py') $Mode $Profile $Job
 if($LASTEXITCODE -ne 0){throw "Media $Mode failed (exit $LASTEXITCODE). Existing verified files are retained."}
}
function Invoke-Renderer([string]$Mode){
 if(-not (Test-Path -LiteralPath $blenderPath)){throw 'Blender 5.2 was not found. Update blenderPath in 02_render/scripts/render.ps1.'}
 & $blenderPath --background --python-exit-code 1 --python (Join-Path $PSScriptRoot 'render.py') -- $Mode $Profile $Job
 if($LASTEXITCODE -ne 0){throw "Render failed (exit $LASTEXITCODE). Re-run the same command to resume."}
}
if($Action -eq 'menu'){
 Write-Host 'CPO PRODUCTION / 1080p 16-bit masters / HEVC + H.264 delivery'
 $encoderConfig=Get-Content -LiteralPath (Join-Path $renderRoot 'encoding.json') -Raw | ConvertFrom-Json
 Write-Host ('Video encoder: '+$encoderConfig.backend+' (NVENC = GPU)')
 Write-Host '1: Check GPU, source, disk and actual video encoders (no scene rendering)'
 Write-Host '2: Tiny technical render test'
 Write-Host '3: Full-quality short samples, stills and both encodes (both orientations)'
 Write-Host '4: FULL production: render ALL scenes + encode BOTH formats (may take days)'
 Write-Host '5: Encode existing complete production PNGs only'
 Write-Host '6: Print benchmark from quality samples'
 Write-Host '7: Activate validated COMPLETE production media on the local website'
 Write-Host '8: Open output folder'
 Write-Host '0: Exit'
 switch(Read-Host 'Select'){
  '1'{$Action='check'}
  '2'{$Action='test'}
  '3'{$Action='quality';$Profile='both';$Job='all'}
  '4'{$Action='final';$Profile='both';$Job='all'}
  '5'{$Action='encode'}
  '6'{$Action='benchmark'}
  '7'{$Action='install'}
  '8'{Invoke-Item -LiteralPath (Join-Path $renderRoot 'output');exit 0}
  '0'{exit 0}
  default{throw 'Unknown selection'}
 }
}
if($Action -notin @('check','test','quality','final','encode','benchmark','install')){throw 'Unknown action'}
if($Profile -notin @('desktop','mobile','both')){throw 'Unknown profile'}
# Keep only this job awake; restore the previous Windows execution state on every exit.
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class CpoRenderPower {
 [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);
}
"@
$previousExecutionState=[CpoRenderPower]::SetThreadExecutionState([uint32]2147483649)
try {
 switch($Action){
  'check'{Invoke-Packager 'check';Invoke-Renderer 'check'}
  'test'{Invoke-Packager 'check';Invoke-Renderer 'test'}
  'quality'{Invoke-Packager 'check';Invoke-Renderer 'quality';Invoke-Packager 'quality';Invoke-Packager 'benchmark'}
  'final'{Invoke-Packager 'check';Invoke-Renderer 'check';Invoke-Renderer 'final';Invoke-Packager 'final'}
  'encode'{Invoke-Packager 'final'}
  'benchmark'{Invoke-Packager 'benchmark'}
  'install'{Invoke-Packager 'install'}
 }
} finally {
 if($previousExecutionState){[void][CpoRenderPower]::SetThreadExecutionState($previousExecutionState)}
 else{[void][CpoRenderPower]::SetThreadExecutionState([uint32]2147483648)}
}
