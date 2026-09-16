# Verified routes and operating decisions

Verified locally on 2026-09-16; refresh inventories when invoked. Models and provider terms can change.

- OpenCode 1.18.31: `opencode run --pure --dir <repo> --model opencode-go/muse-spark-1.3-contributor --variant xhigh --format json <brief>`. Live generation returned ROUTE_OK using existing Go credentials. Native metadata lists minimal/low/medium/high/xhigh; max is not advertised. Do not manufacture max through custom settings and claim support.
- Cursor CLI 2026.09.10-fd3934a: `agent --print --workspace <repo> --trust --model cursor-grok-4.6-xhigh --mode ask --output-format json <brief>`. Live generation returned ROUTE_OK under the existing login. Exact model inventory includes xhigh standard and xhigh-fast; choose standard explicitly. The CLI also lists Muse max through Cursor, but that is a different billing route and is not this workflow's default.
- Native result/session IDs and usage are evidence of completed calls. Requested model/effort flags are not independent server attestation of hidden compute or a quality benchmark.

## Subscription and privacy

[OpenCode Go](https://opencode.ai/docs/go/) documents the opencode-go provider, included model quotas and optional Use balance spillover. Existing Go auth is used; this runner does not extract keys, change credentials, enable balance spillover, or use the user's OpenAI route. Muse Contributor is marked training-enabled and not zero data retention. Avoid excluded/private material; use another authorized route for it.

[Cursor Grok 4.6](https://prod.cursor.com/docs/models/grok-4-6) places Grok in the Cursor Models pool. The standard route has lower listed token prices than Fast; more reasoning is not free quota. [Cursor usage limits](https://prod.cursor.com/help/models-and-usage/usage-limits) explain on-demand billing after included usage if enabled. Dashboard spending settings were not inspected or changed during setup. No CLI-only promise of zero overage is made. Disable provider-side overage if a hard subscription-only ceiling is required; do not silently change account settings.

## Why bounded delegation

The default routing is an engineering choice, not a model leaderboard conclusion. Muse implements; Grok reviews independently; deterministic tests decide behavior. Research is only added for unresolved questions. Measure accepted changes, retries, material review findings and elapsed time on real work before changing defaults.

[Anthropic's multi-agent engineering report](https://www.anthropic.com/engineering/multi-agent-research-system) reports substantial token overhead and notes that coding often has fewer independent tasks than research. This supports avoiding an always-on large swarm, but does not establish performance or savings for these models. Keep contracts and summaries small; offload expensive exploration and implementation; do not repeat their whole work in Codex.

## CLI contracts

- [OpenCode configuration](https://opencode.ai/docs/config/): OPENCODE_CONFIG_CONTENT is a runtime override; managed settings can take precedence.
- [OpenCode permissions](https://opencode.ai/docs/permissions/): deny-by-default with narrow read/edit grants. Tool permissions and receipts are not OS isolation.
- [OpenCode models](https://opencode.ai/docs/models/): model variants are provider-specific.
- [Cursor CLI](https://cursor.com/docs/cli/overview): ask mode is read-only.
- [Cursor headless mode](https://cursor.com/docs/cli/headless): unattended edits generally require force; this workflow uses Grok only for read-only work and does not add force.

## Limits and escalation

Stop a failed route on quota, authentication or region errors; do not rotate accounts or evade limits. Use fresh sessions by default to avoid cross-task contamination. A workflow may use many workers over a large task, but concurrency and total calls stay bounded. The runner serializes each workspace and times out process groups; the coordinator enforces the overall call budget and acceptance.
