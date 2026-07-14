#!/usr/bin/env python3
"""OMEGA Project Module — Claude Code-inspired project-level features.

Provides:
- OMEGA.md project config discovery and loading
- /compass project map generation
- Smart file discovery for context-aware assistance
- Diff preview and approval workflow
- Project-level cost tracking
"""

import os
import re
import json
import time
from pathlib import Path
from datetime import datetime

# ─── Exclusion Patterns ─────────────────────────────────────────────────────

IGNORE_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", ".antigravity", "node_modules",
    "venv", ".venv", ".env", "env", "backups", ".backup",
    ".vscode", ".idea", ".vs", ".DS_Store",
    "__pycache__", "site-packages", ".mypy_cache", ".pytest_cache",
    ".cache", "target", "build", "dist", ".next",
}

IGNORE_EXTS = {
    ".pyc", ".pyo", ".so", ".o", ".obj", ".lib", ".dll", ".exe",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".min.js", ".min.css",
    ".map", ".map.json",
    ".DS_Store", ".gitkeep",
}


def _is_ignored(path):
    """Check if a path should be ignored."""
    # Check if any part of the path is in IGNORE_DIRS
    parts = path.parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        if part.startswith(".") and part not in (".omega", ".github", ".claude"):
            return True
    # Check extension
    if path.suffix.lower() in IGNORE_EXTS:
        return True
    # Check for minified files
    if path.name.endswith(".min.js") or path.name.endswith(".min.css"):
        return True
    return False

# ─── OMEGA.md Discovery ──────────────────────────────────────────────────────

OMEGA_MD_FILENAMES = [
    "OMEGA.md",
    "OMEGA_GLOBAL.md",
    ".omegarc",
    "OMEGA.md",
    "omega.md",
    ".omega/config.json",
]

GLOBAL_OMEGA_MD = Path.home() / ".omega" / "OMEGA_GLOBAL.md"


def discover_omega_md(start_path=None):
    """Find OMEGA.md / CLAUDE.md files from current directory upward.
    
    Returns list of (filepath, content) tuples, nearest first.
    """
    if start_path is None:
        start_path = os.getcwd()
    
    results = []
    
    # Walk up the directory tree looking for OMEGA.md
    current = Path(start_path).resolve()
    while True:
        for name in ["OMEGA.md", "CLAUDE.md", ".claude/instructions.md", "omega.md"]:
            candidate = current / name
            if candidate.exists() and candidate.is_file():
                try:
                    content = candidate.read_text(encoding="utf-8", errors="replace")
                    results.append((str(candidate), content))
                except Exception:
                    pass
        if current.parent == current:
            break
        current = current.parent
    
    # Check global OMEGA.md
    if GLOBAL_OMEGA_MD.exists():
        try:
            content = GLOBAL_OMEGA_MD.read_text(encoding="utf-8", errors="replace")
            results.append((str(GLOBAL_OMEGA_MD), content))
        except Exception:
            pass
    
    return results


def get_project_context(start_path=None):
    """Get project-level context from OMEGA.md files.
    
    Returns a dictionary with:
    - instructions: combined instructions from all OMEGA.md files
    - files: list of (path, content) tuples
    - config: any JSON config found
    """
    if start_path is None:
        start_path = os.getcwd()
    
    context = {
        "instructions": "",
        "files": [],
        "config": {},
    }
    
    files = discover_omega_md(start_path)
    instructions_parts = []
    
    for path, content in files:
        context["files"].append((path, content))
        
        # Try to parse JSON config if file is named .omegarc or config.json
        fname = Path(path).name
        if fname in (".omegarc", "config.json") and path.endswith("omega/config.json"):
            try:
                cfg = json.loads(content)
                context["config"].update(cfg)
                continue  # Don't add JSON config to instructions
            except json.JSONDecodeError:
                pass
        
        instructions_parts.append(f"### From: {path}\n\n{content}")
    
    context["instructions"] = "\n\n".join(instructions_parts)
    return context


