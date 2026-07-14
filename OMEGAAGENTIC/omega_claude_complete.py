#!/usr/bin/env python3
"""OMEGA Claude Code Complete — Missing Features Bringup.

Brings OMEGA to full Claude Code parity by adding:
  14. MCP Client (Model Context Protocol)
  15. Bulk Search & Replace
  16. Project Refactoring Engine
  17. Release Management

Usage: call init_claude_complete() at agent startup to register all new tools.
"""

import os
import sys
import re
import json
import ast
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import OMEGA's tool registration system
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import register_tool, TOOL_MAP
from omega_claude_features import (
    get_mcp_client, get_bulk_search_replace, get_refactoring_engine,
    get_release_manager, MCPClient, BulkSearchReplace, RefactoringEngine,
    ReleaseManager,
)


def _tool_result(data, is_error=False):
    """Create a ToolResult-compatible dict."""
    from tools import ToolResult
    return ToolResult(json.dumps(data, indent=2) if isinstance(data, dict) else str(data), is_error=is_error)


# ═══════════════════════════════════════════════════════════════════════════════
# MCP CLIENT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def mcp_connect(name: str, command: str, args: str = "", env: str = ""):
    """Connect to an MCP server via stdio subprocess.
    
    MCP (Model Context Protocol) servers provide tools like GitHub API, 
    database queries, Slack, Jira, and more. Connect to them and call their tools.
    
    Args:
        name: A friendly name for this connection (used to reference it later)
        command: The executable path or command to run the MCP server
        args: Space-separated arguments for the command
        env: Optional JSON string of extra environment variables
        
    Returns:
        Connection status with available tools
    """
    try:
        client = get_mcp_client()
        arg_list = args.split() if args else []
        env_dict = json.loads(env) if env else None
        result = client.connect_stdio(name, command, arg_list, env_dict)
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"MCP connection error: {e}", is_error=True)


def mcp_list_tools(connection: str = ""):
    """List available tools from MCP connections.
    
    Args:
        connection: Optional connection name. If empty, lists tools from all connections.
        
    Returns:
        Available tools from MCP servers
    """
    try:
        client = get_mcp_client()
        if connection:
            tools = client.list_tools(connection)
            return _tool_result({
                "connection": connection,
                "tool_count": len(tools),
                "tools": [{"name": t.get("name"), "description": t.get("description")} for t in tools]
            })
        else:
            statuses = client.connection_status()
            all_tools = client.list_tools()
            return _tool_result({
                "connections": statuses,
                "total_tools": len(all_tools),
                "tools": [{"connection": t.get("_connection"), "name": t.get("name"), "description": t.get("description")} for t in all_tools]
            })
    except Exception as e:
        return _tool_result(f"Error listing MCP tools: {e}", is_error=True)


def mcp_call_tool(connection: str, tool_name: str, arguments: str = ""):
    """Call a tool on an MCP server.
    
    Invokes a tool exposed by a connected MCP server. For example, call
    GitHub API tools, query databases, send Slack messages, etc.
    
    Args:
        connection: Name of the MCP connection to use
        tool_name: Name of the tool to call
        arguments: Optional JSON string of arguments to pass to the tool
        
    Returns:
        Tool execution result from the MCP server
    """
    try:
        client = get_mcp_client()
        args_dict = json.loads(arguments) if arguments else {}
        result = client.call_tool(connection, tool_name, args_dict)
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Error calling MCP tool: {e}", is_error=True)


def mcp_disconnect(connection: str = ""):
    """Disconnect from MCP server(s).
    
    Args:
        connection: Connection name to disconnect. If empty, disconnects all.
        
    Returns:
        Disconnection status
    """
    try:
        client = get_mcp_client()
        if connection:
            client.disconnect(connection)
            return _tool_result(json.dumps({"success": True, "message": f"Disconnected from '{connection}'"}))
        else:
            count = len(client._connections)
            client.disconnect()
            return _tool_result(json.dumps({"success": True, "message": f"Disconnected from all {count} MCP connections", "total": count}))
    except Exception as e:
        return _tool_result(f"Error disconnecting: {e}", is_error=True)


