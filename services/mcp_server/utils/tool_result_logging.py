from typing import Any


def format_tool_result_for_log(result: Any, max_chars: int = 200, full: bool = False) -> str:
    """Render tool output for logs with optional truncation."""
    rendered = str(result)

    if full or max_chars <= 0 or len(rendered) <= max_chars:
        return rendered

    return f"{rendered[:max_chars]}..."