# ─── Compass: Project Map ──────────────────────────────────────────────────

def generate_project_map(start_path=None, max_depth=3, max_files=50):
    """Generate a project map/overview (like 'compass').
    
    Returns a formatted markdown string with:
    - Project tree
    - Key files detected
    - Git status (if in a repo)
    - Technologies detected
    """
    if start_path is None:
        start_path = os.getcwd()
    
    root = Path(start_path).resolve()
    lines = []
    lines.append(f"# 🧭 Project Map — {root.name}")
    lines.append(f"**Root:** `{root}`")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # ── Detect VCS ──
    git_dir = find_git_root(root)
    if git_dir:
        lines.append("## 🔧 Version Control")
        lines.append(f"**Repository:** `{git_dir}`")
        try:
            import subprocess
            # Get recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=str(git_dir),
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                lines.append("**Recent commits:**")
                for commit in result.stdout.strip().split("\n")[:5]:
                    lines.append(f"  • {commit}")
            # Get branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(git_dir),
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                lines.append(f"**Branch:** `{result.stdout.strip()}`")
            # Check for changes
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(git_dir),
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                changed = [l for l in result.stdout.strip().split("\n") if l.strip()]
                if changed:
                    lines.append(f"**Uncommitted changes:** {len(changed)} file(s)")
                    for f in changed[:10]:
                        lines.append(f"  • {f.strip()}")
        except Exception:
            pass
        lines.append("")
    
    # ── Directory Tree ──
    lines.append("## 📁 Directory Structure")
    
    # Build a compact tree
    tree_lines = _build_tree(root, max_depth, max_files)
    lines.extend(tree_lines)
    lines.append("")
    
    # ── Key Files ──
    lines.append("## 📄 Key Files")
    key_patterns = [
        "**/README*", "**/CONTRIBUTING*", "**/CHANGELOG*", "**/LICENSE*",
        "**/*.md", "**/*.txt", "**/Makefile", "**/Dockerfile*",
        "**/docker-compose*", "**/*.json", "**/*.yaml", "**/*.yml",
        "**/*.toml", "**/*.cfg", "**/*.ini", "**/*.conf",
        "**/setup.py", "**/setup.cfg", "**/pyproject.toml",
        "**/package.json", "**/requirements*.txt",
        "**/*.env*", "**/.gitignore", "**/*.gitkeep",
    ]
    
    found_keys = set()
    for pattern in key_patterns:
        try:
            for match in Path(root).glob(pattern):
                if _is_ignored(match):
                    continue
                rel = match.relative_to(root) if match != root else match.name
                if str(rel) not in found_keys:
                    found_keys.add(str(rel))
        except Exception:
            continue
    
    if found_keys:
        for k in sorted(found_keys)[:20]:
            lines.append(f"  • `{k}`")
        if len(found_keys) > 20:
            lines.append(f"  … and {len(found_keys) - 20} more")
    lines.append("")
    
    # ── Languages / Technologies ──
    lines.append("## 🔍 Tech Stack")
    techs = _detect_technologies(root)
    if techs:
        for tech, files in sorted(techs.items()):
            lines.append(f"  • **{tech}**: {files} file(s)")
    lines.append("")
    
    # ── OMEGA.md files ──
    omega_files = discover_omega_md(root)
    if omega_files:
        lines.append("## ⚙️ OMEGA.md Config")
        for path, _ in omega_files:
            rel = Path(path).relative_to(root) if Path(path) != root else path
            lines.append(f"  • `{rel}` — active")
        lines.append("")
    
    return "\n".join(lines)


