# Open a .pptx in PowerPoint without a window, export every slide to PNG and the deck to PDF.
# Works on a private temporary copy, so a presentation the user already has open (even the same
# file) is never touched or closed, and never quits a PowerPoint instance the user had open.
param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Width = 3840,
  [int]$Height = 2160
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$copy = Join-Path ([System.IO.Path]::GetTempPath()) ('pcv-renderback-' + [guid]::NewGuid().ToString('N') + '.pptx')
Copy-Item -LiteralPath $Pptx -Destination $copy
$app = New-Object -ComObject PowerPoint.Application
$openBefore = $app.Presentations.Count
$pres = $null
try {
  # Open(FileName, ReadOnly, Untitled, WithWindow)
  $pres = $app.Presentations.Open($copy, -1, 0, 0)
  $n = $pres.Slides.Count
  for ($i = 1; $i -le $n; $i++) {
    $pres.Slides.Item($i).Export((Join-Path $OutDir ('slide-{0:D2}.png' -f $i)), 'PNG', $Width, $Height)
  }
  $pres.SaveCopyAs((Join-Path $OutDir 'powerpoint-export.pdf'), 32)  # ppSaveAsPDF
  Write-Output ('{"slides": ' + $n + ', "powerpoint": "' + $app.Version + '"}')
}
finally {
  if ($pres) { $pres.Close() }
  if ($openBefore -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
  Remove-Item -LiteralPath $copy -ErrorAction SilentlyContinue
}
