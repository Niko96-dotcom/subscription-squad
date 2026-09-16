#!/usr/bin/env python3
"""Bounded collector for sibling run directories.

Scans direct children of RUN_ROOT containing receipt.json (sorted),
reads receipts (never output.log), reports terminal results once.
"""
import argparse
import fcntl
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

RUN_LIMIT = 100
PROTECTED_NAMES = ("receipt.json", "result.txt", "output.log")


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Collect sibling run directories without ingesting transcripts."
    )
    ap.add_argument("run_root", help="directory containing sibling run dirs")
    ap.add_argument("--state", required=True, help="state file outside every run dir")
    ap.add_argument(
        "--max-result-chars",
        dest="max_result_chars",
        type=int,
        default=4000,
        help="preview limit, 200..20000",
    )
    ap.add_argument("--max-new-results", type=int, default=2, help="deliver at most 1..10 new handoffs per call (default 2)")
    args = ap.parse_args(argv)
    if not 1 <= args.max_new_results <= 10:
        ap.error("--max-new-results must be in range 1..10")
    if not 200 <= args.max_result_chars <= 20000:
        ap.error("--max-result-chars must be in range 200..20000")
    return args


def _within(child, parent):
    try:
        try:
            return child.is_relative_to(parent)
        except AttributeError:
            child.relative_to(parent)
            return True
    except ValueError:
        return False
    except Exception:
        return False


def _dump(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _run_entry(name, receipt):
    return {
        "name": name,
        "provider": receipt.get("provider"),
        "status": receipt.get("status"),
        "elapsed_seconds": receipt.get("elapsed_seconds"),
        "changed_count": len(receipt.get("changed_paths", [])) if isinstance(receipt.get("changed_paths", []), list) else None,
        "work_status": receipt.get("work_status"),
        "step_count": receipt.get("step_count"),
    }


def _snapshot_runs(children):
    runs = []
    errors = []
    for child in children:
        name = child.name
        rp = child / "receipt.json"
        try:
            raw = rp.read_bytes()
        except Exception as exc:
            errors.append({"name": name, "error": "cannot read receipt: %s" % exc})
            continue
        try:
            rec = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            errors.append({"name": name, "error": "malformed receipt: %s" % exc})
            continue
        if not isinstance(rec, dict):
            errors.append({"name": name, "error": "malformed receipt: not an object"})
            continue
        runs.append(_run_entry(name, rec))
    return runs, errors


def _load_state(state_path):
    if not state_path.exists():
        return {}, None
    if not state_path.is_file():
        return None, "malformed state file: not a regular file"
    try:
        text = state_path.read_text(encoding="utf-8")
    except Exception as exc:
        return None, "malformed state file: cannot read: %s" % exc
    try:
        data = json.loads(text)
    except Exception as exc:
        return None, "malformed state file: bad json: %s" % exc
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("delivered"), dict)
    ):
        return None, "malformed state file: expected {version:1, delivered:dict}"
    return data["delivered"], None


