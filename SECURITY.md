# Security policy

## Reporting a vulnerability

Report security issues privately through GitHub:

<https://github.com/Niko96-dotcom/subscription-squad/security/advisories/new>

Do not open a public issue for a suspected vulnerability, and do not include
secrets, tokens, credentials, private logs, or customer data in any report.
A minimal reproduction with redacted paths is enough to start.

## Scope and trust boundaries

- **Coordinator vs. workers.** Codex coordinates and verifies; provider CLIs
  do the delegated work. A worker `candidate` receipt means transport and
  preservation checks passed, never task acceptance.
- **Workspace vs. run directories.** The Git checkout being edited and each
  `--run-dir` must be separate directories; the runner refuses nested or
  reused run dirs. Collector state must live outside every run directory.
- **Provider CLIs.** `scripts/worker.py` shells out to your installed
  `opencode` and Cursor (`agent`/`cursor-agent`) binaries under your existing
  logins. Binary overrides exist only as
  `SUBSCRIPTION_SQUAD_OPENCODE_BIN` / `SUBSCRIPTION_SQUAD_CURSOR_BIN`.
  The runner does not inspect credentials; the installed CLIs use on-disk login
  plus the inherited environment subject to filtering below.
- **One worker per workspace.** A filesystem lock serializes workers on the
  same checkout; parallel work needs separate workspaces (for example,
  isolated worktrees).

## Least permissions

- The generated OpenCode config is deny-by-default: `read`/`glob`/`grep`/
  `list` are allowed workspace-wide while `bash`, `task`, and `external_directory` are
  denied. Edit ownership does not limit reads. Ask mode denies all edits and allows
  `webfetch`; work mode allows only the literal `--allow-path` entries (each plus
  its children) and denies `webfetch`.
- Preflight (`--check`) and worker runs share filtered provider environments:
  inherited OpenCode config/permission overrides, Cursor API key/endpoint, and common
  provider credentials plus `*_TOKEN`/`*_SECRET`/`*_API_KEY` patterns are removed;
  `HOME`/`PATH`/`XDG` and on-disk logins are preserved. Muse inventory uses the same
  generated provider enablement (`enabled_providers: [opencode-go]`) with ask/no-edit
  permissions. Filtering is not comprehensive scrubbing and not a sandbox.
- `--allow-path` takes only literal workspace-relative files or directories:
  no globs, no absolute paths, no `..`, no `.git` internals.
- `--trust` applies only to the Grok (Cursor) route and only for a workspace
  that is already authorized/trusted or a fixture you created. Never add
  force/yolo flags to bypass a denied action. Grok runs ask-only and cannot
  take `--allow-path`.
- Out-of-scope content edits, any index change, or a `HEAD` move marks the
  run `scope_violation` (exit 3). The coordinator re-verifies with its own
  checks; it does not trust worker output alone.

## Sensitive logs

Run directories are created fresh mode `0700` and contain `output.log` (full native CLI transcript),
`result.txt`, and `receipt.json` (session/native IDs, usage metadata,
content hashes). Treat them as sensitive: keep them outside the repository,
do not paste them into issues or pull requests, and do not concatenate full
histories into prompts. The collector (`scripts/collect.py`) deliberately
never reads `output.log`.

## Limitations, not guarantees

- Permission records and content receipts are evidence, not OS-level
  isolation. Manifests cover tracked and non-ignored files plus the Git
  index and `HEAD`; ignored and external files are not covered. Environment
  filtering removes common credential variables but unusual names and local
  CLI config remain trusted.
- Muse shell use and nested delegation are disabled in the generated
  config; verification commands are run by the coordinator itself.
- Muse Contributor is marked training-enabled without zero data
  retention; do not send secrets, private personal records, or excluded
  code as input down that route. Provider-side overage settings can still bill;
  the runner never changes billing or credentials.

## Tests and CI

Unit tests (`scripts/test_*.py`) use local stub CLIs and temporary
directories only. They make no network or provider calls. CI checks out
source with pinned `actions/checkout v4.2.2` (`persist-credentials: false`),
provisions Python 3.10 and 3.12 with pinned `actions/setup-python v5.6.0`
on `ubuntu-latest` and `macos-latest`, then runs `make ci`
(`compileall` plus unittest discovery). It uses minimal `contents: read`
permissions, `timeout-minutes: 10`, no secrets, no live providers, and
publishes nothing.
