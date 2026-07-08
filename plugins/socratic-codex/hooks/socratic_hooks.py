#!/usr/bin/env python3
"""Lifecycle hooks for the Socratic Codex plugin (Codex and Claude Code).

State model:
- Per-session activity ledger in ``$CLAUDE_PLUGIN_DATA/state/<session_id>.json``
  (Codex exports the same variable for compatibility; ``PLUGIN_DATA`` is the
  Codex-native fallback). Records turn start time, whether a verification
  command ran this turn, once-per-turn completion blocking, and
  lifecycle-context injection dedup, including subagent stop dedup by agent id.
- Goal contract of record in ``<cwd>/.socratic/contract.md``, maintained by the
  model per the skill instructions and restored by the SessionStart hook after
  compaction or resume.
- Bounded audit log in ``$CLAUDE_PLUGIN_DATA/audit.jsonl`` recording recent hook
  interventions (never silent pass-throughs).

All state operations fail silently: a hook must never break the session.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

CONTRACT_RELPATH = os.path.join(".socratic", "contract.md")
CONTRACT_MAX_CHARS = 6000
AUDIT_MAX_BYTES = 256 * 1024
AUDIT_KEEP_BYTES = 128 * 1024
STATE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60

LIFECYCLE_CONTEXT = (
    "Socratic Codex: for sustained work, bind a compact goal contract and "
    "persist it to .socratic/contract.md; inspect before asking; ask only "
    "action-changing user-owned uncertainty; use Boundary Gate before scope, risk, "
    "architecture, side-effect, irreversible, or acceptance changes; do not "
    "claim completion until evidence matches done criteria."
)

BOUNDARY_CONTEXT = (
    "Socratic Codex Boundary Gate: the next tool call may cross a user-owned "
    "scope, risk, side-effect, irreversible, or acceptance boundary. Preserve "
    "the goal contract, checkpoint if the answer changes the next action, and "
    "prefer the smallest reversible step."
)

ACCEPTANCE_CONTEXT = (
    "Socratic Codex Acceptance Close: a completion claim was made without "
    "observed verification this turn (no verification command ran and "
    ".socratic/contract.md has no fresh Verification update). Compare the "
    "original ask, current goal contract, done criteria, and evidence; run or "
    "cite the missing verification and update the Verification section in "
    ".socratic/contract.md, or state explicitly what remains unverified "
    "instead of claiming full completion."
)

CONTRACT_RESTORED_CONTEXT = (
    "Socratic Codex: goal contract restored from .socratic/contract.md after "
    "compaction or resume. Treat it as the contract of record and re-anchor "
    "to it before continuing:\n\n"
)

SUBAGENT_CONTEXT = (
    "Socratic Codex subagent lifecycle: preserve the parent goal contract and "
    "report only distilled findings. Before claiming the delegated work is "
    "complete, include concrete evidence, remaining assumptions, and any "
    "acceptance boundary the parent agent must handle.\n\n"
)

SUBAGENT_ACCEPTANCE_CONTEXT = (
    "Socratic Codex subagent acceptance: your final response claims delegated "
    "work is complete but does not cite concrete verification evidence or an "
    "explicit unverified boundary. Continue once and return a concise handoff "
    "with evidence, assumptions, and what the parent agent must still verify."
)

PROMPT_RE = re.compile(
    r"(\$socratic-codex|/socratic-codex|/goal\b|"
    r"\b(goal|goals|acceptance|handoff|drift|drifting|stuck|rollback|"
    r"roll back|irreversible|migrate|migration|teardown|risky)\b|"
    r"目标|验收|交接|漂移|卡住|回滚|不可逆|迁移|拆除|风险|错了|停止|回到)",
    re.IGNORECASE,
)

# Regex fallback used only for shell segments that shlex cannot parse.
RISKY_TOOL_RE = re.compile(
    r"(\brm\s+-[^;&|]*r|\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-"
    r"[^;&|]*[xdf]|\bgit\s+push\b|\bchmod\s+-R\b|\bchown\s+-R\b|"
    r"\bterraform\s+(apply|destroy)\b|\bkubectl\s+(delete|apply)\b|"
    r"\bdocker\s+system\s+prune\b)",
    re.IGNORECASE,
)

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||;|\||\n")
SUBSTITUTION_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")

RISKY_PATCH_RE = re.compile(
    r"(\*\*\* Delete File:|\.codex-plugin/plugin\.json|"
    r"\.claude-plugin/plugin\.json|hooks/hooks\.json|"
    r"requirements\.toml|config\.toml|\.claude/settings(\.local)?\.json)",
    re.IGNORECASE,
)

SENSITIVE_FILE_RE = re.compile(
    r"(\.codex-plugin/plugin\.json|\.claude-plugin/plugin\.json|"
    r"hooks/hooks\.json|requirements\.toml|\.codex/config\.toml|"
    r"\.claude/settings(\.local)?\.json|\.mcp\.json)",
    re.IGNORECASE,
)

FILE_EDIT_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

VERIFICATION_COMMANDS = frozenset(
    {
        "cargo",
        "go",
        "make",
        "npm",
        "pnpm",
        "python",
        "python3",
        "pytest",
        "ruff",
        "swift",
        "yarn",
    }
)

VERIFICATION_WORD_RE = re.compile(
    r"(test|check|verify|validate|lint|typecheck|build|vet|fmt|clippy|"
    r"pytest|unittest|json\.tool|self-test)",
    re.IGNORECASE,
)

DONE_RE = re.compile(
    r"\b(done|complete|completed|fixed|implemented|finished|ready|shipped)\b|"
    r"完成|已修复|已实现|搞定|结束",
    re.IGNORECASE,
)

# Word-face fallback, used only when the activity ledger is unavailable.
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


# --- State, contract, and audit helpers -----------------------------------


def data_dir() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA")
    if base:
        return Path(base)
    return Path(tempfile.gettempdir()) / "socratic-codex"


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", session_id)
    return data_dir() / "state" / f"{safe}.json"


def cleanup_old_states(now: float | None = None) -> None:
    cutoff = (time.time() if now is None else now) - STATE_MAX_AGE_SECONDS
    try:
        for path in (data_dir() / "state").glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
    except OSError:
        pass


def load_state(session_id: str) -> dict[str, Any]:
    if not session_id:
        return {}
    try:
        loaded = json.loads(state_path(session_id).read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def save_state(session_id: str, state: dict[str, Any]) -> None:
    if not session_id:
        return
    try:
        path = state_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        cleanup_old_states()
        path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def compact_audit(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size > AUDIT_MAX_BYTES:
            tail = path.read_bytes()[-AUDIT_KEEP_BYTES:]
            newline = tail.find(b"\n")
            if newline != -1:
                tail = tail[newline + 1 :]
            path.write_bytes(tail)
    except OSError:
        pass


def audit(event: str, action: str, detail: str = "") -> None:
    try:
        path = data_dir() / "audit.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        compact_audit(path)
        entry = {"ts": round(time.time(), 3), "event": event, "action": action}
        if detail:
            entry["detail"] = detail[:200]
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def contract_path(cwd: str) -> Path:
    return Path(cwd or ".") / CONTRACT_RELPATH


def read_contract(cwd: str) -> str:
    try:
        return contract_path(cwd).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^#{{1,6}}\s*{re.escape(heading)}\b(.*?)(?=^#{{1,6}}\s|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def restored_contract_text(text: str) -> str:
    contract = markdown_section(text, "Contract")
    if contract:
        return f"## Contract\n\n{contract}"[:CONTRACT_MAX_CHARS]
    return text[:CONTRACT_MAX_CHARS]


def contract_verification_updated(cwd: str, since_ts: float) -> bool:
    """True when contract.md was touched this turn and has verification content."""
    path = contract_path(cwd)
    try:
        if path.stat().st_mtime + 1.0 < since_ts:
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    match = re.search(
        r"^#{1,6}\s*verification\b(.*?)(?=^#{1,6}\s|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return bool(match and match.group(1).strip())


# --- Tool-input helpers -----------------------------------------------------


def tool_command(data: dict[str, Any]) -> str:
    tool_input = data.get("tool_input") or {}
    if isinstance(tool_input, dict):
        for key in ("command", "patch", "input"):
            value = tool_input.get(key)
            if value is not None:
                return str(value)
        return json.dumps(tool_input, sort_keys=True)
    return str(tool_input)


def tool_file_path(data: dict[str, Any]) -> str:
    tool_input = data.get("tool_input") or {}
    if isinstance(tool_input, dict):
        return str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    return ""


def risky_tokens(tokens: list[str]) -> bool:
    while tokens and ASSIGNMENT_RE.match(tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return False
    cmd = os.path.basename(tokens[0])
    args = tokens[1:]
    if cmd == "rm":
        return any(t.startswith("-") and set("rR") & set(t) for t in args)
    if cmd == "git":
        sub = args[0] if args else ""
        if sub == "push":
            return True
        if sub == "reset" and "--hard" in args:
            return True
        if sub == "clean":
            return any(t.startswith("-") and set("xdfXD") & set(t) for t in args[1:])
        return False
    if cmd in ("chmod", "chown"):
        return any(t.startswith("-") and set("rR") & set(t) for t in args)
    if cmd == "terraform":
        return bool(args) and args[0] in ("apply", "destroy")
    if cmd == "kubectl":
        return bool(args) and args[0] in ("delete", "apply")
    if cmd == "docker":
        return args[:2] == ["system", "prune"]
    return False


def command_is_risky(command: str) -> bool:
    """Structured risk check: split chains and substitutions, parse each segment."""
    segments = SEGMENT_SPLIT_RE.split(command)
    for outer, inner in SUBSTITUTION_RE.findall(command):
        segments.append(outer or inner)
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            if RISKY_TOOL_RE.search(segment):
                return True
            continue
        if risky_tokens(tokens):
            return True
    return False


def command_is_verification(command: str) -> bool:
    """True for commands that are plausibly intended to verify behavior."""
    segments = SEGMENT_SPLIT_RE.split(command)
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            continue
        while tokens and ASSIGNMENT_RE.match(tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            continue
        cmd = os.path.basename(tokens[0])
        args = tokens[1:]
        if cmd not in VERIFICATION_COMMANDS:
            continue
        if cmd in {"pytest", "ruff"}:
            return True
        if any(VERIFICATION_WORD_RE.search(arg) for arg in args):
            return True
    return False


# --- Event handlers ---------------------------------------------------------


def user_prompt_submit(data: dict[str, Any]) -> None:
    session_id = str(data.get("session_id") or "")
    state = load_state(session_id)
    state["last_prompt_ts"] = time.time()
    state["verification_since_prompt"] = False
    state["completion_blocked_since_prompt"] = False
    state.pop("bash_since_prompt", None)
    inject = bool(
        PROMPT_RE.search(str(data.get("prompt", "")))
        and not state.get("lifecycle_injected")
    )
    if inject:
        state["lifecycle_injected"] = True
    save_state(session_id, state)
    if inject:
        audit("UserPromptSubmit", "inject-lifecycle")
        hook_output("UserPromptSubmit", LIFECYCLE_CONTEXT)


def pre_tool_use(data: dict[str, Any]) -> None:
    tool = str(data.get("tool_name", ""))
    if tool == "Bash":
        session_id = str(data.get("session_id") or "")
        state = load_state(session_id)
        command = tool_command(data)
        if command_is_verification(command) and not state.get("verification_since_prompt"):
            state["verification_since_prompt"] = True
            save_state(session_id, state)
        if command_is_risky(command):
            audit("PreToolUse", "boundary-gate", command)
            hook_output("PreToolUse", BOUNDARY_CONTEXT)
    elif tool == "apply_patch":
        command = tool_command(data)
        if RISKY_PATCH_RE.search(command):
            audit("PreToolUse", "boundary-gate", "apply_patch")
            hook_output("PreToolUse", BOUNDARY_CONTEXT)
    elif tool in FILE_EDIT_TOOLS:
        file_path = tool_file_path(data)
        if SENSITIVE_FILE_RE.search(file_path):
            audit("PreToolUse", "boundary-gate", file_path)
            hook_output("PreToolUse", BOUNDARY_CONTEXT)


def stop(data: dict[str, Any]) -> None:
    if data.get("stop_hook_active"):
        return
    message = str(data.get("last_assistant_message") or "")
    if not DONE_RE.search(message):
        return
    session_id = str(data.get("session_id") or "")
    state = load_state(session_id)
    last_prompt_ts = state.get("last_prompt_ts")
    if isinstance(last_prompt_ts, (int, float)):
        # Behavioral evidence: a verification command ran this turn, or the contract's
        # Verification section was updated this turn. Word-face claims alone
        # do not count when the ledger is available.
        evidence = bool(state.get("verification_since_prompt")) or contract_verification_updated(
            str(data.get("cwd") or ""), float(last_prompt_ts)
        )
    else:
        evidence = bool(EVIDENCE_RE.search(message))
    if not evidence:
        if state.get("completion_blocked_since_prompt"):
            return
        state["completion_blocked_since_prompt"] = True
        save_state(session_id, state)
        audit("Stop", "block-unverified-completion")
        continuation(ACCEPTANCE_CONTEXT)


def subagent_start(data: dict[str, Any]) -> None:
    contract = read_contract(str(data.get("cwd") or "")).strip()
    if not contract:
        return
    agent = str(data.get("agent_type") or "subagent")
    audit("SubagentStart", "inject-contract", agent)
    hook_output("SubagentStart", SUBAGENT_CONTEXT + restored_contract_text(contract))


def subagent_stop(data: dict[str, Any]) -> None:
    if data.get("stop_hook_active"):
        return
    message = str(data.get("last_assistant_message") or "")
    if not DONE_RE.search(message) or EVIDENCE_RE.search(message):
        return
    session_id = str(data.get("session_id") or "")
    agent_id = str(data.get("agent_id") or data.get("agent_type") or "subagent")
    state = load_state(session_id)
    blocked = state.get("subagent_completion_blocked")
    if not isinstance(blocked, list):
        blocked = []
    if agent_id in blocked:
        return
    blocked.append(agent_id)
    state["subagent_completion_blocked"] = blocked[-50:]
    save_state(session_id, state)
    audit("SubagentStop", "block-unverified-completion", agent_id)
    continuation(SUBAGENT_ACCEPTANCE_CONTEXT)


def session_start(data: dict[str, Any]) -> None:
    session_id = str(data.get("session_id") or "")
    state = load_state(session_id)
    if state.get("lifecycle_injected"):
        state["lifecycle_injected"] = False
        save_state(session_id, state)
    contract = read_contract(str(data.get("cwd") or "")).strip()
    if contract:
        audit("SessionStart", "restore-contract", str(data.get("source") or ""))
        hook_output("SessionStart", CONTRACT_RESTORED_CONTEXT + restored_contract_text(contract))


def self_test() -> None:
    import contextlib
    import io
    import tempfile as _tempfile

    # Prompt gating: strong lifecycle signals in, generic coding verbs out.
    assert PROMPT_RE.search("$socratic-codex bind this")
    assert PROMPT_RE.search("/socratic-codex")
    assert PROMPT_RE.search("帮我做验收")
    assert PROMPT_RE.search("rollback the migration")
    assert PROMPT_RE.search("这个方向漂移了，回到原始需求")
    assert not PROMPT_RE.search("please implement this function")
    assert not PROMPT_RE.search("fix the bug in parser.py")
    # Structured risky-command parsing.
    assert command_is_risky("git reset --hard HEAD")
    assert command_is_risky("FOO=1 git push origin main")
    assert command_is_risky("npm test && git push")
    assert command_is_risky("echo $(rm -rf /tmp/x)")
    assert command_is_risky("terraform destroy -auto-approve")
    assert not command_is_risky("git status && npm test")
    assert not command_is_risky("rm file.txt")
    assert not command_is_risky("git commit -m 'reset --hard docs'")
    assert command_is_verification("npm test")
    assert command_is_verification("cargo check")
    assert command_is_verification("python3 -m json.tool hooks.json")
    assert command_is_verification("python3 plugins/socratic-codex/hooks/socratic_hooks.py --self-test")
    assert not command_is_verification("python3 scripts/inspect.py")
    assert not command_is_verification("ls -la")
    assert not command_is_verification("git status")
    # Patch and file-path boundaries.
    assert RISKY_PATCH_RE.search("*** Delete File: README.md")
    assert RISKY_PATCH_RE.search("*** Update File: .claude/settings.json")
    assert tool_command({"tool_input": {"command": "git push"}}) == "git push"
    assert RISKY_PATCH_RE.search(tool_command({"tool_input": {"patch": "*** Delete File: README.md"}}))
    assert tool_file_path({"tool_input": {"file_path": "/repo/.claude/settings.json"}}) == "/repo/.claude/settings.json"
    assert SENSITIVE_FILE_RE.search("/repo/.claude-plugin/plugin.json")
    assert SENSITIVE_FILE_RE.search("/repo/.claude/settings.local.json")
    assert not SENSITIVE_FILE_RE.search("/repo/src/main.py")
    # Completion / evidence word-face fallback.
    assert DONE_RE.search("Implemented the fix.")
    assert EVIDENCE_RE.search("Tests not run.")
    # Subagent lifecycle: inject contract on start and block unsupported final claims once.
    subagent_start_without_contract = io.StringIO()
    with contextlib.redirect_stdout(subagent_start_without_contract):
        subagent_start({"session_id": "sub/0", "cwd": "/no/such/path", "agent_type": "Explore"})
    assert subagent_start_without_contract.getvalue() == ""
    # Contract verification freshness.
    with _tempfile.TemporaryDirectory() as tmp:
        socratic = Path(tmp) / ".socratic"
        socratic.mkdir()
        (socratic / "contract.md").write_text(
            "## Contract\nship feature\n\n## Verification\n- pytest passed (12 tests)\n",
            encoding="utf-8",
        )
        assert contract_verification_updated(tmp, time.time() - 60)
        assert not contract_verification_updated(tmp, time.time() + 3600)
        (socratic / "contract.md").write_text(
            "## Contract\nship feature\n\n## Verification\n", encoding="utf-8"
        )
        assert not contract_verification_updated(tmp, time.time() - 60)
        restored = restored_contract_text(
            "## Contract\ncurrent goal\n\n## Delta Log\n" + ("old goal\n" * 4000)
        )
        assert "current goal" in restored
        assert "old goal" not in restored
        started = io.StringIO()
        with contextlib.redirect_stdout(started):
            subagent_start({"session_id": "sub/1", "cwd": tmp, "agent_type": "Explore"})
        assert '"hookEventName": "SubagentStart"' in started.getvalue()
        assert "ship feature" in started.getvalue()
    # State round-trip.
    os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(_tempfile.mkdtemp()) / "data")
    save_state("s/1", {"verification_since_prompt": True})
    assert load_state("s/1") == {"verification_since_prompt": True}
    assert load_state("missing") == {}
    old = data_dir() / "state" / "old.json"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text("{}", encoding="utf-8")
    os.utime(old, (time.time() - STATE_MAX_AGE_SECONDS - 60,) * 2)
    save_state("fresh", {"ok": True})
    assert not old.exists()
    audit_path = data_dir() / "audit.jsonl"
    audit_path.write_bytes(b'{"old":true}\n' * (AUDIT_MAX_BYTES // 8))
    audit("Stop", "block-unverified-completion")
    assert audit_path.stat().st_size < AUDIT_MAX_BYTES
    # Stop gate: arbitrary Bash is not evidence; repeated block is once per turn.
    os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(_tempfile.mkdtemp()) / "data")
    user_prompt_submit({"session_id": "turn/1", "prompt": "fix parser"})
    pre_tool_use({"session_id": "turn/1", "tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    blocked = io.StringIO()
    with contextlib.redirect_stdout(blocked):
        stop({"session_id": "turn/1", "cwd": tmp, "last_assistant_message": "Implemented and complete."})
    assert '"decision": "block"' in blocked.getvalue()
    repeated = io.StringIO()
    with contextlib.redirect_stdout(repeated):
        stop({"session_id": "turn/1", "cwd": tmp, "last_assistant_message": "Implemented and complete."})
    assert repeated.getvalue() == ""
    user_prompt_submit({"session_id": "turn/2", "prompt": "fix parser"})
    pre_tool_use(
        {
            "session_id": "turn/2",
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m json.tool hooks.json"},
        }
    )
    verified = io.StringIO()
    with contextlib.redirect_stdout(verified):
        stop({"session_id": "turn/2", "cwd": tmp, "last_assistant_message": "Implemented and complete."})
    assert verified.getvalue() == ""
    os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(_tempfile.mkdtemp()) / "data")
    subagent_blocked = io.StringIO()
    with contextlib.redirect_stdout(subagent_blocked):
        subagent_stop(
            {
                "session_id": "turn/3",
                "agent_id": "agent-1",
                "agent_type": "Explore",
                "last_assistant_message": "Implemented and complete.",
            }
        )
    assert '"decision": "block"' in subagent_blocked.getvalue()
    subagent_repeated = io.StringIO()
    with contextlib.redirect_stdout(subagent_repeated):
        subagent_stop(
            {
                "session_id": "turn/3",
                "agent_id": "agent-1",
                "agent_type": "Explore",
                "last_assistant_message": "Implemented and complete.",
            }
        )
    assert subagent_repeated.getvalue() == ""
    subagent_with_evidence = io.StringIO()
    with contextlib.redirect_stdout(subagent_with_evidence):
        subagent_stop(
            {
                "session_id": "turn/3",
                "agent_id": "agent-2",
                "agent_type": "Explore",
                "last_assistant_message": "Completed. Tests not run; parent must verify.",
            }
        )
    assert subagent_with_evidence.getvalue() == ""
    save_state("turn/4", {"subagent_completion_blocked": "bad"})
    subagent_corrupt_state = io.StringIO()
    with contextlib.redirect_stdout(subagent_corrupt_state):
        subagent_stop(
            {
                "session_id": "turn/4",
                "agent_id": "agent-3",
                "agent_type": "Explore",
                "last_assistant_message": "Implemented and complete.",
            }
        )
    assert '"decision": "block"' in subagent_corrupt_state.getvalue()


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    handlers = {
        "user-prompt-submit": user_prompt_submit,
        "pre-tool-use": pre_tool_use,
        "stop": stop,
        "subagent-start": subagent_start,
        "subagent-stop": subagent_stop,
        "session-start": session_start,
    }
    handler = handlers.get(sys.argv[1] if len(sys.argv) > 1 else "")
    if handler is None:
        return 1
    handler(read_input())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
