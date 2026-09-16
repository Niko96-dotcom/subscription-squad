---
name: subscription-squad
description: "Complete coding, review, and research tasks with Codex coordinating Muse Spark 1.3 Contributor through OpenCode Go and Grok 4.6 through Cursor. Use when explicitly invoked, when asked for subscription-backed external subagents, or to minimize Codex usage using existing subscriptions."
---

# Subscription Squad

Keep Codex as a lean coordinator. Delegate substantial implementation and investigation to external CLI workers. Invocation authorizes bounded delegation within the user's task; it does not expand permissions to publish, send messages, buy credits, or modify billing. Complete the requested task and required verification.

## Route and budget

| Work | Route | Default effort |
| --- | --- | --- |
| Implementation, code exploration, focused research | OpenCode Go `opencode-go/muse-spark-1.3-contributor` | `xhigh` |
| Independent review, disputed diagnosis | Cursor `cursor-grok-4.6-xhigh` | encoded in model ID |
| Task decomposition, integration, final acceptance | Current Codex conversation | existing setting |

Use the bundled `scripts/worker.py`; resolve it relative to this file. Do not use native Codex subagents for these roles: they consume Codex usage. Do deterministic operations locally without a model. Do not send the entire conversation to workers. Do not repeatedly inspect sources already delegated unless needed for acceptance.

Start with at most two independent workers concurrently, each in a separate workspace. Add a third only for a concrete independent task that removes a bottleneck. Batch small related tasks in one brief. Default per user task: six worker calls total (including failed calls), at most two implementation attempts per work package, and 900 seconds per call. Reserve two of those calls for repairs or review; do not spend the entire budget on initial audits. These are operating limits, not guaranteed monetary caps. Stop repeated failures; adapt or report the actual blocker. For larger explicit tasks, set a justified finite call budget before launching. Exhausting a budget is a routing decision, not permission for Codex to silently implement the remaining project: resize or extend the external budget with a stated reason within the authorized scope, or report a real blocker.

Use one implementation followed by one cross-model review for ordinary changes. Dispatch acceptance review only after the package is delivered and focused checks pass, with no scope violations. Resolve partial work first; review a frozen partial diff only when an explicitly named diagnostic question warrants the extra call. Add research only for a real unknown; skip ceremonial agents. Review-only requests remain read-only. Trivial edits do not need a swarm. Reserve Codex reasoning for decisions, contradictory evidence, and acceptance, not duplicate full implementations. Codex may make a mechanical local fix or integration edit; substantive new logic, broad test writing, and multi-file repairs go back to a worker with the actual failure evidence. Record why any substantial coordinator implementation was necessary.

## Preflight

1. Inspect applicable AGENTS.md, Git status, and the user's scope. Identify required checks and sensitive paths. Muse Contributor permits provider training; do not send secrets, private personal records, or code the user has excluded from this provider. Read `references/routes.md` for current route limitations and billing caveats when relevant.
2. Run once per task, preferably in parallel:
   `python3 <skill>/scripts/worker.py --provider muse --check`
   `python3 <skill>/scripts/worker.py --provider grok --check`
3. Exact inventory availability is not a successful inference or a quota guarantee. Use the first bounded useful assignment as the live test; avoid repeated hello-world probes. No silent fallback to Codex, another provider, fast/premium models, or pay-as-you-go.
4. The runner uses existing logins and never enables overage. Provider-side overage settings can still charge a balance; the runner cannot enforce a subscription-only monetary ceiling. Never claim otherwise. On quota/auth/billing errors stop that route and report; do not change billing or purchase anything.

## Brief, launch, and collect

Freeze one behavior contract and its acceptance examples before parallel implementation. Assign shared interfaces to one owner; consumers wait for that contract. Default work package: one outcome with roughly 1–4 production files plus its focused tests, not an entire subsystem with docs and all adapters. For broad repetitive docs, finish one canonical version, propagate deterministic substitutions locally, then review consistency.

Muse now defaults to 60 model steps; `--steps 5..120` is an explicit bounded override, independent of wall time. Split oversized packages before increasing it. Four of eight Muse calls in the first substantial run hit 30 steps; that is evidence of a poor fit between package size and budget, not proof that a larger cap guarantees quality.

For review, prefer a self-contained packet containing the actual diff, relevant surrounding source, acceptance criteria and test evidence. Tell Grok to use no tools when that packet is sufficient; tool-driven exploration can be much slower. Never omit required context to make a packet shorter; allow a bounded read-only investigation when needed.

