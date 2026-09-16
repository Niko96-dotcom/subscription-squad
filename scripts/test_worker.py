#!/usr/bin/env python3
"""Tests for subscription-squad worker.py; no real model calls, stubs only."""
import fcntl
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import worker as W

WORKER = pathlib.Path(__file__).with_name('worker.py')
MUSE = W.MUSE_MODEL
GROK = W.GROK_MODEL


def run_git(*args, cwd):
    r = subprocess.run(['git', *args], cwd=str(cwd), capture_output=True, timeout=30)
    assert r.returncode == 0, f'git {args} failed: {r.stderr.decode()[:500]}'
    return r


def make_workspace():
    tmp = tempfile.mkdtemp(prefix='ws-')
    ws = pathlib.Path(tmp)
    run_git('init', cwd=ws)
    run_git('config', 'user.email', 't@t.t', cwd=ws)
    run_git('config', 'user.name', 't', cwd=ws)
    (ws / 'owned.txt').write_text('owned base\n')
    (ws / 'other.txt').write_text('other base\n')
    run_git('add', 'owned.txt', 'other.txt', cwd=ws)
    run_git('commit', '-m', 'init', cwd=ws)
    return ws


def write_stub(path, content):
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


MUSE_STUB = """#!/usr/bin/env python3
import atexit
import sys, os, json, pathlib, subprocess, time
af = os.environ.get('STUB_ARGV_FILE')
if af:
    pathlib.Path(af).write_text(json.dumps(sys.argv))
ef = os.environ.get('STUB_ENV_FILE')
if ef:
    data = {}
    for k in ('OPENCODE_CONFIG_CONTENT','OPENCODE_CONFIG','OPENCODE_PERMISSION','CURSOR_API_KEY','CURSOR_API_ENDPOINT'):
        if k in os.environ:
            data[k] = os.environ[k]
    pathlib.Path(ef).write_text(json.dumps(data))
def find_arg(flag):
    a = sys.argv
    if flag in a:
        i = a.index(flag)
        if i+1 < len(a):
            return a[i+1]
    return None
if len(sys.argv) >= 2 and sys.argv[1] == 'models':
    mode = os.environ.get('STUB_INVENTORY_MODE', 'ok')
    if mode == 'missing':
        print('muse-spark-1.3-contributor')
        print(json.dumps({'id': 'muse-spark-1.3-contributor', 'providerID': 'opencode-go', 'variants': {'high': {'reasoningEffort': 'high'}}}))
    else:
        print('muse-spark-1.3-contributor')
        print(json.dumps({'id': 'muse-spark-1.3-contributor', 'providerID': 'opencode-go', 'variants': {'xhigh': {'reasoningEffort': 'xhigh'}}}))
    sys.exit(0)
if len(sys.argv) >= 2 and sys.argv[1] == 'run':
    atexit.register(lambda: print(json.dumps({'type': 'step_finish', 'part': {'reason': 'stop', 'tokens': {'input': 10}, 'cost': 0.1}})))
    ws = find_arg('--dir')
    beh = os.environ.get('STUB_BEHAVIOR', 'ok')
    if beh == 'sleep':
        time.sleep(10)
        print(json.dumps({'type': 'text', 'text': 'late'}))
        sys.exit(0)
    elif beh == 'error_event':
        print(json.dumps({'type': 'error', 'error': 'boom'}))
        sys.exit(0)
    elif beh == 'empty':
        sys.exit(0)
    elif beh == 'reasoning_mix':
        print(json.dumps({'type': 'text', 'text': 'keep me'}))
        print(json.dumps({'type': 'reasoning', 'text': 'drop me'}))
        print(json.dumps({'type': 'tool_use', 'text': 'drop me too'}))
        sys.exit(0)
    elif beh == 'edit_owned':
        p = pathlib.Path(ws) / 'owned.txt'
        p.write_text(p.read_text() + '\\nedited')
        print(json.dumps({'type': 'text', 'text': 'edited owned'}))
        sys.exit(0)
    elif beh == 'edit_outside':
        p = pathlib.Path(ws) / 'other.txt'
        p.write_text(p.read_text() + '\\nbad edit')
        print(json.dumps({'type': 'text', 'text': 'bad'}))
        sys.exit(0)
    elif beh == 'stage_owned':
        p = pathlib.Path(ws) / 'owned.txt'
        p.write_text(p.read_text() + '\\nstaged edit')
        subprocess.run(['git', '-C', ws, 'add', 'owned.txt'])
        print(json.dumps({'type': 'text', 'text': 'staged'}))
        sys.exit(0)
    else:
        print(json.dumps({'type': 'text', 'text': 'hello candidate', 'sessionID': 'ses_1', 'model': 'opencode-go/muse-spark-1.3-contributor'}))
        sys.exit(0)
print('unexpected muse stub', file=sys.stderr)
sys.exit(2)
"""

