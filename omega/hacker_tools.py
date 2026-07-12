"""
OMEGA Hacker Tools — wrappers around the omega_hacker offensive security module.

All functions follow the same pattern:
    1. Check omega_hacker loaded successfully
    2. Call the underlying omega_hacker function
    3. Return ToolResult with JSON output

Extracted from tools.py on 2026-07-11 as part of Project Ascension Phase 3.
"""

from __future__ import annotations

import json
import urllib.parse

from omega.tools import ToolResult

# ---------------------------------------------------------------------------
# Import from omega_hacker (offensive security framework)
# ---------------------------------------------------------------------------

try:
    from omega_hacker import (
        brute_force_login,
        crack_hash,
        detect_api_endpoints,
        detect_technologies,
        detect_waf,
        detect_wordpress,
        dir_bruteforce,
        exploit_cmdi_execute,
        exploit_graphql_introspection,
        exploit_lfi_read,
        exploit_sqli_extract,
        full_dns_enum,
        generate_reverse_shell,
        generate_webshell,
        generate_xss_exploit,
        hack_deep,
        hack_full,
        hack_website,
        jwt_crack,
        jwt_decode,
        scan_cmdi,
        scan_cors,
        scan_for_sensitive_files,
        scan_lfi,
        scan_ports,
        scan_sqli,
        scan_ssrf,
        scan_ssti,
        scan_xxe,
        subdomain_bruteforce,
        test_elasticsearch,
        test_mongodb,
        test_redis,
        whois_lookup,
    )
    _HAS_HACKER = True
    _HACKER_IMPORT_ERROR = None
except ImportError as e:
    _HAS_HACKER = False
    _HACKER_IMPORT_ERROR = str(e)
