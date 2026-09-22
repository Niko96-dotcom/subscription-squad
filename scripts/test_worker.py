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
GROK_BUILD = W.GROK_BUILD_MODEL
AGY = W.ANTIGRAVITY_MODEL


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


def make_antigravity_settings(payload=None, raw=None):
    directory = pathlib.Path(tempfile.mkdtemp(prefix='agy-settings-'))
    path = directory / 'settings.json'
    if raw is not None:
        path.write_text(raw)
    else:
        if payload is None:
            payload = {'enableTerminalSandbox': True, 'toolPermission': 'proceed-in-sandbox'}
        path.write_text(json.dumps(payload))
    return path


def make_antigravity_home(workspace, write_paths=(), payload=None, raw=None):
    home = pathlib.Path(tempfile.mkdtemp(prefix='agy-home-'))
    settings_dir = home / '.gemini' / 'antigravity-cli'
    settings_dir.mkdir(parents=True)
    if payload is None and raw is None:
        root = str(pathlib.Path(workspace).resolve())
        allow = [f'read_file({root})']
        allow.extend(f'write_file({pathlib.Path(workspace).resolve() / path})'
                     for path in write_paths)
        payload = {'enableTerminalSandbox': True,
                   'toolPermission': 'proceed-in-sandbox',
                   'permissions': {'allow': allow}}
    settings = settings_dir / 'settings.json'
    settings.write_text(raw if raw is not None else json.dumps(payload))
    return home


MUSE_STUB = """#!/usr/bin/env python3
import atexit
import sys, os, json, pathlib, subprocess, time
af = os.environ.get('STUB_ARGV_FILE')
if af:
    pathlib.Path(af).write_text(json.dumps(sys.argv))
ef = os.environ.get('STUB_ENV_FILE')
if ef:
    data = {}
    for k in ('OPENCODE_CONFIG_CONTENT','OPENCODE_CONFIG','OPENCODE_PERMISSION','CURSOR_API_KEY','CURSOR_API_ENDPOINT','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','XAI_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY','OPENCODE_API_KEY','OPENCODE_GO_API_KEY','GH_TOKEN','GITHUB_TOKEN','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN','CUSTOM_TOKEN','CUSTOM_SECRET','CUSTOM_API_KEY'):
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
    elif beh == 'move_head_only':
        tree = subprocess.run(['git', '-C', ws, 'rev-parse', 'HEAD^{tree}'], capture_output=True, text=True).stdout.strip()
        new = subprocess.run(['git', '-C', ws, 'commit-tree', tree, '-m', 'head move'], capture_output=True, text=True).stdout.strip()
        subprocess.run(['git', '-C', ws, 'update-ref', 'HEAD', new], check=True)
        print(json.dumps({'type': 'text', 'text': 'SQUAD_STATUS: complete\\nhead moved'}))
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
    for k in ('CURSOR_API_KEY','CURSOR_API_ENDPOINT','OPENCODE_CONFIG_CONTENT','OPENCODE_CONFIG','OPENCODE_PERMISSION','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','XAI_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY','OPENCODE_API_KEY','OPENCODE_GO_API_KEY','GH_TOKEN','GITHUB_TOKEN','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN','CUSTOM_TOKEN','CUSTOM_SECRET','CUSTOM_API_KEY'):
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
        print('grok-4.7-xhigh  Grok model')
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
        print(json.dumps({'type': 'result', 'subtype': 'success', 'result': 'grok ok', 'is_error': False, 'model': 'grok-4.7-xhigh', 'sessionID': 'ses_g'}))
        sys.exit(0)
print('unexpected cursor stub', file=sys.stderr)
sys.exit(2)
"""


def invoke(args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, env=env, timeout=60)


GROK_BUILD_STUB = """#!/usr/bin/env python3
import sys, os, json, pathlib
af = os.environ.get('STUB_ARGV_FILE')
if af:
    pathlib.Path(af).write_text(json.dumps(sys.argv))
ef = os.environ.get('STUB_ENV_FILE')
if ef:
    data = {}
    for k in ('OPENCODE_CONFIG_CONTENT','OPENCODE_CONFIG','OPENCODE_PERMISSION','CURSOR_API_KEY','CURSOR_API_ENDPOINT','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','XAI_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY','OPENCODE_API_KEY','OPENCODE_GO_API_KEY','GH_TOKEN','GITHUB_TOKEN','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN','CUSTOM_TOKEN','CUSTOM_SECRET','CUSTOM_API_KEY'):
        if k in os.environ:
            data[k] = os.environ[k]
    pathlib.Path(ef).write_text(json.dumps(data))
if 'models' in sys.argv:
    mode = os.environ.get('STUB_INVENTORY_MODE', 'ok')
    if mode == 'missing':
        print('other-model  Other')
    else:
        print('grok-4.7  Grok model')
        print('other-model  Other')
    sys.exit(0)
if '--single' in sys.argv:
    beh = os.environ.get('STUB_BEHAVIOR', 'ok')
    if beh == 'cancelled':
        print(json.dumps({'text': 'partial thought', 'stopReason': 'cancelled', 'sessionId': 'ses_cancel', 'requestId': 'req_1', 'usage': {'input': 5}, 'num_turns': 1, 'total_cost_usd': 0.01, 'modelUsage': 'grok-4.6-build'}))
        sys.exit(0)
    elif beh == 'empty':
        print(json.dumps({'text': '', 'stopReason': 'stop', 'sessionId': 'ses_e', 'modelUsage': 'grok-4.6-build'}))
        sys.exit(0)
    elif beh == 'malformed':
        print('not json at all')
        sys.exit(0)
    elif beh == 'error_key':
        print(json.dumps({'text': 'hi', 'stopReason': 'stop', 'error': 'boom', 'modelUsage': 'grok-4.6-build'}))
        sys.exit(0)
    else:
        print(json.dumps({'text': 'grok build ok', 'stopReason': 'stop', 'sessionId': 'ses_gb', 'requestId': 'req_gb', 'thought': 'reasoning', 'usage': {'input': 10}, 'num_turns': 1, 'total_cost_usd': 0.02, 'modelUsage': 'grok-4.6-build'}))
        sys.exit(0)
print('unexpected grok-build stub', file=sys.stderr)
sys.exit(2)
"""