CURSOR_STUB = """#!/usr/bin/env python3
import sys, os, json, pathlib, subprocess, time
af = os.environ.get('STUB_ARGV_FILE')
if af:
    pathlib.Path(af).write_text(json.dumps(sys.argv))
ef = os.environ.get('STUB_ENV_FILE')
if ef:
    data = {}
    for k in ('CURSOR_API_KEY','CURSOR_API_ENDPOINT','OPENCODE_CONFIG_CONTENT'):
        if k in os.environ:
            data[k] = os.environ[k]
    pathlib.Path(ef).write_text(json.dumps(data))
def find_arg(flag):
    a = sys.argv
    if flag in a:
        i = a.index(flag)
        if i+1 < len(a):
            return a[i+1]
    return None
if 'models' in sys.argv:
    mode = os.environ.get('STUB_INVENTORY_MODE', 'ok')
    if mode == 'missing':
        print('other-model  Other')
    else:
        print('cursor-grok-4.6-xhigh  Grok model')
        print('other-model  Other')
    sys.exit(0)
if '--print' in sys.argv:
    ws = find_arg('--workspace')
    beh = os.environ.get('STUB_BEHAVIOR', 'ok')
    if beh == 'sleep':
        time.sleep(10)
        print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'late', 'is_error': False}))
        sys.exit(0)
    elif beh == 'is_error':
        print(json.dumps({'type': 'result', 'subtype': 'success', 'result': '', 'is_error': True, 'error': 'bad'}))
        sys.exit(0)
    elif beh == 'empty_result':
        print(json.dumps({'type': 'result', 'subtype': 'success', 'result': '', 'is_error': False}))
        sys.exit(0)
    elif beh == 'empty':
        sys.exit(0)
    elif beh == 'edit_outside':
        p = pathlib.Path(ws) / 'other.txt'
        p.write_text(p.read_text() + '\\nbad')
        print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'bad edit', 'is_error': False}))
        sys.exit(0)
    else:
        print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'grok ok', 'is_error': False, 'model': 'cursor-grok-4.6-xhigh', 'sessionID': 'ses_g'}))
        sys.exit(0)
print('unexpected cursor stub', file=sys.stderr)
sys.exit(2)
"""