except Exception as e:
    _HAS_HACKER = False
    _HACKER_IMPORT_ERROR = str(e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_hacker():
    """Return ToolResult error if omega_hacker is not loaded, else None."""
    if not _HAS_HACKER:
        return ToolResult(f"! OMEGA HACKER not loaded: {_HACKER_IMPORT_ERROR}", is_error=True)
    return None


def extract_hostname(target):
    """Extract hostname from URL."""
    target = target.strip()
    if target.startswith(("http://", "https://")):
        return urllib.parse.urlparse(target).hostname
    return target.split("/")[0].split(":")[0]


# ---------------------------------------------------------------------------
# Hacker Tool Wrappers — each wraps an omega_hacker function
# ---------------------------------------------------------------------------

def hack_website_tool(target, quick=True, intense=False):
    err = _check_hacker()
    if err: return err
    try:
        import requests as _req_check
    except ImportError:
        return ToolResult("! requests library required. Run pip_install with ['requests']", is_error=True)
    try:
        result = hack_website(target, quick=quick, intense=intense)
        return ToolResult(json.dumps(result, indent=2, default=str))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def hack_full_tool(target):
    err = _check_hacker()
    if err: return err
    try:
        result = hack_full(target)
        return ToolResult(json.dumps(result, indent=2, default=str))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def hack_deep_tool(target):
    err = _check_hacker()
    if err: return err
    try:
        result = hack_deep(target)
        return ToolResult(json.dumps(result, indent=2, default=str))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_ports_tool(target, timeout=2):
    err = _check_hacker()
    if err: return err
    try:
        host = extract_hostname(target)
        results = scan_ports(host, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_sqli_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_sqli(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_xss_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_xss(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_lfi_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_lfi(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_cmdi_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_cmdi(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_ssrf_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_ssrf(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_ssti_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_ssti(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_xxe_tool(url, timeout=15):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_xxe(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_cors_tool(url, timeout=10):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_cors(url, timeout=timeout)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def crack_hash_tool(hash_value, hash_type="auto"):
    err = _check_hacker()
    if err: return err
    try:
        result = crack_hash(hash_value, hash_type)
        return ToolResult(json.dumps(result, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def jwt_crack_tool(token):
    err = _check_hacker()
    if err: return err
    try:
        result = jwt_crack(token)
        return ToolResult(json.dumps(result, indent=2, default=str))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def generate_webshell_tool(shell_type="php"):
    err = _check_hacker()
    if err: return err
    try:
        result = generate_webshell(shell_type)
        return ToolResult(json.dumps(result, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def generate_reverse_shell_tool(ip, port, shell_type="bash"):
    err = _check_hacker()
    if err: return err
    try:
        result = generate_reverse_shell(ip, port, shell_type)
        return ToolResult(json.dumps(result, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def brute_force_login_tool(login_url, username_field="username", password_field="password", max_attempts=200):
    err = _check_hacker()
    if err: return err
    try:
        result = brute_force_login(login_url, username_field=username_field, password_field=password_field, max_attempts=max_attempts)
        if result:
            return ToolResult(f"! CREDENTIALS FOUND: {result[0]['username']}:{result[0]['password']}")
        return ToolResult("No credentials found in wordlist")
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def subdomain_enum_tool(domain, max_workers=50):
    err = _check_hacker()
    if err: return err
    try:
        results = subdomain_bruteforce(domain, max_workers=max_workers)
        return ToolResult(json.dumps([{"subdomain": s, "ip": ip} for s, ip in results], indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def dir_bruteforce_tool(url, max_workers=15):
    err = _check_hacker()
    if err: return err
    try:
        results = dir_bruteforce(url, max_workers=max_workers)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def exploit_sqli_tool(url, param, technique="error"):
    err = _check_hacker()
    if err: return err
    try:
        results = exploit_sqli_extract(url, param, technique)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def exploit_lfi_tool(url, param, file_to_read="/etc/passwd"):
    err = _check_hacker()
    if err: return err
    try:
        result = exploit_lfi_read(url, param, file_to_read)
        return ToolResult(json.dumps(result, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def exploit_cmdi_tool(url, param, command="id"):
    err = _check_hacker()
    if err: return err
    try:
        result = exploit_cmdi_execute(url, param, command)
        return ToolResult(json.dumps(result, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def full_recon_tool(target):
    err = _check_hacker()
    if err: return err
    try:
        host = extract_hostname(target)
        results = {
            "dns": full_dns_enum(host),
            "whois": whois_lookup(host),
            "ports": scan_ports(host),
            "technologies": detect_technologies(target),
        }
        return ToolResult(json.dumps(results, indent=2, default=str))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def detect_waf_tool(url):
    err = _check_hacker()
    if err: return err
    try:
        results = detect_waf(url)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


def scan_sensitive_files_tool(url):
    err = _check_hacker()
    if err: return err
    try:
        results = scan_for_sensitive_files(url)
        return ToolResult(json.dumps(results, indent=2))
    except Exception as e:
        return ToolResult(f"! Error: {e}", is_error=True)


# ---------------------------------------------------------------------------
# Tool Dictionary — maps tool names to wrapper functions
# ---------------------------------------------------------------------------

_HACKER_TOOLS = {
    "hack_website": hack_website_tool,
    "hack_full": hack_full_tool,
    "hack_deep": hack_deep_tool,
    "scan_ports": scan_ports_tool,
    "scan_sqli": scan_sqli_tool,
    "scan_xss": scan_xss_tool,
    "scan_lfi": scan_lfi_tool,
    "scan_cmdi": scan_cmdi_tool,
    "scan_ssrf": scan_ssrf_tool,
    "scan_ssti": scan_ssti_tool,
    "scan_xxe": scan_xxe_tool,
    "scan_cors": scan_cors_tool,
    "crack_hash": crack_hash_tool,
    "jwt_crack": jwt_crack_tool,
    "generate_webshell": generate_webshell_tool,
    "generate_reverse_shell": generate_reverse_shell_tool,
    "brute_force_login": brute_force_login_tool,
    "subdomain_enum": subdomain_enum_tool,
    "dir_bruteforce": dir_bruteforce_tool,
    "exploit_sqli": exploit_sqli_tool,
    "exploit_lfi": exploit_lfi_tool,
    "exploit_cmdi": exploit_cmdi_tool,
    "full_recon": full_recon_tool,
    "detect_waf": detect_waf_tool,
    "scan_sensitive_files": scan_sensitive_files_tool,
}
