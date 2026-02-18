#!/usr/bin/env python3
"""PreToolUse hook: Block dangerous Bash commands.

Reads tool input from stdin (JSON), checks for dangerous DB/git commands.
Exit 0 = allow, Exit 2 = block (stderr message fed back to Claude).
"""
import json
import re
import sys

DANGEROUS_PATTERNS = [
    # Database destructive commands
    (r"\bDROP\s+(TABLE|DATABASE|INDEX|SCHEMA)\b", "DROP command detected — destructive DB operation"),
    (r"\bTRUNCATE\s+TABLE\b", "TRUNCATE TABLE detected — will delete all data"),
    (r"\bDELETE\s+FROM\s+\w+\s*;?\s*$", "DELETE without WHERE clause — will delete all rows"),
    (r"\bALTER\s+TABLE\s+\w+\s+DROP\b", "ALTER TABLE DROP detected — will remove column/constraint"),
    # Git destructive commands
    (r"\bgit\s+push\s+.*--force\b", "git push --force detected — may overwrite remote history"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard detected — will discard uncommitted changes"),
    (r"\bgit\s+clean\s+-f\b", "git clean -f detected — will delete untracked files"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D detected — force delete branch"),
    # File system destructive
    (r"\brm\s+-rf\s+/", "rm -rf / detected — extremely dangerous"),
    (r"\brmdir\s+/s\b", "rmdir /s detected — recursive directory delete"),
    (r"\bdel\s+/s\s+/q\b", "del /s /q detected — recursive quiet delete"),
    # Alembic destructive
    (r"\balembic\s+downgrade\s+base\b", "alembic downgrade base — rolls back ALL migrations"),
]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)  # Can't parse, allow

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    for pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"BLOCKED: {message}", file=sys.stderr)
            print(f"Command: {command}", file=sys.stderr)
            print("If this is intentional, ask the user for explicit confirmation.", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
