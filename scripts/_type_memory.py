"""Batch-add type hints to memory.py — 56 functions, 0% typed"""
with open('memory.py', 'r') as f:
    content = f.read()

reps = {
    # PersistentMemory class
    'def __init__(self):': 'def __init__(self) -> None:',
    'def _load(self):': 'def _load(self) -> None:',
    'def _save_facts(self):': 'def _save_facts(self) -> None:',
    'def _save_notes(self):': 'def _save_notes(self) -> None:',
    'def _log(self, action, detail=""):': 'def _log(self, action: str, detail: str = "") -> None:',
    'def remember(self, key, value, tags=None):': 'def remember(self, key: str, value: object, tags: list[str] | None = None) -> None:',
    'def recall(self, key):': 'def recall(self, key: str) -> object | None:',
    'def forget(self, key):': 'def forget(self, key: str) -> None:',
    'def list_memories(self, tag=None):': 'def list_memories(self, tag: str | None = None) -> list[dict]:',
    'def search(self, query):': 'def search(self, query: str) -> list[dict]:',
    'def save_note(self, title, content, tags=None):': 'def save_note(self, title: str, content: str, tags: list[str] | None = None) -> None:',
    'def read_note(self, title):': 'def read_note(self, title: str) -> str | None:',
    'def delete_note(self, title):': 'def delete_note(self, title: str) -> None:',
    'def list_notes(self, tag=None):': 'def list_notes(self, tag: str | None = None) -> list[dict]:',
    'def export_all(self):': 'def export_all(self) -> dict:',
    'def import_all(self, data):': 'def import_all(self, data: dict) -> None:',
    'def get_relevant_context(self, query, max_items=5):': 'def get_relevant_context(self, query: str, max_items: int = 5) -> list[dict]:',
    # HistoryKeeper class
    'def __init__(self):': 'def __init__(self) -> None:',
    'def _load_index(self):': 'def _load_index(self) -> None:',
    'def _save_index(self):': 'def _save_index(self) -> None:',
    'def _get_log_path(self, date=None):': 'def _get_log_path(self, date: str | None = None) -> Path:',
    'def _ensure_log_file(self):': 'def _ensure_log_file(self) -> None:',
    'def log_interaction(self, turn_data):': 'def log_interaction(self, turn_data: dict) -> None:',
    'def log_session_start(self):': 'def log_session_start(self) -> None:',
    'def log_session_end(self, summary=""):': 'def log_session_end(self, summary: str = "") -> None:',
    'def search_history(self, query, max_results=20):': 'def search_history(self, query: str, max_results: int = 20) -> list[dict]:',
    'def search_history_by_date(self, date_str):': 'def search_history_by_date(self, date_str: str) -> list[dict]:',
    'def get_stats(self):': 'def get_stats(self) -> dict:',
    'def save_session_snapshot(self, messages):': 'def save_session_snapshot(self, messages: list[dict]) -> str:',
    'def get_latest_session_snapshot(self):': 'def get_latest_session_snapshot(self) -> list[dict] | None:',
    'def get_all_conversation_dates(self):': 'def get_all_conversation_dates(self) -> list[str]:',
    'def export_all_conversations(self, output_path=None):': 'def export_all_conversations(self, output_path: str | None = None) -> str:',
    'def get_session_context(self, session_id, max_turns=50):': 'def get_session_context(self, session_id: str, max_turns: int = 50) -> list[dict]:',
    # SessionManager class
    'def __init__(self, persistent_memory=None):': 'def __init__(self, persistent_memory: PersistentMemory | None = None) -> None:',
    'def start_session(self):': 'def start_session(self) -> None:',
    'def end_session(self, summary=""):': 'def end_session(self, summary: str = "") -> None:',
    'def save_turn(self, user_msg, assistant_msg, tool_calls=None, summary=""):': 'def save_turn(self, user_msg: str, assistant_msg: str, tool_calls: list[dict] | None = None, summary: str = "") -> None:',
    'def save_snapshot(self, messages):': 'def save_snapshot(self, messages: list[dict]) -> None:',
    'def recover_last_session(self, max_turns=50):': 'def recover_last_session(self, max_turns: int = 50) -> list[dict] | None:',
    'def search_everything(self, query, max_results=20):': 'def search_everything(self, query: str, max_results: int = 20) -> dict:',
    'def get_memory_stats(self):': 'def get_memory_stats(self) -> dict:',
    # TokenBudget class
    'def __init__(self, max_tokens=64000):': 'def __init__(self, max_tokens: int = 64000) -> None:',
    'def add_system(self, content):': 'def add_system(self, content: str) -> None:',
    'def set_system(self, content):': 'def set_system(self, content: str) -> None:',
    'def add_user(self, content):': 'def add_user(self, content: str) -> None:',
    'def add_assistant(self, content="", tool_calls=None):': 'def add_assistant(self, content: str = "", tool_calls: list[dict] | None = None) -> None:',
    'def add_tool(self, tool_call_id, content):': 'def add_tool(self, tool_call_id: str, content: str) -> None:',
    'def get_messages(self):': 'def get_messages(self) -> list[dict]:',
    'def clear(self):': 'def clear(self) -> None:',
    'def remove_last_n(self, n):': 'def remove_last_n(self, n: int) -> None:',
    'def estimate_tokens(self):': 'def estimate_tokens(self) -> int:',
    'def trim(self, target_tokens=48000):': 'def trim(self, target_tokens: int = 48000) -> None:',
    'def get_token_stats(self):': 'def get_token_stats(self) -> dict:',
    # Module-level functions
    'def get_persistent_memory():': 'def get_persistent_memory() -> PersistentMemory:',
    'def get_total_recall():': 'def get_total_recall() -> HistoryKeeper:',
    'def reset_memory():': 'def reset_memory() -> None:',
}

matches = 0
misses = []
for old, new in reps.items():
    if old in content:
        content = content.replace(old, new)
        matches += 1
    else:
        misses.append(old)

with open('memory.py', 'w') as f:
    f.write(content)
print(f"Applied {matches}/{len(reps)} type hints")
if misses:
    print(f"MISSES ({len(misses)}):")
    for m in misses:
        print(f"  - {m!r}")
