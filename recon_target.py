#!/usr/bin/env python3
"""Deep recon on grinapplepublicschool.in"""
import urllib3; urllib3.disable_warnings()
import requests as req, socket, concurrent.futures

host = 'www.grinapplepublicschool.in'
base_domain = 'grinapplepublicschool.in'

print("=" * 60)
print(f"  DEEP RECON: {host}")
print("=" * 60)

# Port scan
print("\n[PORTS]")
def check_port(p):
    try:
        s = socket.socket(); s.settimeout(3)
        r = s.connect_ex((host, p)); s.close()
        return p, r==0
    except: return p, False

ports = [21,22,25,53,80,110,143,389,443,445,993,995,1433,3306,3389,5432,8080,8443,8880,10000]
with concurrent.futures.ThreadPoolExecutor(30) as ex:
    futures = {ex.submit(check_port, p): p for p in ports}
    for f in concurrent.futures.as_completed(futures):
        p, open = f.result()
        if open: print(f"  [+] Port {p} OPEN")

# DNS records
print("\n[DNS]")
import dns.resolver
for rec in ['A', 'MX', 'NS', 'TXT', 'SOA', 'CNAME']:
    try:
        answers = dns.resolver.resolve(host, rec)
        for a in answers:
            print(f"  [+] {rec}: {a}")
    except: pass

# Subdomain discovery
print("\n[SUBDOMAINS]")
subs = ['mail', 'webmail', 'cpanel', 'cp', 'admin', 'test', 'dev', 'api', 'm', 
        'ftp', 'blog', 'shop', 'backup', 'direct', 'remote', 'server', 'ns1', 
        'ns2', 'smtp', 'pop', 'imap', 'autodiscover', 'beta', 'app', 'my', 
        'portal', 'secure', 'ssl', 'vpn', 'webdisk', 'whm', 'cloud', 'host', 
        'dns', 'mx', 'www2', 'ww2', 'www', 'forum', 'help', 'support', 'status',
        'cdn', 'static', 'media', 'img', 'files', 'download', 'email', 'web',
        'demo', 'stage', 'staging', 'prod', 'live', 'site', 'new', 'old',
        'office', 'remote', 'vpn', 'dns1', 'dns2', 'dns3', 'dns4']

for sub in subs:
    try:
        full = f'{sub}.{base_domain}'
        ip = socket.gethostbyname(full)
        try:
            s = req.Session(); s.verify=False; s.timeout=5
            s.headers.update({'User-Agent': 'Mozilla/5.0'})
            r = s.get(f'https://{full}', timeout=5)
            title = ''
            if '<title>' in r.text:
                start = r.text.find('<title>') + 7
                end = r.text.find('</title>', start)
                title = r.text[start:end][:60]
            print(f"  [+] {full:40s} -> {ip:15s} [{r.status_code}] {title}")
        except Exception as e:
            print(f"  [+] {full:40s} -> {ip:15s} [web failed: {str(e)[:30]}]")
    except:
        pass

# Try HTTP
print("\n[HTTP ALTERNATIVES]")
for proto in ['http', 'https']:
    for h in [host, base_domain, f'www.{base_domain}']:
        try:
            s = req.Session(); s.verify=False; s.timeout=5
            r = s.get(f'{proto}://{h}', timeout=5)
            print(f"  [+] {proto}://{h:40s} -> {r.status_code} ({len(r.text)} bytes)")
        except Exception as e:
            print(f"  [-] {proto}://{h:40s} -> {str(e)[:40]}")

print("\n[DONE]")
