# Research mode

Use this workflow when `$subscription-squad` is explicitly invoked for a substantive research task. The coordinator owns live retrieval and the final answer; workers synthesize or challenge a frozen evidence packet. Add research only for a real unknown.

## Coordinator-first retrieval

The coordinator owns live web retrieval, source selection, source-date and currentness checks, primary-source preference, citation verification, reconciliation of conflicting evidence, and final integration. Prefer primary sources (official docs, specifications, source repositories, published standards) over secondary summaries. Check publish or last-updated dates against the research question; discard or flag stale sources when currentness matters.

Do not assume any worker route has live web retrieval. Workers operate only on the frozen source packet below. If later retrieval adds a source, update the packet and verify it before that source may influence a worker or the final answer.

## Frozen source packet

Before dispatching research workers, freeze one bounded packet containing:

- the research question and any scope or date constraints;
- each source URL with title and publish date or retrieval date;
- the relevant excerpts, data, or version facts per source;
- open questions or contradictions the workers must address.

Keep the packet bounded but self-contained: include the excerpts a worker needs so it never has to fetch. Never omit required context to make a packet shorter.

## Worker dispatch

For focused substantive research, default to one synthesis or extraction worker on the frozen packet, with a bounded brief stating the question, the packet, the required deliverable (comparison table, extracted facts, or recommendation with evidence), and the handoff format.

For consequential, open-ended, contested, or high-ambiguity research, default to a second independent challenge or contradiction worker after the initial synthesis. Run it after the first draft exists so it has claims to test. Give the challenger the same evidence packet plus the draft claims, without telling it the claims are correct, and ask for contradictions, missing evidence, and alternative interpretations with source references.

Every dispatch must own a concrete deliverable that influences the result; a hello-world probe, generic opinion, duplicate restatement, or after-the-fact rubber stamp does not satisfy the explicit-invocation dispatch contract in `SKILL.md`. Keep the default small.

## Verification and integration

The coordinator verifies every final claim against the frozen sources, reconciles the synthesis with the challenge findings, and removes unsupported claims. Re-check citations (URL, title, date) before integrating. Record the route, elapsed time, decisive checks, and any coordinator repairs in the task-local ledger; call counts and provider tokens alone are not Codex savings.

No worker is required for a deterministic, trivial, or mechanical lookup or extraction that needs no model judgment. A substantive skip is also allowed when all suitable routes are unavailable because of preflight, authentication, quota, or transport failures; when the material is sensitive or excluded for those routes; or when no route adds useful capacity, including when a worker could only restate the packet. State every skip early and report it in the final outcome; never silently substitute a full Codex synthesis for the required dispatch.

## Provisional route roles (evidence-bounded)

Roles are provisional working defaults, not model-quality rankings. Quality remains unmeasured until matched trials with frozen rubrics record acceptance.

- Antigravity: fast structured extraction or comparison from self-contained source packets; latency evidence is N=1 only, and status-marker reliability carries the same N=1 caveat recorded in `references/routes.md`.
- Muse: broad synthesis and implementation-oriented research from self-contained non-sensitive packets; Muse Contributor is training-enabled so avoid secrets, private personal records, or excluded code; status-marker reliability carries the N=1 caveat in `references/routes.md`.
- Legacy Cursor Grok: read-only adversarial review, contradiction checks, and code or architecture research on self-contained packets; live retrieval is not assumed, so the coordinator supplies sources.
- Native Grok Build: deep alternate synthesis or adversarial review on bounded packets; tool-heavy or large reviews carry latency and timeout risk; the wrapper fixes `--disable-web-search`, so live retrieval in the wrapper is not assumed.
- Codex coordinator: retrieval, source selection, citation verification, reconciliation, integration, and acceptance.

All four worker routes are subscription or account-backed provider routes, not guarantees of zero overage; the runner never enables overage or changes billing, and no subscription-only monetary ceiling is claimed. Refresh inventories when invoked and stop a route on quota, authentication, or billing errors.