def mcp_status():
    """Show status of all MCP connections.
    
    Returns:
        Status of all active MCP connections with tool counts
    """
    try:
        client = get_mcp_client()
        statuses = client.connection_status()
        return _tool_result({
            "connections": statuses,
            "total": len(statuses)
        })
    except Exception as e:
        return _tool_result(f"Error: {e}", is_error=True)


# ═══════════════════════════════════════════════════════════════════════════════
# BULK SEARCH & REPLACE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def bulk_search(pattern: str, path: str = "", include: str = "*.*",
                regex: str = "true", case_sensitive: str = "true",
                max_results: str = "500"):
    """Search across project files.
    
    Performs project-wide search with regex support. Finds all occurrences
    of a pattern across files, grouped by file with line numbers.
    
    Args:
        pattern: Search pattern (regex or literal text)
        path: Directory to search (default: current directory)
        include: File glob pattern (e.g. '*.py', '*.{py,js}')
        regex: Set to 'false' for literal text search
        case_sensitive: Set to 'false' for case-insensitive
        max_results: Maximum results to return
        
    Returns:
        Search results grouped by file
    """
    try:
        engine = get_bulk_search_replace()
        result = engine.search(
            pattern=pattern,
            path=path or None,
            include=include,
            regex=regex.lower() == "true",
            case_sensitive=case_sensitive.lower() == "true",
            max_results=int(max_results),
        )
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Search error: {e}", is_error=True)


def bulk_replace(pattern: str, replacement: str, path: str = "",
                 include: str = "*.*", regex: str = "true",
                 dry_run: str = "true", commit_git: str = "false"):
    """Replace text across project files.
    
    Project-wide search-and-replace with regex support. Preview with dry_run=true,
    then execute with dry_run=false. Optionally auto-commits to git.
    
    Args:
        pattern: Search pattern (regex or literal)
        replacement: Replacement text (supports \\1 backreferences for regex)
        path: Directory to process (default: current)
        include: File glob pattern
        regex: Set to 'false' for literal replacement
        dry_run: Set to 'false' to actually modify files
        commit_git: Set to 'true' to auto-commit changes to git
        
    Returns:
        Replacement results with changed files count
    """
    try:
        engine = get_bulk_search_replace()
        result = engine.replace(
            pattern=pattern,
            replacement=replacement,
            path=path or None,
            include=include,
            regex=regex.lower() == "true",
            dry_run=dry_run.lower() == "true",
            commit_git=commit_git.lower() == "true",
        )
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Replace error: {e}", is_error=True)


# ═══════════════════════════════════════════════════════════════════════════════
# REFACTORING TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def rename_symbol(symbol: str, new_name: str, file_types: str = "",
                  path: str = "", dry_run: str = "true"):
    """Rename a symbol (variable, function, class) across the project.
    
    Uses AST parsing for Python files for accurate renaming. Falls back to 
    regex word-boundary matching for other languages.
    
    Args:
        symbol: Current symbol name to rename
        new_name: New symbol name
        file_types: Comma-separated file extensions (default: .py,.js,.ts,.jsx,.tsx)
        path: Project root (default: current directory)
        dry_run: Set to 'false' to actually perform the rename
        
    Returns:
        Rename preview or result with affected files
    """
    try:
        engine = get_refactoring_engine()
        types = [t.strip() for t in file_types.split(",") if t.strip()] if file_types else None
        result = engine.rename_symbol(
            symbol=symbol,
            new_name=new_name,
            file_types=types,
            path=path or None,
            dry_run=dry_run.lower() == "true",
        )
        return _tool_result(result)
    except Exception as e:
        return _tool_result(f"Rename error: {e}", is_error=True)


def extract_function(source_file: str, function_name: str,
                     new_file: str = "", dry_run: str = "true"):
    """Extract a function/method from one file into a new file.
    
    For Python files, preserves imports and creates a proper module.
    
    Args:
        source_file: Path to the source Python file
        function_name: Name of the function to extract
        new_file: Destination file path (auto-named if empty)
        dry_run: Set to 'false' to actually extract
        
    Returns:
        Extraction preview or result
    """
    try:
        engine = get_refactoring_engine()
        result = engine.extract_function(
            source_file=source_file,
            function_name=function_name,
            new_file=new_file or None,
            dry_run=dry_run.lower() == "true",
        )
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Extract error: {e}", is_error=True)


