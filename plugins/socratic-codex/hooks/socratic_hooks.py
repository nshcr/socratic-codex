#!/usr/bin/env python3
"""Lifecycle hooks for the Socratic Codex plugin."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


LIFECYCLE_CONTEXT = (
    "Socratic Codex: for sustained work, bind a compact goal contract; "
    "inspect before asking; ask only user-owned uncertainty; use Boundary Gate "
    "before scope, risk, architecture, side-effect, irreversible, or acceptance "
    "changes; do not claim completion until evidence matches done criteria."
)

BOUNDARY_CONTEXT = (
    "Socratic Codex Boundary Gate: the next tool call may cross a user-owned "
    "scope, risk, side-effect, irreversible, or acceptance boundary. Preserve "
    "the goal contract, checkpoint if the answer changes the next action, and "
    "prefer the smallest reversible step."
)

ACCEPTANCE_CONTEXT = (
    "Socratic Codex Acceptance Close: before finalizing, compare the original "
    "ask, current goal contract, explicit constraints, done criteria, evidence, "
    "and unresolved user-owned boundaries. State missing verification instead "
    "of claiming full completion."
)

PROMPT_RE = re.compile(
    r"(\$socratic-codex|/goal|\b(goal|acceptance|done|complete|completed|"
    r"handoff|drift|stuck|debug|investigate|implement|refactor|migrate|"
    r"rollback|irreversible|risk|risky)\b|目标|验收|完成|结束|漂移|卡住|"
    r"排查|调查|实现|修复|重构|迁移|回滚|不可逆|风险|错了|停止|回到)",
    re.IGNORECASE,
)

RISKY_TOOL_RE = re.compile(
    r"(\brm\s+-[^;&|]*r|\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-"
    r"[^;&|]*[xdf]|\bgit\s+push\b|\bchmod\s+-R\b|\bchown\s+-R\b|"
    r"\bterraform\s+apply\b|\bkubectl\s+(delete|apply)\b|"
    r"\bdocker\s+system\s+prune\b)",
    re.IGNORECASE,
)

RISKY_PATCH_RE = re.compile(
    r"(\*\*\* Delete File:|\.codex-plugin/plugin\.json|hooks/hooks\.json|"
    r"requirements\.toml|config\.toml)",
    re.IGNORECASE,
)

DONE_RE = re.compile(
    r"\b(done|complete|completed|fixed|implemented|finished|ready|shipped)\b|"
    r"完成|已修复|已实现|搞定|结束",
    re.IGNORECASE,
)

EVIDENCE_RE = re.compile(
    r"\b(test|tests|tested|verified|validation|validated|check|checked|"
    r"evidence|partial|missing|unable|not run|not verified)\b|"
    r"测试|验证|校验|证据|未运行|无法|缺少|部分",
    re.IGNORECASE,
)


def hook_output(event: str, context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))


def continuation(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def read_input() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def tool_command(data: dict[str, Any]) -> str:
    tool_input = data.get("tool_input") or {}
    if isinstance(tool_input, dict):
        for key in ("command", "patch", "input"):
            value = tool_input.get(key)
            if value is not None:
                return str(value)
        return json.dumps(tool_input, sort_keys=True)
    return str(tool_input)


def user_prompt_submit(data: dict[str, Any]) -> None:
    if PROMPT_RE.search(str(data.get("prompt", ""))):
        hook_output("UserPromptSubmit", LIFECYCLE_CONTEXT)


def pre_tool_use(data: dict[str, Any]) -> None:
    tool = str(data.get("tool_name", ""))
    command = tool_command(data)
    if tool == "Bash" and RISKY_TOOL_RE.search(command):
        hook_output("PreToolUse", BOUNDARY_CONTEXT)
    elif tool == "apply_patch" and RISKY_PATCH_RE.search(command):
        hook_output("PreToolUse", BOUNDARY_CONTEXT)


def stop(data: dict[str, Any]) -> None:
    if data.get("stop_hook_active"):
        return
    message = str(data.get("last_assistant_message") or "")
    if DONE_RE.search(message) and not EVIDENCE_RE.search(message):
        continuation(ACCEPTANCE_CONTEXT)


def self_test() -> None:
    assert PROMPT_RE.search("帮我实现这个功能并做验收")
    assert RISKY_TOOL_RE.search("git reset --hard HEAD")
    assert RISKY_PATCH_RE.search("*** Delete File: README.md")
    assert tool_command({"tool_input": {"command": "git push"}}) == "git push"
    assert tool_command({"tool_input": "*** Delete File: README.md"}).startswith("*** Delete")
    assert RISKY_PATCH_RE.search(tool_command({"tool_input": {"patch": "*** Delete File: README.md"}}))
    assert DONE_RE.search("Implemented the fix.")
    assert EVIDENCE_RE.search("Tests not run.")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    handlers = {
        "user-prompt-submit": user_prompt_submit,
        "pre-tool-use": pre_tool_use,
        "stop": stop,
    }
    handler = handlers.get(sys.argv[1] if len(sys.argv) > 1 else "")
    if handler is None:
        return 1
    handler(read_input())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
