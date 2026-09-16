# Contributing

Short version: keep changes scoped, run the gate, never paste secrets.

## Prerequisites

- POSIX macOS or Linux, Git, Python 3.10+ (standard library only, no installs).
- Existing OpenCode and Cursor logins if you exercise live provider runs.
  Unit tests never call providers; they use local stubs only.

## Test commands

```bash
make ci
```

That prints the Python version, byte-compiles `scripts/`, and discovers
`scripts/test_*.py`:

```bash
python3 -m unittest discover -s scripts -t scripts -p "test_*.py" -v
```

Run one file while iterating (from the repo root; each line stands alone):

```bash
python3 -m unittest discover -s scripts -t scripts -p "test_worker.py" -v
python3 -m unittest discover -s scripts -t scripts -p "test_collect.py" -v
```

## Ground rules

- Match the actual CLI contracts in `scripts/worker.py` and
  `scripts/collect.py`. If you change a flag or exit code, update the
  examples in `README.md` and `examples/` in the same change.
- Keep run artifacts (`run-dir` contents, collector state) outside the
  repository. They are ignored by `.gitignore` for a reason.
- Do not include secrets, tokens, private logs, or customer data in
  issues, pull requests, or fixtures.
- See [SECURITY.md](SECURITY.md) before reporting anything
  security-sensitive, and [SKILL.md](SKILL.md) for the delegation workflow
  this packaging supports.