def split_file(source_file: str, by: str = "class", 
               output_dir: str = "", dry_run: str = "true"):
    """Split a Python file into multiple files by class or function.
    
    Creates individual files for each class/function and updates the
    original to import from the new modules.
    
    Args:
        source_file: Path to the Python file to split
        by: Split by 'class', 'function', or 'both'
        output_dir: Output directory (uses source dir if empty)
        dry_run: Set to 'false' to actually split
        
    Returns:
        Split preview or result with created files
    """
    try:
        engine = get_refactoring_engine()
        result = engine.split_file(
            source_file=source_file,
            by=by,
            output_dir=output_dir or None,
            dry_run=dry_run.lower() == "true",
        )
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Split error: {e}", is_error=True)


# ═══════════════════════════════════════════════════════════════════════════════
# RELEASE MANAGEMENT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def detect_version(path: str = ""):
    """Detect the current project version from common version files.
    
    Checks package.json, pyproject.toml, setup.cfg, setup.py, Cargo.toml,
    version.txt, and git tags.
    
    Args:
        path: Project root path (default: current directory)
        
    Returns:
        Detected version and source file
    """
    try:
        mgr = get_release_manager()
        result = mgr.detect_version(path=path or None)
        return _tool_result(result)
    except Exception as e:
        return _tool_result(f"Version detection error: {e}", is_error=True)


def bump_version(part: str = "patch", path: str = "",
                 pre_release: str = "", dry_run: str = "true"):
    """Bump the semantic version of the project.
    
    Increments major, minor, or patch version. Updates the version file,
    commits to git, and creates a tag.
    
    Args:
        part: Version part to bump: 'major', 'minor', 'patch', 
              'premajor', 'preminor', 'prepatch'
        path: Project root path
        pre_release: Pre-release tag (e.g. 'alpha', 'beta', 'rc1')
        dry_run: Set to 'false' to actually bump and tag
        
    Returns:
        Old and new version numbers
    """
    try:
        mgr = get_release_manager()
        result = mgr.bump_version(
            part=part,
            path=path or None,
            pre_release=pre_release or None,
            dry_run=dry_run.lower() == "true",
        )
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Version bump error: {e}", is_error=True)


def generate_changelog(path: str = "", from_tag: str = "",
                       to_tag: str = "HEAD", output: str = ""):
    """Generate a changelog from git history.
    
    Categorizes commits by conventional commit type (feat, fix, chore, etc.)
    and outputs organized markdown. Optionally writes to CHANGELOG.md.
    
    Args:
        path: Git repository path
        from_tag: Starting tag/ref (auto-detects last tag)
        to_tag: Ending tag/ref (default: HEAD)
        output: If set, writes changelog to this file (e.g. 'CHANGELOG.md')
        
    Returns:
        Generated changelog content
    """
    try:
        mgr = get_release_manager()
        if output:
            result = mgr.write_changelog(
                path=path or None,
                filename=output,
                from_tag=from_tag or None,
                to_tag=to_tag,
            )
        else:
            result = mgr.generate_changelog(
                path=path or None,
                from_tag=from_tag or None,
                to_tag=to_tag,
            )
        return _tool_result(result, is_error=not result.get("success"))
    except Exception as e:
        return _tool_result(f"Changelog error: {e}", is_error=True)


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION — Call this at agent startup to register all tools
# ═══════════════════════════════════════════════════════════════════════════════