def _build_tree(root, max_depth=3, max_files=50):
    """Build a compact directory tree string."""
    lines = []
    root_path = Path(root)
    count = [0]
    shown_dirs = set()
    
    def _walk(dir_path, depth, prefix=""):
        if depth > max_depth:
            return
        if count[0] >= max_files:
            return
        
        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}  ⚠ (no permission)")
            return
        
        visible = []
        for e in entries:
            if _is_ignored(e):
                continue
            visible.append(e)
        
        for i, entry in enumerate(visible):
            if count[0] >= max_files:
                break
            
            is_last = (i == len(visible) - 1)
            connector = "└── " if is_last else "├── "
            new_prefix = prefix + ("    " if is_last else "│   ")
            
            if entry.is_dir():
                if entry.name not in shown_dirs:
                    shown_dirs.add(entry.name)
                    lines.append(f"{prefix}{connector}📁 {entry.name}/")
                    _walk(entry, depth + 1, new_prefix)
            else:
                try:
                    size = entry.stat().st_size
                    size_str = _format_size(size)
                    lines.append(f"{prefix}{connector}📄 {entry.name}  ({size_str})")
                    count[0] += 1
                except OSError:
                    lines.append(f"{prefix}{connector}📄 {entry.name}")
                    count[0] += 1
    
    _walk(root_path, 0)
    
    if count[0] >= max_files:
        lines.append(f"  … (showing {max_files} of many files)")
    
    return lines


def _format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _detect_technologies(root):
    """Detect programming languages and frameworks used in the project."""
    tech_map = {}
    extensions_map = {
        "Python": [".py", ".pyw", ".ipynb"],
        "JavaScript": [".js", ".jsx", ".mjs"],
        "TypeScript": [".ts", ".tsx"],
        "HTML": [".html", ".htm", ".xhtml"],
        "CSS": [".css", ".scss", ".less", ".sass"],
        "Java": [".java", ".class", ".jar"],
        "C/C++": [".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"],
        "C#": [".cs", ".csx"],
        "Go": [".go"],
        "Rust": [".rs"],
        "Ruby": [".rb", ".erb"],
        "PHP": [".php", ".phtml"],
        "Swift": [".swift"],
        "Kotlin": [".kt", ".kts"],
        "Shell": [".sh", ".bash", ".zsh", ".ps1", ".bat"],
        "SQL": [".sql"],
        "Markdown": [".md", ".mdx"],
        "YAML/JSON": [".yaml", ".yml", ".json"],
        "Docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
        "Terraform": [".tf", ".tfvars"],
    }
    
    try:
        count = 0
        for dirpath, dirnames, filenames in os.walk(str(root)):
            # Prune ignored directories
            dirnames[:] = [d for d in dirnames if not _is_ignored(Path(dirpath) / d)]
            
            for fname in filenames:
                if count > 10000:
                    break
                count += 1
                fpath = Path(dirpath) / fname
                ext = fpath.suffix.lower()
                name = fpath.name
                for tech, exts in extensions_map.items():
                    if ext in exts or any(name == e or name.endswith(e) for e in exts if e.startswith(".") is False):
                        tech_map[tech] = tech_map.get(tech, 0) + 1
                        break
            if count > 10000:
                break
    except (PermissionError, OSError):
        pass
    
    return dict(sorted(tech_map.items(), key=lambda x: -x[1]))


