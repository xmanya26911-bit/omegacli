#!/usr/bin/env python3
"""
ASAR Extractor - Extracts Electron ASAR archives
ASAR format: 4-byte header size (LE) + JSON header + file data
"""
import json
import os
import sys

def extract_asar(asar_path, output_dir):
    with open(asar_path, 'rb') as f:
        # Read header size (4 bytes, little-endian uint32)
        header_size_bytes = f.read(4)
        header_size = int.from_bytes(header_size_bytes, 'little')
        
        # Read header JSON
        header_json = f.read(header_size).decode('utf-8')
        header = json.loads(header_json)
        
        print(f"Header size: {header_size} bytes")
        print(f"Files: {count_files(header)}")
        
        # Extract files
        base_offset = 4 + header_size
        extract_files(header, f, output_dir, base_offset, "")
    
    print(f"\n✅ Extracted to: {output_dir}")

def count_files(node):
    if 'files' in node:
        return sum(count_files(v) for v in node['files'].values())
    return 1

def extract_files(node, f, output_dir, base_offset, path):
    if 'files' in node:
        for name, child in node['files'].items():
            child_path = os.path.join(path, name) if path else name
            extract_files(child, f, output_dir, base_offset, child_path)
    else:
        # It's a file
        offset = node['offset']
        size = node['size']
        executable = node.get('executable', False)
        
        out_path = os.path.join(output_dir, path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        # Seek and read
        f.seek(base_offset + offset)
        data = f.read(size)
        
        with open(out_path, 'wb') as out:
            out.write(data)
        
        if executable:
            os.chmod(out_path, 0o755)
        
        print(f"  {path} ({size} bytes)")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: extract_asar.py <input.asar> <output_dir>")
        sys.exit(1)
    
    extract_asar(sys.argv[1], sys.argv[2])