def invoke(args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, env=env, timeout=60)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.test_root = tempfile.TemporaryDirectory(prefix='subscription-squad-tests-')
        self.addCleanup(self.test_root.cleanup)
        original = tempfile.mkdtemp
        self.temp_patch = patch.object(tempfile, 'mkdtemp',
            side_effect=lambda *a, **kw: original(*a, **dict(kw, dir=self.test_root.name)))
        self.temp_patch.start()
        self.addCleanup(self.temp_patch.stop)

    def test_muse_argv_env_routing(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        argv_file = stubdir / 'argv.json'
        env_file = stubdir / 'env.json'
        env = {
            'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub),
            'STUB_ARGV_FILE': str(argv_file),
            'STUB_ENV_FILE': str(env_file),
            'OPENCODE_CONFIG_CONTENT': 'inherited-prompt',
            'OPENCODE_CONFIG': '/tmp/x',
            'OPENCODE_PERMISSION': 'y',
            'STUB_BEHAVIOR': 'ok',
        }
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'ask',
                    '--run-dir', str(run_dir), 'hello routing'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000] + r.stdout.decode()[:2000])
        argv = json.loads(argv_file.read_text())
        self.assertEqual(argv[1], 'run')
        self.assertIn('--pure', argv)
        self.assertIn('--dir', argv)
        self.assertIn(str(ws.resolve()), argv)
        self.assertIn('--model', argv)
        self.assertIn(MUSE, argv)
        self.assertIn('--variant', argv)
        self.assertIn('xhigh', argv)
        self.assertIn('--format', argv)
        self.assertIn('json', argv)
        self.assertIn('--agent', argv)
        self.assertIn('squad-worker', argv)
        # prompt is last arg and contains fixed instructions + user prompt
        self.assertIn('hello routing', argv[-1])
        self.assertIn('Do not delegate', argv[-1])
        self.assertIn('<=500 words', argv[-1])
        envdump = json.loads(env_file.read_text())
        self.assertIn('OPENCODE_CONFIG_CONTENT', envdump)
        cfg = json.loads(envdump['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(cfg['model'], MUSE)
        self.assertEqual(cfg['small_model'], MUSE)
        self.assertEqual(cfg['enabled_providers'], ['opencode-go'])
        self.assertEqual(cfg['share'], 'disabled')
        self.assertIn('squad-worker', cfg['agent'])
        self.assertEqual(cfg['agent']['squad-worker']['model'], MUSE)
        self.assertEqual(cfg['agent']['squad-worker']['steps'], 60)
        perms = cfg['agent']['squad-worker']['permission']
        for k in ('read', 'glob', 'grep', 'list'):
            self.assertEqual(perms[k], 'allow')
        self.assertEqual(perms['bash'], 'deny')
        self.assertEqual(perms['task'], 'deny')
        self.assertEqual(perms['external_directory'], 'deny')
        # ask mode: edit deny, webfetch allow
        self.assertEqual(perms['edit'], 'deny')
        self.assertEqual(perms['webfetch'], 'allow')
        self.assertEqual(cfg['permission'], perms)
        # inherited stripped: file should not contain inherited values
        self.assertNotEqual(envdump['OPENCODE_CONFIG_CONTENT'], 'inherited-prompt')
        self.assertNotIn('OPENCODE_CONFIG', envdump)
        self.assertNotIn('OPENCODE_PERMISSION', envdump)

    def test_muse_work_config_edit_allow(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        argv_file = stubdir / 'argv.json'
        env_file = stubdir / 'env.json'
        env = {'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_ARGV_FILE': str(argv_file),
               'STUB_ENV_FILE': str(env_file), 'STUB_BEHAVIOR': 'ok'}
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'do work'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000])
        cfg = json.loads(json.loads(env_file.read_text())['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(cfg['agent']['squad-worker']['permission']['edit'], {'*':'deny', 'owned.txt':'allow', 'owned.txt/*':'allow'})
        self.assertEqual(cfg['agent']['squad-worker']['permission']['webfetch'], 'deny')
        argv = json.loads(argv_file.read_text())
        self.assertIn('owned.txt', argv[-1])

    def test_grok_argv_env_routing(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        argv_file = stubdir / 'argv.json'
        env_file = stubdir / 'env.json'
        env = {'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_ARGV_FILE': str(argv_file),
               'STUB_ENV_FILE': str(env_file), 'CURSOR_API_KEY': 'secret', 'CURSOR_API_ENDPOINT': 'https://x',
               'STUB_BEHAVIOR': 'ok'}
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--mode', 'ask',
                    '--trust', '--run-dir', str(run_dir), 'hello grok'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000] + r.stdout.decode()[:2000])
        argv = json.loads(argv_file.read_text())
        self.assertIn('--print', argv)
        self.assertEqual(argv[argv.index('--output-format') + 1], 'json')
        self.assertIn('--workspace', argv)
        self.assertIn(str(ws.resolve()), argv)
        self.assertIn('--model', argv)
        self.assertIn(GROK, argv)
        self.assertIn('--mode', argv)
        self.assertIn('ask', argv)
        self.assertIn('--trust', argv)
        self.assertIn('hello grok', argv[-1])
        self.assertIn('Do not delegate', argv[-1])
        envdump = json.loads(env_file.read_text())
        self.assertNotIn('CURSOR_API_KEY', envdump)
        self.assertNotIn('CURSOR_API_ENDPOINT', envdump)

    def test_unsupported_variant(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--variant', 'low', '--check'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
        self.assertNotEqual(r.returncode, 0)

    def test_grok_work_rejected(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'x'],
                   env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub)})
        self.assertNotEqual(r.returncode, 0)

    def test_trust_only_cursor(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--trust',
                    '--run-dir', str(run_dir), 'x'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
        self.assertNotEqual(r.returncode, 0)

    def test_check_muse_ok_and_missing(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--check'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_INVENTORY_MODE': 'ok'})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        self.assertIn('subscription_squad_check=ok', r.stdout.decode())
        self.assertIn(MUSE, r.stdout.decode())
        r2 = invoke(['--workspace', str(ws), '--provider', 'muse', '--check'],
                    env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_INVENTORY_MODE': 'missing'})
        self.assertNotEqual(r2.returncode, 0)

    def test_check_grok_ok_and_missing(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--check'],
                   env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_INVENTORY_MODE': 'ok'})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        self.assertIn('subscription_squad_check=ok', r.stdout.decode())
        self.assertIn(GROK, r.stdout.decode())
        r2 = invoke(['--workspace', str(ws), '--provider', 'grok', '--check'],
                    env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_INVENTORY_MODE': 'missing'})
        self.assertNotEqual(r2.returncode, 0)

    def test_muse_error_event_exit0_fails(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'error_event'})
        self.assertNotEqual(r.returncode, 0)
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'worker_failed')

    def test_grok_error_exit0_fails(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_BEHAVIOR': 'is_error'})
        self.assertNotEqual(r.returncode, 0)

    def test_ask_mode_edit_detection(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'ask',
                    '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'edit_outside'})
        self.assertEqual(r.returncode, 3, msg=r.stdout.decode()[:2000] + r.stderr.decode()[:2000])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertTrue(receipt.get('scope_violation'))

    def test_owned_edit_success(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'fix'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'edit_owned'})
        self.assertEqual(r.returncode, 0, msg=r.stdout.decode()[:2000] + r.stderr.decode()[:2000])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'candidate')
        self.assertIn('owned.txt', receipt['changed_paths'])
        self.assertNotIn('other.txt', receipt['changed_paths'])
        result = (run_dir / 'result.txt').read_text()
        self.assertIn('edited owned', result)

    def test_index_mutation_fails(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'fix'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'stage_owned'})
        self.assertEqual(r.returncode, 3, msg=r.stdout.decode()[:2000])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertTrue(receipt.get('scope_violation'))
        # cleanup index for other tests (fresh ws each time so no need)

    def test_empty_output_fails(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'empty'})
        self.assertNotEqual(r.returncode, 0)
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'worker_failed')

    def test_grok_empty_output_fails(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_BEHAVIOR': 'empty_result'})
        self.assertNotEqual(r.returncode, 0)

    def test_timeout(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--timeout', '1',
                    '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'sleep'})
        self.assertEqual(r.returncode, 124, msg=r.stdout.decode()[:2000] + r.stderr.decode()[:2000])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'timeout')

    def test_lock_rejection(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        lock_path = W.lock_path_for(ws.resolve())
        fh = open(lock_path, 'a+')
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            rundir_parent = tempfile.mkdtemp(prefix='runs-')
            run_dir = pathlib.Path(rundir_parent) / 'run1'
            r = invoke(['--workspace', str(ws), '--provider', 'muse',
                        '--run-dir', str(run_dir), 'hi'],
                       env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('lock', (r.stderr.decode() + r.stdout.decode()).lower())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()

    def test_path_escape(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'work',
                    '--allow-path', '../escape', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
        self.assertNotEqual(r.returncode, 0)
        r2 = invoke(['--workspace', str(ws), '--provider', 'muse', '--mode', 'work',
                     '--allow-path', '/abs', '--run-dir', str(pathlib.Path(rundir_parent) / 'run2'), 'hi'],
                    env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
        self.assertNotEqual(r2.returncode, 0)

    def test_run_dir_outside_required(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        # missing run-dir
        r = invoke(['--workspace', str(ws), '--provider', 'muse', 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
        self.assertNotEqual(r.returncode, 0)
        # inside workspace
        inside = ws / 'run-inside'
        r2 = invoke(['--workspace', str(ws), '--provider', 'muse', '--run-dir', str(inside), 'hi'],
                    env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub)})
        self.assertNotEqual(r2.returncode, 0)

    def test_parse_excludes_reasoning(self):
        raw = (b'{"type":"text","text":"keep"}\n'
               b'{"type":"reasoning","text":"drop"}\n'
               b'{"type":"tool_use","text":"drop2"}\n'
               b'{"type":"step_finish","part":{"reason":"stop"}}\n')
        text, meta, err = W.parse_muse_output(raw)
        self.assertEqual(text, 'keep')
        self.assertFalse(err)

    def test_parse_grok_result(self):
        raw = json.dumps({'type': 'result', 'subtype': 'success', 'result': 'hello', 'is_error': False}).encode()
        text, meta, err = W.parse_grok_output(raw)
        self.assertEqual(text, 'hello')
        self.assertFalse(err)
        raw2 = json.dumps({'type': 'result', 'subtype': 'success', 'result': '', 'is_error': True}).encode()
        _, _, err2 = W.parse_grok_output(raw2)
        self.assertTrue(err2)

    def test_step_budget_and_partial_delivery(self):
        self.assertEqual(W.build_opencode_config('ask', [], 75)['agent']['squad-worker']['steps'],75)
        for label in ('complete','partial','blocked','needs_context'):
            text,status,capped=W.classify_handoff('progress\nSQUAD_STATUS: '+label+'\nFiles: none','work',3,60)
            self.assertTrue(text.startswith('SQUAD_STATUS:'))
            self.assertEqual(status,label)
            self.assertFalse(capped)
        self.assertEqual(W.classify_handoff('SQUAD_STATUS: complete','work',30,30)[1:],('partial',True))
        self.assertEqual(W.classify_handoff('Maximum steps for this agent have been reached.','work')[1],'partial')
        self.assertEqual(W.classify_handoff('SQUAD_STATUS: partial\nremaining test','work')[1],'partial')
        self.assertEqual(W.classify_handoff('SQUAD_STATUS: complete\nHistorical maximum steps reached in prior run','ask')[1],'complete')

    def test_final_step_only_with_full_usage(self):
        events=[{'type':'step_start'}, {'type':'text','part':{'text':'progress noise'}},
                {'type':'step_finish','part':{'reason':'tool-calls','tokens':{'input':10}}},
                {'type':'step_start'}, {'type':'text','part':{'text':'SQUAD_STATUS: complete\nDone'}},
                {'type':'step_finish','part':{'reason':'stop','tokens':{'input':20}}}]
        text,meta,error=W.parse_muse_output('\n'.join(map(json.dumps,events)))
        self.assertNotIn('progress noise',text)
        self.assertFalse(error)
        self.assertEqual(meta['step_count'],2)
        self.assertEqual(len(meta['usage']['steps']),2)

    def test_final_handoff_survives_trailing_tool_step(self):
        events=[{'type':'step_start'}, {'type':'text','part':{'text':'SQUAD_STATUS: partial\nRemaining task'}},
                {'type':'step_finish','part':{'reason':'tool-calls'}}, {'type':'step_start'}]
        text,meta,error=W.parse_muse_output('\n'.join(map(json.dumps,events)))
        self.assertIn('Remaining task',text)
        self.assertTrue(error)  # An unfinished stream is still a transport failure.
        text,status,capped=W.classify_handoff('SQUAD_STATUS: complete\nFound defects, step-capped example:\nSQUAD_STATUS: partial','ask')
        self.assertEqual(status,'complete')
        self.assertFalse(capped)

    def test_real_step_cap_and_provider_error_precedence(self):
        for failure in (False,True):
            with self.subTest(failure=failure):
                ws=make_workspace(); stubdir=pathlib.Path(tempfile.mkdtemp(prefix='stub-')); stub=stubdir/'opencode'
                events=[{'type':'step_finish','part':{'reason':'tool-calls'}} for _ in range(4)]
                events += [{'type':'text','part':{'text':'SQUAD_STATUS: complete'}},
                           {'type':'step_finish','part':{'reason':'stop'}}]
                if failure:events.append({'type':'error','error':'provider failure'})
                write_stub(stub,'#!/usr/bin/env python3\nimport json\nevents='+repr(events)+'\nfor e in events: print(json.dumps(e))\n')
                run=stubdir/'run'
                result=invoke(['--workspace',str(ws),'--provider','muse','--steps','5','--run-dir',str(run),'deliver'],
                              {'SUBSCRIPTION_SQUAD_OPENCODE_BIN':str(stub)})
                self.assertEqual(result.returncode,1 if failure else 4,result.stderr.decode())
                receipt=json.loads((run/'receipt.json').read_text())
                self.assertEqual(receipt['work_status'],'partial')
                self.assertEqual(receipt['status'],'worker_failed' if failure else 'incomplete')

    def test_incomplete_run_exit_code_and_receipt(self):
        ws=make_workspace(); stubdir=pathlib.Path(tempfile.mkdtemp(prefix='stub-')); stub=stubdir/'opencode'
        write_stub(stub,MUSE_STUB.replace('hello candidate','SQUAD_STATUS: partial'))
        run=stubdir/'run'
        result=invoke(['--workspace',str(ws),'--provider','muse','--steps','45','--run-dir',str(run),'finish'],
                      {'SUBSCRIPTION_SQUAD_OPENCODE_BIN':str(stub)})
        self.assertEqual(result.returncode,4,result.stderr.decode())
        receipt=json.loads((run/'receipt.json').read_text())
        self.assertEqual(receipt['status'],'incomplete')
        self.assertEqual(receipt['work_status'],'partial')
        self.assertEqual(receipt['step_budget'],45)
        self.assertTrue(receipt['protected_content_unchanged'])

    def test_nested_workspace_rejected(self):
        ws=make_workspace(); nested=ws/'nested'; nested.mkdir()
        stubdir=pathlib.Path(tempfile.mkdtemp(prefix='stub-')); stub=stubdir/'opencode'
        write_stub(stub,MUSE_STUB)
        result=invoke(['--workspace',str(nested),'--provider','muse','hello'],
                      {'SUBSCRIPTION_SQUAD_OPENCODE_BIN':str(stub)})
        self.assertNotEqual(result.returncode,0)
        self.assertIn('checkout root',result.stderr.decode())

    def test_real_inventory_shape_and_wrong_provider(self):
        metadata={'id':'muse-spark-1.3-contributor','providerID':'opencode-go','variants':{'xhigh':{'reasoningEffort':'xhigh'}}}
        self.assertTrue(W.muse_inventory_ok('opencode-go/muse-spark-1.3-contributor\n'+json.dumps(metadata)))
        metadata['providerID']='other-provider'
        self.assertFalse(W.muse_inventory_ok(json.dumps(metadata)))

    def test_grok_plaintext_is_not_success(self):
        self.assertTrue(W.parse_grok_output('Quota exceeded')[2])
        self.assertTrue(W.parse_grok_output('{"result":"invented shape"}')[2])

    def test_muse_incomplete_and_usage_steps(self):
        events=[{'type':'text','part':{'type':'text','text':'candidate'}},
                {'type':'step_finish','part':{'reason':'tool-calls','tokens':{'input':10},'cost':0.1}}]
        self.assertTrue(W.parse_muse_output('\n'.join(map(json.dumps,events)))[2])
        events.append({'type':'step_finish','part':{'reason':'stop','tokens':{'input':20},'cost':0.2}})
        text,meta,error=W.parse_muse_output('\n'.join(map(json.dumps,events)))
        self.assertFalse(error)
        self.assertEqual(len(meta['usage']['steps']),2)
        self.assertEqual(meta['usage']['steps'][1]['cost'],0.2)

    def test_no_shell_and_no_generic_model_flag(self):
        src = WORKER.read_text()
        self.assertNotIn('shell=True', src)
        # CLI must not define generic --model / --skip-model-check; internal provider argv still uses --model.
        self.assertNotIn("add_argument('--model'", src)
        self.assertNotIn('add_argument("--model"', src)
        self.assertNotIn('skip-model-check', src)
        r = subprocess.run([sys.executable, str(WORKER), '--help'], capture_output=True, timeout=10)
        help_text = r.stdout.decode()
        self.assertIn('--provider', help_text)
        self.assertNotIn('--skip-model-check', help_text)
        # --help lists --provider but no generic --model flag line
        self.assertNotRegex(help_text, r'(?m)^\\s*--model\\b')

    def test_stdout_compact_and_result(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        env = {'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'reasoning_mix'}
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--run-dir', str(run_dir), 'hi'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        out = r.stdout.decode()
        self.assertIn('subscription_squad_run_dir=', out)
        self.assertIn(MUSE, out)
        result = (run_dir / 'result.txt').read_text()
        self.assertIn('keep me', result)
        self.assertNotIn('drop me', result)


if __name__ == '__main__':
    unittest.main()
