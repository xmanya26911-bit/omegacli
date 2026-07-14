"""Second pass: type the remaining untyped functions in cli.py"""
with open('cli.py', 'r') as f:
    content = f.read()

reps = {
    'def set_active_theme(theme_name):': 'def set_active_theme(theme_name: str) -> None:',
    'def _apply_rich_theme():': 'def _apply_rich_theme() -> None:',
    'def safe_char(ch, fallback):': 'def safe_char(ch: str, fallback: str) -> str:',
    'def format_size(size):': 'def format_size(size: int) -> str:',
    'def _ansi(n, bright=False):': 'def _ansi(n: int, bright: bool = False) -> str:',
    'def _theme_ansi(key):': 'def _theme_ansi(key: str) -> str:',
    'def _theme_ansi_bright(key):': 'def _theme_ansi_bright(key: str) -> str:',
    'def print_banner(config=None, compact=False):': 'def print_banner(config: dict | None = None, compact: bool = False) -> None:',
    '    def __init__(self, message="Thinking"):': '    def __init__(self, message: str = "Thinking") -> None:',
    'def print_assistant_thinking(text):': 'def print_assistant_thinking(text: str) -> None:',
    'def print_thinking_block(content):': 'def print_thinking_block(content: str) -> None:',
    'def print_assistant_message(text):': 'def print_assistant_message(text: str) -> None:',
    'def get_input(model_name="unknown", message_count=0, token_estimate=0):': 'def get_input(model_name: str = "unknown", message_count: int = 0, token_estimate: int = 0) -> str:',
    'def _protocol_name(name):': 'def _protocol_name(name: str) -> str:',
    'def print_tool_call(name, args=None, duration=None):': 'def print_tool_call(name: str, args: str | None = None, duration: str | None = None) -> None:',
    'def print_tool_result(content, is_error=False):': 'def print_tool_result(content: str, is_error: bool = False) -> None:',
    'def print_info(text):': 'def print_info(text: str) -> None:',
    'def print_diff(diff_text, max_lines=50):': 'def print_diff(diff_text: str, max_lines: int = 50) -> None:',
    'def print_warning(text):': 'def print_warning(text: str) -> None:',
    'def print_error(text):': 'def print_error(text: str) -> None:',
    'def print_success(text):': 'def print_success(text: str) -> None:',
    'def print_table(title, columns, rows):': 'def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:',
    'def print_code(code, language="python"):': 'def print_code(code: str, language: str = "python") -> None:',
    'def print_welcome(model_name="unknown"):': 'def print_welcome(model_name: str = "unknown") -> None:',
    'def print_theme_list(current_theme):': 'def print_theme_list(current_theme: str) -> None:',
}

for old, new in reps.items():
    if old in content:
        content = content.replace(old, new)
    else:
        print(f'MISS: {old[:70]}')

with open('cli.py', 'w') as f:
    f.write(content)
print('Done — second pass complete')
