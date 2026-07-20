"""Session status tracking — token usage, tool stats, elapsed time."""

import time


class SessionTracker:
    """Tracks session-level stats: tokens, tool calls, elapsed time.

    This is the Phase 3 "Live Status" infrastructure — a centralized
    object that the prompt bar footer and response footer query.
    """

    def __init__(self):
        self.token_count_input = 0
        self.token_count_output = 0
        self.tool_invocation_count = 0
        self.message_count = 0
        self._start = time.time()
        self._tool_stats = {}  # tool_name -> {"count": int, "total_time": float}

    def elapsed(self):
        """Return seconds since session start."""
        return time.time() - self._start

    def elapsed_str(self):
        """Return elapsed time as HH:MM:SS."""
        e = int(self.elapsed())
        h, m, s = e // 3600, (e % 3600) // 60, e % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def record_token_input(self, text):
        """Estimate input tokens (~4 chars per token) and add to counter."""
        self.token_count_input += max(1, len(text) // 4)

    def record_token_output(self, text):
        """Estimate output tokens (~4 chars per token) and add to counter."""
        self.token_count_output += max(1, len(text) // 4)

    def record_tool_call(self, name, duration=None):
        """Record a tool invocation with optional execution time."""
        self.tool_invocation_count += 1
        if name not in self._tool_stats:
            self._tool_stats[name] = {"count": 0, "total_time": 0.0}
        self._tool_stats[name]["count"] += 1
        if duration:
            self._tool_stats[name]["total_time"] += duration

    def get_tool_summary(self, limit=5):
        """Return list of (name, count, total_time) for most-used tools."""
        sorted_tools = sorted(
            self._tool_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )
        return [(name, stats["count"], stats["total_time"])
                for name, stats in sorted_tools[:limit]]

    def total_tokens(self):
        """Return estimated total tokens used."""
        return self.token_count_input + self.token_count_output

    def summary_dict(self):
        """Return dict of all stats for display purposes."""
        return {
            "messages": self.message_count,
            "tools": self.tool_invocation_count,
            "tokens_input": self.token_count_input,
            "tokens_output": self.token_count_output,
            "tokens_total": self.total_tokens(),
            "elapsed": self.elapsed_str(),
            "elapsed_seconds": int(self.elapsed()),
        }
