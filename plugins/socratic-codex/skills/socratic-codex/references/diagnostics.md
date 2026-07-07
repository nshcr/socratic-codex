# Diagnostic Recovery — Full Protocol

Read for sustained diagnostic loops. Precondition: expected behavior is known. If not, bind or repair the contract first unless action is frozen.

## Ledger

Keep expected, observed, exact mismatch, changed inputs, last known good, and observed/inferred/unknown status. Mirror durable entries into `## Delta Log`; keep `## Contract` short and current.

## Ground truth

If ground truth is missing, create or identify the smallest runnable test, reproducer, assertion, fixture, command, or observable check. Generated tests must derive from the contract, original failure, or confirmed expected behavior, never current implementation alone.

## Hypotheses

Keep 2-4 hypotheses with predictions or falsifiers. Run the smallest observation or change that can eliminate one hypothesis. Failed experiments count only when they rule something out, narrow the fault class, improve the reproducer, or expose a missing observation. Record ruled-out facts and a reassembly path before teardown, refactor, migration, or multi-file edit. Ask only if the next discriminator is user-owned, risky, irreversible, or changes scope, verification, or done criteria.

## Bias guards

Guard against defended first theory, newest-symptom bias, false binary, stale plan, green-test tunnel vision, broad edit without falsifier, tool noise as product truth, and implementation-derived tests.

## Exit

Exit recovery when the root cause is confirmed by a discriminating observation, or checkpoint when the next discriminator crosses a user-owned boundary. Two unclear or non-progress iterations after entering recovery mean the reproducer or the hypothesis set is wrong — rebuild those before more edits.
