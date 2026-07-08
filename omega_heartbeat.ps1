$logPath = "D:\TERMINALCLI\omega\omega_log.txt"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
try {
    $ip = (Invoke-WebRequest -Uri "https://ifconfig.me" -UseBasicParsing -TimeoutSec 10).Content
    Add-Content -Path $logPath -Value "[$date] HEARTBEAT: $ip"
} catch {
    Add-Content -Path $logPath -Value "[$date] HEARTBEAT: LOCAL_ONLY - $_"
}
