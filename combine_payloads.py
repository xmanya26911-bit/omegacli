#!/usr/bin/env python3
"""Combine all payload databases into master payload library"""
import json, os

payload_files = {
    'sqli': 'payloads_sqli.json',
    'xss': 'payloads_xss.json',
    'cmdi': 'payloads_cmdi.json',
    'lfi': 'payloads_lfi.json',
    'ssti': 'payloads_ssti.json',
}

master = {
    'total_payloads': 0,
    'categories': {},
    'payloads': {}
}

for cat, fname in payload_files.items():
    if os.path.exists(fname):
        with open(fname) as f:
            data = json.load(f)
        master['payloads'][cat] = data.get('payloads', [])
        master['categories'][cat] = len(master['payloads'][cat])
        master['total_payloads'] += len(master['payloads'][cat])
        print(f"[+] {cat}: {len(master['payloads'][cat])} payloads")
    else:
        print(f"[-] {fname} not found")

with open('payloads_master.json', 'w') as f:
    json.dump(master, f)

print(f"\n[=] TOTAL: {master['total_payloads']} payloads in master database")
print(f"[=] Categories: {json.dumps(master['categories'])}")
print(f"[+] Saved to payloads_master.json")
