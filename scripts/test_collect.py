#!/usr/bin/env python3
"""Tests for collect.py using tempfile and subprocess only."""
import hashlib
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

COLLECT = Path(__file__).with_name("collect.py")


def run_collect(run_root, state_file, max_chars=None, wait=None, poll=None, max_new_results=None):
    cmd = [sys.executable, str(COLLECT), str(run_root), "--state", str(state_file)]
    if max_chars is not None:
        cmd += ["--max-result-chars", str(max_chars)]
    if wait is not None:
        cmd += ["--wait", str(wait)]
    if poll is not None:
        cmd += ["--poll", str(poll)]
    if max_new_results is not None:
        cmd += ["--max-new-results", str(max_new_results)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    data = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            data = json.loads(out)
        except Exception:
            data = None
    return proc, data


def write_run(
    root,
    name,
    provider="muse",
    status="candidate",
    result_text="hello",
    work_status="complete",
    elapsed=1.5,
    changed=1,
    steps=2,
    result_sha_override="__auto__",
    write_result=True,
    add_newline=True,
    output_marker="LOGDATA",
    receipt_extra=None,
):
    d = Path(root) / name
    d.mkdir(parents=True, exist_ok=True)
    raw_for_hash = None
    if result_text is not None:
        raw_for_hash = result_text.encode("utf-8")
        correct = hashlib.sha256(raw_for_hash).hexdigest()
    else:
        correct = None
    if result_sha_override == "__auto__":
        h_used = correct
    else:
        h_used = result_sha_override
    if write_result and raw_for_hash is not None:
        blob = raw_for_hash + b"\n" if add_newline else raw_for_hash
        (d / "result.txt").write_bytes(blob)
    receipt = {
        "provider": provider,
        "status": status,
        "elapsed_seconds": elapsed,
        "changed_paths": [f"file{i}.py" for i in range(changed)],
        "work_status": work_status,
        "step_count": steps,
    }
    if h_used is not None:
        receipt["result_sha256"] = h_used
    if receipt_extra:
        receipt.update(receipt_extra)
    (d / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    if output_marker is not None:
        if output_marker == "__DIR__":
            p = d / "output.log"
            if p.is_file() or p.is_symlink():
                p.unlink()
            p.mkdir(exist_ok=True)
        else:
            (d / "output.log").write_text(output_marker, encoding="utf-8")
    return d


class CollectTests(unittest.TestCase):
    def test_bounded_delivery_and_real_changed_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            for n in ['a','b','c']:write_run(root,n,changed=3)
            proc,first=run_collect(root,state)
            self.assertEqual(proc.returncode,0,proc.stdout)
            self.assertEqual(len(first['new_results']),2)
            self.assertEqual(first['runs'][0]['changed_count'],3)
            proc,second=run_collect(root,state)
            self.assertEqual([r['name'] for r in second['new_results']],['c'])
            self.assertEqual(run_collect(root,state)[1]['new_results'],[])

    def test_symlink_state_uses_same_nonblocking_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'a');state.write_text('{"version":1,"delivered":{}}')
            alias=Path(td)/'alias.json';alias.symlink_to(state)
            with open(str(state)+'.lock','w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                proc,data=run_collect(root,alias)
                self.assertNotEqual(proc.returncode,0)
                self.assertIn('locked',data['errors'][0]['error'])
                self.assertEqual(json.loads(state.read_text())['delivered'],{})
            self.assertEqual(len(run_collect(root,alias)[1]['new_results']),1)

    def test_unknown_receipt_status_is_not_delivered(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'a',status='imaginary')
            proc,data=run_collect(root,state)
            self.assertNotEqual(proc.returncode,0)
            self.assertEqual(data['new_results'],[])

    def test_first_then_repeat_no_reprint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "a", result_text="hello world")
            p1, d1 = run_collect(root, state)
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertIsNotNone(d1)
            self.assertEqual(len(d1["runs"]), 1)
            self.assertEqual(len(d1["new_results"]), 1)
            self.assertEqual(len(d1["errors"]), 0)
            self.assertEqual(d1["new_results"][0]["name"], "a")
            self.assertNotIn("accepted", json.dumps(d1).lower())
            self.assertTrue(state.is_file())
            p2, d2 = run_collect(root, state)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(len(d2["runs"]), 1)
            self.assertEqual(len(d2["new_results"]), 0)
            self.assertEqual(len(d2["errors"]), 0)

    def test_running_to_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(
                root,
                "r1",
                status="running",
                result_text=None,
                result_sha_override=None,
                write_result=False,
            )
            p1, d1 = run_collect(root, state)
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertEqual(len(d1["new_results"]), 0)
            self.assertEqual(len(d1["errors"]), 0)
            self.assertEqual(d1["runs"][0]["status"], "running")
            write_run(root, "r1", status="candidate", result_text="now done")
            p2, d2 = run_collect(root, state)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(len(d2["new_results"]), 1)
            self.assertEqual(d2["new_results"][0]["name"], "r1")

    def test_modified_receipt_redelivers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "a", result_text="same content", elapsed=1.0)
            _, d1 = run_collect(root, state)
            self.assertEqual(len(d1["new_results"]), 1)
            _, d2 = run_collect(root, state)
            self.assertEqual(len(d2["new_results"]), 0)
            write_run(root, "a", result_text="same content", elapsed=9.9)
            _, d3 = run_collect(root, state)
            self.assertEqual(len(d3["new_results"]), 1)

    def test_corrupt_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "good", result_text="ok-content")
            bad = root / "bad"
            bad.mkdir()
            (bad / "receipt.json").write_text("{not json", encoding="utf-8")
            (bad / "output.log").write_text("x", encoding="utf-8")
            p1, d1 = run_collect(root, state)
            self.assertNotEqual(p1.returncode, 0)
            self.assertIsNotNone(d1)
            self.assertTrue(len(d1["errors"]) > 0)
            self.assertEqual(len([r for r in d1["new_results"] if r["name"] == "good"]), 1)
            p2, d2 = run_collect(root, state)
            self.assertNotEqual(p2.returncode, 0)
            self.assertEqual(len(d2["new_results"]), 0)
            self.assertTrue(len(d2["errors"]) > 0)

    def test_corrupt_state_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "a", result_text="hi")
            p0, _ = run_collect(root, state)
            self.assertEqual(p0.returncode, 0)
            good = state.read_text(encoding="utf-8")
            self.assertIn("delivered", good)
            state.write_text("not-json{{{", encoding="utf-8")
            p1, d1 = run_collect(root, state)
            self.assertNotEqual(p1.returncode, 0)
            self.assertTrue(len(d1["errors"]) > 0)
            self.assertEqual(state.read_text(encoding="utf-8"), "not-json{{{")
            state.write_text(json.dumps({"version": 2, "delivered": {}}), encoding="utf-8")
            p2, d2 = run_collect(root, state)
            self.assertNotEqual(p2.returncode, 0)
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["version"], 2)

    def test_missing_result_retried(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(
                root,
                "a",
                result_text="intended",
                write_result=False,
            )
            p1, d1 = run_collect(root, state)
            self.assertNotEqual(p1.returncode, 0)
            self.assertEqual(len(d1["new_results"]), 0)
            self.assertTrue(len(d1["errors"]) > 0)
            # fix by writing correct file (worker style with newline)
            (root / "a" / "result.txt").write_bytes(b"intended\n")
            p2, d2 = run_collect(root, state)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(len(d2["new_results"]), 1)

    def test_hash_mismatch_retried(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "a", result_text="real", result_sha_override="0" * 64)
            p1, d1 = run_collect(root, state)
            self.assertNotEqual(p1.returncode, 0)
            self.assertEqual(len(d1["new_results"]), 0)
            correct = hashlib.sha256(b"real").hexdigest()
            rec_path = root / "a" / "receipt.json"
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            rec["result_sha256"] = correct
            rec_path.write_text(json.dumps(rec), encoding="utf-8")
            p2, d2 = run_collect(root, state)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(len(d2["new_results"]), 1)

    def test_truncation_with_full_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            long_text = "X" * 5000
            write_run(root, "big", result_text=long_text)
            p1, d1 = run_collect(root, state, max_chars=200)
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertEqual(len(d1["new_results"]), 1)
            e = d1["new_results"][0]
            self.assertTrue(e["truncated"])
            self.assertEqual(len(e["preview"]), 200)
            self.assertEqual(e["full_chars"], 5001)
            self.assertTrue(os.path.isabs(e["result_path"]))
            self.assertTrue(Path(e["result_path"]).is_file())
            self.assertIn("status", e)
            self.assertIn("work_status", e)

    def test_two_terminal_results(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "b", result_text="second")
            write_run(root, "a", result_text="first")
            p1, d1 = run_collect(root, state)
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertEqual(len(d1["runs"]), 2)
            self.assertEqual([r["name"] for r in d1["runs"]], ["a", "b"])
            self.assertEqual(len(d1["new_results"]), 2)
            for r in d1["runs"]:
                for k in ("name", "provider", "status", "elapsed_seconds", "changed_count", "work_status", "step_count"):
                    self.assertIn(k, r)

    def test_no_reading_output_log(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            marker = "UNIQUE_MARKER_SHOULD_NOT_LEAK_9f8b7a"
            write_run(root, "a", result_text="hello", output_marker="log start %s log end" % marker)
            p1, d1 = run_collect(root, state)
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertNotIn(marker, p1.stdout)
            self.assertNotIn(marker, json.dumps(d1))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            state = Path(td) / "state.json"
            write_run(root, "b", result_text="world", output_marker="__DIR__")
            p2, d2 = run_collect(root, state)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(len(d2["new_results"]), 1)

    def test_state_inside_run_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "runs"
            root.mkdir()
            d = write_run(root, "a", result_text="hi")
            receipt_before = (d / "receipt.json").read_bytes()
            result_before = (d / "result.txt").read_bytes()
            bad_state = d / "state.json"
            p1, data = run_collect(root, bad_state)
            self.assertNotEqual(p1.returncode, 0)
            self.assertIsNotNone(data)
            self.assertTrue(len(data["errors"]) > 0)
            self.assertEqual((d / "receipt.json").read_bytes(), receipt_before)
            self.assertEqual((d / "result.txt").read_bytes(), result_before)
            self.assertFalse(bad_state.is_file())

    def test_wait_returns_promptly_with_terminal_undelivered(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'a',result_text='ready')
            t0=time.monotonic()
            proc,data=run_collect(root,state,wait=5,poll=0.05)
            el=time.monotonic()-t0
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(len(data['new_results']),1)
            self.assertIn('waited_seconds',data)
            self.assertIn('wait_timed_out',data)
            self.assertIs(data['wait_timed_out'],False)
            self.assertIsInstance(data['waited_seconds'],float)
            self.assertEqual(data['waited_seconds'],round(data['waited_seconds'],3))
            self.assertLess(el,2.0)
            self.assertLess(data['waited_seconds'],2.0)

    def test_wait_timeout_with_only_running(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'r1',status='running',result_text=None,result_sha_override=None,write_result=False)
            t0=time.monotonic()
            proc,data=run_collect(root,state,wait=0.3,poll=0.05)
            el=time.monotonic()-t0
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(data['new_results'],[])
            self.assertIs(data['wait_timed_out'],True)
            self.assertIsInstance(data['waited_seconds'],float)
            self.assertGreaterEqual(el,0.2)
            self.assertLess(el,2.0)
            self.assertGreaterEqual(data['waited_seconds'],0.2)

    def test_wait_poll_larger_than_wait_does_not_oversleep(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'r1',status='running',result_text=None,result_sha_override=None,write_result=False)
            t0=time.monotonic()
            proc,data=run_collect(root,state,wait=0.3,poll=60)
            el=time.monotonic()-t0
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(data['new_results'],[])
            self.assertIs(data['wait_timed_out'],True)
            self.assertIsInstance(data['waited_seconds'],float)
            self.assertLess(el,5.0)
            self.assertLessEqual(data['waited_seconds'],0.3+1.0)

    def test_wait_delivers_run_becoming_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'r1',status='running',result_text=None,result_sha_override=None,write_result=False)
            def flip():
                time.sleep(0.15)
                write_run(root,'r1',status='candidate',result_text='now done')
            th=threading.Thread(target=flip)
            th.start()
            try:
                t0=time.monotonic()
                proc,data=run_collect(root,state,wait=2,poll=0.05)
                el=time.monotonic()-t0
            finally:
                th.join(timeout=5)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(len(data['new_results']),1)
            self.assertEqual(data['new_results'][0]['name'],'r1')
            self.assertIs(data['wait_timed_out'],False)
            self.assertIsInstance(data['waited_seconds'],float)
            self.assertLess(el,1.5)

    def test_wait_all_delivered_returns_immediately(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'a',result_text='hi')
            _,d1=run_collect(root,state)
            self.assertEqual(len(d1['new_results']),1)
            t0=time.monotonic()
            proc,data=run_collect(root,state,wait=2,poll=0.05)
            el=time.monotonic()-t0
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(data['new_results'],[])
            self.assertIs(data['wait_timed_out'],False)
            self.assertIn('waited_seconds',data)
            self.assertLess(el,1.5)

    def test_no_wait_has_no_wait_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'a',result_text='hi')
            proc,data=run_collect(root,state)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertNotIn('waited_seconds',data)
            self.assertNotIn('wait_timed_out',data)

    def test_invalid_wait_poll_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'runs';root.mkdir();state=Path(td)/'state.json'
            write_run(root,'a',result_text='hi')
            for extra in (['--wait','-1'],['--wait','4000'],['--poll','0']):
                cmd=[sys.executable,str(COLLECT),str(root),'--state',str(state)]+extra
                proc=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
                self.assertNotEqual(proc.returncode,0,extra)


if __name__ == "__main__":
    unittest.main()
