# Acceptance Close — Full Protocol

Read before claiming completion or handing off acceptance.

## Compare

Compare original ask, current session contract (`.socratic/contracts/<session-id>.md`), constraints, done criteria, evidence, and remaining assumed/user-owned boundaries. Skipping this makes completion unsupported.

## Evidence

Tests prove completion only when they directly cover done criteria. Otherwise state what they prove, what remains an acceptance judgment, and what check or review is still needed.

Update `## Verification` with exact commands, test counts, observed outputs, or explicitly missing checks. Hooks treat a fresh Verification update or conservative verification command as behavioral evidence; without either, an unsupported completion claim is sent back once for re-anchoring.

## Re-anchor

After any brake, drift, diagnostic recovery, refactor, migration, workflow change, side effect, or accumulated deviation, completion requires re-anchored evidence matching the current contract, not the pre-deviation plan.

## Close

If all done criteria are satisfied and no boundary remains, close. If residual acceptance is user-owned (business meaning, visual quality, external side effects, irreversible steps), hand off that boundary without claiming full completion.
