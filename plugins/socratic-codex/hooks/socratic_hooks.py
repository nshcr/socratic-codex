#!/usr/bin/env python3
"""Lifecycle hooks for the Socratic Codex plugin (Codex and Claude Code).

State model:
- Per-session activity ledger in ``$CLAUDE_PLUGIN_DATA/state/<session_id>.json``
  (Codex exports the same variable for compatibility; ``PLUGIN_DATA`` is the
  Codex-native fallback). Records turn start time, whether a verification
  command ran this turn, whether a Socratic lifecycle is active, once-per-turn
  completion blocking, lifecycle-context injection dedup, and subagent stop
  dedup by agent id.
- Goal contract of record in ``<cwd>/.socratic/contracts/<safe-session-id>.md``,
  maintained by the model per the skill instructions and restored by the
  SessionStart hook after compaction or resume.
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

CONTRACT_DIR_RELPATH = os.path.join(".socratic", "contracts")
CONTRACT_MAX_CHARS = 6000
AUDIT_MAX_BYTES = 256 * 1024
AUDIT_KEEP_BYTES = 128 * 1024
STATE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60

LIFECYCLE_CONTEXT_TEMPLATE = (
    "Socratic Codex: for sustained work, bind a compact goal contract and "
    "persist it to {path}; if it is missing, recreate it from current context "
    "before material action; inspect before asking; ask only action-changing "
    "user-owned uncertainty; use Boundary Gate before scope, risk, architecture, "
    "side-effect, irreversible, or acceptance changes; do not claim completion "
    "until evidence matches done criteria."
)

BOUNDARY_CONTEXT_TEMPLATE = (
    "Socratic Codex Boundary Gate: the next tool call may cross a user-owned "
    "scope, risk, side-effect, irreversible, or acceptance boundary. Preserve "
    "the goal contract at {path}, checkpoint if the answer changes the next "
    "action, and prefer the smallest reversible step."
)

ACCEPTANCE_CONTEXT_TEMPLATE = (
    "Socratic Codex Acceptance Close: a completion claim was made without "
    "observed verification this turn (no verification command ran and "
    "{path} has no fresh Verification update). Compare the original ask, "
    "current goal contract, done criteria, and evidence; run or cite the "
    "missing verification and update the Verification section in {path}, or "
    "state explicitly what remains unverified instead of claiming full "
    "completion."
)

CONTRACT_RESTORED_CONTEXT_TEMPLATE = (
    "Socratic Codex: goal contract restored from {path} after "
    "compaction or resume. Treat it as the contract of record and re-anchor "
    "to it before continuing:\n\n"
)

CONTRACT_MISSING_CONTEXT_TEMPLATE = (
    "Socratic Codex: no session goal contract found at {path}. If this lifecycle "
    "continues sustained work, recreate a compact contract there from current "
    "context before material action."
)

SUBAGENT_CONTEXT_TEMPLATE = (
    "Socratic Codex subagent lifecycle: preserve the parent goal contract and "
    "contract path ({path}), then "
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
    r"(\$socratic-codex|/socratic-codex|@socratic-codex|"
    r"plugin://socratic-codex|/goal\b|"
    r"\b(goal|goals|acceptance|handoff|drift|drifting|stuck|rollback|"
    r"roll back|irreversible|migrate|migration|teardown|risky)\b|"
    r"目标|验收|交接|漂移|卡住|回滚|不可逆|迁移|拆除|风险|错了|"
    r"停止(提问|追问|问我|问))",
    re.IGNORECASE,
)

CONTINUE_RE = re.compile(r"\b(continue|resume|proceed|carry on)\b|继续|接着|收尾", re.IGNORECASE)

DISABLE_RE = re.compile(
    r"\b(no|skip|disable|stop using)[ -]socratic-codex\b|"
    r"不需要(使用)?\s*socratic-codex|不要(使用)?\s*socratic-codex|停用\s*socratic-codex",
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

FILE_EDIT_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

SENSITIVE_PATH_SUFFIXES = (
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    "hooks/hooks.json",
    "requirements.toml",
    ".codex/config.toml",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".mcp.json",
)

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

UNVERIFIED_BOUNDARY_RE = re.compile(
    r"\b(partial|missing|unable|not run|not verified|unverified|must verify|"
    r"needs? verification|remains? unverified)\b|"
    r"未运行|无法|缺少|部分|未验证|仍需验证",
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


def safe_session_id(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", session_id) or "unknown-session"


def state_path(session_id: str) -> Path:
    return data_dir() / "state" / f"{safe_session_id(session_id)}.json"


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


def contract_relpath(session_id: str) -> str:
    return os.path.join(CONTRACT_DIR_RELPATH, f"{safe_session_id(session_id)}.md")


def contract_path(cwd: str, session_id: str) -> Path:
    return Path(cwd or ".") / contract_relpath(session_id)


def read_contract(cwd: str, session_id: str) -> str:
    try:
        return contract_path(cwd, session_id).read_text(encoding="utf-8", errors="replace")
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


def lifecycle_active(state: dict[str, Any]) -> bool:
    return bool(state.get("lifecycle_session_active") or state.get("lifecycle_active_since_prompt"))


def contract_verification_updated(cwd: str, session_id: str, since_ts: float) -> bool:
    """True when the session contract was touched this turn and has verification content."""
    path = contract_path(cwd, session_id)
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


def normalized_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def path_is_sensitive(value: str) -> bool:
    path = normalized_path(value)
    if not path:
        return False
    return any(path == suffix or path.endswith(f"/{suffix}") for suffix in SENSITIVE_PATH_SUFFIXES)


def patch_crosses_boundary(patch: str) -> bool:
    for line in patch.splitlines():
        if line.startswith("*** Delete File: "):
            return True
        if line.startswith(("*** Add File: ", "*** Update File: ")):
            _, path = line.split(": ", 1)
            if path_is_sensitive(path):
                return True
    return False


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
            if "--dry-run" in args or "-n" in args:
                return False
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
    prompt = str(data.get("prompt", ""))
    lifecycle_prompt = bool(PROMPT_RE.search(prompt))
    disabled = bool(DISABLE_RE.search(prompt))
    restored = bool(state.get("lifecycle_restored_from_contract"))
    session_active = bool(state.get("lifecycle_session_active"))
    active = False if disabled else lifecycle_prompt or (session_active and (not restored or bool(CONTINUE_RE.search(prompt))))
    state["last_prompt_ts"] = time.time()
    state["verification_since_prompt"] = False
    state["completion_blocked_since_prompt"] = False
    state["lifecycle_active_since_prompt"] = active
    state["lifecycle_session_active"] = active
    if disabled or lifecycle_prompt or CONTINUE_RE.search(prompt):
        state["lifecycle_restored_from_contract"] = False
    state.pop("bash_since_prompt", None)
    inject = bool(
        lifecycle_prompt and not state.get("lifecycle_injected")
    )
    if inject:
        state["lifecycle_injected"] = True
    save_state(session_id, state)
    if inject:
        audit("UserPromptSubmit", "inject-lifecycle")
        hook_output("UserPromptSubmit", LIFECYCLE_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)))


def pre_tool_use(data: dict[str, Any]) -> None:
    tool = str(data.get("tool_name", ""))
    session_id = str(data.get("session_id") or "")
    if tool == "Bash":
        state = load_state(session_id)
        command = tool_command(data)
        if command_is_verification(command) and not state.get("verification_since_prompt"):
            state["verification_since_prompt"] = True
            save_state(session_id, state)
        if command_is_risky(command):
            audit("PreToolUse", "boundary-gate", command)
            hook_output("PreToolUse", BOUNDARY_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)))
    elif tool == "apply_patch":
        command = tool_command(data)
        if patch_crosses_boundary(command):
            audit("PreToolUse", "boundary-gate", "apply_patch")
            hook_output("PreToolUse", BOUNDARY_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)))
    elif tool in FILE_EDIT_TOOLS:
        file_path = tool_file_path(data)
        if path_is_sensitive(file_path):
            audit("PreToolUse", "boundary-gate", file_path)
            hook_output("PreToolUse", BOUNDARY_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)))


def stop(data: dict[str, Any]) -> None:
    if data.get("stop_hook_active"):
        return
    message = str(data.get("last_assistant_message") or "")
    if not DONE_RE.search(message):
        return
    session_id = str(data.get("session_id") or "")
    state = load_state(session_id)
    cwd = str(data.get("cwd") or "")
    if not lifecycle_active(state):
        return
    last_prompt_ts = state.get("last_prompt_ts")
    contract = read_contract(cwd, session_id).strip()
    unverified_boundary = bool(UNVERIFIED_BOUNDARY_RE.search(message))
    if not contract and not unverified_boundary:
        if state.get("completion_blocked_since_prompt"):
            return
        state["completion_blocked_since_prompt"] = True
        save_state(session_id, state)
        audit("Stop", "block-missing-contract", contract_relpath(session_id))
        continuation(CONTRACT_MISSING_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)))
        return
    if isinstance(last_prompt_ts, (int, float)):
        # Behavioral evidence: a verification command ran this turn, or the contract's
        # Verification section was updated this turn. Word-face claims alone
        # do not count when the ledger is available.
        evidence = (
            bool(state.get("verification_since_prompt"))
            or contract_verification_updated(cwd, session_id, float(last_prompt_ts))
            or unverified_boundary
        )
    else:
        evidence = bool(EVIDENCE_RE.search(message))
    if not evidence:
        if state.get("completion_blocked_since_prompt"):
            return
        state["completion_blocked_since_prompt"] = True
        save_state(session_id, state)
        audit("Stop", "block-unverified-completion")
        continuation(ACCEPTANCE_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)))


def subagent_start(data: dict[str, Any]) -> None:
    session_id = str(data.get("session_id") or "")
    state = load_state(session_id)
    if not lifecycle_active(state):
        return
    contract = read_contract(str(data.get("cwd") or ""), session_id).strip()
    if not contract:
        audit("SubagentStart", "missing-contract", contract_relpath(session_id))
        hook_output(
            "SubagentStart",
            SUBAGENT_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id))
            + CONTRACT_MISSING_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)),
        )
        return
    agent = str(data.get("agent_type") or "subagent")
    agent_id = str(data.get("agent_id") or agent)
    active = state.get("active_subagents")
    if not isinstance(active, list):
        active = []
    active.append(agent_id)
    state["active_subagents"] = active[-50:]
    save_state(session_id, state)
    audit("SubagentStart", "inject-contract", agent)
    hook_output(
        "SubagentStart",
        SUBAGENT_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id))
        + restored_contract_text(contract),
    )


def subagent_stop(data: dict[str, Any]) -> None:
    if data.get("stop_hook_active"):
        return
    message = str(data.get("last_assistant_message") or "")
    if not DONE_RE.search(message) or EVIDENCE_RE.search(message):
        return
    session_id = str(data.get("session_id") or "")
    agent_id = str(data.get("agent_id") or data.get("agent_type") or "subagent")
    state = load_state(session_id)
    active = state.get("active_subagents")
    agent_active = isinstance(active, list) and agent_id in active
    if not lifecycle_active(state) and not agent_active:
        return
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
    contract = read_contract(str(data.get("cwd") or ""), session_id).strip()
    if contract:
        state["lifecycle_session_active"] = True
        state["lifecycle_restored_from_contract"] = True
        save_state(session_id, state)
        audit("SessionStart", "restore-contract", str(data.get("source") or ""))
        hook_output(
            "SessionStart",
            CONTRACT_RESTORED_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id))
            + restored_contract_text(contract),
        )
    elif lifecycle_active(state):
        state["lifecycle_restored_from_contract"] = True
        save_state(session_id, state)
        audit("SessionStart", "missing-contract", contract_relpath(session_id))
        hook_output(
            "SessionStart",
            CONTRACT_MISSING_CONTEXT_TEMPLATE.format(path=contract_relpath(session_id)),
        )


def self_test() -> None:
    import contextlib
    import io
    import tempfile as _tempfile

    # Prompt gating: strong lifecycle signals in, generic coding verbs out.
    assert PROMPT_RE.search("$socratic-codex bind this")
    assert PROMPT_RE.search("/socratic-codex")
    assert PROMPT_RE.search("@socratic-codex")
    assert PROMPT_RE.search("plugin://socratic-codex@socratic-codex")
    assert PROMPT_RE.search("帮我做验收")
    assert PROMPT_RE.search("rollback the migration")
    assert PROMPT_RE.search("这个方向漂移了，回到原始需求")
    assert PROMPT_RE.search("停止问我")
    assert not PROMPT_RE.search("please implement this function")
    assert not PROMPT_RE.search("fix the bug in parser.py")
    assert not PROMPT_RE.search("停止这个后台服务")
    assert DISABLE_RE.search("不需要使用 socratic-codex")
    assert DISABLE_RE.search("no-socratic-codex")
    # Structured risky-command parsing.
    assert command_is_risky("git reset --hard HEAD")
    assert command_is_risky("FOO=1 git push origin main")
    assert command_is_risky("npm test && git push")
    assert command_is_risky("echo $(rm -rf /tmp/x)")
    assert command_is_risky("terraform destroy -auto-approve")
    assert not command_is_risky("git status && npm test")
    assert not command_is_risky("git push --dry-run origin main")
    assert not command_is_risky("rm file.txt")
    assert not command_is_risky("git commit -m 'reset --hard docs'")
    assert command_is_verification("npm test")
    assert command_is_verification("cargo check")
    assert command_is_verification("python3 -m json.tool hooks.json")
    assert command_is_verification("python3 plugins/socratic-codex/hooks/socratic_hooks.py --self-test")
    assert not command_is_verification("python3 scripts/inspect.py")
    assert not command_is_verification("ls -la")
    assert not command_is_verification("git status")
    risky_hook = io.StringIO()
    with contextlib.redirect_stdout(risky_hook):
        pre_tool_use({"session_id": "risk/1", "tool_name": "Bash", "tool_input": {"command": "git push"}})
    assert ".socratic/contracts/risk-1.md" in risky_hook.getvalue()
    # Patch and file-path boundaries.
    assert patch_crosses_boundary("*** Delete File: README.md")
    assert patch_crosses_boundary("*** Update File: .claude/settings.json")
    assert tool_command({"tool_input": {"command": "git push"}}) == "git push"
    assert patch_crosses_boundary(tool_command({"tool_input": {"patch": "*** Delete File: README.md"}}))
    assert not patch_crosses_boundary("*** Update File: README.md\n+ Mention config.toml in docs\n")
    assert tool_file_path({"tool_input": {"file_path": "/repo/.claude/settings.json"}}) == "/repo/.claude/settings.json"
    assert path_is_sensitive("/repo/.claude-plugin/plugin.json")
    assert path_is_sensitive("/repo/.claude/settings.local.json")
    assert not path_is_sensitive("/repo/src/main.py")
    assert not path_is_sensitive("/repo/docs/hooks/hooks.json.md")
    # Completion / evidence word-face fallback.
    assert DONE_RE.search("Implemented the fix.")
    assert EVIDENCE_RE.search("Tests not run.")
    assert UNVERIFIED_BOUNDARY_RE.search("Tests not run; parent must verify.")
    assert contract_relpath("turn/2") == os.path.join(".socratic", "contracts", "turn-2.md")
    # Subagent lifecycle: inject contract on start and block unsupported final claims once.
    subagent_start_without_contract = io.StringIO()
    with contextlib.redirect_stdout(subagent_start_without_contract):
        subagent_start({"session_id": "sub/0", "cwd": "/no/such/path", "agent_type": "Explore"})
    assert subagent_start_without_contract.getvalue() == ""
    # Contract verification freshness.
    with _tempfile.TemporaryDirectory() as tmp:
        contract = contract_path(tmp, "sub/1")
        contract.parent.mkdir(parents=True)
        contract.write_text(
            "## Contract\nship feature\n\n## Verification\n- pytest passed (12 tests)\n",
            encoding="utf-8",
        )
        assert contract_verification_updated(tmp, "sub/1", time.time() - 60)
        assert not contract_verification_updated(tmp, "sub/1", time.time() + 3600)
        contract.write_text(
            "## Contract\nship feature\n\n## Verification\n", encoding="utf-8"
        )
        assert not contract_verification_updated(tmp, "sub/1", time.time() - 60)
        restored = restored_contract_text(
            "## Contract\ncurrent goal\n\n## Delta Log\n" + ("old goal\n" * 4000)
        )
        assert "current goal" in restored
        assert "old goal" not in restored
        stale_started = io.StringIO()
        with contextlib.redirect_stdout(stale_started):
            subagent_start({"session_id": "sub/1", "cwd": tmp, "agent_type": "Explore"})
        assert stale_started.getvalue() == ""
        os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(_tempfile.mkdtemp()) / "data")
        save_state("sub/missing", {"lifecycle_session_active": True})
        missing_started = io.StringIO()
        with contextlib.redirect_stdout(missing_started):
            subagent_start({"session_id": "sub/missing", "cwd": tmp, "agent_type": "Explore"})
        assert "no session goal contract found" in missing_started.getvalue()
        assert ".socratic/contracts/sub-missing.md" in missing_started.getvalue()
        save_state("sub/1", {"lifecycle_session_active": True})
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
    # Stop gate: ordinary turns skip; active lifecycle turns require evidence once.
    os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(_tempfile.mkdtemp()) / "data")
    with _tempfile.TemporaryDirectory() as stop_tmp:
        user_prompt_submit({"session_id": "turn/1", "prompt": "fix parser", "cwd": stop_tmp})
        pre_tool_use({"session_id": "turn/1", "tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        skipped = io.StringIO()
        with contextlib.redirect_stdout(skipped):
            stop({"session_id": "turn/1", "cwd": stop_tmp, "last_assistant_message": "Implemented and complete."})
        assert skipped.getvalue() == ""
        with contextlib.redirect_stdout(io.StringIO()):
            user_prompt_submit({"session_id": "turn/2", "prompt": "$socratic-codex fix parser", "cwd": stop_tmp})
        pre_tool_use({"session_id": "turn/2", "tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        blocked = io.StringIO()
        with contextlib.redirect_stdout(blocked):
            stop({"session_id": "turn/2", "cwd": stop_tmp, "last_assistant_message": "Implemented and complete."})
        assert '"decision": "block"' in blocked.getvalue()
        repeated = io.StringIO()
        with contextlib.redirect_stdout(repeated):
            stop({"session_id": "turn/2", "cwd": stop_tmp, "last_assistant_message": "Implemented and complete."})
        assert repeated.getvalue() == ""
        with contextlib.redirect_stdout(io.StringIO()):
            user_prompt_submit({"session_id": "turn/2b", "prompt": "$socratic-codex fix parser", "cwd": stop_tmp})
        gap = io.StringIO()
        with contextlib.redirect_stdout(gap):
            stop({"session_id": "turn/2b", "cwd": stop_tmp, "last_assistant_message": "Implemented. Tests not run."})
        assert gap.getvalue() == ""
        with contextlib.redirect_stdout(io.StringIO()):
            user_prompt_submit({"session_id": "turn/3", "prompt": "$socratic-codex fix parser", "cwd": stop_tmp})
        turn3_contract = contract_path(stop_tmp, "turn/3")
        turn3_contract.parent.mkdir(parents=True, exist_ok=True)
        turn3_contract.write_text("## Contract\nfinish goal\n\n## Verification\n", encoding="utf-8")
        pre_tool_use(
            {
                "session_id": "turn/3",
                "tool_name": "Bash",
                "tool_input": {"command": "python3 -m json.tool hooks.json"},
            }
        )
        verified = io.StringIO()
        with contextlib.redirect_stdout(verified):
            stop({"session_id": "turn/3", "cwd": stop_tmp, "last_assistant_message": "Implemented and complete."})
        assert verified.getvalue() == ""
        with contextlib.redirect_stdout(io.StringIO()):
            user_prompt_submit({"session_id": "turn/no-contract-verified", "prompt": "$socratic-codex fix parser", "cwd": stop_tmp})
        pre_tool_use(
            {
                "session_id": "turn/no-contract-verified",
                "tool_name": "Bash",
                "tool_input": {"command": "python3 -m json.tool hooks.json"},
            }
        )
        missing_despite_verification = io.StringIO()
        with contextlib.redirect_stdout(missing_despite_verification):
            stop(
                {
                    "session_id": "turn/no-contract-verified",
                    "cwd": stop_tmp,
                    "last_assistant_message": "Implemented and complete.",
                }
            )
        assert '"decision": "block"' in missing_despite_verification.getvalue()
        assert ".socratic/contracts/turn-no-contract-verified.md" in missing_despite_verification.getvalue()
        user_prompt_submit({"session_id": "turn/4", "prompt": "fix parser", "cwd": stop_tmp})
        missing_contract_new_task = io.StringIO()
        with contextlib.redirect_stdout(missing_contract_new_task):
            stop({"session_id": "turn/4", "cwd": stop_tmp, "last_assistant_message": "Finished."})
        assert missing_contract_new_task.getvalue() == ""
        missing_inactive_restore = io.StringIO()
        with contextlib.redirect_stdout(missing_inactive_restore):
            session_start({"session_id": "turn/5", "cwd": stop_tmp, "source": "resume"})
        assert missing_inactive_restore.getvalue() == ""
        user_prompt_submit({"session_id": "turn/5", "prompt": "fix parser", "cwd": stop_tmp})
        restored_but_new_task = io.StringIO()
        with contextlib.redirect_stdout(restored_but_new_task):
            stop({"session_id": "turn/5", "cwd": stop_tmp, "last_assistant_message": "Finished."})
        assert restored_but_new_task.getvalue() == ""
        save_state("turn/missing", {"lifecycle_session_active": True})
        missing_contract = io.StringIO()
        with contextlib.redirect_stdout(missing_contract):
            session_start({"session_id": "turn/missing", "cwd": stop_tmp, "source": "resume"})
        assert "no session goal contract found" in missing_contract.getvalue()
        user_prompt_submit({"session_id": "turn/missing", "prompt": "fix parser", "cwd": stop_tmp})
        missing_new_task = io.StringIO()
        with contextlib.redirect_stdout(missing_new_task):
            stop({"session_id": "turn/missing", "cwd": stop_tmp, "last_assistant_message": "Finished."})
        assert missing_new_task.getvalue() == ""
        save_state("turn/missing-continue", {"lifecycle_session_active": True})
        with contextlib.redirect_stdout(io.StringIO()):
            session_start({"session_id": "turn/missing-continue", "cwd": stop_tmp, "source": "resume"})
        user_prompt_submit({"session_id": "turn/missing-continue", "prompt": "continue", "cwd": stop_tmp})
        missing_continue = io.StringIO()
        with contextlib.redirect_stdout(missing_continue):
            stop(
                {
                    "session_id": "turn/missing-continue",
                    "cwd": stop_tmp,
                    "last_assistant_message": "Finished.",
                }
            )
        assert '"decision": "block"' in missing_continue.getvalue()
        assert ".socratic/contracts/turn-missing-continue.md" in missing_continue.getvalue()
        turn6_contract = contract_path(stop_tmp, "turn/6")
        turn6_contract.parent.mkdir(parents=True, exist_ok=True)
        turn6_contract.write_text(
            "## Contract\nfinish goal\n\n## Verification\n", encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            session_start({"session_id": "turn/6", "cwd": stop_tmp, "source": "resume"})
        user_prompt_submit({"session_id": "turn/6", "prompt": "continue", "cwd": stop_tmp})
        contract_blocked = io.StringIO()
        with contextlib.redirect_stdout(contract_blocked):
            stop({"session_id": "turn/6", "cwd": stop_tmp, "last_assistant_message": "Finished."})
        assert '"decision": "block"' in contract_blocked.getvalue()
    os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(_tempfile.mkdtemp()) / "data")
    subagent_inactive = io.StringIO()
    with contextlib.redirect_stdout(subagent_inactive):
        subagent_stop(
            {
                "session_id": "turn/3",
                "agent_id": "agent-0",
                "agent_type": "Explore",
                "last_assistant_message": "Implemented and complete.",
            }
        )
    assert subagent_inactive.getvalue() == ""
    save_state("turn/3", {"lifecycle_session_active": True})
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
    save_state("turn/4", {"subagent_completion_blocked": "bad", "lifecycle_session_active": True})
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