def init_claude_complete():
    """Register all Claude Code Complete tools into OMEGA.
    
    Call this once at agent startup. Adds 12 new tools:
    - mcp_connect, mcp_list_tools, mcp_call_tool, mcp_disconnect, mcp_status
    - bulk_search, bulk_replace
    - rename_symbol, extract_function, split_file
    - detect_version, bump_version, generate_changelog
    """
    tools_to_register = [
        # MCP Client
        {
            "name": "mcp_connect",
            "description": "Connect to an MCP (Model Context Protocol) server via stdio. MCP servers provide tools like GitHub API, database queries, Slack, Jira. Args: name (connection name), command (executable), args (cmd args), env (JSON env vars). Returns connection status with available tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Friendly name for this connection (used to reference it later)"},
                    "command": {"type": "string", "description": "Executable path or command to run the MCP server"},
                    "args": {"type": "string", "description": "Space-separated command line arguments"},
                    "env": {"type": "string", "description": "Optional JSON string of extra environment variables"}
                },
                "required": ["name", "command"]
            },
            "func": mcp_connect,
        },
        {
            "name": "mcp_list_tools",
            "description": "List available tools from connected MCP servers. If connection is specified, lists tools from that server only. Otherwise lists tools from all active connections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "connection": {"type": "string", "description": "Optional connection name to filter by"}
                },
                "required": []
            },
            "func": mcp_list_tools,
        },
        {
            "name": "mcp_call_tool",
            "description": "Call a tool on a connected MCP server. Invokes a tool like create_github_issue, query_database, send_slack_message, etc. Args: connection (name), tool_name, arguments (JSON string).",
            "parameters": {
                "type": "object",
                "properties": {
                    "connection": {"type": "string", "description": "Connection name (from mcp_connect)"},
                    "tool_name": {"type": "string", "description": "Name of the tool to call"},
                    "arguments": {"type": "string", "description": "Optional JSON string of tool arguments"}
                },
                "required": ["connection", "tool_name"]
            },
            "func": mcp_call_tool,
        },
        {
            "name": "mcp_disconnect",
            "description": "Disconnect from MCP server(s). If connection name is provided, disconnects only that one. If empty, disconnects all active connections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "connection": {"type": "string", "description": "Connection name to disconnect (empty = all)"}
                },
                "required": []
            },
            "func": mcp_disconnect,
        },
        {
            "name": "mcp_status",
            "description": "Show status of all active MCP connections including server info and tool counts.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "func": mcp_status,
        },
        # Bulk Search & Replace
        {
            "name": "bulk_search",
            "description": "Search across project files using regex or literal text. Returns results grouped by file with line numbers. Supports file type filtering with glob patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex or literal text)"},
                    "path": {"type": "string", "description": "Directory to search (default: current directory)"},
                    "include": {"type": "string", "description": "File glob pattern, e.g. '*.py' or '*.{py,js}' (default: '*.*')"},
                    "regex": {"type": "string", "description": "Set to 'false' for literal text search (default: 'true')"},
                    "case_sensitive": {"type": "string", "description": "Set to 'false' for case-insensitive (default: 'true')"},
                    "max_results": {"type": "string", "description": "Maximum results to return (default: '500')"}
                },
                "required": ["pattern"]
            },
            "func": bulk_search,
        },
        {
            "name": "bulk_replace",
            "description": "Replace text across project files with preview and execution modes. Supports regex backreferences. Use dry_run=true to preview, dry_run=false to execute. Optionally auto-commits to git.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex or literal)"},
                    "replacement": {"type": "string", "description": "Replacement text (supports \\\\1 backreferences)"},
                    "path": {"type": "string", "description": "Directory to process (default: current)"},
                    "include": {"type": "string", "description": "File glob pattern (default: '*.*')"},
                    "regex": {"type": "string", "description": "Set to 'false' for literal replacement (default: 'true')"},
                    "dry_run": {"type": "string", "description": "Set to 'false' to modify files (default: 'true')"},
                    "commit_git": {"type": "string", "description": "Set to 'true' to auto-commit (default: 'false')"}
                },
                "required": ["pattern", "replacement"]
            },
            "func": bulk_replace,
        },
        # Refactoring
        {
            "name": "rename_symbol",
            "description": "Rename a symbol (variable, function, class) across the entire project. Uses AST for Python (accurate), regex word-boundary for other languages. Preview with dry_run=true.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Current symbol name to rename"},
                    "new_name": {"type": "string", "description": "New symbol name"},
                    "file_types": {"type": "string", "description": "Comma-separated extensions, e.g. '.py,.js,.ts' (default: Python, JS, TS, Java, C++ files)"},
                    "path": {"type": "string", "description": "Project root path (default: current)"},
                    "dry_run": {"type": "string", "description": "Set to 'false' to actually perform rename (default: 'true')"}
                },
                "required": ["symbol", "new_name"]
            },
            "func": rename_symbol,
        },
        {
            "name": "extract_function",
            "description": "Extract a function from a Python file into its own new file. Preserves imports and creates a proper module. Uses AST for accurate parsing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_file": {"type": "string", "description": "Path to the source Python file"},
                    "function_name": {"type": "string", "description": "Name of the function to extract"},
                    "new_file": {"type": "string", "description": "Destination file path (auto-named if empty)"},
                    "dry_run": {"type": "string", "description": "Set to 'false' to actually extract (default: 'true')"}
                },
                "required": ["source_file", "function_name"]
            },
            "func": extract_function,
        },
        {
            "name": "split_file",
            "description": "Split a Python file into multiple files by class or function. Creates individual files and updates the original to import from the new modules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_file": {"type": "string", "description": "Path to the Python file to split"},
                    "by": {"type": "string", "description": "Split by: 'class', 'function', or 'both' (default: 'class')"},
                    "output_dir": {"type": "string", "description": "Output directory (uses source dir if empty)"},
                    "dry_run": {"type": "string", "description": "Set to 'false' to actually split (default: 'true')"}
                },
                "required": ["source_file"]
            },
            "func": split_file,
        },
        # Release Management
        {
            "name": "detect_version",
            "description": "Detect the current project version from version files or git tags. Checks package.json, pyproject.toml, setup.cfg, setup.py, Cargo.toml, version.txt, and git describe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Project root path (default: current directory)"}
                },
                "required": []
            },
            "func": detect_version,
        },
        {
            "name": "bump_version",
            "description": "Bump the semantic version of the project. Increments major/minor/patch. Updates the version file, commits to git, and creates a tag. Preview with dry_run=true.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part": {"type": "string", "description": "Version part: 'major', 'minor', 'patch', 'premajor', 'preminor', 'prepatch'"},
                    "path": {"type": "string", "description": "Project root path"},
                    "pre_release": {"type": "string", "description": "Pre-release tag, e.g. 'alpha', 'beta', 'rc1'"},
                    "dry_run": {"type": "string", "description": "Set to 'false' to actually bump (default: 'true')"}
                },
                "required": ["part"]
            },
            "func": bump_version,
        },
        {
            "name": "generate_changelog",
            "description": "Generate a changelog from git history. Categorizes commits by conventional commit types (feat, fix, chore, refactor, docs, etc.). Optionally writes to CHANGELOG.md file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Git repository path (default: current)"},
                    "from_tag": {"type": "string", "description": "Starting tag (auto-detects last tag if empty)"},
                    "to_tag": {"type": "string", "description": "Ending tag/ref (default: 'HEAD')"},
                    "output": {"type": "string", "description": "Write to file, e.g. 'CHANGELOG.md'"}
                },
                "required": []
            },
            "func": generate_changelog,
        },
    ]
    
    registered = []
    errors = []
    for tool_def in tools_to_register:
        name = tool_def["name"]
        try:
            if name in TOOL_MAP:
                # Update existing
                TOOL_MAP[name] = tool_def["func"]
                # Also update in prompts.py TOOL_DEFINITIONS if it exists
                try:
                    from prompts import TOOL_DEFINITIONS
                    for i, td in enumerate(TOOL_DEFINITIONS):
                        if td.get("function", {}).get("name") == name:
                            TOOL_DEFINITIONS[i]["function"]["description"] = tool_def["description"]
                            TOOL_DEFINITIONS[i]["function"]["parameters"] = tool_def["parameters"]
                            break
                    else:
                        # Not found, append
                        TOOL_DEFINITIONS.append({
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": tool_def["description"],
                                "parameters": tool_def["parameters"],
                            }
                        })
                except Exception:
                    pass
                registered.append(f"{name} (updated)")
            else:
                # Use the official register_tool mechanism
                result = register_tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    parameters=tool_def["parameters"],
                    code=f"""
def {name}(**kwargs):
    from omega_claude_complete import {name}
    return {name}(**kwargs)
"""
                )
                if hasattr(result, 'is_error') and result.is_error:
                    errors.append(f"{name}: {result.content}")
                else:
                    registered.append(name)
        except Exception as e:
            errors.append(f"{name}: {e}")
    
    # Also register directly in TOOL_MAP for safety
    for tool_def in tools_to_register:
        TOOL_MAP[tool_def["name"]] = tool_def["func"]
    
    return {
        "registered": registered,
        "count": len(registered),
        "errors": errors,
        "error_count": len(errors),
    }


if __name__ == "__main__":
    result = init_claude_complete()
    print(json.dumps(result, indent=2))
