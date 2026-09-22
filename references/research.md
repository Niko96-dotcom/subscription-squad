# Research mode

Use this workflow when `$subscription-squad` is invoked for substantive research. Astra owns live retrieval and the final answer; workers synthesize or challenge a frozen evidence packet. Add research only for a real unknown. For command templates and runner semantics see [execution](execution.md); for provider terms see [routes](routes.md).

## Astra-first retrieval

Astra owns live web retrieval, source selection, source-date and currentness checks, primary-source preference, citation verification, reconciliation of conflicting evidence, and final integration. Prefer primary sources over secondary summaries. Check publish or last-updated dates against the question; discard or flag stale sources when currentness matters.

Do not assume any worker route has live retrieval. Workers operate only on the frozen packet below. If later retrieval adds a source, update the packet and verify it before that source influences a worker or the final answer.

## Frozen source packet

Before dispatching research workers, freeze one bounded packet containing:

- the research question and any scope or date constraints;
- each source URL with title and publish or retrieval date;
- the relevant excerpts, data, or version facts per source;
- open questions or contradictions the workers must address.

Keep the packet self-contained: include the excerpts a worker needs so it never has to fetch. Never omit required context to shorten a packet. Confirm the packet is accessible from the worker workspace: embed excerpts directly and do not rely on outside files or live retrieval.

## Worker dispatch

For focused research, default to one synthesis or extraction worker on the frozen packet, with a bounded brief stating the question, the packet, the required deliverable (comparison table, extracted facts, or recommendation with evidence), and the handoff format.

For consequential, contested, or high-ambiguity research, add a second independent challenge worker after the first draft exists so it has claims to test. Give the challenger the same packet plus the draft claims, without telling it the claims are correct, and ask for contradictions, missing evidence, and alternative interpretations with source references. Do not force extraction-then-synthesis when one worker suffices, with no challenger for trivial work.

Every dispatch must own a concrete deliverable that influences the result; a probe, generic opinion, duplicate restatement, or rubber stamp does not satisfy the dispatch contract in `SKILL.md`. Keep the default small.

## Verification and integration

Astra verifies every final claim against the frozen sources, reconciles synthesis with challenge findings, and removes unsupported claims. Re-check citations before integrating. Record route, elapsed time, attempts, acceptance, material findings, and substantive coordinator repairs in a task-local ledger; call counts and provider tokens alone are not Codex savings.

No worker is required for a deterministic lookup needing no model judgment. A skip is also allowed when all suitable routes are unavailable, when material is sensitive or excluded for those routes, or when no route adds useful capacity. State every skip early and in the final outcome; never silently substitute a full Astra synthesis for the required dispatch.

## Provisional route roles

Roles are provisional working defaults, not quality rankings. Quality remains unmeasured until matched trials with frozen rubrics record acceptance.

- Antigravity: structured extraction or comparison from self-contained packets; also the selected alternate for implementation-oriented writing when explicitly chosen.
- Muse: broad synthesis and implementation-oriented research from self-contained non-sensitive packets; training-enabled, so avoid secrets, private records, or excluded code.
- Cursor Grok: read-only adversarial review and contradiction checks on self-contained packets; Astra supplies sources.
- Native Grok Build: alternate read-only synthesis or review on bounded packets; tool-heavy or large reviews carry latency and timeout risk.
- Astra: retrieval, source selection, citation verification, reconciliation, integration, and acceptance.

All four worker routes are subscription or account-backed, not guarantees of zero overage; the runner never enables overage or changes billing. Refresh inventories when invoked and stop a route on quota, authentication, or billing errors.
