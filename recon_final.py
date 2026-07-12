#!/usr/bin/env python3
"""Final recon on grinapplepublicschool.in"""
import urllib3; urllib3.disable_warnings()
import requests as req, socket, concurrent.futures

host = 'www.grinapplepublicschool.in'
base = 'grinapplepublicschool.in'

print("=== PORT SCAN ===")
svc_map = {21:'FTP',22:'SSH',25:'SMTP',53:'DNS',80:'HTTP',110:'POP3',143:'IMAP',
           389:'LDAP',443:'HTTPS',445:'SMB',993:'IMAPS',995:'POP3S',
           1433:'MSSQL',3306:'MySQL',3389:'RDP',5432:'PostgreSQL',
           8080:'HTTP-Alt',8443:'HTTPS-Alt',8880:'HTTP-Alt2',10000:'Webmin'}

def check(p):
    try:
        s=socket.socket(); s.settimeout(3); r=s.connect_ex((host,p)); s.close()
        return p, r==0
    except: return p, False

with concurrent.futures.ThreadPoolExecutor(30) as ex:
    futures = {ex.submit(check,p):p for p in svc_map.keys()}
    for f in concurrent.futures.as_completed(futures):
        p,o = f.result()
        if o: print(f"  [+] {p:5d} {svc_map.get(p,'unknown')}")

print("=== HTTP HEADERS ===")
s = req.Session(); s.verify=False; s.timeout=10
s.headers.update({'User-Agent':'Mozilla/5.0'})
try:
    r = s.get('https://'+host, timeout=10)
    print(f"  Status: {r.status_code}")
    for k,v in r.headers.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(f"  Error: {e}")

print("=== DNS ===")
try:
    ip = socket.gethostbyname(host)
    print(f"  A: {ip}")
    # Try reverse
    try:
        rev = socket.gethostbyaddr(ip)
        print(f"  PTR: {rev[0]}")
    except: pass
except: print("  DNS resolution failed")

print("=== SUBDOMAIN CHECK ===")
subs = ['mail','webmail','cpanel','cp','admin','test','api','ftp','blog','shop',
        'backup','ns1','ns2','smtp','pop','imap','autodiscover','beta','app',
        'portal','secure','vpn','webdisk','whm','cloud','www2','dev','stage']
for sub in subs:
    try:
        f = f'{sub}.{base}'
        a = socket.gethostbyname(f)
        try:
            s2 = req.Session(); s2.verify=False; s2.timeout=5
            s2.headers.update({'User-Agent':'Mozilla/5.0'})
            r2 = s2.get(f'https://{f}', timeout=5)
            t = ''
            if r2.status_code == 200 and len(r2.text) > 50:
                si = r2.text.find('<title>')
                if si >= 0:
                    ei = r2.text.find('</title>', si)
                    t = r2.text[si+7:ei][:50]
            print(f"  [+] {sub:15s} -> {a:15s} [{r2.status_code}] {t}")
        except:
            print(f"  [+] {sub:15s} -> {a:15s} [web fail]")
    except:
        pass

print("=== DONE ===")
