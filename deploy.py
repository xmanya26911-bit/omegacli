#!/usr/bin/env python3
"""OMEGA Cloud Deployer — deploys OMEGA instances to remote servers."""
import os, sys, json, subprocess, argparse
from pathlib import Path

OMEGA_DIR = Path(r"D:\TERMINALCLI\omega")

def create_requirements():
    """Create minimal requirements for cloud deployment."""
    reqs = """requests>=2.28.0
pycryptodome>=3.15.0
websocket-client>=1.4.0
cryptography>=39.0.0
"""
    (OMEGA_DIR / "cloud_requirements.txt").write_text(reqs)

def generate_deploy_package():
    """Generate a ZIP of core OMEGA files for deployment."""
    import zipfile
    import io
    
    # Core files needed for remote operation
    core_files = [
        "omega_beacon.py", "evolve.py", "config.py", "memory.py",
        "tools.py", "agent.py", "llm.py", "prompts.py", "cli.py",
        "omega_evolution.py", "omega_hacker.py",
    ]
    
    package_path = OMEGA_DIR / "omega_deploy.zip"
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in core_files:
            fpath = OMEGA_DIR / fname
            if fpath.exists():
                zf.write(fpath, fname)
        # Add requirements
        create_requirements()
        zf.write(OMEGA_DIR / "cloud_requirements.txt", "requirements.txt")
    
    print(f"Deploy package created: {package_path}")
    return package_path

def deploy_to_server(host: str, username: str, password: str = "", key_file: str = ""):
    """Deploy OMEGA to a remote server via SSH."""
    package = generate_deploy_package()
    
    # Use scp to copy the package
    if key_file:
        cmd = f'scp -i "{key_file}" "{package}" {username}@{host}:~/omega_deploy.zip'
    else:
        cmd = f'scp "{package}" {username}@{host}:~/omega_deploy.zip'
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"SCP failed: {result.stderr}")
        return False
    
    # Remote setup commands
    remote_cmds = [
        "cd ~ && unzip -o omega_deploy.zip -d omega/",
        "cd ~/omega && pip install -r requirements.txt",
        "cd ~/omega && nohup python omega_beacon.py > omega_beacon.log 2>&1 &",
    ]
    
    for cmd in remote_cmds:
        if key_file:
            ssh_cmd = f'ssh -i "{key_file}" {username}@{host} "{cmd}"'
        else:
            ssh_cmd = f'ssh {username}@{host} "{cmd}"'
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Remote command failed: {cmd}: {result.stderr}")
            return False
    
    print(f"OMEGA deployed to {host}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OMEGA Cloud Deployer")
    parser.add_argument("--host", help="Remote server hostname/IP")
    parser.add_argument("--user", help="SSH username")
    parser.add_argument("--key", help="SSH key file path")
    parser.add_argument("--package", action="store_true", help="Just create deploy package")
    args = parser.parse_args()
    
    if args.package:
        generate_deploy_package()
    elif args.host and args.user:
        deploy_to_server(args.host, args.user, key_file=args.key or "")
    else:
        print("Usage:")
        print("  python deploy.py --package")
        print("  python deploy.py --host 1.2.3.4 --user root --key ~/.ssh/id_rsa")
