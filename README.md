# Subscription Squad

![Subscription Squad banner: dark slate panel reading Subscription Squad, Codex coordinates, Muse implements, Grok reviews.](assets/banner.svg)

[![CI](https://github.com/Niko96-dotcom/subscription-squad/actions/workflows/ci.yml/badge.svg)](https://github.com/Niko96-dotcom/subscription-squad/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](Makefile)

Keep Codex as a lean coordinator. Delegate bounded implementation to
Muse Spark 1.3 Contributor via OpenCode Go, and independent review to
Grok 4.6 via Cursor — using logins and subscriptions you already have.
No new accounts, no billing changes, no permission expansion.

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
CLI logged in to OpenCode Go and the Cursor CLI logged in with access to
the exact models above. Tests need neither provider nor login. Run both
`--check` commands below: model availability and subscription quotas can change.

## Install the skill for Codex

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

Invoke from Codex with the skill name, for example:

```text
$subscription-squad implement <owned paths> per SKILL.md with a frozen brief
```

See [SKILL.md](SKILL.md) for when to invoke, budgets, preflight,
and brief/collect rules.

## Quickstart

All prompts live outside the target checkout. Every `--run-dir` is fresh
(must not exist yet) and outside the checkout.

**1. Check both routes** (inventory behind your existing logins):

```bash
python3 scripts/worker.py --provider muse --check
python3 scripts/worker.py --provider grok --check
```

**2. Implement with Muse** (owned paths only):

```bash
python3 scripts/worker.py --provider muse --mode work \
  --workspace /ABSOLUTE/checkout --allow-path src/owned_file.py \
  --prompt-file /ABSOLUTE/prompts/brief.txt --run-dir /ABSOLUTE/task-runs/work-1 --timeout 900
```

**3. Review with Grok** (read-only; no `--allow-path`):

```bash
python3 scripts/worker.py --provider grok --mode ask \
  --workspace /ABSOLUTE/checkout --trust \
  --prompt-file /ABSOLUTE/prompts/review.txt --run-dir /ABSOLUTE/task-runs/review-1 --timeout 600
```

Pass `--trust` only for an already authorized/trusted workspace or a
fixture you created. See [examples/](examples/) for brief shapes.

**4. Collect** (state file outside every run dir; repeat until
`new_results` is empty):

```bash
python3 scripts/collect.py /ABSOLUTE/task-runs --state /ABSOLUTE/collection-state.json
```

**5. Accept (you, not a worker).** `candidate` means transport and
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
  6 calls per task, 900 s per call, 60 model steps. Details in
  [SKILL.md](SKILL.md).
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
  as sensitive anyway. Coordinator checks decide acceptance.
- **Billing unchanged.** Existing auth only; the runner never enables
  overage or changes credentials, but provider-side overage settings can
  still bill. See [references/routes.md](references/routes.md).

## Tests and CI

```bash
make ci
```

`make ci` prints the Python version, byte-compiles `scripts/`, and runs
unittest discovery over `scripts/test_*.py`. Tests use local stub CLIs
and temp dirs — no network, no providers, no secrets.

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) checks out source
with pinned `actions/checkout v4.2.2`, provisions Python 3.10 and 3.12 with
pinned `actions/setup-python v5.6.0` on `ubuntu-latest` and `macos-latest`,
then runs `make ci` with minimal `contents: read`, `persist-credentials: false`,
and `timeout-minutes: 10`. No live providers, no secrets, nothing published.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately via
GitHub security advisories — never as public issues, never with secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for test commands and ground rules.

## License

MIT — see [LICENSE](LICENSE). Copyright 2026 Niko.
