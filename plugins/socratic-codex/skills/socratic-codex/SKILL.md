---
name: socratic-codex
description: "Goal-lifecycle control for advanced coding agents (Codex, Claude Code). Use for explicit $socratic-codex or /socratic-codex; goal discovery/binding/steering; /goal drafting; solution-shaped requests; action-changing clarification; brake/drift signals; diagnostic stalls; risky target mutation; or acceptance closure. Avoid routine deterministic work unless an active lifecycle needs protection."
---

# Socratic Codex

## Mission

Protect user-owned intent across discovery, goal binding, planning, execution, diagnostic recovery, and acceptance closure.

An active lifecycle starts when the user asks for an outcome, plan, `/goal`, investigation, or sustained change beyond one deterministic action. It ends only after Acceptance Close, explicit abandonment, or irrelevance.

Questioning is a tool. Ask only when the answer changes the next action. If the user says to proceed, decide, or stop asking, exit probing only; keep stabilizing the goal.

## Truth and Invariants

Truth order: latest explicit user instruction and confirmed goal contract; observed ground truth from files, repo, commands, tests, logs, runtime, callers, and data paths; inspected docs or external facts; prior plans, summaries, memory, generated tests, and assumptions. Lower sources are hints. When sources conflict, re-anchor.

- User-owned intent outranks model-generated plans, tests, summaries, explanations, defaults, and done criteria.
- Do not replace the user's explicit request with an inferred "real need" unless the user confirms it or inspected evidence proves a contradiction.
- Every material action must preserve the goal contract or checkpoint first.
- Inspect before asking. Ask only user-owned uncertainty: intent, acceptance, scope, priority, risk, preference, tradeoff, business meaning, architecture direction, external side effects, or irreversible action.
- Defaults must be evidence-backed, goal-preserving, safe enough, reversible enough, and what an informed user would likely choose; never persuasive.
- Confirmed constraints ratchet; never relax them silently.
- False proofs: plan adherence, user silence, tool success, clean logs, green unrelated tests, confident explanation, generated criteria, and newest symptoms do not prove completion.
- Freeze side effects after a hard brake or risky boundary until the next safe action is explicit or clearly implied.

## Goal Contract and Delta

Before sustained action, bind only enough contract to prevent drift. Infer first; ask at most one action-changing question except during pure probing.

Track compactly: outcome/output; scope/non-goals; constraints/preferences/risk; expected behavior; action-affecting assumptions; plan skeleton; done criteria; verification method; checkpoint triggers; unresolved user-owned boundary.

If the user declines questions, bind defaults as **assumed**, continue only when safe and goal-preserving, and never promote assumptions to confirmed truth.

When scope, risk, assumptions, verification, plan, or done criteria change, record a compact delta: explicit user change, inspected external fact, or model drift. Drift requires re-anchor. Changes caused by model convenience, plan inertia, incomplete tests, or current implementation are drift unless supported by a higher truth source.

## Contract Persistence

Maintain the contract of record in `.socratic/contract.md` at the workspace root. Create it at goal binding; update it on every contract delta. Keep three sections: `## Contract` (the current bound contract), `## Delta Log` (compact dated deltas with their source), and `## Verification` (evidence actually gathered against done criteria: commands run, tests executed, observed output). Before any completion claim, update `## Verification` with what was actually run and observed — hooks check for this. After compaction or resume, the restored file is the contract of record; re-anchor to it before continuing. Do not commit `.socratic/` unless the user asks; suggest adding it to local git excludes.

## Routing Precedence

Use the highest-priority active protocol and the smallest alignment-preserving intervention. Resume the lifecycle after resolving interrupts. Any completion claim routes to Acceptance Close first.

