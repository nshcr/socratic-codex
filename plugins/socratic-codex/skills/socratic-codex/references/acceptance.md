# Acceptance Close — Full Protocol

Load this before claiming completion or handing off acceptance.

## Compare before claiming

Compare original ask, current contract (`.socratic/contract.md`), explicit constraints, done criteria, current evidence, and remaining assumed or user-owned boundaries. A completion claim that skips this comparison is unsupported by definition.

## Evidence standards

Tests prove completion only when they directly cover done criteria. Otherwise state what evidence proves, what remains an acceptance judgment, and whether review or another check is required. If verification is unavailable, report partial completion and the missing check; do not claim full completion.

Update `## Verification` in `.socratic/contract.md` with what was actually run and observed: exact verification commands, test counts, observed outputs, or explicitly missing checks. Hooks treat a fresh Verification update or a conservative verification-command match as the behavioral evidence for a completion claim — a claim without either will be sent back once for re-anchoring.

## Re-anchored completion

After any brake, drift, diagnostic recovery, refactor, migration, workflow change, side effect, or accumulated deviation, completion requires re-anchored evidence matching the current contract, not the pre-deviation plan.

## Close or hand off

If all done criteria are satisfied and no boundary remains, close the lifecycle. If residual acceptance is user-owned (business meaning, visual quality, external side effects, irreversible steps), hand off the specific boundary explicitly without claiming full completion.