def _atomic_write(state_path, data):
    parent = state_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    d = str(parent) if str(parent) else "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), sort_keys=True)
            f.write("\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, state_path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    args = parse_args(argv)
    run_root = Path(args.run_root)
    state_path = Path(args.state)
    max_chars = args.max_result_chars

    if not run_root.is_dir():
        print(_dump({"runs": [], "new_results": [], "errors": [{"error": "run root not a directory"}]}))
        return 1
    try:
        children = [
            p for p in run_root.iterdir() if p.is_dir() and (p / "receipt.json").is_file()
        ]
    except Exception as exc:
        print(_dump({"runs": [], "new_results": [], "errors": [{"error": "cannot scan run root: %s" % exc}]}))
        return 1
    children.sort(key=lambda p: p.name)

    if len(children) > RUN_LIMIT:
        print(
            _dump(
                {
                    "runs": [],
                    "new_results": [],
                    "errors": [{"error": "too many runs: %d exceeds %d" % (len(children), RUN_LIMIT)}],
                }
            )
        )
        return 1

    try:
        state_resolved = state_path.resolve()
    except Exception:
        state_resolved = state_path.absolute()

    if state_resolved.name in PROTECTED_NAMES:
        runs, perr = _snapshot_runs(children)
        perr.append({"error": "state file must not overwrite %s" % state_resolved.name})
        print(_dump({"runs": runs, "new_results": [], "errors": perr}))
        return 1

    for c in children:
        try:
            cres = c.resolve()
        except Exception:
            cres = c.absolute()
        if _within(state_resolved, cres):
            runs, perr = _snapshot_runs(children)
            perr.append({"error": "state file must live outside every run directory"})
            print(_dump({"runs": runs, "new_results": [], "errors": perr}))
            return 1

    state_path = state_resolved
    lock_path = Path(str(state_path) + ".lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(_dump({"runs": [], "new_results": [], "errors": [{"error": "cannot create state dir: %s" % exc}]}))
        return 1
    try:
        lock_f = open(lock_path, "a+")
    except Exception as exc:
        print(_dump({"runs": [], "new_results": [], "errors": [{"error": "cannot open lockfile: %s" % exc}]}))
        return 1

    try:
        try:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(_dump({"runs": [], "new_results": [], "errors": [{"error": "collection state is locked; retry after the active collector exits"}]}))
            return 1
        try:
            delivered, state_err = _load_state(state_path)
            if state_err is not None:
                runs, perr = _snapshot_runs(children)
                perr.append({"error": state_err})
                print(_dump({"runs": runs, "new_results": [], "errors": perr}))
                return 1

            runs = []
            new_results = []
            errors = []
            pending = {}

            for child in children:
                name = child.name
                receipt_path = child / "receipt.json"
                try:
                    receipt_bytes = receipt_path.read_bytes()
                except Exception as exc:
                    errors.append({"name": name, "error": "cannot read receipt: %s" % exc})
                    continue
                receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
                try:
                    receipt = json.loads(receipt_bytes.decode("utf-8"))
                except Exception as exc:
                    errors.append({"name": name, "error": "malformed receipt: %s" % exc})
                    continue
                if not isinstance(receipt, dict):
                    errors.append({"name": name, "error": "malformed receipt: not an object"})
                    continue
                if receipt.get("status") not in {"running", "candidate", "incomplete", "worker_failed", "error", "timeout", "interrupted", "scope_violation", "unverified_preservation"} or not isinstance(receipt.get("changed_paths", []), list):
                    errors.append({"name": name, "error": "malformed receipt: invalid status or changed_paths"})
                    continue
                runs.append(_run_entry(name, receipt))
                status = receipt.get("status")
                work_status = receipt.get("work_status")
                provider = receipt.get("provider")
                if status == "running":
                    continue
                result_path = child / "result.txt"
                if not result_path.is_file():
                    errors.append({"name": name, "error": "missing result.txt for terminal receipt"})
                    continue
                try:
                    raw = result_path.read_bytes()
                except Exception as exc:
                    errors.append({"name": name, "error": "cannot read result.txt: %s" % exc})
                    continue
                h_raw = hashlib.sha256(raw).hexdigest()
                h_stripped = None
                if raw.endswith(b"\n"):
                    h_stripped = hashlib.sha256(raw[:-1]).hexdigest()
                declared = receipt.get("result_sha256")
                if not isinstance(declared, str):
                    errors.append({"name": name, "error": "missing result_sha256 in receipt"})
                    continue
                decl = declared.strip()
                matched = None
                if decl.lower() == h_raw.lower():
                    matched = h_raw
                elif h_stripped is not None and decl.lower() == h_stripped.lower():
                    matched = h_stripped
                else:
                    errors.append({"name": name, "error": "result_sha256 mismatch"})
                    continue
                try:
                    receipt_resolved = str(receipt_path.resolve())
                except Exception:
                    receipt_resolved = str(receipt_path.absolute())
                key = "%s|%s|%s" % (receipt_resolved, receipt_sha, matched)
                if key in delivered or len(new_results) >= args.max_new_results:
                    continue
                try:
                    full_text = raw.decode("utf-8", errors="replace")
                except Exception:
                    full_text = ""
                full_chars = len(full_text)
                if full_chars > max_chars:
                    preview = full_text[:max_chars]
                    truncated = True
                else:
                    preview = full_text
                    truncated = False
                try:
                    abs_result = str(result_path.resolve())
                except Exception:
                    abs_result = str(result_path.absolute())
                if not os.path.isabs(abs_result):
                    abs_result = str(Path.cwd() / abs_result)
                new_results.append(
                    {
                        "name": name,
                        "provider": provider,
                        "status": status,
                        "work_status": work_status,
                        "error": str(receipt.get("error", ""))[:500],
                        "scope_violation": bool(receipt.get("scope_violation")),
                        "preview": preview,
                        "truncated": truncated,
                        "full_chars": full_chars,
                        "result_path": abs_result,
                        "result_sha256": matched,
                    }
                )
                pending[key] = True

            if pending or not state_path.exists():
                merged = dict(delivered)
                merged.update(pending)
                try:
                    _atomic_write(state_path, {"version": 1, "delivered": merged})
                except Exception as exc:
                    errors.append({"error": "cannot write state: %s" % exc})
                    print(_dump({"runs": runs, "new_results": [], "errors": errors}))
                    return 1

            print(_dump({"runs": runs, "new_results": new_results, "errors": errors}))
            return 1 if errors else 0
        finally:
            try:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
    finally:
        try:
            lock_f.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
