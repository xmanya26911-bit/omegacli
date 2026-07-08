#!/usr/bin/env python3
"""OMEGA Agent -- Core conversation loop with tool execution, memory injection, and commands."""

import sys
import os
import json
import time
import threading
import traceback
import requests
from pathlib import Path

from memory import ShortTermMemory, get_persistent_memory, get_total_recall, AutoSaveManager
from llm import LLMClient, LLMError, LLMAuthError, LLMRetryError
from prompts import build_system_prompt, TOOL_DEFINITIONS
from tools import execute_tool, TOOL_MAP
from omega_project import (
    get_project_context, get_project_context_block,
    generate_project_map, smart_find_files,
    generate_diff_preview, format_diff_for_display,
    get_cost_tracker, discover_omega_md,
)
from omega_claude_features import (
    get_hooks, get_sub_agent_manager, get_context_compressor,
    get_verification_engine, get_codebase_index, get_permission_system,
    detect_dead_imports, detect_unused_variables, detect_duplicate_code,
    CICDManager, CrossLanguageAnalyzer, BrowserAutomation,
    review_pull_request, deploy_staging, print_features_doc,
    HOOK_EVENTS,
)
from cli import (
    print_user_input,
    print_assistant_thinking,
    print_assistant_done,
    print_assistant_message,
    print_assistant_header,
    print_thinking_block,
    print_thinking_busy,
    print_thinking_start,
    print_thinking_done,
    reset_streaming_header,
    print_tool_call,
    print_tool_result,
    print_task_complete,
    print_info,
    print_warning,
    print_error,
    print_success,
    set_current_tool,
    clear_current_tool,
    print_table,
    print_welcome,
    print_help as cli_print_help,
    print_theme_list,
    get_input,
    set_active_theme,
    get_active_theme,
    get_theme_names,
    AVAILABLE_THEMES,
    format_size,
    print_diff,
)

# Try to enable readline/history for interactive mode
HISTORY_FILE = os.path.expanduser("~/.omega/history.txt")
SESSION_DIR = Path.home() / ".omega" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
try:
    import readline
    HAVE_READLINE = True
    try:
        readline.read_history_file(HISTORY_FILE)
    except (FileNotFoundError, OSError):
        pass
    readline.set_history_length(500)
except ImportError:
    HAVE_READLINE = False


def _save_history():
    """Save readline history if available."""
    if HAVE_READLINE:
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            readline.write_history_file(HISTORY_FILE)
        except OSError:
            pass


