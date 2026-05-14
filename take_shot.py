import subprocess, time, os, sys
from pathlib import Path

# Take screenshot using PowerShell
timestamp = time.strftime("%Y-%m-%d_%H-%M")
out_dir = Path("logs")
out_dir.mkdir(exist_ok=True)
out_path = out_dir / f"{timestamp}.png"

ps_cmd = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('{str(out_path).replace(chr(92), chr(92)+chr(92))}')
$g.Dispose()
$bmp.Dispose()
"""

result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
if result.returncode == 0:
    print(f"OK: {out_path}")
else:
    print(f"ERR: {result.stderr}")
