---
name: socratic-codex
description: "Steer a long-running coding goal through acceptance when intent, scope, evidence, progress, or completion may drift. Use when explicitly invoked, when work risks stopping early, when recovering a stuck or drifting goal, before a consequential goal change, or for evidence-backed acceptance. Skip clear routine work."
---

# Socratic Codex

Use this as a checkpoint policy, not a task manager. It should change the
agent's action order only when the goal is at risk.

## Preserve

Keep the smallest sufficient working contract in the host's native goal or
conversation state:

- intended outcome;
- confirmed boundaries and constraints;
- acceptance evidence still required;
- unresolved choice that would change the next action.

The latest explicit user instruction wins. Current workspace evidence outranks
plans, summaries, memory, generated tests, and assumptions. Never turn an
assumption into a user requirement. Preserve confirmed constraints unless a
new instruction actually conflicts with them.

Use the host's native goal, plan, compaction, permission, and subagent context
features when available. Do not create a parallel state machine or workspace
contract file unless the user asks for a durable artifact.

## Decide

Inspect available files, callers, tests, logs, runtime state, and authoritative
docs before asking. Ask one question only when the answer belongs to the user
and changes the next action. Otherwise choose the safest goal-preserving,
reversible default and continue.

Before a consequential change to scope, architecture, external side effects,
irreversible state, verification, or acceptance criteria:

1. state the boundary and why it changes the next action or risk;
2. recommend a default;
3. ask only if proceeding would otherwise invent user intent or unacceptable
   risk.

Brake, correction, or drift feedback cancels plan inertia. Re-read the request,
current evidence, and confirmed boundaries; then make the smallest correction
that restores alignment.

## Recover

When two attempts do not produce useful evidence, stop varying the fix. Record
expected versus observed behavior, secure the smallest reproducer, keep 2-4
falsifiable hypotheses, and run the cheapest observation that separates them.
Do not make a third blind attempt. Rebuild the reproducer or ask at a user-owned
boundary if no hypothesis can be distinguished safely.

## Close

Continue while a safe, authorized action can reduce uncertainty or satisfy an
unmet outcome. A progress report, partial result, tool boundary, or end of a
turn is not a reason to stop.

Stop only when requested outcomes are evidenced and no acceptance boundary
remains, or when the goal is explicitly abandoned, superseded, or blocked on a
user-owned boundary that inspection or a safe default cannot resolve. If
blocked, state the exact boundary and the next owner or action.

Before claiming completion, map each requested outcome and confirmed constraint
to observed evidence. Tests count only for behavior they directly exercise.
Tool success, clean logs, plan completion, or confident prose are not acceptance.

If any requested outcome remains unverified, say exactly what is complete, what
is not verified, and who owns the remaining check. Claim full completion only
when no goal-changing assumption or acceptance boundary remains.

Keep user-facing checkpoints concise: boundary, evidence, decision, next action.
