#!/usr/bin/env python3
"""OMEGA Memory System — Persistent long-term and short-term memory with search.
   ENHANCED with TOTAL RECALL: auto-save everything, cross-session persistence,
   full conversation history indexing, and intelligent recall."""

import os
import re
import json
import time
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock, Thread
from collections import defaultdict, deque

MEMORY_DIR = Path.home() / ".omega" / "memory"
TOTAL_RECALL_DIR = MEMORY_DIR / "total_recall"

# =============================================================================
# PART 1: PERSISTENT MEMORY (Facts + Notes) — enhanced with tags & search
# =============================================================================

class PersistentMemory:
    """Persistent, thread-safe memory using JSON files."""

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        TOTAL_RECALL_DIR.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self._facts_path = MEMORY_DIR / "facts.json"
        self._notes_path = MEMORY_DIR / "notes.json"
        self._log_path = MEMORY_DIR / "history.log"
        self._facts = {}
        self._notes = []
        self._load()

    def _load(self):
        """Load facts and notes from disk."""
        if self._facts_path.exists():
            try:
                self._facts = json.loads(self._facts_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._facts = {}
        if self._notes_path.exists():
            try:
                self._notes = json.loads(self._notes_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._notes = []

    def _save_facts(self):
        """Save facts atomically."""
        tmp = self._facts_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._facts, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp.replace(self._facts_path)

    def _save_notes(self):
        """Save notes atomically."""
        tmp = self._notes_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._notes, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp.replace(self._notes_path)

    def _log(self, action, detail=""):
        """Append to activity log."""
        try:
            ts = datetime.now().isoformat()
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {action}: {detail}\n")
        except OSError:
            pass

    def remember(self, key, value, tags=None):
        """Save a fact to persistent memory."""
        with self.lock:
            now = datetime.now().isoformat()
            if key in self._facts:
                self._facts[key]["value"] = value
                self._facts[key]["updated"] = now
                if tags:
                    existing = set(self._facts[key].get("tags", []))
                    existing.update(tags)
                    self._facts[key]["tags"] = list(existing)
            else:
                self._facts[key] = {
                    "value": value,
                    "tags": tags or [],
                    "created": now,
                    "updated": now,
                }
            self._save_facts()
            self._log("remember", f"{key}={value[:100]}")
            return f"✓ Remembered: {key}"

    def recall(self, key):
        """Retrieve a specific memory by key."""
        with self.lock:
            if key in self._facts:
                f = self._facts[key]
                result = f"Key: {key}\nValue: {f['value']}"
                if f.get("tags"):
                    result += f"\nTags: {', '.join(f['tags'])}"
                result += f"\nCreated: {f['created']}\nUpdated: {f['updated']}"
                return result

            # Fuzzy match: suggest similar keys
            similar = [k for k in self._facts if key.lower() in k.lower()]
            if similar:
                return f"Not found: '{key}'. Did you mean: {', '.join(similar[:5])}?"
            return f"No memory found for key: {key}"

    def forget(self, key):
        """Delete a memory by key."""
        with self.lock:
            if key in self._facts:
                del self._facts[key]
                self._save_facts()
                self._log("forget", key)
                return f"✓ Forgotten: {key}"
            return f"No memory found for key: {key}"

    def list_memories(self, tag=None):
        """List all memories, optionally filtered by tag."""
        with self.lock:
            if not self._facts:
                return "No memories stored yet."
            items = []
            for key, f in sorted(self._facts.items()):
                if tag and tag not in f.get("tags", []):
                    continue
                value_preview = f["value"][:80].replace("\n", " ")
                tags = f.get("tags", [])
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                items.append(f"  {key}: {value_preview}{tag_str}")
            if not items:
                return f"No memories with tag: {tag}"
            header = f"Stored memories ({len(items)}):"
            return header + "\n" + "\n".join(items)

    def search(self, query):
        """Search memories and notes by relevance scoring."""
        with self.lock:
            results = []
            q = query.lower()
            q_words = set(q.split())

            # Search facts
            for key, f in self._facts.items():
                score = 0
                if q in key.lower():
                    score += 10
                key_words = set(key.lower().split())
                score += len(q_words & key_words) * 3
                if q in f["value"].lower():
                    score += 5
                value_words = set(f["value"].lower().split())
                score += len(q_words & value_words) * 2
                for t in f.get("tags", []):
                    if q in t.lower():
                        score += 3
                if score > 0:
                    results.append({
                        "type": "fact",
                        "key": key,
                        "value": f["value"][:200],
                        "score": score,
                        "tags": f.get("tags", []),
                        "updated": f["updated"],
                    })

            # Search notes
            for note in self._notes:
                score = 0
                title = note.get("title", "")
                content = note.get("content", "")
                if q in title.lower():
                    score += 8
                if q in content.lower():
                    score += 4
                title_words = set(title.lower().split())
                score += len(q_words & title_words) * 3
                content_words = set(content.lower().split())
                score += len(q_words & content_words) * 1
                for t in note.get("tags", []):
                    if q in t.lower():
                        score += 2
                if score > 0:
                    results.append({
                        "type": "note",
                        "key": title,
                        "value": content[:200],
                        "score": score,
                        "tags": note.get("tags", []),
                        "updated": note.get("updated", ""),
                    })

            results.sort(key=lambda r: -r["score"])

            if not results:
                return f"No memories matching '{query}'"

            output = f"Memory search results for '{query}' ({len(results)} matches):\n"
            for r in results[:20]:
                tag_str = f" [{', '.join(r['tags'])}]" if r["tags"] else ""
                output += f"\n  [{r['type']}] {r['key']}{tag_str}\n"
                output += f"    {r['value'][:120]}"
            return output

    def save_note(self, title, content, tags=None):
        """Save a longer document/note."""
        with self.lock:
            now = datetime.now().isoformat()
            for note in self._notes:
                if note["title"] == title:
                    note["content"] = content
                    note["updated"] = now
                    if tags:
                        existing = set(note.get("tags", []))
                        existing.update(tags)
                        note["tags"] = list(existing)
                    self._save_notes()
                    self._log("update_note", title)
                    return f"✓ Updated note: {title}"
            self._notes.append({
                "title": title,
                "content": content,
                "tags": tags or [],
                "created": now,
                "updated": now,
            })
            self._save_notes()
            self._log("save_note", title)
            return f"✓ Saved note: {title}"

    def read_note(self, title):
        """Read a saved note by title."""
        with self.lock:
            for note in self._notes:
                if note["title"] == title:
                    result = f"Title: {note['title']}"
                    if note.get("tags"):
                        result += f"\nTags: {', '.join(note['tags'])}"
                    result += f"\nCreated: {note['created']}\n"
                    result += f"\n{note['content']}"
                    return result
            similar = [n["title"] for n in self._notes if title.lower() in n["title"].lower()]
            if similar:
                return f"Not found: '{title}'. Did you mean: {', '.join(similar[:5])}?"
            return f"No note found: {title}"

    def delete_note(self, title):
        """Delete a note by title."""
        with self.lock:
            for i, note in enumerate(self._notes):
                if note["title"] == title:
                    self._notes.pop(i)
                    self._save_notes()
                    self._log("delete_note", title)
                    return f"✓ Deleted note: {title}"
            return f"No note found: {title}"

    def list_notes(self, tag=None):
        """List all notes, optionally filtered by tag."""
        with self.lock:
            if not self._notes:
                return "No notes saved yet."
            items = []
            for note in self._notes:
                if tag and tag not in note.get("tags", []):
                    continue
                title = note["title"]
                preview = note["content"][:60].replace("\n", " ")
                tags = note.get("tags", [])
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                items.append(f"  {title}: {preview}{tag_str}")
            if not items:
                return f"No notes with tag: {tag}"
            return f"Notes ({len(items)}):\n" + "\n".join(items)

    def export_all(self):
        """Export all facts and notes as a JSON-serializable dict."""
        with self.lock:
            return {
                "version": 2,
                "exported_at": datetime.now().isoformat(),
                "facts": dict(self._facts),
                "notes": list(self._notes),
            }

    def import_all(self, data):
        """Import facts and notes from an export dict. Returns summary string."""
        with self.lock:
            facts_count = 0
            if "facts" in data:
                for key, val in data["facts"].items():
                    if key not in self._facts:
                        self._facts[key] = val
                        facts_count += 1
            notes_count = 0
            if "notes" in data:
                existing_titles = {n["title"] for n in self._notes}
                for note in data["notes"]:
                    if note["title"] not in existing_titles:
                        self._notes.append(note)
                        notes_count += 1
                        existing_titles.add(note["title"])
            self._save_facts()
            self._save_notes()
            return f"Imported {facts_count} facts and {notes_count} notes (skipped duplicates)"

    def get_relevant_context(self, query, max_items=5):
        """Get relevant memory context for a user query (for injection into system prompt)."""
        if not query:
            return ""
        with self.lock:
            results = []
            q = query.lower()
            q_words = set(q.split())

            for key, f in self._facts.items():
                score = 0
                if q in key.lower():
                    score += 3
                for word in q_words:
                    if word in key.lower():
                        score += 2
                    if word in f["value"].lower():
                        score += 1
                if score > 0:
                    results.append(("fact", key, f["value"][:200], score))

            for note in self._notes:
                score = 0
                title = note.get("title", "")
                content = note.get("content", "")
                if q in title.lower():
                    score += 3
                for word in q_words:
                    if word in title.lower():
                        score += 2
                    if word in content.lower():
                        score += 1
                if score > 0:
                    results.append(("note", title, content[:200], score))

            results.sort(key=lambda r: -r[3])
            if not results:
                return ""
            context = "\n[Relevant memories for this request]:\n"
            for typ, key, val, _ in results[:max_items]:
                val_short = val[:150]
                context += f"  [{typ}] {key}: {val_short}\n"
            return context


# =============================================================================
# PART 2: TOTAL RECALL — Auto-save everything, full conversation history
# =============================================================================

class ConversationLogger:
    """Append-only logger that records EVERY interaction permanently.
    
    Each conversation turn is logged as a JSON line (JSONL format) in 
    daily compressed log files under ~/.omega/memory/total_recall/.
    
    Structure:
      total_recall/
        conversations/          # Daily JSONL conversation logs
          conv_2026-01-01.jsonl.gz
          conv_2026-01-02.jsonl.gz
        index.json              # Search index for fast retrieval
        sessions/               # Full session snapshots (auto-saved)
          session_20260101_120000.json.gz
    """
    
    def __init__(self):
        TOTAL_RECALL_DIR.mkdir(parents=True, exist_ok=True)
        self._conv_dir = TOTAL_RECALL_DIR / "conversations"
        self._conv_dir.mkdir(parents=True, exist_ok=True)
        self._session_dir = TOTAL_RECALL_DIR / "sessions"
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = TOTAL_RECALL_DIR / "index.json"
        self._lock = Lock()
        self._today = None
        self._current_log = None  # Current file handle
        self._index = self._load_index()
        self._turn_count = 0
        self._session_id = None
        
    def _load_index(self):
        """Load the search index from disk."""
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "version": 2,
            "created": datetime.now().isoformat(),
            "total_turns": 0,
            "total_sessions": 0,
            "topics": {},          # topic -> count
            "tools_used": {},      # tool_name -> count
            "last_updated": datetime.now().isoformat(),
        }
    
    def _save_index(self):
        """Save the search index atomically."""
        self._index["last_updated"] = datetime.now().isoformat()
        tmp = self._index_path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(self._index, indent=2, ensure_ascii=False), 
                encoding="utf-8"
            )
            tmp.replace(self._index_path)
        except OSError:
            pass
    
    def _get_log_path(self, date=None):
        """Get the path for today's conversation log file."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self._conv_dir / f"conv_{date}.jsonl.gz"
    
    def _ensure_log_file(self):
        """Ensure the current log file is open and ready."""
        import time as _time
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._today or self._current_log is None:
            if self._current_log is not None:
                try:
                    self._current_log.close()
                except Exception:
                    pass
            self._today = today
            log_path = self._get_log_path(today)
            # Retry with backoff if file is locked by another process
            for attempt in range(5):
                try:
                    self._current_log = gzip.open(str(log_path), "at", encoding="utf-8", newline="")
                    break
                except PermissionError:
                    if attempt < 4:
                        _time.sleep(0.5 * (attempt + 1))
                    else:
                        # Fallback: per-process temp file
                        tmp = str(log_path) + f".{os.getpid()}.tmp"
                        self._current_log = gzip.open(tmp, "wt", encoding="utf-8", newline="")
        return self._current_log
    
    def log_interaction(self, turn_data):
        """Record a complete interaction turn (user msg + assistant response + tool calls).
        
        Args:
            turn_data: dict with keys:
                - timestamp: ISO datetime
                - user: str (user message)
                - assistant: str or None (assistant text response)
                - tool_calls: list of {name, arguments, result, duration} or None
                - summary: str or None (auto-generated summary of this turn)
        """
        with self._lock:
            # Ensure all fields
            entry = {
                "timestamp": turn_data.get("timestamp", datetime.now().isoformat()),
                "session_id": self._session_id,
                "turn_number": self._turn_count,
                "user": turn_data.get("user", ""),
                "assistant": turn_data.get("assistant", ""),
                "tool_calls": turn_data.get("tool_calls") or [],
                "summary": turn_data.get("summary", ""),
            }
            
            # Write to today's compressed log
            logfile = self._ensure_log_file()
            line = json.dumps(entry, ensure_ascii=False)
            logfile.write(line + "\n")
            logfile.flush()
            
            # Update index stats
            self._index["total_turns"] += 1
            if entry["summary"]:
                for word in entry["summary"].lower().split()[:20]:
                    pass  # We could extract topics here if needed
            for tc in (turn_data.get("tool_calls") or []):
                name = tc.get("name", "unknown")
                self._index["tools_used"][name] = self._index["tools_used"].get(name, 0) + 1
            
            self._turn_count += 1
            self._save_index()
    
    def log_session_start(self):
        """Start a new session and record it in the index."""
        now = datetime.now()
        self._session_id = now.strftime("S%Y%m%d_%H%M%S_%f")
        self._turn_count = 0
        
        # Save session metadata to index
        if "sessions" not in self._index:
            self._index["sessions"] = {}
        self._index["sessions"][self._session_id] = {
            "started": now.isoformat(),
            "turns": 0,
            "date": now.strftime("%Y-%m-%d"),
        }
        self._index["total_sessions"] = len(self._index["sessions"])
        self._save_index()
        return self._session_id
    
    def log_session_end(self, summary=""):
        """Record session end time and save a full snapshot."""
        if not self._session_id:
            return
        with self._lock:
            now = datetime.now().isoformat()
            if "sessions" in self._index and self._session_id in self._index["sessions"]:
                self._index["sessions"][self._session_id]["ended"] = now
                self._index["sessions"][self._session_id]["turns"] = self._turn_count
                self._index["sessions"][self._session_id]["summary"] = summary[:200]
                self._save_index()
        
        # Close current log file
        if self._current_log is not None:
            try:
                self._current_log.close()
            except Exception:
                pass  # Log file may already be closed
            self._current_log = None
    
    def search_history(self, query, max_results=20):
        """Search the entire conversation history for matching text.
        
        This scans all daily log files (using grep-like search) and returns
        matching turns with context.
        """
        q = query.lower()
        results = []
        
        # Scan all conversation logs
        conv_files = sorted(self._conv_dir.glob("conv_*.jsonl.gz"), reverse=True)
        
        for fpath in conv_files[:60]:  # Search last 60 days for performance
            try:
                with gzip.open(str(fpath), "rt", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        
                        # Search in all text fields
                        search_text = (
                            (entry.get("user") or "") + " " +
                            (entry.get("assistant") or "") + " " +
                            (entry.get("summary") or "")
                        ).lower()
                        
                        if q in search_text:
                            # Also search tool call results
                            tool_text = ""
                            for tc in entry.get("tool_calls") or []:
                                tool_text += (tc.get("name") or "") + " " + (tc.get("result") or "") + " "
                            if q in tool_text.lower():
                                pass  # Already matched
                            
                            results.append({
                                "timestamp": entry.get("timestamp", ""),
                                "session_id": entry.get("session_id", ""),
                                "user": (entry.get("user") or "")[:120],
                                "assistant": (entry.get("assistant") or "")[:200],
                                "summary": (entry.get("summary") or "")[:150],
                                "tool_count": len(entry.get("tool_calls") or []),
                            })
                            
                            if len(results) >= max_results:
                                break
                if len(results) >= max_results:
                    break
            except (OSError, EOFError):
                continue
        
        return results
    
    def search_history_by_date(self, date_str):
        """Get all conversations from a specific date (YYYY-MM-DD)."""
        fpath = self._get_log_path(date_str)
        if not fpath.exists():
            return []
        
        turns = []
        try:
            with gzip.open(str(fpath), "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            turns.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except (OSError, EOFError):
            pass
        return turns
    
    def get_stats(self):
        """Get conversation statistics."""
        stats = {
            "total_turns": self._index.get("total_turns", 0),
            "total_sessions": self._index.get("total_sessions", 0),
            "tools_used": dict(sorted(
                self._index.get("tools_used", {}).items(),
                key=lambda x: -x[1]
            )[:20]),
            "daily_files": len(list(self._conv_dir.glob("conv_*.jsonl.gz"))),
            "session_files": len(list(self._session_dir.glob("session_*.json.gz"))),
            "last_updated": self._index.get("last_updated", ""),
        }
        return stats
    
    def save_session_snapshot(self, messages):
        """Save a full session snapshot (all messages) as a compressed JSON file.
        
        This captures the ENTIRE conversation context, not just individual turns,
        so you can pick up exactly where you left off.
        """
        if not self._session_id:
            return None
        with self._lock:
            now = datetime.now()
            snapshot = {
                "session_id": self._session_id,
                "saved_at": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "messages": messages,
                "turn_count": self._turn_count,
            }
            # Save to session file
            fname = f"session_{now.strftime('%Y%m%d_%H%M%S')}.json.gz"
            fpath = self._session_dir / fname
            try:
                with gzip.open(str(fpath), "wt", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
            except OSError:
                return None
            # Update index with latest snapshot reference
            if "sessions" in self._index and self._session_id in self._index["sessions"]:
                self._index["sessions"][self._session_id]["last_snapshot"] = str(fpath)
                self._index["sessions"][self._session_id]["last_snapshot_time"] = now.isoformat()
                self._index["sessions"][self._session_id]["messages_count"] = len(messages)
                self._save_index()
            return str(fpath)
    
    def get_latest_session_snapshot(self):
        """Find and return the most recent session snapshot data."""
        sessions = sorted(self._session_dir.glob("session_*.json.gz"), reverse=True)
        if not sessions:
            return None
        latest = sessions[0]
        try:
            with gzip.open(str(latest), "rt", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    
    def get_all_conversation_dates(self):
        """Get list of all dates that have conversation logs."""
        dates = []
        for f in sorted(self._conv_dir.glob("conv_*.jsonl.gz"), reverse=True):
            # Extract date from filename: conv_2026-01-01.jsonl.gz
            match = re.search(r"conv_(\d{4}-\d{2}-\d{2})", f.name)
            if match:
                dates.append(match.group(1))
        return dates
    
    def export_all_conversations(self, output_path=None):
        """Export ALL conversations to a single JSON file."""
        if output_path is None:
            output_path = MEMORY_DIR / f"conversation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        all_turns = []
        for fpath in sorted(self._conv_dir.glob("conv_*.jsonl.gz")):
            try:
                with gzip.open(str(fpath), "rt", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                all_turns.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except OSError:
                continue
        
        export = {
            "exported_at": datetime.now().isoformat(),
            "total_turns": len(all_turns),
            "total_sessions": self._index.get("total_sessions", 0),
            "conversations": all_turns,
        }
        
        output_path.write_text(
            json.dumps(export, indent=2, ensure_ascii=False), 
            encoding="utf-8"
        )
        return str(output_path)
    
    def get_session_context(self, session_id, max_turns=50):
        """Get all turns from a specific session (for context restoration)."""
        turns = []
        for fpath in sorted(self._conv_dir.glob("conv_*.jsonl.gz"), reverse=True):
            try:
                with gzip.open(str(fpath), "rt", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if entry.get("session_id") == session_id:
                            turns.append(entry)
                            if len(turns) >= max_turns:
                                break
                if len(turns) >= max_turns:
                    break
            except OSError:
                continue
        return turns


# =============================================================================
# PART 3: AUTO-SAVE MANAGER — Integrates with agent loop
# =============================================================================

class AutoSaveManager:
    """Manages automatic saving of everything.
    
    - Auto-saves conversation turns immediately after each exchange
    - Maintains a rolling window of recent sessions for fast recovery
    - Creates session snapshots periodically
    - Extracts and saves key facts from conversations
    """
    
    def __init__(self, persistent_memory=None):
        self.logger = ConversationLogger()
        self.pm = persistent_memory or get_persistent_memory()
        self._last_save_time = time.time()
        self._turn_count = 0
        
    def start_session(self):
        """Begin a new session — called at agent startup."""
        session_id = self.logger.log_session_start()
        return session_id
    
    def end_session(self, summary=""):
        """End the current session."""
        self.logger.log_session_end(summary=summary)
    
    def save_turn(self, user_msg, assistant_msg, tool_calls=None, summary=""):
        """Auto-save a single conversation turn immediately."""
        self._turn_count += 1
        turn_data = {
            "timestamp": datetime.now().isoformat(),
            "user": user_msg or "",
            "assistant": assistant_msg or "",
            "tool_calls": tool_calls or [],
            "summary": summary or "",
        }
        self.logger.log_interaction(turn_data)
    
    def save_snapshot(self, messages):
        """Save a full session snapshot. Returns the file path."""
        return self.logger.save_session_snapshot(messages)
    
    def recover_last_session(self, max_turns=50):
        """Get the most recent session's conversation turns for context recovery."""
        return self.logger.get_latest_session_snapshot()
    
    def search_everything(self, query, max_results=20):
        """Search ALL memory sources (facts, notes, conversations)."""
        results = []
        
        # Search persistent memory (facts + notes)
        mem_results = self.pm.search(query)
        if mem_results:
            results.append({"source": "persistent_memory", "content": mem_results})
        
        # Search conversation history
        conv_results = self.logger.search_history(query, max_results=max_results)
        if conv_results:
            results.append({"source": "conversation_history", "content": conv_results})
        
        return results
    
    def get_memory_stats(self):
        """Get comprehensive memory statistics."""
        conv_stats = self.logger.get_stats()
        facts_count = len(self.pm._facts) if hasattr(self.pm, '_facts') else 0
        notes_count = len(self.pm._notes) if hasattr(self.pm, '_notes') else 0
        
        return {
            **conv_stats,
            "persistent_facts": facts_count,
            "persistent_notes": notes_count,
            "conversation_dates": self.logger.get_all_conversation_dates(),
        }


