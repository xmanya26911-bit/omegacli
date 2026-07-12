"""Analyze tools.py structure — classes, functions, categories."""
import ast
from pathlib import Path

with open("D:\\TERMINALCLI\\omega\\tools.py", "r", encoding="utf-8") as f:
    text = f.read()

tree = ast.parse(text)

# Categorize by docstring prefix and function naming patterns
categories = {
    "File/IO": [],
    "Network/HTTP": [],
    "Crypto/Hash": [],
    "System/Process": [],
    "Data/Format": [],
    "Web/Search": [],
    "Browser": [],
    "Auth/Security": [],
    "Hacking/Exploit": [],
    "DevOps/Infra": [],
    "UI/Render": [],
    "Utils/Helpers": [],
    "Other": [],
}

uncategorized = []

for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.FunctionDef):
        name = node.name
        doc = ast.get_docstring(node) or ""
        doc_first = doc.split("\n")[0].lower()
        loc = (node.end_lineno or node.lineno) - node.lineno + 1
        
        # Categorize by name prefix and docstring
        assigned = False
        if any(kw in name for kw in ["read_file", "write_file", "edit", "append", "patch", "glob", "grep", "hash", "diff", "search_file", "list_dir", "tree"]):
            cat = "File/IO"
        elif any(kw in name for kw in ["web_", "http", "fetch", "curl", "download", "url", "rest_", "api_"]):
            cat = "Network/HTTP"
        elif any(kw in name for kw in ["crypto", "encrypt", "decrypt", "hash", "aes", "rsa", "md5", "sha"]):
            cat = "Crypto/Hash"
        elif any(kw in name for kw in ["system", "process", "exec", "shell", "cmd_", "terminal", "service_", "registry"]):
            cat = "System/Process"
        elif any(kw in name for kw in ["json", "xml", "csv", "yaml", "toml", "format", "parse", "serialize"]):
            cat = "Data/Format"
        elif any(kw in name for kw in ["search", "browse", "screenshot", "navigate", "click", "type_", "scrape"]):
            cat = "Web/Search"
        elif any(kw in name for kw in ["sql", "sqli", "xss", "lfi", "rfi", "ssrf", "exploit", "payload", "reverse_shell", "webshell", "brute", "fuzz", "bypass"]):
            cat = "Hacking/Exploit"
        elif any(kw in name for kw in ["auth", "login", "jwt", "oauth", "saml", "token", "cred", "phish"]):
            cat = "Auth/Security"
        elif any(kw in name for kw in ["docker", "k8s", "deploy", "nginx", "cloud", "aws", "gcp", "azure"]):
            cat = "DevOps/Infra"
        elif any(kw in name for kw in ["render", "display", "print_", "log", "format_", "banner"]):
            cat = "UI/Render"
        elif any(kw in name for kw in ["get_", "set_", "parse", "convert", "validate", "normalize", "random", "uuid", "timer"]):
            cat = "Utils/Helpers"
        else:
            cat = "Other"
        
        categories[cat].append((name, node.lineno, loc, doc_first))

# Print analysis
print("=" * 70)
print("  tools.py STRUCTURAL ANALYSIS — 7,206 lines, 240 functions")
print("=" * 70)
print()

for cat, items in sorted(categories.items()):
    if items:
        total_loc = sum(item[2] for item in items)
        print(f"  {cat:20s}  {len(items):>4} functions  {total_loc:>5} LOC")
        for name, line, loc, doc in sorted(items)[:3]:
            print(f"    {name:40s}  line {line:>4}  {loc:>4} LOC  {doc[:50]}")
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")
        print()

print("--- UNCATEGORIZED ---")
for name, line, loc, doc in sorted(uncategorized)[:10]:
    print(f"  {name:40s}  line {line:>4}  {loc:>4} LOC  {doc[:50]}")
if uncategorized:
    print(f"  ... and {len(uncategorized) - 10} more")
print()

# Identify TOOL_MAP
print("--- TOOL_MAP ---")
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in ("TOOL_MAP", "tool_map", "tool_registry"):
                print(f"  Found at line {node.lineno}")
                # Get approximate size
                if isinstance(node.value, ast.Dict):
                    print(f"  Dict with {len(node.value.keys)} keys")
                elif isinstance(node.value, ast.Call):
                    print(f"  Call expression")
                break
