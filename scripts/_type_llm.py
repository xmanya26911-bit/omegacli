"""Add type hints to llm.py"""
with open('llm.py', 'r') as f:
    content = f.read()

# Add Config import
content = content.replace(
    'from datetime import datetime',
    'from datetime import datetime\nfrom typing import Generator\nfrom config import Config'
)

reps = {
    'def __init__(self, config):': 'def __init__(self, config: Config) -> None:',
    'def _rate_limit_wait(self):': 'def _rate_limit_wait(self) -> None:',
    'def chat(self, messages, tools=None, stream=True, max_retries=3):': 'def chat(self, messages: list[dict], tools: list[dict] | None = None, stream: bool = True, max_retries: int = 3) -> dict | Generator:',
    'def _handle_response(self, response):': 'def _handle_response(self, response: requests.Response) -> dict:',
    'def _handle_stream(self, response):': 'def _handle_stream(self, response: requests.Response) -> Generator[tuple[str, str | list], None, None]:',
    'def count_tokens(self, messages):': 'def count_tokens(self, messages: list[dict]) -> int:',
    'def get_token_stats(self):': 'def get_token_stats(self) -> dict:',
}

for old, new in reps.items():
    if old in content:
        content = content.replace(old, new)
    else:
        print(f'MISS: {old!r}')

with open('llm.py', 'w') as f:
    f.write(content)
print('Done')