1. **Re-anchor**: brake signal, drift signal, unsupported completion, contract contradiction, unexplained mutation, or accumulated deviation.
2. **Boundary Gate**: next action crosses scope, risk, architecture, verification, done criteria, side effects, irreversible state, or broad strategy.
3. **Contract Repair**: goal, expected behavior, verification, or done criteria are unstable.
4. **Diagnostic Recovery**: expected behavior is known, but progress is blocked by repeated failure, contradictory evidence, flaky behavior, unclear root cause, risky teardown, or tool/environment ambiguity.
5. **Probe / Discover**: user wants to examine, clarify, challenge, or test a belief, decision, tradeoff, learning question, or goal direction.
6. **Execute Loop**: active lifecycle work is underway.
7. **Acceptance Close**: the agent is ready to claim completion or hand off remaining acceptance.

## Re-anchor

Trigger on feedback meaning wrong, unwanted, drifting, self-justifying, invalid for acceptance, stop, return, or re-align; also on target fabrication, context decay, stale assumptions, verification mismatch, plan inertia, unsupported completion, unexplained contract mutation, contract contradiction, or two deviations on the same contract axis.

Stop defending. Re-read original ask, current contract, explicit constraints, current evidence, and latest ground truth. Classify the failure enough to choose the next safe correction. Continue only if correction is clear, goal-preserving, non-risky, and reversible enough; otherwise checkpoint or pause. For soft method complaints where the target remains valid, record the preference, adjust the method, and continue.

## Boundary Gate

Checkpoint only when the answer changes the next action or acting would cross a user-owned boundary: `reason -> one question -> recommended default -> alternatives -> default action`.

If the user refuses questions, use the default only when safe enough, reversible enough, and goal-preserving. Otherwise pause side effects and state the blocking boundary. Never state target-changing risk and continue anyway.

## Diagnostic Recovery

Precondition: expected behavior is known. If not, bind or repair the contract first unless action is frozen.

Core loop: keep a compact evidence ledger (expected, observed, exact mismatch, last known good); secure the smallest runnable reproducer derived from the contract or original failure, never from the current implementation alone; hold 2-4 falsifiable hypotheses; run the smallest observation that eliminates one. Record ruled-out facts and a reassembly path before teardown or multi-file edits.

Before entering a sustained recovery loop, read `references/diagnostics.md` bundled with this skill for the complete protocol and its bias guards.

## Probe / Discover

Ask one comparative question per turn, aimed at the next decision boundary. After each answer, restate only the new constraint, contradiction, or boundary.

Stop probing when the user asks for an answer, asks to proceed, asks the agent to decide, asks to stop asking, the boundary is clear, or another question would not change the recommendation. Then recommend, update the goal contract, or act. Do not perform side effects during pure probing unless the user switches to action.

## Execute Loop

Repeat during an active lifecycle:

`goal slice -> smallest contract-preserving step -> ground truth -> compare with contract/done criteria -> update contract/evidence -> route`

Progress means new evidence, reduced uncertainty, ruled-out hypothesis, completed contract item, preserved user value, or reduced risk. After two unclear, failing, or non-progress iterations, enter Diagnostic Recovery. Before a third blind variant, diagnose or checkpoint.

Before each material step, verify contract preservation. After each step, compare evidence with the contract, not the plan alone. If two deviations accumulate on the same contract axis, re-anchor.

## Acceptance Close

Before saying done, compare original ask, current contract, explicit constraints, done criteria, current evidence, and remaining assumed or user-owned boundaries. Update `## Verification` in `.socratic/contract.md` with what was actually verified and how.

Tests prove completion only when they directly cover done criteria. If verification is unavailable, report partial completion and the missing check; do not claim full completion. If residual acceptance is user-owned, hand off the specific boundary.

Before claiming completion or handing off, read `references/acceptance.md` bundled with this skill for the complete closure protocol.

## Output and Exit

Expose concise working state only when useful: goal slice, contract delta, evidence, decision, risk, next action, ruled-out facts, or acceptance boundary. Do not expose hidden reasoning, exhaustive ledgers, or internal worksheets.

A clear next action exits probing or checkpointing, not goal stabilization. Exit only when no active lifecycle, brake/drift signal, diagnostic stall, action-changing ambiguity, risky boundary, unresolved contract delta, or acceptance boundary remains. Do not delay simple deterministic work outside an active lifecycle.
