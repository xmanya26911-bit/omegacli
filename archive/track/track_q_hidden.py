import requests, json, re, sys

print('=== TRACK Q: THE HIDDEN PASSWORD FIELD ===')
print()

s = requests.Session()

# 1. Get the forgot password page and extract the usi token
print('1. Extract usi token from ForgotPasswd')
r = s.get('https://accounts.google.com/ForgotPasswd', timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')

usi_pat = re.compile(r'name="usi" value="([^"]+)"')
usi_match = usi_pat.search(r.text)
if usi_match:
    usi = usi_match.group(1)
    print(f'  usi token: {usi}')
    
    bg_pat = re.compile(r'name="bgresponse" value="([^"]+)"')
    bg_match = bg_pat.search(r.text)
    if bg_match:
        print(f'  bgresponse: {bg_match.group(1)}')
    
    domain_pat = re.compile(r'name="domain" value="([^"]+)"')
    domain_match = domain_pat.search(r.text)
    if domain_match:
        print(f'  domain: {domain_match.group(1)}')
else:
    print('  No usi token found')

# 2. Try signin/recovery page
print()
print('2. Recovery page analysis')
r = s.get('https://accounts.google.com/signin/recovery', params={'hl': 'en'}, timeout=10)
print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')

# 3. Analyze sign-in page auth flows
print()
print('3. Sign-in page analysis')
r = s.get('https://accounts.google.com/ServiceLogin', params={'hl': 'en'}, timeout=10)
text_lower = r.text.lower()
pw_cnt = text_lower.count('password')
pk_cnt = text_lower.count('passkey')
wa_cnt = text_lower.count('webauthn')
print(f'  "password" mentioned: {pw_cnt} times')
print(f'  "passkey" mentioned: {pk_cnt} times')
print(f'  "webauthn" mentioned: {wa_cnt} times')

# 4. Try service login with email pre-filled
print()
print('4. ServiceLogin with email parameter')
r = s.get('https://accounts.google.com/ServiceLogin', params={
    'service': 'mail',
    'continue': 'https://mail.google.com/mail/',
    'Email': 'test@gmail.com',
    'flowName': 'GlifWebSignIn',
    'flowEntry': 'ServiceLogin'
}, timeout=10)

text = r.text.lower()
if 'identifier' in text and 'password' in text:
    print('  Shows BOTH email and password fields')
elif 'password' in text and 'identifier' not in text:
    print('  *** ONLY PASSWORD FIELD - SKIPPED EMAIL STEP! ***')
elif 'identifier' in text and 'password' not in text:
    print('  Only email field shown')
else:
    print('  Page structure unclear')

# 5. Try usi token replay
print()
print('5. usi token replay test')
if usi_match:
    usi = usi_match.group(1)
    r = s.post('https://accounts.google.com/ForgotPasswd', data={
        'usi': usi,
        'Email': 'test@gmail.com',
        'domain': '',
        'region': 'IN',
        'hiddenPassword': '',
        'bgresponse': 'js_disabled'
    }, timeout=10)
    print(f'  HTTP {r.status_code} ({len(r.text)} bytes)')
    print(f'  Response: {r.text[:300]}')

# 6. Try the OAuth out-of-band flow (urn:ietf:wg:oauth:2.0:oob)
print()
print('6. OAuth out-of-band flow')
oob_url = 'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=77185425430.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob&scope=https://mail.google.com/'
r = requests.get(oob_url, allow_redirects=False, timeout=10)
print(f'  HTTP {r.status_code} loc={r.headers.get("Location", "")[:150]}')

# 7. Try OOB auto (returns code in page title)
print()
print('7. OOB auto flow')
oob_auto = 'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=77185425430.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob:auto&scope=https://mail.google.com/'
r = requests.get(oob_auto, allow_redirects=False, timeout=10)
print(f'  HTTP {r.status_code} loc={r.headers.get("Location", "")[:150]}')

# 8. Try localhost with specific port
print()
print('8. localhost with specific port redirect')
for port in ['80', '8080', '3000', '5000', '9000']:
    url = f'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=77185425430.apps.googleusercontent.com&redirect_uri=http://localhost:{port}&scope=https://mail.google.com/'
    r = requests.get(url, allow_redirects=False, timeout=10)
    loc = r.headers.get("Location", "")
    if 'signin' in loc or 'error' in loc:
        status = 'redirect to signin/error'
    else:
        status = loc[:80]
    print(f'  port {port}: HTTP {r.status_code} - {status}')