ANTIGRAVITY_STUB = """#!/usr/bin/env python3
import sys, os, json, pathlib
af = os.environ.get('STUB_ARGV_FILE')
if af:
    pathlib.Path(af).write_text(json.dumps(sys.argv))
ef = os.environ.get('STUB_ENV_FILE')
if ef:
    data = {}
    for k in ('OPENCODE_CONFIG_CONTENT','OPENCODE_CONFIG','OPENCODE_PERMISSION','CURSOR_API_KEY','CURSOR_API_ENDPOINT','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','XAI_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY','OPENCODE_API_KEY','OPENCODE_GO_API_KEY','GH_TOKEN','GITHUB_TOKEN','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN','CUSTOM_TOKEN','CUSTOM_SECRET','CUSTOM_API_KEY'):
        if k in os.environ:
            data[k] = os.environ[k]
    pathlib.Path(ef).write_text(json.dumps(data))
cf = os.environ.get('STUB_CWD_FILE')
if cf:
    pathlib.Path(cf).write_text(os.getcwd())
if 'models' in sys.argv:
    mode = os.environ.get('STUB_INVENTORY_MODE', 'ok')
    if mode == 'missing':
        print('other-model  Other')
    else:
        print('gemini-3.8-flash-high  Gemini 3.8 Flash (High)')
        print('other-model  Other')
    sys.exit(0)
if any(a.startswith('--print=') for a in sys.argv):
    beh = os.environ.get('STUB_BEHAVIOR', 'ok')
    if beh == 'empty_response':
        print(json.dumps({'conversation_id': 'conv_e', 'status': 'SUCCESS', 'response': '', 'duration_seconds': 1, 'num_turns': 1, 'usage': {'input': 5}, 'denied_actions': []}))
        sys.exit(0)
    elif beh == 'denied':
        print(json.dumps({'conversation_id': 'conv_d', 'status': 'SUCCESS', 'response': 'hi', 'duration_seconds': 1, 'num_turns': 1, 'usage': {'input': 5}, 'denied_actions': [{'action': 'edit'}]}))
        sys.exit(0)
    elif beh == 'nonsuccess':
        print(json.dumps({'conversation_id': 'conv_f', 'status': 'FAILED', 'response': 'hi', 'duration_seconds': 1, 'num_turns': 1, 'usage': {}, 'denied_actions': []}))
        sys.exit(0)
    elif beh == 'malformed':
        print('not json')
        sys.exit(0)
    else:
        print(json.dumps({'conversation_id': 'conv_ok', 'status': 'SUCCESS', 'response': 'agy ok', 'duration_seconds': 2, 'num_turns': 1, 'usage': {'input': 7}, 'denied_actions': []}))
        sys.exit(0)
print('unexpected agy stub', file=sys.stderr)
sys.exit(2)
"""


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
            'OPENAI_API_KEY': 'sk-inherited',
            'ANTHROPIC_API_KEY': 'sk-ant-inherited',
            'GH_TOKEN': 'gh-inherited',
            'AWS_SECRET_ACCESS_KEY': 'aws-inherited',
            'CURSOR_API_KEY': 'cursor-inherited',
            'CURSOR_API_ENDPOINT': 'https://inherited',
            'CUSTOM_TOKEN': 'tok-inherited',
            'CUSTOM_SECRET': 'sec-inherited',
            'CUSTOM_API_KEY': 'key-inherited',
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
        for k in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GH_TOKEN', 'AWS_SECRET_ACCESS_KEY',
                  'CURSOR_API_KEY', 'CURSOR_API_ENDPOINT', 'CUSTOM_TOKEN', 'CUSTOM_SECRET', 'CUSTOM_API_KEY'):
            self.assertNotIn(k, envdump)

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
               'OPENAI_API_KEY': 'sk-inherited', 'GH_TOKEN': 'gh-inherited',
               'OPENCODE_CONFIG_CONTENT': 'inherited-prompt', 'CUSTOM_TOKEN': 'tok-inherited',
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
        self.assertEqual(argv[argv.index('--model') + 1], 'grok-4.7-xhigh')
        self.assertIn('--mode', argv)
        self.assertIn('ask', argv)
        self.assertIn('--trust', argv)
        self.assertIn('hello grok', argv[-1])
        self.assertIn('Do not delegate', argv[-1])
        envdump = json.loads(env_file.read_text())
        self.assertNotIn('CURSOR_API_KEY', envdump)
        self.assertNotIn('CURSOR_API_ENDPOINT', envdump)
        self.assertNotIn('OPENAI_API_KEY', envdump)
        self.assertNotIn('GH_TOKEN', envdump)
        self.assertNotIn('OPENCODE_CONFIG_CONTENT', envdump)
        self.assertNotIn('CUSTOM_TOKEN', envdump)

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

    def test_sanitized_provider_env_shared(self):
        base = dict(os.environ)
        base.update({'OPENAI_API_KEY': 'sk-x', 'GH_TOKEN': 'g', 'AWS_SECRET_ACCESS_KEY': 's',
                     'OPENCODE_CONFIG_CONTENT': 'x', 'OPENCODE_CONFIG': 'y', 'OPENCODE_PERMISSION': 'z',
                     'CURSOR_API_KEY': 'c', 'CURSOR_API_ENDPOINT': 'e',
                     'CUSTOM_TOKEN': 't', 'CUSTOM_SECRET': 's', 'CUSTOM_API_KEY': 'k'})
        with patch.dict(os.environ, base, clear=True):
            # Preserve normal env and fixture controls that do not look like credentials.
            os.environ['HOME'] = '/home/tester'
            os.environ['PATH'] = '/usr/bin'
            os.environ['STUB_BEHAVIOR'] = 'ok'
            os.environ['SUBSCRIPTION_SQUAD_OPENCODE_BIN'] = '/tmp/opencode'
            env = W.sanitized_provider_env()
            for k in ('OPENAI_API_KEY', 'GH_TOKEN', 'AWS_SECRET_ACCESS_KEY', 'OPENCODE_CONFIG_CONTENT',
                      'OPENCODE_CONFIG', 'OPENCODE_PERMISSION', 'CURSOR_API_KEY', 'CURSOR_API_ENDPOINT',
                      'CUSTOM_TOKEN', 'CUSTOM_SECRET', 'CUSTOM_API_KEY'):
                self.assertNotIn(k, env)
            self.assertEqual(env['HOME'], '/home/tester')
            self.assertEqual(env['STUB_BEHAVIOR'], 'ok')
            self.assertEqual(env['SUBSCRIPTION_SQUAD_OPENCODE_BIN'], '/tmp/opencode')

    def test_muse_preflight_filtered_env_and_generated_config(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        env_file = stubdir / 'env.json'
        env = {'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_ENV_FILE': str(env_file),
               'STUB_INVENTORY_MODE': 'ok', 'OPENCODE_CONFIG_CONTENT': 'inherited',
               'OPENCODE_CONFIG': '/tmp/x', 'OPENAI_API_KEY': 'sk-x', 'GH_TOKEN': 'g',
               'CUSTOM_SECRET': 's', 'CURSOR_API_KEY': 'c'}
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--check'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        envdump = json.loads(env_file.read_text())
        self.assertIn('OPENCODE_CONFIG_CONTENT', envdump)
        self.assertNotEqual(envdump['OPENCODE_CONFIG_CONTENT'], 'inherited')
        cfg = json.loads(envdump['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(cfg['enabled_providers'], ['opencode-go'])
        self.assertEqual(cfg['share'], 'disabled')
        self.assertEqual(cfg['permission']['edit'], 'deny')
        self.assertEqual(cfg['permission']['webfetch'], 'allow')
        for k in ('OPENCODE_CONFIG', 'OPENAI_API_KEY', 'GH_TOKEN', 'CUSTOM_SECRET', 'CURSOR_API_KEY'):
            self.assertNotIn(k, envdump)

    def test_grok_preflight_filtered_env(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        env_file = stubdir / 'env.json'
        env = {'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_ENV_FILE': str(env_file),
               'STUB_INVENTORY_MODE': 'ok', 'CURSOR_API_KEY': 'secret',
               'OPENAI_API_KEY': 'sk-x', 'OPENCODE_CONFIG_CONTENT': 'inherited'}
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--check'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        envdump = json.loads(env_file.read_text())
        self.assertNotIn('CURSOR_API_KEY', envdump)
        self.assertNotIn('OPENAI_API_KEY', envdump)
        self.assertNotIn('OPENCODE_CONFIG_CONTENT', envdump)

    def test_parse_grok_session_id_variants(self):
        for key, val in (('session_id', 'a1'), ('sessionID', 'ses_g'), ('sessionId', 'c3')):
            raw = json.dumps({'type': 'result', 'subtype': 'success', 'result': 'hi',
                              'is_error': False, key: val}).encode()
            _, meta, err = W.parse_grok_output(raw)
            self.assertFalse(err)
            self.assertEqual(meta.get(key), val)

    def test_grok_session_native_end_to_end(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub), 'STUB_BEHAVIOR': 'ok'})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000] + r.stdout.decode()[:1000])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt.get('session_native'), 'ses_g')
        self.assertEqual(receipt.get('native_meta', {}).get('sessionID'), 'ses_g')

    def test_head_only_movement_marks_unprotected(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'muse', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'move_head_only'})
        self.assertEqual(r.returncode, 3, msg=r.stdout.decode()[:2000] + r.stderr.decode()[:2000])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertTrue(receipt.get('scope_violation'))
        self.assertFalse(receipt.get('protected_content_unchanged'))
        self.assertNotEqual(receipt.get('head_before'), receipt.get('head_after'))
        self.assertEqual(receipt.get('changed_paths'), [])
        self.assertEqual(receipt.get('index_changed_paths'), [])

    def test_run_dir_mode_0700(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'opencode'
        write_stub(stub, MUSE_STUB)
        rundir_parent = tempfile.mkdtemp(prefix='runs-')
        run_dir = pathlib.Path(rundir_parent) / 'run1'
        old = os.umask(0o022)
        try:
            r = invoke(['--workspace', str(ws), '--provider', 'muse', '--run-dir', str(run_dir), 'hi'],
                       env_extra={'SUBSCRIPTION_SQUAD_OPENCODE_BIN': str(stub), 'STUB_BEHAVIOR': 'ok'})
        finally:
            os.umask(old)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        mode = stat.S_IMODE(os.stat(run_dir).st_mode)
        self.assertEqual(mode, 0o700)

    def test_grok_build_ask_argv_env(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'grok'
        write_stub(stub, GROK_BUILD_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        argv_file = stubdir / 'argv.json'
        env_file = stubdir / 'env.json'
        env = {'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN': str(stub), 'STUB_ARGV_FILE': str(argv_file),
               'STUB_ENV_FILE': str(env_file), 'CURSOR_API_KEY': 'secret',
               'OPENAI_API_KEY': 'sk-x', 'OPENCODE_CONFIG_CONTENT': 'inherited',
               'CUSTOM_TOKEN': 't', 'STUB_BEHAVIOR': 'ok'}
        r = invoke(['--workspace', str(ws), '--provider', 'grok-build', '--mode', 'ask',
                    '--run-dir', str(run_dir), 'hello build'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000] + r.stdout.decode()[:2000])
        argv = json.loads(argv_file.read_text())
        self.assertEqual(argv[argv.index('--cwd') + 1], str(ws.resolve()))
        self.assertEqual(argv[argv.index('--model') + 1], GROK_BUILD)
        self.assertEqual(GROK_BUILD, 'grok-4.7')
        self.assertEqual(argv[argv.index('--reasoning-effort') + 1], 'xhigh')
        self.assertEqual(argv[argv.index('--permission-mode') + 1], 'plan')
        self.assertIn('--no-subagents', argv)
        self.assertIn('--disable-web-search', argv)
        self.assertEqual(argv[argv.index('--output-format') + 1], 'json')
        self.assertIn('--single', argv)
        self.assertIn('hello build', argv[argv.index('--single') + 1])
        self.assertIn('Do not delegate', argv[-1])
        joined = ' '.join(argv)
        for bad in ('--trust', '--dangerously-skip-permissions', 'bypassPermissions', 'always-approve', '--yolo', '--force'):
            self.assertNotIn(bad, joined)
        envdump = json.loads(env_file.read_text())
        for k in ('CURSOR_API_KEY', 'OPENAI_API_KEY', 'OPENCODE_CONFIG_CONTENT', 'CUSTOM_TOKEN'):
            self.assertNotIn(k, envdump)

    def test_grok_build_work_accept_edits(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'grok'
        write_stub(stub, GROK_BUILD_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        argv_file = stubdir / 'argv.json'
        r = invoke(['--workspace', str(ws), '--provider', 'grok-build', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'do work'],
                   env_extra={'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN': str(stub),
                              'STUB_ARGV_FILE': str(argv_file), 'STUB_BEHAVIOR': 'ok'})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000] + r.stdout.decode()[:2000])
        argv = json.loads(argv_file.read_text())
        self.assertEqual(argv[argv.index('--permission-mode') + 1], 'acceptEdits')
        self.assertIn('owned.txt', argv[-1])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['provider'], 'grok-build')
        self.assertEqual(receipt['model'], GROK_BUILD)
        self.assertEqual(receipt['model_requested'], GROK_BUILD)
        self.assertEqual(receipt['variant'], 'xhigh')
        self.assertEqual(receipt['effort'], 'xhigh')
        self.assertEqual(receipt['session_native'], 'ses_gb')
        # modelUsage is not a scalar model report; only model/modelID/model_id count.
        self.assertIsNone(receipt['model_reported'])
        self.assertEqual(receipt['native_meta'].get('modelUsage'), 'grok-4.6-build')
        self.assertIn('input', json.dumps(receipt.get('usage_native', {})))

    def test_antigravity_ask_argv_env_cwd(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'agy'
        write_stub(stub, ANTIGRAVITY_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        argv_file = stubdir / 'argv.json'
        env_file = stubdir / 'env.json'
        cwd_file = stubdir / 'cwd.txt'
        home = make_antigravity_home(ws)
        env = {'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': str(stub), 'STUB_ARGV_FILE': str(argv_file),
               'STUB_ENV_FILE': str(env_file), 'STUB_CWD_FILE': str(cwd_file),
               'HOME': str(home),
               'GEMINI_API_KEY': 'secret', 'OPENAI_API_KEY': 'sk-x', 'STUB_BEHAVIOR': 'ok'}
        r = invoke(['--workspace', str(ws), '--provider', 'antigravity', '--mode', 'ask',
                    '--run-dir', str(run_dir), 'hello agy'], env_extra=env)
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000] + r.stdout.decode()[:2000])
        argv = json.loads(argv_file.read_text())
        self.assertEqual(argv[argv.index('--model') + 1], AGY)
        self.assertEqual(argv[argv.index('--effort') + 1], 'high')
        self.assertEqual(argv[argv.index('--mode') + 1], 'plan')
        self.assertEqual(argv[argv.index('--output-format') + 1], 'json')
        self.assertIn('--new-project', argv)
        self.assertIn('--sandbox', argv)
        self.assertIn('--print-timeout', argv)
        prints = [a for a in argv if a.startswith('--print=')]
        self.assertEqual(len(prints), 1)
        self.assertIn('hello agy', prints[0])
        self.assertIn('Do not delegate', prints[0])
        # flags must precede --print=<prompt>
        self.assertLess(argv.index('--model'), argv.index(prints[0]))
        self.assertLess(argv.index('--mode'), argv.index(prints[0]))
        self.assertLess(argv.index('--sandbox'), argv.index(prints[0]))
        joined = ' '.join(argv)
        for bad in ('--trust', '--dangerously-skip-permissions', '--disable-slash-commands', 'always-approve', 'bypassPermissions', '--yolo'):
            self.assertNotIn(bad, joined)
        self.assertEqual(pathlib.Path(cwd_file).read_text(), str(ws.resolve()))
        envdump = json.loads(env_file.read_text())
        self.assertNotIn('GEMINI_API_KEY', envdump)
        self.assertNotIn('OPENAI_API_KEY', envdump)

    def test_antigravity_work_accept_edits(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'agy'
        write_stub(stub, ANTIGRAVITY_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        argv_file = stubdir / 'argv.json'
        cwd_file = stubdir / 'cwd.txt'
        home = make_antigravity_home(ws, ['owned.txt'])
        r = invoke(['--workspace', str(ws), '--provider', 'antigravity', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'do work'],
                   env_extra={'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': str(stub),
                              'HOME': str(home),
                              'STUB_ARGV_FILE': str(argv_file), 'STUB_CWD_FILE': str(cwd_file),
                              'STUB_BEHAVIOR': 'ok'})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:2000] + r.stdout.decode()[:2000])
        argv = json.loads(argv_file.read_text())
        self.assertEqual(argv[argv.index('--mode') + 1], 'accept-edits')
        self.assertIn('--new-project', argv)
        self.assertIn('--sandbox', argv)
        prints = [a for a in argv if a.startswith('--print=')]
        self.assertLess(argv.index('--sandbox'), argv.index(prints[0]))
        self.assertIn('owned.txt', prints[0])
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['provider'], 'antigravity')
        self.assertEqual(receipt['model'], AGY)
        self.assertEqual(receipt['variant'], 'high')
        self.assertEqual(receipt['effort'], 'high')
        self.assertNotEqual(receipt.get('variant'), 'xhigh')
        self.assertEqual(receipt['session_native'], 'conv_ok')

    def test_check_grok_build_ok_and_missing(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'grok'
        write_stub(stub, GROK_BUILD_STUB)
        r = invoke(['--workspace', str(ws), '--provider', 'grok-build', '--check'],
                   env_extra={'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN': str(stub), 'STUB_INVENTORY_MODE': 'ok'})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        self.assertIn('subscription_squad_check=ok', r.stdout.decode())
        self.assertIn(GROK_BUILD, r.stdout.decode())
        r2 = invoke(['--workspace', str(ws), '--provider', 'grok-build', '--check'],
                    env_extra={'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN': str(stub), 'STUB_INVENTORY_MODE': 'missing'})
        self.assertNotEqual(r2.returncode, 0)

    def test_check_antigravity_ok_and_missing(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'agy'
        write_stub(stub, ANTIGRAVITY_STUB)
        home = make_antigravity_home(ws)
        r = invoke(['--workspace', str(ws), '--provider', 'antigravity', '--check'],
                   env_extra={'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': str(stub), 'STUB_INVENTORY_MODE': 'ok',
                              'HOME': str(home)})
        self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
        self.assertIn('subscription_squad_check=ok', r.stdout.decode())
        self.assertIn(AGY, r.stdout.decode())
        r2 = invoke(['--workspace', str(ws), '--provider', 'antigravity', '--check'],
                    env_extra={'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': str(stub), 'STUB_INVENTORY_MODE': 'missing',
                               'HOME': str(home)})
        self.assertNotEqual(r2.returncode, 0)

    def test_antigravity_settings_path_and_validation(self):
        self.assertEqual(
            W.resolve_antigravity_settings_path({
                'SUBSCRIPTION_SQUAD_ANTIGRAVITY_SETTINGS': '/tmp/custom/settings.json',
                'HOME': '/tmp/home'}),
            pathlib.Path('/tmp/home/.gemini/antigravity-cli/settings.json'))
        self.assertEqual(
            W.resolve_antigravity_settings_path({'HOME': '/tmp/fake-home'}),
            pathlib.Path('/tmp/fake-home/.gemini/antigravity-cli/settings.json'))

        good = make_antigravity_settings()
        self.assertEqual(W.check_antigravity_sandbox_settings(settings_path=good), good)

        invalid = (
            make_antigravity_settings(raw='{not json'),
            make_antigravity_settings(raw='[]'),
            make_antigravity_settings(payload={
                'enableTerminalSandbox': False,
                'toolPermission': 'proceed-in-sandbox'}),
            make_antigravity_settings(payload={
                'enableTerminalSandbox': True,
                'toolPermission': 'request-review'}),
        )
        missing = pathlib.Path(tempfile.mkdtemp(prefix='agy-settings-')) / 'missing.json'
        for path in (*invalid, missing):
            with self.subTest(path=path), self.assertRaises(ValueError) as ctx:
                W.check_antigravity_sandbox_settings(settings_path=path)
            message = str(ctx.exception)
            self.assertIn(str(path), message)
            self.assertIn('enableTerminalSandbox', message)
            self.assertIn('toolPermission', message)

    def test_antigravity_bad_settings_fail_before_cli(self):
        for payload in (
            {'enableTerminalSandbox': False, 'toolPermission': 'proceed-in-sandbox'},
            {'enableTerminalSandbox': True, 'toolPermission': 'request-review'},
        ):
            with self.subTest(payload=payload):
                ws = make_workspace()
                stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
                stub = stubdir / 'agy'
                write_stub(stub, ANTIGRAVITY_STUB)
                argv_file = stubdir / 'argv.json'
                home = make_antigravity_home(ws, payload=payload)
                settings = home / '.gemini' / 'antigravity-cli' / 'settings.json'
                result = invoke(
                    ['--workspace', str(ws), '--provider', 'antigravity', '--check'],
                    env_extra={
                        'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': str(stub),
                        'HOME': str(home),
                        'STUB_ARGV_FILE': str(argv_file),
                    })
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(argv_file.exists())
                self.assertIn(str(settings), result.stderr.decode())

    def test_antigravity_workspace_files_need_no_global_grant(self):
        ws = make_workspace()
        good = make_antigravity_settings()
        self.assertEqual(
            W.check_antigravity_sandbox_settings(settings_path=good),
            good)

    def test_antigravity_project_reuse_or_create(self):
        ws = make_workspace()
        home = pathlib.Path(tempfile.mkdtemp(prefix='agy-home-'))
        self.assertEqual(W.antigravity_project_args(ws, {'HOME': str(home)}), ['--new-project'])
        project_dir = home / '.gemini' / 'config' / 'projects'
        project_dir.mkdir(parents=True)
        (project_dir / 'match.json').write_text(json.dumps({
            'id': 'project-123',
            'projectResources': {'resources': [{'folderUri': ws.resolve().as_uri()}]}}))
        self.assertEqual(
            W.antigravity_project_args(ws, {'HOME': str(home)}),
            ['--project', 'project-123'])
        (project_dir / 'broken.json').write_text('{bad json')
        self.assertEqual(
            W.antigravity_project_args(ws, {'HOME': str(home)}),
            ['--project', 'project-123'])

    def test_antigravity_project_malformed_resources_empty_id_and_gitfolder(self):
        ws = make_workspace()
        home = pathlib.Path(tempfile.mkdtemp(prefix='agy-home-'))
        project_dir = home / '.gemini' / 'config' / 'projects'
        project_dir.mkdir(parents=True)
        env = {'HOME': str(home)}

        # Malformed projectResources shapes must be skipped and return ['--new-project']
        malformed_shapes = [
            {'id': 'stale', 'projectResources': None},
            {'id': 'str-res', 'projectResources': 'invalid'},
            {'id': 'list-res', 'projectResources': [{'folderUri': ws.resolve().as_uri()}]},
            {'id': 'num-res', 'projectResources': 123},
            {'id': 'null-list', 'projectResources': {'resources': None}},
            {'id': 'str-list', 'projectResources': {'resources': 'invalid'}},
            {'id': 'default-cli-project', 'name': 'CLI Project', 'projectResources': {}},
        ]
        for i, shape in enumerate(malformed_shapes):
            p = project_dir / f'bad_{i}.json'
            p.write_text(json.dumps(shape))
            self.assertEqual(W.antigravity_project_args(ws, env), ['--new-project'])
            p.unlink()

        # Malformed earlier entry does not prevent later valid match
        (project_dir / '00-stale.json').write_text(json.dumps({'id': 'stale', 'projectResources': None}))
        (project_dir / '01-match.json').write_text(json.dumps({
            'id': 'match-456',
            'name': 'subscription-squad',
            'projectResources': {'resources': [{'folderUri': ws.resolve().as_uri()}]}}))
        self.assertEqual(W.antigravity_project_args(ws, env), ['--project', 'match-456'])
        (project_dir / '00-stale.json').unlink()
        (project_dir / '01-match.json').unlink()

        # Empty project IDs must not be reused
        for empty_id in ('', '   '):
            (project_dir / 'empty_id.json').write_text(json.dumps({
                'id': empty_id,
                'projectResources': {'resources': [{'folderUri': ws.resolve().as_uri()}]}}))
            self.assertEqual(W.antigravity_project_args(ws, env), ['--new-project'])
            (project_dir / 'empty_id.json').unlink()

        # Earlier empty ID skipped in favor of later valid matching entry
        (project_dir / '00-empty.json').write_text(json.dumps({
            'id': '',
            'projectResources': {'resources': [{'folderUri': ws.resolve().as_uri()}]}}))
        (project_dir / '01-valid.json').write_text(json.dumps({
            'id': 'valid-789',
            'projectResources': {'resources': [{'folderUri': ws.resolve().as_uri()}]}}))
        self.assertEqual(W.antigravity_project_args(ws, env), ['--project', 'valid-789'])
        (project_dir / '00-empty.json').unlink()
        (project_dir / '01-valid.json').unlink()

        # Nested gitFolder resource matching
        (project_dir / 'git-proj.json').write_text(json.dumps({
            'id': 'project-git',
            'name': 'Forge',
            'projectResources': {
                'resources': [{
                    'gitFolder': {
                        'folderUri': ws.resolve().as_uri(),
                        'allowWrite': True,
                    }
                }]
            }}))
        self.assertEqual(W.antigravity_project_args(ws, env), ['--project', 'project-git'])

    def test_trust_rejected_for_new_providers(self):
        ws = make_workspace()
        for prov, key, stubname, stubsrc in (
                ('grok-build', 'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN', 'grok', GROK_BUILD_STUB),
                ('antigravity', 'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN', 'agy', ANTIGRAVITY_STUB)):
            stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
            stub = stubdir / stubname
            write_stub(stub, stubsrc)
            run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
            r = invoke(['--workspace', str(ws), '--provider', prov, '--trust',
                        '--run-dir', str(run_dir), 'x'], env_extra={key: str(stub)})
            self.assertNotEqual(r.returncode, 0, msg=prov)

    def test_steps_rejected_for_new_providers(self):
        ws = make_workspace()
        for prov, key, stubname, stubsrc in (
                ('grok-build', 'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN', 'grok', GROK_BUILD_STUB),
                ('antigravity', 'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN', 'agy', ANTIGRAVITY_STUB)):
            stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
            stub = stubdir / stubname
            write_stub(stub, stubsrc)
            run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
            r = invoke(['--workspace', str(ws), '--provider', prov, '--steps', '45',
                        '--run-dir', str(run_dir), 'x'], env_extra={key: str(stub)})
            self.assertNotEqual(r.returncode, 0, msg=prov)

    def test_parse_grok_build_success_and_failures(self):
        ok = json.dumps({'text': 'hi', 'stopReason': 'stop', 'sessionId': 's1',
                         'requestId': 'r1', 'usage': {'input': 1}, 'num_turns': 1,
                         'total_cost_usd': 0.01, 'modelUsage': 'grok-4.6-build'}).encode()
        text, meta, err = W.parse_grok_build_output(ok)
        self.assertEqual(text, 'hi')
        self.assertFalse(err)
        self.assertEqual(meta['sessionId'], 's1')
        self.assertEqual(meta['modelUsage'], 'grok-4.6-build')
        cancelled = json.dumps({'text': 'partial', 'stopReason': 'cancelled', 'sessionId': 's1'}).encode()
        self.assertTrue(W.parse_grok_build_output(cancelled)[2])
        self.assertTrue(W.parse_grok_build_output(b'not json')[2])
        self.assertTrue(W.parse_grok_build_output(json.dumps({'text': '', 'stopReason': 'stop'}).encode())[2])
        self.assertTrue(W.parse_grok_build_output(json.dumps({'text': 'hi'}).encode())[2])
        self.assertTrue(W.parse_grok_build_output(json.dumps({'text': 'hi', 'stopReason': 'error'}).encode())[2])
        self.assertTrue(W.parse_grok_build_output(json.dumps({'text': 'hi', 'error': 'boom'}).encode())[2])

    def test_parse_antigravity_success_and_failures(self):
        ok = json.dumps({'conversation_id': 'c1', 'status': 'SUCCESS', 'response': 'hi',
                         'duration_seconds': 1, 'num_turns': 1, 'usage': {'input': 1},
                         'denied_actions': []}).encode()
        text, meta, err = W.parse_antigravity_output(ok)
        self.assertEqual(text, 'hi')
        self.assertFalse(err)
        self.assertEqual(meta['conversation_id'], 'c1')
        empty = json.dumps({'conversation_id': 'c1', 'status': 'SUCCESS', 'response': '',
                            'denied_actions': []}).encode()
        self.assertTrue(W.parse_antigravity_output(empty)[2])
        denied = json.dumps({'conversation_id': 'c1', 'status': 'SUCCESS', 'response': 'hi',
                             'denied_actions': [{'action': 'edit'}]}).encode()
        self.assertTrue(W.parse_antigravity_output(denied)[2])
        failed = json.dumps({'conversation_id': 'c1', 'status': 'FAILED', 'response': 'hi',
                             'denied_actions': []}).encode()
        self.assertTrue(W.parse_antigravity_output(failed)[2])
        self.assertTrue(W.parse_antigravity_output(b'nope')[2])

    def test_grok_build_noisy_prefix_observed_shape(self):
        final = {'text': 'SQUAD_STATUS: complete\nDone', 'stopReason': 'stop',
                 'sessionId': 'ses_1', 'requestId': 'req_1', 'thought': 'reasoning',
                 'usage': {'input': 10}, 'num_turns': 1, 'total_cost_usd': 0.02,
                 'modelUsage': {'grok-4.6-build': {'input': 10, 'output': 5}}}
        prefix = '\x1b[33mWARN retrying request\x1b[0m\n\x1b[31mERROR transient upstream\x1b[0m\narbitrary warning line\n'
        raw = (prefix + json.dumps(final) + '\n').encode()
        text, meta, err = W.parse_grok_build_output(raw)
        self.assertFalse(err)
        self.assertIn('SQUAD_STATUS: complete', text)
        self.assertEqual(meta['sessionId'], 'ses_1')
        self.assertEqual(meta['modelUsage'], {'grok-4.6-build': {'input': 10, 'output': 5}})
        # dict modelUsage must never become model_reported, nor may its key be inferred.
        self.assertIsNone(W._scalar_model_reported(meta))

    def test_antigravity_noisy_prefix(self):
        final = {'conversation_id': 'conv_ok', 'status': 'SUCCESS', 'response': 'agy ok',
                 'duration_seconds': 2, 'num_turns': 1, 'usage': {'input': 7}, 'denied_actions': []}
        raw = ('\x1b[33mWARN deprecated flag\x1b[0m\nsome warning line\n' + json.dumps(final) + '\n').encode()
        text, meta, err = W.parse_antigravity_output(raw)
        self.assertFalse(err)
        self.assertEqual(text, 'agy ok')
        self.assertEqual(meta['conversation_id'], 'conv_ok')

    def test_noisy_prefix_terminal_failures_stay_closed(self):
        prefix = '\x1b[33mWARN noisy\x1b[0m\nnoise line\n'
        cancelled = {'text': 'partial', 'stopReason': 'cancelled', 'sessionId': 's1',
                     'requestId': 'r1', 'thought': 't', 'usage': {'input': 1},
                     'num_turns': 1, 'total_cost_usd': 0.01,
                     'modelUsage': {'grok-4.6-build': {'input': 1}}}
        self.assertTrue(W.parse_grok_build_output((prefix + json.dumps(cancelled)).encode())[2])
        empty = dict(cancelled, text='', stopReason='stop')
        self.assertTrue(W.parse_grok_build_output((prefix + json.dumps(empty)).encode())[2])
        errkey = dict(cancelled, stopReason='stop', text='hi', error='boom')
        self.assertTrue(W.parse_grok_build_output((prefix + json.dumps(errkey)).encode())[2])
        denied = {'conversation_id': 'c1', 'status': 'SUCCESS', 'response': 'hi',
                  'duration_seconds': 1, 'num_turns': 1, 'usage': {'input': 1},
                  'denied_actions': [{'action': 'edit'}]}
        self.assertTrue(W.parse_antigravity_output((prefix + json.dumps(denied)).encode())[2])
        empty_agy = dict(denied, response='', denied_actions=[])
        self.assertTrue(W.parse_antigravity_output((prefix + json.dumps(empty_agy)).encode())[2])
        failed = dict(denied, denied_actions=[], status='FAILED')
        self.assertTrue(W.parse_antigravity_output((prefix + json.dumps(failed)).encode())[2])

    def test_terminal_garbage_not_accepted(self):
        ok_gb = {'text': 'hi', 'stopReason': 'stop', 'sessionId': 's1',
                 'requestId': 'r1', 'thought': 't', 'usage': {'input': 1},
                 'num_turns': 1, 'total_cost_usd': 0.01,
                 'modelUsage': {'grok-4.6-build': {'input': 1}}}
        ok_agy = {'conversation_id': 'c1', 'status': 'SUCCESS', 'response': 'hi',
                  'duration_seconds': 1, 'num_turns': 1, 'usage': {'input': 1}, 'denied_actions': []}
        # Valid earlier JSON followed by non-JSON terminal garbage must fail, not fall back.
        self.assertTrue(W.parse_grok_build_output((json.dumps(ok_gb) + '\nTRAILING GARBAGE {{{ not json\n').encode())[2])
        self.assertTrue(W.parse_antigravity_output((json.dumps(ok_agy) + '\nTRAILING GARBAGE {{{ not json\n').encode())[2])
        # Truncated terminal JSON fails even when an earlier valid object exists.
        truncated = '{"text": "partial", "stopReason": "stop"'
        self.assertTrue(W.parse_grok_build_output((json.dumps(ok_gb) + '\n' + truncated).encode())[2])
        self.assertTrue(W.parse_grok_build_output((truncated).encode())[2])
        self.assertTrue(W.parse_antigravity_output(b'{"level":"warn","msg":"diag"}\nWARN noise\n')[2])
        # Diagnostic JSON terminal without provider fields must not validate.
        self.assertTrue(W.parse_grok_build_output(b'{"level":"warn","msg":"diag"}\n')[2])

    def test_model_reported_scalar_only(self):
        self.assertIsNone(W._scalar_model_reported({'modelUsage': {'grok-4.6-build': {'input': 1}}}))
        self.assertIsNone(W._scalar_model_reported({'modelUsage': 'grok-4.6-build'}))
        self.assertIsNone(W._scalar_model_reported({'model_usage': 'x'}))
        self.assertIsNone(W._scalar_model_reported({'model': {'nested': 1}}))
        self.assertIsNone(W._scalar_model_reported({}))
        self.assertEqual(W._scalar_model_reported({'model': 'grok-4.6'}), 'grok-4.6')
        self.assertEqual(W._scalar_model_reported({'modelID': 'm1'}), 'm1')
        self.assertEqual(W._scalar_model_reported({'model_id': 'm2'}), 'm2')

    def test_grok_build_cancelled_exit0_fails(self):
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'grok'
        write_stub(stub, GROK_BUILD_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'grok-build', '--run-dir', str(run_dir), 'hi'],
                   env_extra={'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN': str(stub), 'STUB_BEHAVIOR': 'cancelled'})
        self.assertNotEqual(r.returncode, 0)
        receipt = json.loads((run_dir / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'worker_failed')

    def test_antigravity_denied_and_empty_fail(self):
        for beh in ('empty_response', 'denied', 'nonsuccess', 'malformed'):
            with self.subTest(beh=beh):
                ws = make_workspace()
                stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
                stub = stubdir / 'agy'
                write_stub(stub, ANTIGRAVITY_STUB)
                run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
                home = make_antigravity_home(ws)
                r = invoke(['--workspace', str(ws), '--provider', 'antigravity', '--run-dir', str(run_dir), 'hi'],
                           env_extra={'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': str(stub), 'STUB_BEHAVIOR': beh,
                                      'HOME': str(home)})
                self.assertNotEqual(r.returncode, 0, msg=beh)
                receipt = json.loads((run_dir / 'receipt.json').read_text())
                self.assertEqual(receipt['status'], 'worker_failed')

    def test_inventory_ok_new_providers(self):
        self.assertTrue(W.grok_build_inventory_ok('grok-4.7  Grok model\n'))
        self.assertTrue(W.grok_build_inventory_ok('  * grok-4.7 (default)\n  - grok-4.7-build-fast\n'))
        self.assertFalse(W.grok_build_inventory_ok('other-model  Other\n'))
        self.assertFalse(W.grok_build_inventory_ok('grok-4.7-build-fast  Other\n'))
        self.assertFalse(W.grok_build_inventory_ok('grok-4.7-build-fast  variant of grok-4.7\n'))
        self.assertFalse(W.grok_build_inventory_ok('grok-4.6  Grok model\n'))
        self.assertTrue(W.antigravity_inventory_ok('gemini-3.8-flash-high  Gemini 3.8 Flash (High)'))
        self.assertFalse(W.antigravity_inventory_ok('other-model  Other'))
        self.assertTrue(W.grok_build_inventory_ok(json.dumps({'id': 'grok-4.7'})))
        self.assertFalse(W.grok_build_inventory_ok(json.dumps({'id': 'grok-4.7-build-fast'})))
        self.assertFalse(W.grok_build_inventory_ok(json.dumps({'name': 'grok-4.7', 'id': 'grok-4.7-build-fast'})))
        self.assertTrue(W.antigravity_inventory_ok(json.dumps({'id': 'gemini-3.8-flash-high'})))
        self.assertTrue(W.grok_inventory_ok('grok-4.7-xhigh  Grok model\n'))
        self.assertFalse(W.grok_inventory_ok('grok-4.7-xhigh-fast  Grok model\n'))
        self.assertFalse(W.grok_inventory_ok('cursor-grok-4.6-xhigh  Grok model\n'))

    def test_resolve_env_override_and_fallback(self):
        with patch.dict(os.environ, {'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN': '/tmp/custom-grok'}):
            self.assertEqual(W.resolve_grok_build_bin(), '/tmp/custom-grok')
        with patch.dict(os.environ, {'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN': '/tmp/custom-agy'}):
            self.assertEqual(W.resolve_antigravity_bin(), '/tmp/custom-agy')

    def test_cursor_resolution_prefers_cursor_agent_over_generic_agent(self):
        def fake_which(name):
            return {'agent': '/tmp/grok/agent', 'cursor-agent': '/tmp/cursor-agent'}.get(name)
        with patch.dict(os.environ, {}, clear=True), patch.object(W.shutil, 'which', side_effect=fake_which):
            self.assertEqual(W.resolve_cursor_bin(), '/tmp/cursor-agent')

    def test_check_includes_resolved_bin_all_providers(self):
        cases = (
            ('muse', 'SUBSCRIPTION_SQUAD_OPENCODE_BIN', 'opencode', MUSE_STUB),
            ('grok', 'SUBSCRIPTION_SQUAD_CURSOR_BIN', 'cursor-agent', CURSOR_STUB),
            ('grok-build', 'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN', 'grok', GROK_BUILD_STUB),
            ('antigravity', 'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN', 'agy', ANTIGRAVITY_STUB),
        )
        for prov, key, stubname, stubsrc in cases:
            with self.subTest(provider=prov):
                ws = make_workspace()
                stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
                stub = stubdir / stubname
                write_stub(stub, stubsrc)
                home = make_antigravity_home(ws)
                r = invoke(['--workspace', str(ws), '--provider', prov, '--check'],
                           env_extra={key: str(stub), 'STUB_INVENTORY_MODE': 'ok',
                                      'HOME': str(home),
                                      'CURSOR_API_KEY': 'secret-should-not-leak',
                                      'OPENAI_API_KEY': 'sk-should-not-leak'})
                self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000])
                out = r.stdout.decode()
                self.assertIn('subscription_squad_check=ok', out)
                self.assertIn(f'bin={stub}', out)
                self.assertNotIn('secret-should-not-leak', out)
                self.assertNotIn('sk-should-not-leak', out)

    def test_receipt_includes_provider_bin_all_providers(self):
        cases = (
            ('muse', 'SUBSCRIPTION_SQUAD_OPENCODE_BIN', 'opencode', MUSE_STUB,
             ['--mode', 'work', '--allow-path', 'owned.txt']),
            ('grok', 'SUBSCRIPTION_SQUAD_CURSOR_BIN', 'cursor-agent', CURSOR_STUB,
             ['--mode', 'ask', '--trust']),
            ('grok-build', 'SUBSCRIPTION_SQUAD_GROK_BUILD_BIN', 'grok', GROK_BUILD_STUB,
             ['--mode', 'ask']),
            ('antigravity', 'SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN', 'agy', ANTIGRAVITY_STUB,
             ['--mode', 'ask']),
        )
        for prov, key, stubname, stubsrc, extra in cases:
            with self.subTest(provider=prov):
                ws = make_workspace()
                stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
                stub = stubdir / stubname
                write_stub(stub, stubsrc)
                run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
                home = make_antigravity_home(ws)
                r = invoke(['--workspace', str(ws), '--provider', prov,
                            '--run-dir', str(run_dir), *extra, 'hi'],
                           env_extra={key: str(stub), 'STUB_BEHAVIOR': 'ok',
                                      'HOME': str(home)})
                self.assertEqual(r.returncode, 0, msg=r.stderr.decode()[:1000] + r.stdout.decode()[:1000])
                receipt = json.loads((run_dir / 'receipt.json').read_text())
                self.assertEqual(receipt.get('provider_bin'), str(stub))

    def test_final_prompt_requires_literal_status_line(self):
        for mode in ('ask', 'work'):
            owned = [] if mode == 'ask' else [pathlib.Path('owned.txt')]
            prompt = W.build_final_prompt('do thing', mode, owned)
            self.assertIn('MUST begin with exactly one of these four complete literal lines', prompt)
            for label in ('complete', 'partial', 'blocked', 'needs_context'):
                self.assertIn(f'SQUAD_STATUS: {label}', prompt)
            self.assertNotIn('First line exactly SQUAD_STATUS: complete, partial', prompt)
        # Missing status stays unreported; the runner never fabricates it.
        _, status, _ = W.classify_handoff('hello candidate', 'ask')
        self.assertEqual(status, 'unreported')

    def test_cursor_resolution_full_order_and_env_override(self):
        with patch.dict(os.environ, {'SUBSCRIPTION_SQUAD_CURSOR_BIN': '/tmp/env-cursor'}):
            with patch.object(W.shutil, 'which', return_value='/tmp/other'):
                self.assertEqual(W.resolve_cursor_bin(), '/tmp/env-cursor')
        # cursor-agent beats bundled/cursor/generic agent
        def which_both(name):
            return {'agent': '/tmp/grok/agent', 'cursor-agent': '/tmp/cursor-agent'}.get(name)
        with patch.dict(os.environ, {}, clear=True), patch.object(W.shutil, 'which', side_effect=which_both):
            with patch.object(W.os, 'access', return_value=True):
                self.assertEqual(W.resolve_cursor_bin(), '/tmp/cursor-agent')
        # generic agent must not shadow cursor when cursor-agent/bundled are absent
        def which_cursor_agent(name):
            return {'cursor': '/tmp/cursor', 'agent': '/tmp/grok/agent'}.get(name)
        with patch.dict(os.environ, {}, clear=True), patch.object(W.shutil, 'which', side_effect=which_cursor_agent):
            with patch.object(W.os, 'access', return_value=False):
                self.assertEqual(W.resolve_cursor_bin(), '/tmp/cursor')
        # bundled Cursor beats generic agent
        def which_only_agent(name):
            return {'agent': '/tmp/grok/agent'}.get(name)
        with patch.dict(os.environ, {}, clear=True), patch.object(W.shutil, 'which', side_effect=which_only_agent):
            with patch.object(W.os, 'access', side_effect=lambda p, m: p == '/Applications/Cursor.app/Contents/Resources/app/bin/cursor'):
                self.assertEqual(W.resolve_cursor_bin(), '/Applications/Cursor.app/Contents/Resources/app/bin/cursor')
        # generic agent remains the last resort
        with patch.dict(os.environ, {}, clear=True), patch.object(W.shutil, 'which', side_effect=which_only_agent):
            with patch.object(W.os, 'access', return_value=False):
                self.assertEqual(W.resolve_cursor_bin(), '/tmp/grok/agent')
        # nothing found stays None
        with patch.dict(os.environ, {}, clear=True), patch.object(W.shutil, 'which', return_value=None):
            with patch.object(W.os, 'access', return_value=False):
                self.assertIsNone(W.resolve_cursor_bin())
        # argv shape follows the resolved binary name
        self.assertEqual(W.cursor_base_argv('/tmp/cursor-agent'), ['/tmp/cursor-agent'])
        self.assertEqual(W.cursor_base_argv('/tmp/grok/agent'), ['/tmp/grok/agent'])
        self.assertEqual(W.cursor_base_argv('/tmp/cursor'), ['/tmp/cursor', 'agent'])

    def test_legacy_muse_grok_regression(self):
        self.assertEqual(W.GROK_MODEL, 'grok-4.7-xhigh')
        self.assertEqual(W.GROK_BUILD_MODEL, 'grok-4.7')
        self.assertEqual(W.MUSE_MODEL, 'opencode-go/muse-spark-1.3-contributor')
        # legacy grok stays ask-only; trust stays cursor-only; steps stays muse-only
        ws = make_workspace()
        stubdir = pathlib.Path(tempfile.mkdtemp(prefix='stub-'))
        stub = stubdir / 'cursor-agent'
        write_stub(stub, CURSOR_STUB)
        run_dir = pathlib.Path(tempfile.mkdtemp(prefix='runs-')) / 'run1'
        r = invoke(['--workspace', str(ws), '--provider', 'grok', '--mode', 'work',
                    '--allow-path', 'owned.txt', '--run-dir', str(run_dir), 'x'],
                   env_extra={'SUBSCRIPTION_SQUAD_CURSOR_BIN': str(stub)})
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
