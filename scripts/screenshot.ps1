Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logsDir = Join-Path (Split-Path $PSScriptRoot -Parent) "logs"

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Force $logsDir | Out-Null
}

$outputPath = Join-Path $logsDir "$timestamp.png"

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save($outputPath)
$graphics.Dispose()
$bitmap.Dispose()

Write-Output $outputPath