# =============================================================================
# PART 4: Short-Term Memory (unchanged but integrated with Total Recall)
# =============================================================================

class ShortTermMemory:
    """Short-term conversation memory with token-aware trimming."""
    
    def __init__(self, max_tokens=64000):
        self.messages = []
        self.max_tokens = max_tokens

    def add_system(self, content):
        """Add system message at the beginning."""
        self.messages.insert(0, {"role": "system", "content": content})

    def set_system(self, content):
        """Replace system message."""
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": content}
        else:
            self.messages.insert(0, {"role": "system", "content": content})

    def add_user(self, content):
        """Add user message."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content="", tool_calls=None):
        """Add assistant message with optional tool calls."""
        msg = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool(self, tool_call_id, content):
        """Add tool result message."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    def get_messages(self):
        return self.messages

    def clear(self):
        self.messages = []

    def remove_last_n(self, n):
        if n > 0 and len(self.messages) > 0:
            self.messages = self.messages[:-n]

    def estimate_tokens(self):
        """Rough token estimation."""
        total = 0
        for msg in self.messages:
            total += len(str(msg)) // 4
        return total

    def trim(self, target_tokens=48000):
        """Remove oldest complete turns but SUMMARIZE them first so context is preserved.
        Never orphans tool messages without their preceding assistant(tool_calls).
        """
        if self.estimate_tokens() <= target_tokens:
            return self.estimate_tokens()

        summaries = []

        while self.estimate_tokens() > target_tokens and len(self.messages) > 2:
            idx = 1
            if idx >= len(self.messages):
                break
            role = self.messages[idx]["role"]
            if role == "user":
                user_content = self.messages[idx].get("content", "")
                summaries.append(f"User asked: {user_content[:200]}")
                self.messages.pop(idx)
                if idx < len(self.messages) and self.messages[idx]["role"] == "assistant":
                    asst = self.messages[idx]
                    if asst.get("content"):
                        summaries.append(f"Assistant responded: {asst['content'][:200]}")
                    if asst.get("tool_calls"):
                        for tc in asst["tool_calls"]:
                            fn = tc.get("function", {}).get("name", "")
                            summaries.append(f"Called tool: {fn}")
                    self.messages.pop(idx)
                    while idx < len(self.messages) and self.messages[idx]["role"] == "tool":
                        self.messages.pop(idx)
            elif role == "assistant":
                asst = self.messages[idx]
                if asst.get("content"):
                    summaries.append(f"Assistant: {asst['content'][:200]}")
                if asst.get("tool_calls"):
                    for tc in asst["tool_calls"]:
                        fn = tc.get("function", {}).get("name", "")
                        summaries.append(f"Called tool: {fn}")
                self.messages.pop(idx)
                while idx < len(self.messages) and self.messages[idx]["role"] == "tool":
                    self.messages.pop(idx)
            elif role == "tool":
                while idx < len(self.messages) and self.messages[idx]["role"] == "tool":
                    self.messages.pop(idx)
            else:
                self.messages.pop(idx)

        if summaries:
            summary_text = "[Conversation history summary]: " + " | ".join(summaries)
            # Insert after system message
            self.messages.insert(1, {"role": "system", "content": f"(summarized) {summary_text}"})

        return self.estimate_tokens()

    def get_token_stats(self):
        return {
            "messages": len(self.messages),
            "estimated_tokens": self.estimate_tokens(),
        }


# =============================================================================
# PART 5: GLOBAL SINGLETONS
# =============================================================================

_persistent = None
_recall = None


def get_persistent_memory():
    """Get or create the global PersistentMemory instance."""
    global _persistent
    if _persistent is None:
        _persistent = PersistentMemory()
    return _persistent


def get_total_recall():
    """Get or create the global TotalRecall (auto-save manager) instance."""
    global _recall
    if _recall is None:
        _recall = AutoSaveManager(get_persistent_memory())
    return _recall


def reset_memory():
    """Reset all memory singletons (for testing/cleanup)."""
    global _persistent, _recall
    if _persistent is not None:
        pass  # Keep persistent data
    if _recall is not None:
        _recall.end_session()
    _recall = None
