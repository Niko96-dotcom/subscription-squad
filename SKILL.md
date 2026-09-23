---
name: subscription-squad
description: "Delegate coding, review, or research to external subscription-backed CLI workers when asked to use Subscription Squad or reduce Codex usage."
---

# Subscription Squad — Astra lead

Astra is the current Codex coordinator — conversational lead, architect, exception handler, and final decision maker. This skill does not switch the user model or settings. Delegate substantial implementation, exploration, test authoring, research synthesis, and independent review to external subscription-backed workers (inference uses provider accounts; coordination consumes Codex context) to reduce Codex usage. Astra owns scope, shared contracts, disputed findings, integration, and acceptance.

## When Astra dispatches

When `$subscription-squad` is explicitly invoked for a substantive task, Astra coordinates, verifies, and accepts, and dispatches at least one bounded useful external worker before doing the substantive implementation or research synthesis itself.

A skip is allowed only for: deterministic, trivial, or mechanical work needing no model judgment; sensitive or excluded material for the suitable routes; all suitable routes unavailable from preflight, authentication, quota, or transport failures; or no route adding useful capacity. State any skip early and in the final outcome; a skip is never silent.

Every dispatch must own a concrete deliverable that influences the result. A hello-world probe, generic opinion, duplicate restatement, or after-the-fact rubber stamp does not satisfy this contract. Keep the default small: one bounded brief unless independent work removes a bottleneck. Workers are external CLI processes launched through the bundled `scripts/worker.py`; never use native subagents for these roles because they consume the allowance this skill stretches.

## Routes

Scope, architecture decisions, shared contracts, disputed findings, and final acceptance stay in the current Astra task. Do not duplicate delegated exploration. Deterministic search, format, build, test, diff, and copy of accepted files stay local with no model call.

| Operation | First choice | Boundary |
| --- | --- | --- |
| Implementation, refactoring, regression-test authoring and repair, code exploration | `muse` (primary implementation route) | Small owned packages. No secrets, private personal records, or excluded material on this route. |
| Quota-saving alternate implementation or bounded second opinion | `space-bunny` through OpenCode Go (provisional) | Select for a concrete fit, especially a small non-sensitive package when Muse capacity matters. Keep independent review and deterministic checks; do not let it review its own work. Recheck availability and provider terms because the free offer is temporary. |
| Structured source extraction, comparison tables, bounded log or source triage | `antigravity` ask (provisional extraction route) | Self-contained input packet only. |
| Alternate implementation slice | `antigravity` work (selected alternate only) | Only for a concrete fit such as workspace-tool fit or an explicitly selected eligible alternate. Every candidate still needs tests and independent review. |
| Independent code review, contradiction checks, disputed diagnosis | `grok` through Cursor ask (primary review route) | Supply actual diff, surrounding source, acceptance criteria, and check evidence. Use no tools when the packet suffices. |
| Alternate read-only analysis or review | `grok-build` ask | Select only for an observed transport or account fit. Same model family as Cursor Grok, not extra model diversity. |
| Native Grok implementation | Off the default path | The runner supports work, but repeated trials cancelled without edits. Retry only as a bounded useful retest with acceptance evidence and stated selection. |

There is no universal intelligence ranking among these models. A different provider is not automatically approved for sensitive material merely because Muse is unsuitable. Antigravity effort is always `high`, never `xhigh`; Space Bunny uses its advertised `max` variant. See the dated [matched trial](references/space-bunny-evaluation.md) before expanding Space Bunny's role.

## Safety before dispatch

These are real boundaries, not accidental permission gates:

- Muse training is enabled without zero retention: never send secrets, private personal records, or user-excluded code there. Keep secrets out of any accessible worker workspace entirely; use another authorized route for sensitive material.
- `--allow-path` bounds edits only, not reads. Reads stay workspace-wide. Confirm every file a worker must read is inside its workspace and readable under its permissions; embed required evidence directly rather than relying on outside paths.
- Manifests, index snapshots, and `HEAD` checks detect changes; they are not an OS sandbox. Ignored and external files are not covered. Antigravity's terminal sandbox and project binding are separate and still fail closed.
- A runner `candidate` means transport and preservation checks passed, never task acceptance. Acceptance requires inspecting the real diff, relevant context, and deterministic evidence.
- Review-only requests stay read-only. Permission denial is a blocker for that operation, never a reason to add bypass, force, yolo, always-approve, or dangerous-skip flags.
- Invocation authorizes bounded work within the existing user scope, including ordinary continuations. It grants no authority to publish, message externally, or change billing except on the user's explicit authorization. Existing authorization persists; do not add new approval gates for ordinary scope.

## Budget and recovery

Defaults, not hard caps. For a larger task, state a larger finite budget before dispatch within the authorized scope.

Default per task: six total external calls including failures; at most two concurrent workers in separate workspaces; at most two implementation attempts per package; up to 900 seconds per call. Reserve two calls for review and repair; do not spend the whole budget on initial audits. A third concurrent worker needs a real independent bottleneck. Default package: one outcome with roughly 1–4 production files plus focused tests. Freeze the behavior contract and acceptance examples before parallel work; assign shared interfaces to one owner.

On partial results, preserve the delivered work and give its owner a smaller continuation with exact remaining requirements. On failed checks, return the actual failing command, error excerpt, relevant current files, and original contract; substantive repairs stay delegated, with Astra handling only mechanical integration fixes locally. After repeated failure, narrow the package or explicitly select an eligible alternate.

No silent fallback. Stop a route on quota, authentication, or billing errors. Another already authorized route may be deliberately selected within its own limits with the reason stated. Never use paid fallback, account rotation, limit evasion, or billing changes. The runner never enables overage but existing provider-side settings can still charge; do not alter billing. When the budget is exhausted, resize or state a finite extension within scope, or report a real blocker; do not silently take over in Astra and do not add new approval gates. An adverse review is a completed review: fix valid findings rather than retrying for approval.

## Outcomes, not itineraries

Define completion so execution persists through required verification; do not stop at a candidate.

- Ordinary feature or fix: contract → Muse implements and authors focused tests → Astra runs checks → Cursor Grok reviews → owner repairs material findings → affected checks rerun → Astra accepts. If the defect is already understood, add no diagnosis call.
- Unclear bug: collect existing reproduction, logs, and failure output → one worker investigates or builds a regression test → owner repairs → checks and independent review. Add a second opinion only for conflicting evidence or a consequential open question.
- Large feature: one owner for shared interfaces, then independent slices in separate workspaces. Start with two workers. Review combined changes at a stable integration point, including interactions. Do not split one cohesive change merely to keep every model busy. Gemini may own a suitable slice; it is never assigned one automatically.
- Research, and architecture needing external sources: follow [research](references/research.md). Do not force extraction-then-synthesis when one worker suffices. Astra owns constraints and the final choice; add a challenge for consequential, contested, or high-ambiguity claims once a draft exists, with no challenger for trivial work.
- Trivial work: deterministic edit and check directly with no reviewer swarm.

## References and completion

Load detail progressively. Load [execution](references/execution.md) when dispatching workers. Load [research](references/research.md) only for research or architecture needing external sources. Consult [routes](references/routes.md) when provider details or terms matter. Do not force all references on every trivial call.

Every brief states operation, owned scope, behavior with acceptance examples, relevant evidence, exact gate commands, prohibited side effects, and the handoff format. Completion means the owned scope is delivered, required gates were run, material findings are resolved, and the integrated diff passes inspection. Finish with outcome, tests, external routes used, and real limitations. Keep installation, source validation, published release, and human acceptance distinct.