def find_git_root(path):
    """Find the git root directory from a path."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


# ─── Smart File Discovery ──────────────────────────────────────────────────

def _walk_files(root_path, max_count=10000):
    """Iterative directory walk that skips ignored dirs.
    
    Uses os.walk which allows pruning directories at the traversal level,
    avoiding recursion into ignored directories.
    """
    root = Path(root_path).resolve()
    count = 0
    for dirpath, dirnames, filenames in os.walk(str(root)):
        # Prune ignored directories at the traversal level
        dirnames[:] = [d for d in dirnames if not _is_ignored(Path(dirpath) / d)]
        
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if _is_ignored(fpath):
                continue
            try:
                rel = str(fpath.relative_to(root))
                size = fpath.stat().st_size
                mtime = fpath.stat().st_mtime
                yield rel, size, mtime
                count += 1
                if count >= max_count:
                    return
            except (OSError, ValueError):
                continue


def smart_find_files(query, start_path=None, max_results=15):
    """Given a natural language query, find the most relevant files.
    
    Uses multiple strategies:
    1. Direct grep for terms in the query
    2. Glob patterns matching project structure
    3. Recently modified files
    4. Key config files
    """
    if start_path is None:
        start_path = os.getcwd()
    
    root = Path(start_path).resolve()
    results = []
    seen = set()
    
    # Extract keywords from query
    keywords = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', query.lower())
    # Filter out common stop words
    stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can",
                  "had", "her", "was", "one", "our", "out", "has", "have", "been",
                  "find", "show", "list", "get", "file", "files", "code", "this",
                  "that", "with", "from", "what", "which", "where", "when", "make",
                  "like", "just", "also", "how", "tell", "give", "need", "want",
                  "does", "doing", "done", "some", "any", "each", "every"}
    keywords = [k for k in keywords if k not in stop_words and len(k) > 2]
    
    # Strategy 1: Look for files matching keywords by name
    keywords_lower = [k.lower() for k in keywords[:5]]
    for rel, size, mtime in _walk_files(root, max_count=10000):
        rel_lower = rel.lower()
        for kw in keywords_lower:
            if kw in rel_lower:
                if rel not in seen and len(seen) < max_results:
                    seen.add(rel)
                    results.append((rel, "📄", size, "name-match"))
                break
    
    # Strategy 2: Look for key project files
    key_names = ["readme", "contributing", "changelog", "license",
                 "makefile", "dockerfile", "docker-compose",
                 "setup.py", "setup.cfg", "pyproject.toml",
                 "package.json", "requirements", "cargo.toml",
                 "go.mod", "gemfile", "pipfile", "cmakelists",
                 ".gitignore", ".env", "omega.md", "claude.md"]
    for rel, size, mtime in _walk_files(root, max_count=5000):
        rel_lower = rel.lower()
        for key in key_names:
            if key in rel_lower:
                if rel not in seen and len(seen) < max_results:
                    seen.add(rel)
                    results.append((rel, "⚙️", size, "key-file"))
                break
    
    # Strategy 3: Recently modified files (within last 7 days)
    now = time.time()
    for rel, size, mtime in _walk_files(root, max_count=5000):
        if rel in seen:
            continue
        if now - mtime < 7 * 86400:  # 7 days
            if len(seen) < max_results:
                seen.add(rel)
                results.append((rel, "🕐", size, "recent"))
    
    # Sort: name matches first, then key files, then recent
    priority = {"name-match": 0, "key-file": 1, "recent": 2}
    results.sort(key=lambda x: (priority.get(x[3], 99), x[0]))
    
    return results[:max_results]


def get_project_context_block(start_path=None):
    """Build a context block for the system prompt from OMEGA.md files."""
    ctx = get_project_context(start_path)
    if not ctx["instructions"]:
        return ""
    
    # Format as a context block
    block = "\n\n---\n## 📋 Project Instructions (from OMEGA.md)\n\n"
    block += ctx["instructions"]
    block += "\n---\n"
    return block


# ─── Diff Preview ──────────────────────────────────────────────────────────

def generate_diff_preview(old_content, new_content, filepath="file"):
    """Generate a unified diff between old and new content.
    
    Returns a formatted string showing the diff.
    """
    import difflib
    
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        n=3,
    )
    
    result = "".join(diff)
    if not result:
        return "  (no changes)"
    
    return result


def format_diff_for_display(diff_text, max_lines=50):
    """Format a diff for terminal display with colour indicators."""
    if not diff_text or diff_text == "  (no changes)":
        return "  (no changes)"
    
    lines = diff_text.split("\n")
    output = []
    added = 0
    removed = 0
    
    for line in lines[:max_lines]:
        if line.startswith("+") and not line.startswith("+++"):
            output.append(f"  + {line[1:]}")
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            output.append(f"  - {line[1:]}")
            removed += 1
        elif line.startswith("@@"):
            output.append(f"  {line}")
        elif line.startswith("diff --git") or line.startswith("index "):
            continue
        else:
            output.append(f"   {line}" if line.strip() else "")
    
    summary = f"\n  ┊ {added} addition(s), {removed} deletion(s)"
    if len(lines) > max_lines:
        summary += f" ({len(lines) - max_lines} more lines)"
    
    return "\n".join(output) + summary


# ─── Cost Tracking ──────────────────────────────────────────────────────────

class CostTracker:
    """Track token usage and estimated costs per session/task."""
    
    # Per-million-token pricing (approximate for OpenCode)
    INPUT_PRICE_PER_M = 0.15   # $0.15 per million input tokens
    OUTPUT_PRICE_PER_M = 0.60  # $0.60 per million output tokens
    
    def __init__(self):
        self.total_input = 0
        self.total_output = 0
        self.task_input = 0
        self.task_output = 0
        self.task_count = 0
        self._history = []
    
    def record(self, input_tokens, output_tokens, task_name=""):
        """Record token usage for a request."""
        self.total_input += input_tokens
        self.total_output += output_tokens
        self.task_input += input_tokens
        self.task_output += output_tokens
        
        entry = {
            "task": task_name or f"Request {self.task_count + 1}",
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
            "cost": self._calculate_cost(input_tokens, output_tokens),
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(entry)
        self.task_count += 1
    
    def start_task(self):
        """Start a new task tracking period."""
        self.task_input = 0
        self.task_output = 0
    
    def _calculate_cost(self, inp, out):
        """Calculate estimated cost in USD."""
        cost = (inp / 1_000_000 * self.INPUT_PRICE_PER_M +
                out / 1_000_000 * self.OUTPUT_PRICE_PER_M)
        return round(cost, 6)
    
    def get_session_summary(self):
        """Get full session cost summary."""
        if self.task_count == 0:
            return "No usage recorded."
        
        total_cost = self._calculate_cost(self.total_input, self.total_output)
        avg_cost = total_cost / self.task_count if self.task_count else 0
        
        lines = [
            f"📊 **Usage Summary** — {self.task_count} request(s)",
            f"",
            f"  • Input tokens:  {self.total_input:,}",
            f"  • Output tokens: {self.total_output:,}",
            f"  • Total tokens:  {self.total_input + self.total_output:,}",
            f"  • Est. cost:     ${total_cost:.4f}",
            f"  • Avg/request:   ${avg_cost:.6f}",
        ]
        return "\n".join(lines)
    
    def get_task_summary(self):
        """Get current task cost summary."""
        if self.task_input == 0 and self.task_output == 0:
            return ""
        
        cost = self._calculate_cost(self.task_input, self.task_output)
        total = self.task_input + self.task_output
        
        lines = [
            f"  ═ Task: {self.task_input:,} in → {self.task_output:,} out = {total:,} tok | ${cost:.4f}",
        ]
        return "\n".join(lines)


# Global cost tracker instance
_cost_tracker = CostTracker()


def get_cost_tracker():
    return _cost_tracker


# ─── OMEGA.md Generator ────────────────────────────────────────────────────

def generate_omega_md_template(project_name=""):
    """Generate a template OMEGA.md file for a project."""
    if not project_name:
        project_name = Path(os.getcwd()).name
    
    return f"""# OMEGA.md — {project_name}

## Project Overview

Brief description of what this project does.

## Architecture

Key architectural patterns and decisions.

## Conventions

- **Code style:** Describe coding conventions
- **Testing:** Testing framework and patterns
- **Naming:** Naming conventions

## Key Commands

- `make build` — Build the project
- `make test` — Run tests
- `make clean` — Clean build artifacts

## Important Files

- `src/` — Source code
- `tests/` — Test suite
- `config/` — Configuration files

## Notes for OMEGA

Add any specific instructions for how OMEGA should interact with this project.
"""


# ─── Module Exports ────────────────────────────────────────────────────────

__all__ = [
    "discover_omega_md",
    "get_project_context",
    "generate_project_map",
    "smart_find_files",
    "get_project_context_block",
    "generate_diff_preview",
    "format_diff_for_display",
    "CostTracker",
    "get_cost_tracker",
    "generate_omega_md_template",
]
