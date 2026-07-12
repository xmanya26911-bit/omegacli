#!/usr/bin/env python3
"""Master payload generator - generates ALL payload types at once"""
import json, os, sys

print("=" * 60)
print("  OMEGA MASSIVE PAYLOAD GENERATOR")
print("=" * 60)

# Run all generators
generators = [
    ('SQLi', 'gen_sqli_payloads.py'),
    ('XSS', 'gen_xss_payloads.py'),
    ('CMDi', 'gen_cmdi_payloads.py'),
]

all_payloads = {}

for name, script in generators:
    print(f"\n[*] Generating {name} payloads...")
    try:
        exec(open(script).read())
        if os.path.exists(f'payloads_{name.lower()}.json'):
            with open(f'payloads_{name.lower()}.json') as f:
                data = json.load(f)
            all_payloads[name] = data['count']
            print(f"  [+] {data['count']} {name} payloads generated")
    except Exception as e:
        print(f"  [!] Error: {e}")

print("\n" + "=" * 60)
print(f"  TOTAL PAYLOADS: {sum(all_payloads.values())}")
print("=" * 60)

# Generate combined payload database
combined = {}
for name in ['sqli', 'xss', 'cmdi']:
    fname = f'payloads_{name}.json'
    if os.path.exists(fname):
        with open(fname) as f:
            data = json.load(f)
        combined[name] = data['payloads']

with open('payloads_master.json', 'w') as f:
    json.dump({
        'total': sum(len(v) for v in combined.values()),
        'categories': {k: len(v) for k, v in combined.items()},
        'payloads': combined
    }, f)

print(f"\n[+] Master payload database saved: payloads_master.json")