Create a concise prompt file outside the target checkout. Include actual schema/CLI examples for integration work; require regression fixtures to match observed formats rather than inventing mock contracts. Include goal, owned paths, inputs to read, frozen behavior, acceptance criteria, prohibited side effects, and a <=500-word handoff. Tell workers they are not alone and must preserve others' edits. For external research, collect relevant primary-source snapshots once with the coordinator’s working web tools, retaining URLs and retrieval dates; have the worker compare those artifacts. Do not assume Cursor ask-mode has live search/fetch. If a worker actually needs unavailable retrieval, stop that attempt and supply sources rather than buying another identical research call. Demand supported findings and explicit uncertainty.

For implementation use an isolated worktree at a verified commit when possible. A new worktree does not include dirty/untracked changes: explicitly transfer only relevant authorized changes, or serialize work in the current checkout with a baseline. Do not stash, reset, clean or overwrite unrelated changes. Do not run any other edits while a worker uses the same checkout. Separate review snapshots allow independent parallel work. The runner rejects simultaneous use of the same workspace.

```bash
python3 <skill>/scripts/worker.py --provider muse --mode work \
  --workspace /absolute/checkout --allow-path src/owned_file.py \
  --prompt-file /absolute/brief.txt --run-dir /absolute/fresh-run-dir --timeout 900

python3 <skill>/scripts/worker.py --provider grok --mode ask \
  --workspace /absolute/checkout --trust \
  --prompt-file /absolute/review.txt --run-dir /absolute/fresh-review-dir --timeout 600
```

Use `--trust` only for a workspace already authorized/trusted or a fixture you created. Never add force/yolo flags to bypass a denied action. `--allow-path` repeats; grant narrow files or directories. Muse shell and nested delegation are disabled: Codex runs verification commands itself. After each candidate, run focused checks once and send only failing commands, relevant error excerpts, current file versions, and the original acceptance criteria back to the owner. Do not rewrite the repair yourself or weaken tests to accept it. Run the full required gate at stable integration points and final acceptance; rerun after material changes, not on every small intermediate edit. Grok is a read-only reviewer in this runner. Both routes keep their native CLI logs and a compact result file.

Run long calls through the host's asynchronous process/session tools. Wait on process completion, usually 30–60 seconds at a time; keep user updates brief. Do useful independent work between waits, not repeated source rereads. Collect sibling run folders with:

```bash
python3 <skill>/scripts/collect.py /absolute/task-runs --state /absolute/collection-state.json
```

The collector emits compact statuses and at most two new terminal handoffs per call (configurable with `--max-new-results`); keep collecting completed batches until `new_results` is empty. Each changed terminal handoff is delivered once; it never reads raw output logs. On unchanged runs it emits no repeated results. It flags preview truncation and gives the full file path: read the omitted portion before making a dependent decision. Keep state and run artifacts outside source. Do not `cat run*/receipt.json` (native usage can be large), concatenate every past result, or replay the full task history. For retrospective task inspection, request compact metadata first and filter/store large tool responses before exposing only relevant excerpts.

Runner `candidate` means transport/preservation checks passed, never task acceptance. `work_status` separately records the model's `complete|partial|blocked|needs_context` report; missing status is `unreported` and needs inspection. Do not spend another model call merely to reformat a missing marker: inspect the delivered work and record your classification in the task ledger without rewriting the original receipt. `incomplete` exits 4 and retains partial edits plus its handoff; step-limit detection overrides a completion claim. A genuine provider error or unfinished stream stays a failure even if partial text exists; the retained last text and delivery status help recovery without accepting it. Do not automatically retry a delivered adverse review. A review can be **complete** while rejecting the code: put findings/verdict in its body, not a delivery-blocked status. Give partial work a smaller continuation brief, current snapshot, and exact remaining items. Never integrate it merely because the CLI exited zero. No unspecified last-session resumes.

## Acceptance and learning

A worker success is a candidate. Inspect changed paths and the actual diff, then run required behavior tests and repository gates yourself. Give Grok the actual change and acceptance criteria, without telling it the implementation is correct. Require actionable defects with file/line, concrete consequence and evidence; no stylistic churn. Resolve significant findings, then repeat only affected checks and review.

Content manifests detect tracked/nonignored changes, index changes, and HEAD drift; they are not an OS sandbox and do not cover ignored/external files. Preserve failure evidence; never auto-revert user work. Import only accepted changes from an isolated worker workspace and recheck the final integrated state.

For each package record route, elapsed time, attempts, partial/blocked outcome, decisive checks, reviewer findings, and substantive coordinator repairs in a short task-local ledger outside source. Track externally delivered/accepted packages and coordinator repair work separately; call count and provider tokens alone are not Codex savings. Adapt routing from observed correctness and repair rates; do not claim a universally best model or a percentage of Codex savings without matched measurement. Worker inference uses other accounts, but coordinator context still consumes Codex.

Finish with outcome, tests, external routes used, and real limitations. Keep installation, source validation, published release, and human acceptance distinct.