class Agent:
    def __init__(self, config):
        self.config = config
        # Apply theme from config at startup (with backward compatibility)
        theme_name = getattr(config, 'theme', 'default-dark')
        # Map old "dark"/"light" to new theme names
        legacy_map = {"dark": "default-dark", "light": "default-light"}
        theme_name = legacy_map.get(theme_name, theme_name)
        if theme_name in AVAILABLE_THEMES:
            set_active_theme(theme_name)
        self.memory = ShortTermMemory()
        self.long_term = get_persistent_memory()
        self.recall = get_total_recall()          # TOTAL RECALL auto-save system
        self.llm = LLMClient(config)
        self.running = False
        self.tool_call_count = 0
        self._last_user_input = ""
        self._last_assistant_output = ""
        self._session_conversations = []
        self.cost_tracker = get_cost_tracker()
        self._project_context_loaded = False
        self._setup_system()
        # Auto-start Total Recall session and recover previous context
        self.recall.start_session()
        self._auto_recover_context()
        # Load OMEGA.md project config into system prompt
        self._inject_project_context()
        # Initialize Claude Code Complete features (MCP, bulk ops, refactoring, release)
        self._init_claude_complete()

    def _init_claude_complete(self):
        """Register Claude Code Complete tools at startup."""
        try:
            from omega_claude_complete import init_claude_complete
            result = init_claude_complete()
            count = result.get("count", 0)
            if count > 0:
                print_info(f"🔧 Claude Code Complete: {count} tools loaded")
        except Exception as e:
            pass  # Silent fail on startup

    def _setup_system(self):
        """Initialize or reset the system prompt."""
        self.memory.clear()
        system = build_system_prompt()
        self.memory.add_system(system)

    def _inject_project_context(self):
        """Load OMEGA.md / CLAUDE.md project config into system prompt.
        
        Discovers project-level instructions files from the current
        working directory and its parents, then injects them into
        the system prompt for context-aware assistance.
        """
        try:
            context_block = get_project_context_block()
            if context_block:
                current = self.memory.get_messages()
                if current and current[0]["role"] == "system":
                    current[0]["content"] += context_block
                    self._project_context_loaded = True
                    # Log what was loaded
                    ctx = get_project_context()
                    files = [Path(f).name for f, _ in ctx["files"]]
                    if files:
                        print_info(f"📋 Loaded project config: {', '.join(files)}")
        except Exception:
            pass  # Never let config loading crash startup

    def _auto_recover_context(self):
        """Auto-recover the last session's conversation context.
        
        When you come back after a month, this picks up where you left off.
        """
        try:
            snapshot = self.recall.recover_last_session()
            if snapshot and snapshot.get("messages"):
                messages = snapshot.get("messages", [])
                # Only recover if there are meaningful messages (not just system)
                non_system = [m for m in messages if m.get("role") != "system"]
                if len(non_system) >= 2:
                    # Inject previous session summary as context
                    session_id = snapshot.get("session_id", "previous session")
                    turn_count = snapshot.get("turn_count", 0)
                    date = snapshot.get("date", "recently")
                    summary = (
                        f"[CONTINUING FROM PREVIOUS SESSION: {session_id} on {date} "
                        f"with {turn_count} turns. "
                        f"Context loaded from auto-saved snapshot.]"
                    )
                    current = self.memory.get_messages()
                    if current and current[0]["role"] == "system":
                        current[0]["content"] += f"\n\n{summary}"
                        
                        # Also inject recent key exchanges from the previous session
                        important_turns = []
                        for msg in non_system[-10:]:  # Last 10 messages
                            if msg["role"] == "user":
                                content = msg.get("content", "")
                                if content and len(content) > 10:
                                    important_turns.append(f"User: {content[:200]}")
                            elif msg["role"] == "assistant":
                                content = msg.get("content", "")
                                if content and len(content) > 10:
                                    important_turns.append(f"OMEGA: {content[:200]}")
                        
                        if important_turns:
                            context = "\n[Previous conversation context (auto-recovered)]:\n"
                            context += "\n".join(important_turns[-6:])  # Last 6 exchanges
                            current[0]["content"] += context
        except Exception:
            pass  # Silently continue if recovery fails
    
    def _auto_save_turn(self):
        """Auto-save the current conversation turn to Total Recall.
        
        Called AFTER each assistant response is complete.
        This ensures EVERY exchange is permanently recorded.
        """
        try:
            # Gather tool calls from the last assistant message
            tool_calls_data = []
            messages = self.memory.get_messages()
            for msg in reversed(messages):
                if msg["role"] == "assistant" and msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        tool_calls_data.append({
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments", "")[:500],
                        })
                    break
            
            # Save conversation turn
            self.recall.save_turn(
                user_msg=self._last_user_input,
                assistant_msg=self._last_assistant_output[:5000] if self._last_assistant_output else "",
                tool_calls=tool_calls_data,
                summary="",  # Could be AI-generated summary in future
            )
            
            # Auto-save full session snapshot periodically (every 5 turns)
            if self.tool_call_count > 0 and self.tool_call_count % 5 == 0:
                self.recall.save_snapshot(self.memory.get_messages())
                
        except Exception:
            pass  # Never let saving crash the conversation
    
    def _inject_memory_context(self, user_input):
        """Inject relevant memories into system prompt context."""
        relevant = self.long_term.get_relevant_context(user_input)
        if relevant:
            current = self.memory.get_messages()
            if current and current[0]["role"] == "system":
                current[0]["content"] += relevant

    def run_once(self, user_input):
        """Execute a single user request through the agent loop."""
        # Sanitize memory: remove orphaned tool_calls from any previous interrupted turn
        self._ensure_consistent_memory()

        # Validate config before proceeding
        issues = self.config.validate()
        if issues:
            for issue in issues:
                print_warning(issue)

        # Track for auto-save
        self._last_user_input = user_input
        self._last_assistant_output = ""

        self._inject_memory_context(user_input)
        self.memory.add_user(user_input)

        steps = 0
        max_steps = self.config.max_steps
        self.tool_call_count = 0

        while steps < max_steps:
            steps += 1
            # ── Context Compression (Claude Code+) ──
            self.memory.trim(self.config.max_tokens)
            if steps > 3 and steps % 4 == 0:
                try:
                    compressor = get_context_compressor()
                    msgs = self.memory.get_messages()
                    if compressor.should_compress(msgs):
                        compressed = compressor.compress(msgs)
                        self.memory.messages = compressed
                except Exception:
                    pass

            try:
                result = self.llm.chat(
                    self.memory.get_messages(),
                    tools=TOOL_DEFINITIONS,
                    stream=True,
                )
            except LLMAuthError as e:
                print_error(str(e))
                print_info("Configure your API key with: /configure api_key YOUR_KEY")
                self.memory.remove_last_n(1)
                return
            except LLMRetryError as e:
                print_error(str(e))
                self.memory.remove_last_n(1)
                return
            except LLMError as e:
                print_error(str(e))
                self.memory.remove_last_n(1)
                return
            except Exception as e:
                print_error(f"Unexpected API error: {e}")
                self.memory.remove_last_n(1)
                return

            collected_content = ""
            collected_tool_calls = None
            saw_tool_calls = False
            _stream_retries = 0
            _max_stream_retries = 3
            _reasoning_lines = 0

            # Stream watchdog: prevent infinite hang during LLM streaming
            _stream_start_time = time.time()
            _stream_max_wait = 120  # 2 minutes max for any stream to complete

            # Show a subtle live indicator during streaming
            while _stream_retries < _max_stream_retries:
                try:
                    for event_type, event_data in result:
                        # Check stream timeout on each event
                        if time.time() - _stream_start_time > _stream_max_wait:
                            raise TimeoutError(f"Stream timed out after {_stream_max_wait}s")
                        if event_type == "content":
                            if not collected_content:
                                print_thinking_start()
                            collected_content += event_data
                            if event_data.strip():
                                print_assistant_thinking(event_data)
                                _reasoning_lines += 1
                        elif event_type == "tool_calls":
                            saw_tool_calls = True
                            collected_tool_calls = event_data
                        elif event_type == "done":
                            pass
                    break  # Success — exit retry loop
                except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError) as _stream_err:
                    _stream_retries += 1
                    if _stream_retries < _max_stream_retries:
                        # Reset stream start time for retry
                        _stream_start_time = time.time()
                        print_info(f"Stream interrupted, retrying ({_stream_retries}/{_max_stream_retries})...")
                        result = self.llm.chat(
                            self.memory.get_messages(),
                            tools=TOOL_DEFINITIONS,
                            stream=True,
                        )
                    else:
                        print_error(f"Stream failed after {_max_stream_retries} retries: {_stream_err}")
                        raise
                except TimeoutError:
                    print_error(f"Stream timed out after {_stream_max_wait}s — API may be stuck")
                    # Break out — use whatever we collected so far
                    break
            reset_streaming_header()

            # ── Display the content in proper style based on context ──
            if saw_tool_calls and collected_content:
                print_thinking_done()
            elif collected_content:
                print_assistant_message(collected_content)

            if not collected_tool_calls:
                if collected_content:
                    self.memory.add_assistant(content=collected_content)
                    self._last_assistant_output = collected_content
                break
            else:
                # Track assistant text even when there are tool calls
                if collected_content:
                    self._last_assistant_output = collected_content

            # Combine content + tool_calls into ONE assistant message
            assistant_tc = []
            for tc in collected_tool_calls:
                assistant_tc.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                })
            self.memory.add_assistant(content=collected_content, tool_calls=assistant_tc)

            saw_finish = False

            # ── Heartbeat: show OMEGA is alive during long tool execution ──
            # FIXED: Thread-safe heartbeat with lock, proper cleanup, no stdout races
            _heartbeat_running = threading.Event()
            _heartbeat_running.set()
            _heartbeat_thread = None
            _heartbeat_start = time.time()
            _heartbeat_lock = threading.Lock()
            
            def _heartbeat_loop():
                import sys as _sys
                while _heartbeat_running.is_set():
                    interrupted = _heartbeat_running.wait(5.0)
                    if interrupted:
                        break  # Event was set (shutdown signal)
                    if not _heartbeat_running.is_set():
                        break
                    elapsed = int(time.time() - _heartbeat_start)
                    with _heartbeat_lock:
                        try:
                            if elapsed < 60:
                                _sys.stdout.write(f"\r  ⏳ Processing... ({elapsed}s)")
                            else:
                                mins = elapsed // 60
                                secs = elapsed % 60
                                _sys.stdout.write(f"\r  ⏳ Processing... ({mins}m {secs}s)")
                            _sys.stdout.flush()
                        except (ValueError, OSError):
                            pass  # stdout closed, silently stop

            try:
                _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
                _heartbeat_thread.start()

                # Execute each tool call
                for tc in collected_tool_calls:
                    tc_id = tc["id"]
                    tc_name = tc["function"]["name"]
                    tc_args = tc["function"]["arguments"]

                    if tc_name == "finish":
                        saw_finish = True

                    # ── Run pre-tool hooks (Claude Code+) ──
                    try:
                        hook_ctx = {
                            "tool_name": tc_name,
                            "tool_args": tc_args,
                            "cwd": os.getcwd(),
                        }
                        get_hooks().run("pre_tool", hook_ctx)
                    except Exception:
                        pass
                    
                    _start = time.time()
                    set_current_tool(tc_name)

                    self.tool_call_count += 1
                    result = execute_tool(tc_name, tc_args)
                    clear_current_tool()
                    _elapsed = time.time() - _start
                    
                    # ── Run post-tool hooks (Claude Code+) ──
                    try:
                        hook_ctx["result"] = str(result)
                        hook_ctx["is_error"] = result.is_error if hasattr(result, 'is_error') else False
                        get_hooks().run("post_tool", hook_ctx)
                        if result.is_error:
                            get_hooks().run("on_error", hook_ctx)
                    except Exception:
                        pass
                    # Print tool call with timing info
                    if _elapsed > 0.5:
                        print_tool_call(tc_name, tc_args, duration=_elapsed)
                    else:
                        print_tool_call(tc_name, tc_args)
                    sys.stdout.flush()
                    # Self-healing: if tool fails with missing module, auto-install and retry
                    if result.is_error:
                        err_lower = result.content.lower()
                        if "no module named" in err_lower or "import error" in err_lower or "importerror" in err_lower:
                            import re as _re
                            match = _re.search(r"['\"]?([a-zA-Z_][a-zA-Z0-9_.]*)['\"]?", err_lower)
                            if match:
                                mod_name = match.group(1).split(".")[0]
                                if mod_name:
                                    print_info(f"Self-healing: installing missing module '{mod_name}'...")
                                    try:
                                        from tools import pip_install as _pip_install
                                        pip_res = _pip_install([mod_name])
                                        print_tool_result(str(pip_res), pip_res.is_error)
                                        # Retry the tool
                                        result = execute_tool(tc_name, tc_args)
                                        _elapsed = time.time() - _start
                                    except Exception:
                                        pass
                    # Self-protection: auto-verify syntax after self-modification
                    if tc_name in ("write_file", "edit_file") and not result.is_error:
                        import json as _json
                        try:
                            args_obj = _json.loads(tc_args) if isinstance(tc_args, str) else tc_args
                            fpath = args_obj.get("path", "")
                            if "omega" in fpath.replace("\\", "/").lower() and fpath.endswith(".py"):
                                import ast as _ast
                                import os as _os
                                abs_path = fpath if _os.path.isabs(fpath) else _os.path.join(_os.getcwd(), fpath)
                                if _os.path.exists(abs_path):
                                    try:
                                        _ast.parse(open(abs_path, encoding="utf-8").read())
                                        self._last_syntax_ok = True
                                    except SyntaxError as syn_err:
                                        self._last_syntax_ok = False
                                        print_warning(f"SYNTAX ERROR in {_os.path.basename(abs_path)}: {syn_err}")
                                        print_warning("Fix the syntax error before continuing.")
                        except Exception:
                            pass

                    result_str = str(result)

                    print_tool_result(result_str, result.is_error)
                    self.memory.add_tool(tc_id, result_str)
            finally:
                # ── Stop heartbeat ──
                # FIXED: Use Event for clean shutdown, lock stdout, clear any stale output
                _heartbeat_running.clear()  # Signal thread to stop
                if _heartbeat_thread and _heartbeat_thread.is_alive():
                    _heartbeat_thread.join(timeout=2.0)
                with _heartbeat_lock:
                    try:
                        sys.stdout.write("\r" + " " * 50 + "\r")  # Clear heartbeat line
                        sys.stdout.flush()
                    except (ValueError, OSError):
                        pass

            if saw_finish:
                # ── Self-Verification Engine (Claude Code+) ──
                try:
                    # Build tool history from current session
                    tool_history = []
                    msgs = self.memory.get_messages()
                    for msg in msgs:
                        if msg.get("role") == "assistant" and msg.get("tool_calls"):
                            for tc in msg["tool_calls"]:
                                fn = tc.get("function", {})
                                tool_history.append({
                                    "tool": fn.get("name", ""),
                                    "args": fn.get("arguments", ""),
                                })
                        elif msg.get("role") == "tool":
                            if tool_history:
                                tool_history[-1]["result"] = msg.get("content", "")
                    
                    verifier = get_verification_engine()
                    v_result = verifier.verify(self._last_user_input, tool_history)
                    
                    if v_result["passed"]:
                        for p in v_result["passed"][:3]:
                            print_info(f"  ✅ {p}")
                    if v_result["warnings"]:
                        for w in v_result["warnings"][:3]:
                            print_warning(f"  ⚠️  {w}")
                    if v_result["failed"]:
                        for f in v_result["failed"][:3]:
                            print_warning(f"  ❌ {f}")
                except Exception:
                    pass  # Never let verification crash completion
                
                print_task_complete("Task complete")
                self._print_usage_stats()
                # Run shutdown hooks
                try:
                    get_hooks().run("on_shutdown", {"task": self._last_user_input})
                except Exception:
                    pass
                # TOTAL RECALL: auto-save this turn permanently
                self._auto_save_turn()
                return

        # TOTAL RECALL: auto-save this turn (even without finish())
        self._auto_save_turn()

        if steps >= max_steps:
            print_warning(f"Reached maximum steps ({max_steps}). Ending conversation turn.")
            self._print_usage_stats()

    def _print_usage_stats(self):
        """Print token usage statistics with cost tracking."""
        stats = self.llm.get_token_stats()
        if stats["total_tokens"] > 0:
            # Record in cost tracker
            prompt_tok = stats.get("prompt_tokens", 0)
            completion_tok = stats.get("completion_tokens", 0)
            self.cost_tracker.record(prompt_tok, completion_tok, self._last_user_input[:50])
            
            mem_stats = self.memory.get_token_stats()
            cost_summary = self.cost_tracker.get_task_summary()
            if cost_summary:
                print_info(cost_summary)
            print_table(
                "Usage",
                ["Metric", "Value"],
                [
                    ["Prompt Tokens", f"{stats['prompt_tokens']:,}"],
                    ["Completion Tokens", f"{stats['completion_tokens']:,}"],
                    ["Total Tokens", f"{stats['total_tokens']:,}"],
                    ["Context Messages", str(mem_stats.get("messages", 0))],
                    ["Tools Called", str(self.tool_call_count)],
                ],
            )

    def _ensure_consistent_memory(self):
        """Remove orphaned assistant(tool_calls) messages that lack tool responses.
        Prevents API error: 'assistant message with tool_calls must be followed by
        tool messages responding to each tool_call_id'."""
        msgs = self.memory.messages
        i = 0
        while i < len(msgs):
            msg = msgs[i]
            if msg["role"] == "assistant" and "tool_calls" in msg:
                tc_ids = {tc["id"] for tc in msg["tool_calls"]}
                j = i + 1
                # Collect all tool responses that follow
                while j < len(msgs) and (msgs[j]["role"] == "tool" or msgs[j]["role"] == "assistant"):
                    if msgs[j]["role"] == "tool" and msgs[j]["tool_call_id"] in tc_ids:
                        tc_ids.remove(msgs[j]["tool_call_id"])
                    elif msgs[j]["role"] == "assistant":
                        break
                    j += 1
                if tc_ids:
                    # Orphaned! Remove from i to j (assistant + its tool messages)
                    del msgs[i:j]
                    continue
                i = j
            else:
                i += 1

    def run_interactive(self):
        """Run interactive REPL loop."""
        self.running = True
        print_welcome(self.config.model)

        while self.running:
            try:
                # Get enriched context for prompt
                mem_stats = self.memory.get_token_stats()
                msg_count = mem_stats.get("messages", 0) - 1  # exclude system
                tok_est = mem_stats.get("estimated_tokens", 0)
                user_input = get_input(
                    model_name=self.config.model,
                    message_count=msg_count,
                    token_estimate=tok_est,
                )
                if user_input is None:
                    print()
                    break

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                print_user_input(user_input)
                self.run_once(user_input)

            except KeyboardInterrupt:
                print("\n  ...interrupted")
                self._ensure_consistent_memory()
                continue
            except Exception as e:
                print_error(f"Unexpected error: {e}")
                traceback.print_exc()
                continue
            finally:
                _save_history()

    def _handle_command(self, cmd):
        """Handle slash commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command in ("/exit", "/quit", "/q"):
            # TOTAL RECALL: End session with summary
            try:
                mem_stats = self.memory.get_token_stats()
                summary = f"Session ended. {mem_stats['messages']} messages, {self.tool_call_count} tool calls."
                self.recall.end_session(summary=summary)
                # Save final snapshot
                self.recall.save_snapshot(self.memory.get_messages())
            except Exception:
                pass
            print_success("Shutting down OMEGA. Catch you later! 👋")
            _save_history()
            self.running = False

        elif command == "/clear":
            self._setup_system()
            print_success("Conversation cleared. History preserved in memory.")

        elif command == "/model":
            if arg and arg in self.config.AVAILABLE_MODELS:
                self.config.set_model(arg)
                self.llm = LLMClient(self.config)
                print_success(f"Model changed to: {arg}")
            elif arg:
                print_info(f"Unknown model: {arg}")
                print_info(f"Available: {', '.join(self.config.AVAILABLE_MODELS)}")
            else:
                print_info(f"Current model: {self.config.model}")
                print_info(f"Available: {', '.join(self.config.AVAILABLE_MODELS)}")

        elif command == "/configure":
            self._handle_configure(arg)

        elif command == "/recall":
            """Search ALL historical conversations with Total Recall."""
            if not arg:
                print_info("Usage: /recall <search query>")
                print_info("Searches every conversation you've ever had.")
                print_info("Examples: /recall python script, /recall backup, /recall 'project alpha'")
            else:
                print_info(f"Searching all conversation history for: '{arg}'...")
                results = self.recall.logger.search_history(arg, max_results=15)
                if results:
                    print_success(f"Found {len(results)} matching conversations:")
                    for i, r in enumerate(results, 1):
                        ts = r.get("timestamp", "?")[:19]  # Trim to seconds
                        user_msg = r.get("user", "")[:80]
                        asst_msg = r.get("assistant", "")[:100]
                        print(f"\n  {i}. [{ts}]")
                        print(f"     You: {user_msg}")
                        if asst_msg:
                            print(f"     OMEGA: {asst_msg}")
                else:
                    print_info("No matches found in conversation history.")
                # Also show memory results
                mem_result = self.long_term.search(arg)
                if mem_result and "No memories" not in mem_result:
                    print(mem_result)

        elif command == "/memory":
            if arg:
                result = self.long_term.search(arg)
            else:
                result = self.long_term.list_memories()
            print_info("Persistent memory:")
            print(result)

        elif command in ("/notes", "/note"):
            if arg:
                result = self.long_term.list_notes(tag=arg)
            else:
                result = self.long_term.list_notes()
            print_info("Saved notes:")
            print(result)

        elif command == "/forget":
            if arg:
                result = self.long_term.forget(arg)
                print_info(result)
            else:
                print_info("Usage: /forget <key>")

        elif command == "/diagnose":
            from tools import self_diagnose
            result = self_diagnose()
            if result.is_error:
                print_error(result.content)
            else:
                print(result.content)

        elif command == "/stats":
            stats = self.llm.get_token_stats()
            mem_stats = self.memory.get_token_stats()
            print_table(
                "Session Statistics",
                ["Metric", "Value"],
                [
                    ["Prompt Tokens", f"{stats['prompt_tokens']:,}"],
                    ["Completion Tokens", f"{stats['completion_tokens']:,}"],
                    ["Total Tokens", f"{stats['total_tokens']:,}"],
                    ["Messages in Context", str(mem_stats["messages"])],
                    ["Est. Context Tokens", f"{mem_stats['estimated_tokens']:,}"],
                    ["Tools Called", str(self.tool_call_count)],
                ],
            )

        elif command == "/help":
            self._print_help()

        elif command == "/theme":
            if not arg:
                # List available themes
                print_theme_list(get_active_theme())
            elif arg in AVAILABLE_THEMES:
                set_active_theme(arg)
                self.config.theme = arg
                self.config.save()
                print_success(f"Theme changed to: {arg}")
                # Re-draw welcome with new theme
                print_welcome(self.config.model)
            else:
                print_info(f"Unknown theme: '{arg}'")
                print_info(f"Available themes: {', '.join(AVAILABLE_THEMES)}")
                print_info("Example: /theme dracula")

        elif command == "/save":
            self._save_session(arg)

        elif command == "/load":
            self._load_session(arg)

        elif command == "/sessions":
            self._list_sessions()

        elif command == "/backup":
            from tools import backup_memories
            result = backup_memories(arg if arg else None)
            if result.is_error:
                print_error(result.content)
            else:
                print(result.content)

        elif command == "/env":
            from tools import get_env
            result = get_env(arg if arg else None)
            print(result.content)

        elif command == "/processes" or command == "/ps":
            from tools import list_processes
            result = list_processes(arg)
            print(result.content)

        elif command == "/update":
            from tools import check_update
            result = check_update()
            print(result.content)

        elif command == "/cache":
            from tools import cache_stats, clear_cache
            if arg == "clear":
                result = clear_cache()
            else:
                result = cache_stats()
            print(result.content)

        elif command == "/find":
            """Smart file discovery — find relevant files by description."""
            if not arg:
                print_info("Usage: /find <description of files to find>")
                print_info("Example: /find python config files")
            else:
                print_info(f"🔍 Searching for files related to: '{arg}'...")
                try:
                    results = smart_find_files(arg)
                    if results:
                        print_success(f"Found {len(results)} relevant file(s):")
                        for rel, icon, size, method in results:
                            size_str = format_size(size)
                            tag = {"name-match": "name", "key-file": "key", "recent": "recent"}.get(method, method)
                            print(f"  {icon} `{rel}` ({size_str}) [{tag}]")
                    else:
                        print_info("No relevant files found.")
                except Exception as e:
                    print_error(f"Error searching files: {e}")

        elif command == "/history":
            """Show Total Recall conversation statistics."""
            stats = self.recall.get_memory_stats()
            print_info("? TOTAL RECALL -- Conversation History Stats:")
            dates = stats.get("conversation_dates", [])
            print(f"  Total conversations logged: {stats.get('total_turns', 0):,} turns")
            print(f"  Total sessions: {stats.get('total_sessions', 0)}")
            print(f"  Active conversation days: {len(dates)}")
            print(f"  Persistent facts stored: {stats.get('persistent_facts', 0)}")
            print(f"  Persistent notes: {stats.get('persistent_notes', 0)}")
            tools = stats.get("tools_used", {})
            if tools:
                print(f"  Most used tools:")
                for name, count in list(tools.items())[:8]:
                    print(f"    {name}: {count}x")
            if dates:
                print(f"  Conversation dates: {dates[0]} to {dates[-1]}")
            print_info("Use /recall <query> to search all conversations.")

        elif command == "/compass":
            """Generate a project map/overview (Claude Code 'compass' equivalent)."""
            import time as _time
            print_info("🧭 Generating project map...")
            try:
                start = _time.time()
                map_text = generate_project_map()
                elapsed = _time.time() - start
                print_assistant_message(map_text)
                print_success(f"Project map generated ({elapsed:.1f}s)")
            except Exception as e:
                print_error(f"Failed to generate project map: {e}")

        elif command == "/cost":
            """Show token usage and cost tracking."""
            summary = self.cost_tracker.get_session_summary()
            print_assistant_message(summary)

        elif command == "/project":
            """Show OMEGA.md / project config status."""
            files = discover_omega_md()
            if files:
                print_success(f"Found {len(files)} project config file(s):")
                for path, content in files:
                    rel = Path(path)
                    preview = content[:200].replace("\n", " ")
                    if len(content) > 200:
                        preview += "..."
                    print(f"\n  📄 **{rel.name}** (`{rel.parent}`)")
                    print(f"     {preview}")
            else:
                print_info("No OMEGA.md / CLAUDE.md found.")
                print_info("Create one with: /project init")
            
            if self._project_context_loaded:
                print_success("✓ Project context is active in this session")
            else:
                print_info("○ No project context loaded")

        elif command.startswith("/project init"):
            """Initialize OMEGA.md for this project."""
            from omega_project import generate_omega_md_template
            name = arg[5:].strip() if len(arg) > 5 else ""
            template = generate_omega_md_template(name)
            
            target = Path.cwd() / "OMEGA.md"
            if target.exists():
                print_warning(f"OMEGA.md already exists at {target}")
                print_info("Delete it first or edit manually.")
            else:
                try:
                    target.write_text(template, encoding="utf-8")
                    print_success(f"✅ Created OMEGA.md at {target}")
                    print_info("Edit it with project-specific instructions for OMEGA.")
                    # Reload context
                    self._inject_project_context()
                except Exception as e:
                    print_error(f"Failed to create OMEGA.md: {e}")

        elif command == "/review-pr" or command == "/review":
            """Review pull request or uncommitted changes."""
            print_info("🔍 Running PR review...")
            try:
                result = review_pull_request(arg if arg else None)
                if "error" in result:
                    print_error(result["error"])
                else:
                    print_success(result.get("summary", "Review complete"))
                    if result.get("files_changed"):
                        print_info(f"Files changed: {len(result['files_changed'])}")
                        for f in result["files_changed"][:15]:
                            print(f"  📄 {f}")
                    if result.get("issues"):
                        print_warning(f"Issues found ({len(result['issues'])}):")
                        for issue in result["issues"]:
                            print(f"  ⚠️  {issue}")
                    if result.get("suggestions"):
                        print_info("Suggestions:")
                        for s in result["suggestions"]:
                            print(f"  💡 {s}")
            except Exception as e:
                print_error(f"Review failed: {e}")

        elif command == "/deploy":
            """Deploy pipeline (staging/production)."""
            env = arg.lower() if arg else "staging"
            print_info(f"🚀 Running deployment pipeline for: {env}")
            try:
                result = deploy_staging()
                for step in result.get("steps", []):
                    status = "✅" if step.get("passed") else "❌"
                    print(f"  {status} {step['step']}")
                    if step.get("output"):
                        print(f"     {step['output'][:150]}")
                print_success(f"Deploy status: {result.get('overall', 'unknown')}")
                if result.get("message"):
                    print_info(result["message"])
            except Exception as e:
                print_error(f"Deploy failed: {e}")

        elif command == "/audit-security":
            """Quick security audit."""
            print_info("🔒 Running security audit...")
            from tools import analyze_code
            try:
                result = analyze_code(".")
                if hasattr(result, 'content'):
                    print(result.content)
                else:
                    print_info(result)
            except Exception as e:
                print_error(f"Security audit failed: {e}")

        elif command == "/lint":
            """Run linters on codebase."""
            path = arg if arg else "."
            print_info(f"🔍 Running linters on: {path}")
            try:
                ci = CICDManager()
                result = ci.run_linter(path)
                if result.get("linters_run"):
                    print_success(f"Linters run: {', '.join(result['linters_run'])}")
                for p in result.get("passed", []):
                    print(f"  ✅ {p}")
                for w in result.get("warnings", [])[:15]:
                    print(f"  ⚠️  {w}")
                if result.get("issues"):
                    print_warning(f"Total issues: {len(result['issues'])}")
            except Exception as e:
                print_error(f"Linting failed: {e}")

        elif command == "/test":
            """Run tests and report results."""
            test_path = arg if arg else "."
            print_info(f"🧪 Running tests: {test_path}")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header", "-q"],
                    capture_output=True, text=True, timeout=120
                )
                output = result.stdout + "\n" + result.stderr
                if result.returncode == 0:
                    print_success("All tests passed! ✅")
                else:
                    print_warning(f"Tests failed (exit code: {result.returncode})")
                print(output[-2000:])
            except subprocess.TimeoutExpired:
                print_error("Tests timed out (120s)")
            except FileNotFoundError:
                print_info("pytest not installed. Install with: pip install pytest")
            except Exception as e:
                print_error(f"Test run failed: {e}")

        elif command == "/index":
            """Build codebase index for faster navigation."""
            path = arg if arg else "."
            print_info(f"📚 Building codebase index for: {path}")
            try:
                index = get_codebase_index()
                stats = index.build(path, force=True)
                if stats:
                    print_success(f"Index built: {stats.get('files_indexed', 0)} files, "
                                  f"{stats.get('total_symbols', 0)} symbols "
                                  f"({stats.get('elapsed', 0)}s)")
                print_info("Use /symbol <name> to search indexed symbols.")
            except Exception as e:
                print_error(f"Index build failed: {e}")

        elif command == "/symbol":
            """Find symbol definitions across codebase."""
            if not arg:
                print_info("Usage: /symbol <name>")
                print_info("Example: /symbol Authentication")
            else:
                print_info(f"🔍 Searching for symbol: '{arg}'")
                try:
                    index = get_codebase_index()
                    # Try building if not already indexed
                    if not index.index.get("files"):
                        print_info("Index not built yet. Build with: /index .")
                        print_info("Searching with grep instead...")
                        from tools import grep as grep_tool
                        result = grep_tool(arg, "*.py", ".")
                        print(result.content)
                    else:
                        results = index.search_symbol(arg)
                        defs = index.find_definition(arg)
                        refs = index.find_references(arg)
                        
                        if defs:
                            print_success(f"Definitions ({len(defs)}):")
                            for d in defs:
                                print(f"  📍 {d['file']}:{d['line']} ({d['kind']})")
                        if results:
                            print_info(f"All matches ({len(results)}):")
                            for r in results[:20]:
                                print(f"  • {r['file']}:{r['line']} ({r['kind']}) — {r['symbol']}")
                        if not defs and not results:
                            print_info("No symbols found matching that name.")
                except Exception as e:
                    print_error(f"Symbol search failed: {e}")

        elif command == "/callgraph":
            """Show function call relationships."""
            path = arg if arg else "."
            print_info(f"🕸️  Building call graph for: {path}")
            try:
                index = get_codebase_index()
                graph = index.build_call_graph(path)
                if graph:
                    print_success(f"Call graph built: {len(graph)} functions")
                    # Show top-level overview
                    for func, calls in list(graph.items())[:30]:
                        if calls:
                            calls_str = ", ".join(calls[:5])
                            print(f"  📞 {func} -> {calls_str}")
                            if len(calls) > 5:
                                print(f"       ... and {len(calls) - 5} more")
                        else:
                            print(f"  📞 {func} -> (no internal calls)")
                    if len(graph) > 30:
                        print(f"  ... and {len(graph) - 30} more functions")
                else:
                    print_info("No Python files found to analyze.")
            except Exception as e:
                print_error(f"Call graph failed: {e}")

        elif command == "/deadcode":
            """Find dead imports and unused variables."""
            path = arg if arg else "."
            print_info(f"🗑️  Analyzing dead code in: {path}")
            try:
                dead_imports = detect_dead_imports(path)
                unused_vars = detect_unused_variables(path)
                
                if dead_imports:
                    print_warning(f"Unused imports ({len(dead_imports)}):")
                    for item in dead_imports[:20]:
                        print(f"  📄 {item['file']}:{item['line']} — import {item['import']}")
                    if len(dead_imports) > 20:
                        print(f"  ... and {len(dead_imports) - 20} more")
                else:
                    print_success("No unused imports found.")
                
                if unused_vars:
                    print_warning(f"Unused variables ({len(unused_vars)}):")
                    for item in unused_vars[:20]:
                        print(f"  📄 {item['file']} in {item['function']}() — '{item['variable']}'")
                    if len(unused_vars) > 20:
                        print(f"  ... and {len(unused_vars) - 20} more")
                else:
                    print_success("No unused variables found.")
                
                if not dead_imports and not unused_vars:
                    print_success("Clean code! No dead code detected.")
            except Exception as e:
                print_error(f"Dead code analysis failed: {e}")

        elif command == "/duplicates":
            """Find duplicate code blocks."""
            path = arg if arg else "."
            print_info(f"♻️  Analyzing duplicate code in: {path}")
            try:
                duplicates = detect_duplicate_code(path, min_lines=6)
                if duplicates:
                    print_warning(f"Found {len(duplicates)} duplicate group(s):")
                    for dup in duplicates[:15]:
                        locations = dup.get("locations", [])
                        print(f"\n  📋 Appears in {dup['count']} places:")
                        for loc in locations[:5]:
                            print(f"     📄 {loc['file']}:{loc['line']} ({loc['kind']}: {loc['name']})")
                        if dup.get("code_preview"):
                            preview = dup["code_preview"][:150]
                            print(f"     ```{preview}```")
                    if len(duplicates) > 15:
                        print(f"\n  ... and {len(duplicates) - 15} more groups")
                else:
                    print_success("No significant code duplication detected.")
            except Exception as e:
                print_error(f"Duplicate analysis failed: {e}")

        elif command == "/hooks":
            """Manage hooks system."""
            parts = arg.split(maxsplit=1) if arg else []
            subcmd = parts[0] if parts else "list"
            rest = parts[1] if len(parts) > 1 else ""
            
            hooks = get_hooks()
            
            if subcmd == "list":
                all_hooks = hooks.list_hooks()
                if all_hooks:
                    print_success(f"Hooks ({len(all_hooks)} registered):")
                    for h in all_hooks:
                        status = "✅" if h.get("enabled") else "⏸️"
                        print(f"  {status} [{h['event']}] {h['name']}")
                        print(f"     Action: {h['action']}")
                        if h.get("condition"):
                            print(f"     Condition: {h['condition']}")
                        print(f"     Runs: {h.get('run_count', 0)}x")
                else:
                    print_info("No hooks registered.")
                    print_info("Usage: /hooks add <event> <action> [name]")
                    print_info(f"Events: {', '.join(sorted(HOOK_EVENTS.keys()))}")
            
            elif subcmd == "add":
                # Format: /hooks add pre_edit "black --quiet file.py" "Format before edit"
                from omega_claude_features import HOOK_EVENTS
                parts2 = rest.split(maxsplit=2) if rest else []
                if len(parts2) >= 2:
                    event = parts2[0]
                    action = parts2[1].strip('"\'')
                    name = parts2[2].strip('"\'') if len(parts2) > 2 else ""
                    result = hooks.register(event, action, name)
                    if result.get("success"):
                        print_success(f"Hook added: [{event}] {name or action[:40]}")
                    else:
                        print_error(result.get("error", "Failed to add hook"))
                else:
                    print_info("Usage: /hooks add <event> <action> [name]")
                    print_info(f"Example: /hooks add pre_edit 'black --quiet {rest}' 'Format on save'")
            
            elif subcmd == "remove" or subcmd == "rm":
                if rest:
                    hooks.unregister(rest)
                    print_success(f"Hook removed: {rest}")
                else:
                    print_info("Usage: /hooks remove <name>")
            
            else:
                print_info(f"Unknown hooks subcommand: {subcmd}")
                print_info("Usage: /hooks list|add|remove")

        elif command == "/permissions" or command == "/perm":
            """Set or view permission mode."""
            perm = get_permission_system()
            if not arg:
                current = perm.get_mode()
                print_info(f"Current permission mode: {current}")
                print_info("Modes: accept_all (default), auto_accept_known, ask_always, whitelist")
                print_info("Example: /permissions ask_always")
            else:
                result = perm.set_mode(arg)
                if result.get("success"):
                    print_success(f"Permission mode set to: {arg}")
                else:
                    print_error(result.get("error", f"Invalid mode: {arg}"))

        elif command == "/claude-features" or command == "/features":
            """Show all Claude Code+ features."""
            doc = print_features_doc()
            print(doc)

        elif command == "/system":
            from tools import system_info
            result = system_info()
            print(result.content)

        else:
            print_info(f"Unknown command: {command}. Type /help for commands.")

    def _handle_configure(self, arg):
        """Handle /configure command."""
        if not arg:
            print_info("Usage: /configure <setting> <value>")
            print_info("Settings: api_key <key>, base_url <url>, model <name>")
            print_info(f"Current API key: {'***' + self.config.api_key[-4:] if self.config.api_key else 'Not set'}")
            print_info(f"Current base URL: {self.config.base_url}")
            print_info(f"Current model: {self.config.model}")
            return

        parts = arg.split(maxsplit=1)
        setting = parts[0].lower()
        value = parts[1] if len(parts) > 1 else ""

        if setting == "api_key":
            if value:
                self.config.save_secret("api_key", value)
                self.llm = LLMClient(self.config)
                print_success("API key saved securely (stored in ~/.omega/.secrets.json)")
            else:
                print_info("Usage: /configure api_key YOUR_API_KEY")

        elif setting == "base_url":
            if value:
                self.config.base_url = value
                self.config.save()
                self.llm = LLMClient(self.config)
                print_success(f"Base URL set to: {value}")
            else:
                print_info("Usage: /configure base_url URL")

        elif setting == "model":
            if value:
                if self.config.set_model(value):
                    self.llm = LLMClient(self.config)
                    print_success(f"Model set to: {value}")
                else:
                    print_info(f"Unknown model. Available: {', '.join(self.config.AVAILABLE_MODELS)}")
            else:
                print_info(f"Current model: {self.config.model}")

        else:
            print_info(f"Unknown setting: {setting}")
            print_info("Settings: api_key, base_url, model")

    def _save_session(self, name=""):
        """Save current conversation to a session file."""
        if not name:
            from datetime import datetime
            name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_path = SESSION_DIR / f"{name}.json"
        messages = self.memory.get_messages()
        # Don't save the system prompt (regenerated on load)
        messages_no_system = [m for m in messages if m["role"] != "system"]
        data = {
            "name": name,
            "messages": messages_no_system,
            "tool_call_count": self.tool_call_count,
        }
        try:
            session_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            stats = self.memory.get_token_stats()
            print_success(f"Session saved: {name} ({len(messages_no_system)} messages, ~{stats['estimated_tokens']:,} tokens)")
        except Exception as e:
            print_error(f"Failed to save session: {e}")

    def _load_session(self, name):
        """Load a conversation from a session file."""
        if not name:
            print_info("Usage: /load <session_name>")
            return
        session_path = SESSION_DIR / f"{name}.json"
        if not session_path.exists():
            # List available sessions
            self._list_sessions()
            print_info(f"No session found: {name}")
            return
        try:
            data = json.loads(session_path.read_text(encoding="utf-8"))
            self._setup_system()
            for msg in data.get("messages", []):
                self.memory.messages.append(msg)
            self.tool_call_count = data.get("tool_call_count", 0)
            print_success(f"Loaded session: {name} ({len(data.get('messages', []))} messages)")
        except Exception as e:
            print_error(f"Failed to load session: {e}")

    def _list_sessions(self):
        """List all saved sessions."""
        sessions = sorted(SESSION_DIR.glob("*.json"))
        if not sessions:
            print_info("No saved sessions.")
            return
        rows = []
        for s in sessions:
            try:
                data = json.loads(s.read_text(encoding="utf-8"))
                name = data.get("name", s.stem)
                msg_count = len(data.get("messages", []))
                rows.append([name, str(msg_count), s.stem + ".json"])
            except Exception:
                rows.append([s.stem, "?", "?"])
        print_table("Saved Sessions", ["Name", "Messages", "File"], rows)

    def _print_help(self):
        """Print help information — Claude Code inspired with all new commands."""
        cli_print_help()
        # Also print the enhanced commands
        from cli import console as _rconsole, _use_rich, _current_theme, get_theme_colors
        from cli import sanitize as _sanitize
        c = get_theme_colors() if _use_rich else {}
        
        extra_help = [
            ("Project (Claude Code+)", [
                ("/compass", "🧭 Generate project map with structure, tech, git status"),
                ("/project", "Show OMEGA.md / CLAUDE.md project config status"),
                ("/project init [name]", "Create OMEGA.md template for this project"),
                ("/cost", "Show token usage and estimated cost"),
                ("/find <query>", "Smart file discovery — find relevant files by description"),
                ("/index [path]", "📚 Build codebase index for symbol navigation"),
                ("/symbol <name>", "🔍 Search symbols across indexed codebase"),
                ("/callgraph [path]", "🕸️  Build function call relationship graph"),
            ]),
            ("Code Quality (Claude Code+)", [
                ("/lint [path]", "🔍 Run linters (ruff/flake8) on codebase"),
                ("/test [path]", "🧪 Run pytest and show results"),
                ("/deadcode [path]", "🗑️  Find unused imports and variables"),
                ("/duplicates [path]", "♻️  Find duplicate code blocks"),
                ("/audit-security", "🔒 Quick security audit with OWASP checks"),
            ]),
            ("DevOps (Claude Code+)", [
                ("/review-pr [num]", "🔍 Review PR diff or uncommitted changes"),
                ("/deploy [env]", "🚀 Run deployment pipeline (staging/prod)"),
                ("/hooks list|add|rm", "🔗 Manage pre/post action hooks"),
                ("/permissions [mode]", "🔒 Set permission mode (accept_all|ask_always)"),
            ]),
            ("Advanced", [
                ("/claude-features", "📋 Show all Claude Code+ features added"),
            ]),
        ]
        
        if _use_rich:
            from rich.text import Text
            for cat_name, commands in extra_help:
                _rconsole.print(f"\n  [bold {c['title']}]{cat_name}[/bold {c['title']}]")
                for cmd, desc in commands:
                    _rconsole.print(f"    [bold {c['tool_call']}]{cmd:<26}[/bold {c['tool_call']}] {desc}")
            _rconsole.print(f"\n  [dim {c['dim_text']}]What shall we build? 😎[/dim {c['dim_text']}]")
            _rconsole.print()
        else:
            from cli import _theme_ansi_bright, _theme_ansi, Style, _S
            tc = _theme_ansi_bright("title")
            cmd_color = _theme_ansi_bright("tool")
            dc = _theme_ansi("dim")
            print(f"  {tc}Project (Claude Code+):{Style.RESET_ALL}")
            for cmd, desc in extra_help[0][1]:
                print(f"    {cmd_color}{cmd:<26}{Style.RESET_ALL} {dc}{desc}{Style.RESET_ALL}")
            print()
            print(f"  {dc}What shall we build? 😎{Style.RESET_ALL}")
            print()
