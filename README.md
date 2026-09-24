# Subscription Squad

![Subscription Squad banner: dark slate panel reading Subscription Squad, Codex coordinates, Muse implements, Grok reviews.](assets/banner.svg)

[![CI](https://github.com/Niko96-dotcom/subscription-squad/actions/workflows/ci.yml/badge.svg)](https://github.com/Niko96-dotcom/subscription-squad/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](Makefile)

Keep Astra as the lean coordinator, architect, and final decision maker. Delegate bounded implementation to
Muse Spark 1.3 Contributor via OpenCode Go — and independent review to Grok 4.7 xhigh
via Cursor (legacy) — with Gemini 3.8 Flash via Antigravity for structured extraction
or a selected alternate implementation slice, and native Grok Build ask as an alternate
read-only route — using logins and subscriptions
you already have. No new accounts, no billing changes, no permission expansion.

```bash
git clone https://github.com/Niko96-dotcom/subscription-squad.git
cd subscription-squad
```

This repo is the runnable skill plus two standard-library CLIs.
[SKILL.md](SKILL.md) is authoritative for routing, budgets, and briefs;
`scripts/worker.py --help` and `scripts/collect.py --help` are
authoritative for flags. This README is only the landing page.

## Requirements

macOS or Linux, Python 3.10+, and Git. Live workers also need the OpenCode
CLI logged in to OpenCode Go, the Cursor CLI logged in with access to
the exact models above, the Grok Build CLI (`grok`) logged in with access
to `grok-4.7`, and the Antigravity CLI (`agy`) logged in with access to
`gemini-3.8-flash-high`. Headless Antigravity runs also require
`enableTerminalSandbox: true` and `toolPermission: "proceed-in-sandbox"` in
`~/.gemini/antigravity-cli/settings.json`. The runner validates these values,
binds the cwd as a project, and forces `--sandbox`. Tests need neither provider nor login. Run all
`--check` commands below: model availability and subscription quotas can change.

## Install the skill

Keep one active Codex copy at `~/.codex/skills/subscription-squad`.
The repository checkout is source, `~/.codex/skill-backups` contains retained
copies, and `~/.claude/skills` is a separate Claude installation. These are
not additional active Codex installs. Do not put renamed copies with the same
skill name under `~/.codex/skills`.

Copy the skill files into your Codex skills directory. The snippet refuses
an existing destination — including a dangling symlink — and the final
`mkdir` without `-p` fails on races. Remove or back up the destination
yourself to upgrade:

```bash
SRC="/path/to/subscription-squad"
DEST="$HOME/.codex/skills/subscription-squad"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  echo "refusing: $DEST already exists" >&2
  exit 1
fi
mkdir -p "$(dirname "$DEST")" &&
mkdir "$DEST" &&
cp "$SRC/SKILL.md" "$DEST/SKILL.md" &&
cp -R "$SRC/scripts" "$SRC/references" "$SRC/agents" "$DEST/"
```

Invoke in Codex with the skill name, for example:

```text
$subscription-squad implement <owned paths> per SKILL.md with a frozen brief
```

For other agent CLIs, install [the portable entrypoint](adapters/portable/SKILL.md)
as `SKILL.md` in that CLI's personal `skills/subscription-squad` directory,
alongside exact copies of this repository's `scripts/` and `references/`.
The portable entrypoint is explicit-use and prevents a worker launched by the
runner from dispatching another worker. Claude Code may instead retain its
own coordinator and relay adapter while syncing the shared scripts and
references; do not overwrite a host-specific entrypoint with Codex wording.

See [SKILL.md](SKILL.md) for when to invoke, budgets, preflight,
and brief/collect rules.

## Quickstart

All prompts live outside the target checkout. Every `--run-dir` is fresh
(must not exist yet) and outside the checkout.

**1. Check all routes** (inventory behind your existing logins):

```bash
python3 scripts/worker.py --provider muse --check
python3 scripts/worker.py --provider space-bunny --check
python3 scripts/worker.py --provider grok --check
python3 scripts/worker.py --provider grok-build --check
python3 scripts/worker.py --provider antigravity --check
```

**2. Implement with Muse** (owned paths only):

```bash
python3 scripts/worker.py --provider muse --mode work \
  --workspace /ABSOLUTE/checkout --allow-path src/owned_file.py \
  --prompt-file /ABSOLUTE/prompts/brief.txt --run-dir /ABSOLUTE/task-runs/work-1 --timeout 900
```

Selected alternate implementation (only for a concrete fit; every candidate still needs tests and review):

```bash
python3 scripts/worker.py --provider antigravity --mode work \
  --workspace /ABSOLUTE/checkout --allow-path src/owned_file.py \
  --prompt-file /ABSOLUTE/prompts/brief.txt --run-dir /ABSOLUTE/task-runs/work-agy-1 --timeout 900
```

Native Grok Build work remains supported by the runner but is off the default path after repeated cancelled trials without edits; retry only as a bounded useful retest with acceptance evidence — see [SKILL.md](SKILL.md).

Space Bunny Free is a provisional OpenCode Go alternate for bounded work. It uses the advertised `max` reasoning variant and the same ownership and preservation checks as Muse. Its free availability and provider terms are time-limited; see the [matched evaluation](references/space-bunny-evaluation.md) before changing the default route.

**3. Review with Grok** (legacy Cursor, read-only; no `--allow-path`):

```bash
python3 scripts/worker.py --provider grok --mode ask \
  --workspace /ABSOLUTE/checkout --trust \
  --prompt-file /ABSOLUTE/prompts/review.txt --run-dir /ABSOLUTE/task-runs/review-1 --timeout 1200
```

Alternate review (read-only ask uses `plan`; no `--trust`). Native
`grok-build` ask stays in the runner but is off the default path after
repeated timeouts; see [routes](references/routes.md).

```bash
python3 scripts/worker.py --provider antigravity --mode ask \
  --workspace /ABSOLUTE/checkout \
  --prompt-file /ABSOLUTE/prompts/review.txt --run-dir /ABSOLUTE/task-runs/review-agy-1 --timeout 600
```

Pass `--trust` only for an already authorized/trusted workspace or a
fixture you created. See [examples/](examples/) for brief shapes.

**4. Collect** (state file outside every run dir; repeat until
`new_results` is empty; `--wait` blocks until a result is ready instead of polling):

```bash
python3 scripts/collect.py /ABSOLUTE/task-runs --state /ABSOLUTE/collection-state.json --wait 600
```

**5. Accept (Astra, not a worker).** `candidate` means transport and
preservation checks passed — not acceptance. Inspect the diff, run focused
checks and the repo gate yourself, and integrate only what passes.

Full flag details: `python3 scripts/worker.py --help`,
`python3 scripts/collect.py --help`.

## Boundaries

- **Owned paths limit edits, not reads.** `--allow-path` names literal workspace-relative
  files/dirs (no globs, no `..`, no `.git`). Work requires at least one;
  ask forbids all edits. `read`/`glob`/`grep`/`list` stay workspace-wide and
  ask-mode Muse allows `webfetch`; only `edit` is bounded. Exclude secrets and
  private data from the checkout before delegating. See [SKILL.md](SKILL.md).
- **Small packages, bounded calls.** Default: 1 implementation + 1
  cross-model review, max 2 concurrent workers in separate workspaces,
  6 calls per task including failures, max 2 implementation attempts per package,
  900 s per call (1200 s for Cursor Grok reviews), 60 model steps (OpenCode routes only). Reserve 2 calls for review/repair;
  state a larger finite budget before dispatch for larger tasks within the authorized scope.
  Grok Build uses fixed `xhigh` reasoning; Antigravity uses fixed `high` effort with
  `gemini-3.8-flash-high` (never `xhigh`). Details in [SKILL.md](SKILL.md).
- **Privacy is about inputs.** Muse Contributor is marked
  training-enabled without zero data retention: do not send secrets,
  private personal records, or excluded code as input down that route.
  Preflight (`--check`) and worker runs share filtered provider environments:
  inherited OpenCode config/permission overrides, Cursor API key/endpoint, and
  common provider credentials (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
  `GOOGLE_API_KEY`, `XAI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `OPENCODE_API_KEY`,
  `OPENCODE_GO_API_KEY`, `GH_TOKEN`, `GITHUB_TOKEN`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, plus `*_TOKEN`/`*_SECRET`/`*_API_KEY`
  patterns) are removed; `HOME`/`PATH`/`XDG` and on-disk logins are preserved.
  Muse runs set a generated config (`share: disabled`, `enabled_providers: [opencode-go]`;
  ask/no-edit permissions for inventory). Filtering is not a sandbox: unusual
  credential names and local CLI config remain trusted, and the installed CLIs use
  your login plus the remaining environment. Use another authorized route
  for sensitive material.
- **Receipts are evidence, not a sandbox.** Manifests cover tracked and
  non-ignored files plus the index and `HEAD`; ignored and external files
   are not covered. Tool permissions and manifests do not isolate processes like an OS
   sandbox. Fresh `--run-dir` directories are created mode `0700`, but treat transcripts
   as sensitive anyway. Astra checks decide acceptance. Receipts record
  provider, requested model, and actual effort/variant truthfully (`high`, not
  `xhigh`, for Antigravity); reported `modelUsage`/session metadata is preserved
  without claiming it is independent attestation of hidden reasoning.
- **Antigravity fails closed.** Before invoking `agy`, the runner requires the
  sandbox settings above, reuses a project bound to the cwd (or creates it once),
  and passes `--sandbox` on every ask and work call. Project binding makes the cwd the recognized workspace, whose file
  tools are allowed by Antigravity's workspace policy. Outside-workspace access
  can still require review and fail in headless mode; the runner never adds
  dangerous-skip or always-proceed modes.
- **Billing unchanged.** Existing auth only; the runner never enables
  overage or changes credentials, but provider-side overage settings can
  still bill. Native Grok Build and Antigravity routes are
  subscription/account-backed, with no CLI-only promise of zero overage.
  See [references/routes.md](references/routes.md).

## Tests and CI

```bash
make ci
```

`make ci` prints the Python version, byte-compiles `scripts/`, and runs
unittest discovery over `scripts/test_*.py`. Tests use local stub CLIs
and temp dirs — no network, no providers, no secrets.

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) checks out source
with pinned `actions/checkout v7.0.1`, provisions Python 3.10 and 3.12 with
pinned `actions/setup-python v7.0.0` on `ubuntu-latest` and `macos-latest`,
then runs `make ci` with minimal `contents: read`, `persist-credentials: false`,
and `timeout-minutes: 10`. No live providers, no secrets, nothing published.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately via
GitHub security advisories — never as public issues, never with secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for test commands and ground rules.

## License

MIT — see [LICENSE](LICENSE). Copyright 2026 Niko.
