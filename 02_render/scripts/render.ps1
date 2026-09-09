param([string]$Action='menu',[string]$Profile='both',[string]$Job='all')
$ErrorActionPreference='Stop'
$renderRoot=Split-Path $PSScriptRoot
$blenderPath='C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
if(-not (Test-Path -LiteralPath $blenderPath)){throw 'Blender 5.2 was not found. Update blenderPath in 02_render/scripts/render.ps1.'}
if($Action -eq 'menu'){
 Write-Host 'CPO FINAL RENDER / 30fps PNG sequences'
 Write-Host '1: Check files and settings (no rendering)'
 Write-Host '2: Small test: 5 frames for each orientation'
 Write-Host '3: Final render: desktop, all clips'
 Write-Host '4: Final render: mobile, all clips'
 Write-Host '5: Final render: both orientations, all clips'
 Write-Host '6: Open output folder'
 Write-Host '0: Exit'
 $choice=Read-Host 'Select'
 switch($choice){
 '1'{$Action='check'}
 '2'{$Action='test'}
 '3'{$Action='final';$Profile='desktop'}
 '4'{$Action='final';$Profile='mobile'}
 '5'{$Action='final';$Profile='both'}
 '6'{Invoke-Item -LiteralPath (Join-Path $renderRoot 'output');exit 0}
 '0'{exit 0}
 default{throw 'Unknown selection'}
 }
}
if($Action -notin @('check','test','final')){throw 'Unknown action'}
& $blenderPath --background --python-exit-code 1 --python (Join-Path $PSScriptRoot 'render.py') -- $Action $Profile $Job
if($LASTEXITCODE -ne 0){throw "Render failed (exit $LASTEXITCODE). See output above."}
