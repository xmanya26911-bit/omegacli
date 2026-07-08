# Start OMEGA Web Server
$script = "D:\TERMINALCLI\omega\omega_server.py"
$log = "D:\TERMINALCLI\omega\web_server.log"

# Kill existing if running
Get-Process -Name python* | Where-Object { $_.CommandLine -like "*omega_server*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "$script" -RedirectStandardOutput $log

Write-Host "? OMEGA Web Server started!"
Write-Host "? http://192.168.1.3:8080"
Write-Host "? Log: $log"
