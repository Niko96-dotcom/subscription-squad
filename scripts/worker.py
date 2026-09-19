#!/usr/bin/env python3
"""Bounded subscription-squad worker runner; receipts are evidence, not a filesystem sandbox."""
import argparse
import fcntl
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


MUSE_MODEL = "opencode-go/muse-spark-1.3-contributor"
MUSE_VARIANT = "xhigh"
GROK_MODEL = "cursor-grok-4.6-xhigh"
GROK_BUILD_MODEL = "grok-4.6"
GROK_BUILD_EFFORT = "xhigh"
ANTIGRAVITY_MODEL = "gemini-3.8-flash-high"
ANTIGRAVITY_EFFORT = "high"

# Exact inherited overrides/credentials filtered from provider subprocesses.
# Suffixes cover additional *_TOKEN / *_SECRET / *_API_KEY style credentials.
# Filtering is not a sandbox: unusual credential names and on-disk CLI config
# remain trusted. HOME/PATH/XDG and on-disk logins are preserved.
_CREDENTIAL_EXACT = frozenset({
    'OPENCODE_CONFIG_CONTENT', 'OPENCODE_CONFIG', 'OPENCODE_PERMISSION',
    'CURSOR_API_KEY', 'CURSOR_API_ENDPOINT',
    'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY',
    'XAI_API_KEY', 'GROQ_API_KEY', 'OPENROUTER_API_KEY',
    'OPENCODE_API_KEY', 'OPENCODE_GO_API_KEY',
    'GH_TOKEN', 'GITHUB_TOKEN',
    'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
})
_CREDENTIAL_SUFFIXES = ('_API_KEY', '_APIKEY', '_TOKEN', '_SECRET')


def sanitized_provider_env():
    """Shared filtered environment for preflight and worker subprocesses."""
    env = dict(os.environ)
    for key in list(env.keys()):
        upper = key.upper()
        if upper in _CREDENTIAL_EXACT or upper.endswith(_CREDENTIAL_SUFFIXES):
            env.pop(key, None)
    return env


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def git(workspace, *args):
    return subprocess.run(['git', '-C', str(workspace), *args], capture_output=True, timeout=30)


def snapshot(workspace, excluded):
    check = git(workspace, 'rev-parse', '--is-inside-work-tree')
    if check.returncode:
        raise ValueError('A Git workspace is required for protected-content evidence; use an isolated initialized fixture for other work.')
    names = git(workspace, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    if names.returncode:
        raise ValueError('could not enumerate workspace content')
    result = {}
    for name in sorted(set(os.fsdecode(v) for v in names.stdout.split(b'\0') if v)):
        p = workspace / name
        if excluded == p or excluded in p.parents:
            continue
        if p.is_symlink():
            result[name] = {'kind': 'symlink', 'hash': digest(os.fsencode(os.readlink(p)))}
        elif p.is_file():
            result[name] = {'kind': 'file', 'hash': digest(p.read_bytes()), 'mode': p.stat().st_mode & 0o777}
        elif not p.exists():
            result[name] = {'kind': 'missing'}
        elif p.is_dir():
            raise ValueError(f'nested tracked directory requires a separate worker workspace: {name}')
    return result


def index_snapshot(workspace):
    result = git(workspace, 'ls-files', '--stage', '-z')
    if result.returncode:
        raise ValueError('could not enumerate Git index')
    entries = {}
    for raw in result.stdout.split(b'\0'):
        if not raw:
            continue
        metadata, raw_name = raw.split(b'\t', 1)
        mode, blob, stage = metadata.decode('ascii').split()
        entries.setdefault(os.fsdecode(raw_name), []).append({'mode': mode, 'blob': blob, 'stage': stage})
    return entries


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2)+'\n')
    tmp.replace(path)


def stop_group(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass  # Record the failure even if the OS cannot reap a killed child promptly.


def interrupted(signum, frame):
    raise InterruptedError(f'received signal {signum}')


def preflight(command, timeout, env=None):
    if env is None:
        env = sanitized_provider_env()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True, env=env)
    try:
        raw, _ = proc.communicate(timeout=timeout)
        if proc.returncode:
            raise ValueError('preflight failed: '+raw.decode(errors='replace')[-2000:])
        return raw.decode(errors='replace')
    finally:
        stop_group(proc)


def resolve_opencode_bin():
    env = os.environ.get('SUBSCRIPTION_SQUAD_OPENCODE_BIN')
    if env:
        return env
    return shutil.which('opencode')


def resolve_cursor_bin():
    env = os.environ.get('SUBSCRIPTION_SQUAD_CURSOR_BIN')
    if env:
        return env
    # Prefer Cursor's unambiguous binary name. Grok Build also installs a
    # generic `agent` executable, so choosing `agent` first can silently query
    # the wrong provider inventory.
    found = shutil.which('cursor-agent')
    if found:
        return found
    bundled = '/Applications/Cursor.app/Contents/Resources/app/bin/cursor'
    if os.access(bundled, os.X_OK):
        return bundled
    found = shutil.which('cursor')
    if found:
        return found
    return shutil.which('agent')


def resolve_grok_build_bin():
    env = os.environ.get('SUBSCRIPTION_SQUAD_GROK_BUILD_BIN')
    if env:
        return env
    found = shutil.which('grok')
    if found:
        return found
    cand = os.path.expanduser('~/.grok/bin/grok')
    if os.access(cand, os.X_OK):
        return cand
    return None


def resolve_antigravity_bin():
    env = os.environ.get('SUBSCRIPTION_SQUAD_ANTIGRAVITY_BIN')
    if env:
        return env
    found = shutil.which('agy')
    if found:
        return found
    cand = os.path.expanduser('~/.local/bin/agy')
    if os.access(cand, os.X_OK):
        return cand
    return None


def cursor_base_argv(cursor_bin):
    name = Path(cursor_bin).name if cursor_bin else ''
    if name in ('agent', 'cursor-agent'):
        return [cursor_bin]
    return [cursor_bin, 'agent']


def extract_json_objects(text):
    objs = []
    dec = json.JSONDecoder()
    i = 0
    n = len(text)
    while i < n:
        lb = text.find('{', i)
        ls = text.find('[', i)
        cands = [x for x in (lb, ls) if x != -1]
        if not cands:
            break
        i = min(cands)
        try:
            obj, end = dec.raw_decode(text[i:])
            objs.append(obj)
            i += end
        except json.JSONDecodeError:
            i += 1
    return objs


_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')


def _terminal_json_dict(data):
    """Return the final top-level JSON dict that runs to end of stream.

    Noisy WARN/ERROR (possibly ANSI-colored) prefixes are ignored, but the
    candidate must extend to end-of-stream modulo whitespace/ANSI. This fails
    closed: an earlier valid JSON followed by non-JSON terminal garbage yields
    None instead of the earlier object.
    """
    text = data.decode(errors='replace') if isinstance(data, bytes) else data
    dec = json.JSONDecoder()
    starts = []
    pos = text.find('{')
    while pos != -1:
        starts.append(pos)
        pos = text.find('{', pos + 1)
    for start in reversed(starts):
        try:
            obj, end = dec.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        tail = text[start + end:]
        if _ANSI_RE.sub('', tail).strip() != '':
            continue
        if isinstance(obj, dict):
            return obj
        return None
    return None


def _scalar_model_reported(meta):
    """Only an explicit scalar model/modelID/model_id counts; never modelUsage."""
    for key in ('model', 'modelID', 'model_id'):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def muse_inventory_ok(text):
    return any(isinstance(item, dict)
               and item.get('id') == 'muse-spark-1.3-contributor'
               and item.get('providerID') == 'opencode-go'
               and isinstance(item.get('variants'), dict)
               and MUSE_VARIANT in item['variants']
               for item in extract_json_objects(text))


def grok_inventory_ok(text):
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == GROK_MODEL:
            return True
    return False


def grok_build_inventory_ok(text):
    for item in extract_json_objects(text):
        if isinstance(item, dict) and item.get('id') == GROK_BUILD_MODEL:
            return True
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == GROK_BUILD_MODEL:
            return True
    for tok in re.split(r'[\s,;|]+', text):
        if tok.strip('"\'`') == GROK_BUILD_MODEL:
            return True
    return False


def antigravity_inventory_ok(text):
    for item in extract_json_objects(text):
        if isinstance(item, dict) and item.get('id') == ANTIGRAVITY_MODEL:
            return True
        if isinstance(item, dict) and item.get('model') == ANTIGRAVITY_MODEL:
            return True
    for tok in re.split(r'[\s,;|]+', text):
        if tok.strip('"\'`') == ANTIGRAVITY_MODEL:
            return True
    return False


def build_opencode_config(mode, owned, steps=60):
    if mode == 'ask':
        edit_perm = 'deny'
        webfetch_perm = 'allow'
    else:
        edit_perm = {'*': 'deny'}
        for path in owned:
            edit_perm[str(path)] = 'allow'
            edit_perm[str(path) + '/*'] = 'allow'
        webfetch_perm = 'deny'
    perms = {
        '*': 'deny',
        'read': 'allow',
        'glob': 'allow',
        'grep': 'allow',
        'list': 'allow',
        'edit': edit_perm,
        'bash': 'deny',
        'task': 'deny',
        'external_directory': 'deny',
        'webfetch': webfetch_perm,
    }
    return {
        'model': MUSE_MODEL,
        'small_model': MUSE_MODEL,
        'enabled_providers': ['opencode-go'],
        'share': 'disabled',
        'permission': dict(perms),
        'agent': {
            'squad-worker': {
                'model': MUSE_MODEL,
                'steps': steps,
                'mode': 'primary',
                'permission': dict(perms),
            }
        },
        'default_agent': 'squad-worker',
    }


def build_final_prompt(user_prompt, mode, owned):
    base = user_prompt.rstrip()
    lines = [base, '', 'Fixed worker instructions: Do not delegate to other agents. Do not commit, install packages, or access or emit secrets. Respect ownership.']
    if mode == 'ask':
        lines.append('Allowed paths: none (ask mode permits no edits). Do not modify any files.')
    else:
        allowed = ', '.join(str(p) for p in owned)
        lines.append(f'Allowed paths: {allowed}. Only these owned files or dirs may change; do not modify any other content.')
    lines.append('You are not alone: preserve pre-existing and other workers edits. Batch relevant reads; make only the requested change. Do not expand the architecture or change acceptance criteria.')
    lines.append('Finish with a concise handoff in <=500 words. Your response MUST begin with exactly one of these four complete literal lines and nothing else on that line: `SQUAD_STATUS: complete`, `SQUAD_STATUS: partial`, `SQUAD_STATUS: blocked`, `SQUAD_STATUS: needs_context`. Complete means the assigned edits or analysis are delivered, not independently accepted. Then list changed files, checks actually run, remaining work, risks, and exact next action. If tools or steps run out, report partial and list unfinished requirements. Do not invent test results.')
    return '\n'.join(lines)


def parse_muse_output(data):
    text = data.decode(errors='replace') if isinstance(data, bytes) else data
    texts, steps, meta = [], [], {}
    previous_texts = []
    saw_error = False
    finished = False
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        part = event.get('part', {})
        if not isinstance(part, dict):
            part = {}
        if event.get('sessionID'):
            meta['sessionID'] = event['sessionID']
        if event.get('type') == 'error' or event.get('error') or event.get('is_error'):
            saw_error = True
        if event.get('type') == 'step_start':
            if texts:
                previous_texts = texts
            texts = []  # Only the final model step is the handoff; full stream stays in output.log.
        if event.get('type') == 'text':
            value = part.get('text', event.get('text', ''))
            if isinstance(value, str) and value.strip():
                texts.append(value)
        if event.get('type') == 'step_finish':
            steps.append({k: part[k] for k in ('tokens', 'cost', 'reason') if k in part})
            finished = part.get('reason') == 'stop'
    meta['step_count'] = len(steps)
    if steps:
        meta['usage'] = {'steps': steps}
    # An interrupted stream with some text must not become a successful candidate.
    return '\n'.join(texts or previous_texts).strip(), meta, saw_error or not finished


def parse_grok_output(data):
    text = data.decode(errors='replace') if isinstance(data, bytes) else data
    try:
        obj = json.loads(text)
    except ValueError:
        return '', {}, True
    if not isinstance(obj, dict) or obj.get('type') != 'result':
        return '', {}, True
    meta = {k: obj[k] for k in ('session_id', 'sessionID', 'sessionId', 'usage', 'model', 'request_id') if k in obj}
    result = obj.get('result', '')
    if not isinstance(result, str):
        result = ''
    return result.strip(), meta, bool(obj.get('is_error') or obj.get('error') or obj.get('subtype') != 'success' or not result.strip())


def parse_grok_build_output(data):
    obj = _terminal_json_dict(data)
    if not isinstance(obj, dict):
        return '', {}, True
    meta = {k: obj[k] for k in ('text', 'stopReason', 'sessionId', 'requestId', 'thought',
                                'usage', 'num_turns', 'total_cost_usd', 'modelUsage',
                                'model', 'session_id', 'request_id') if k in obj}
    if obj.get('error') or obj.get('is_error') or obj.get('errors'):
        return '', meta, True
    result = obj.get('text', '')
    if not isinstance(result, str):
        result = ''
    result = result.strip()
    if not result:
        return '', meta, True
    stop = obj.get('stopReason')
    if stop is None:
        return '', meta, True
    norm = str(stop).strip().lower()
    if norm not in ('stop', 'end_turn', 'completed', 'complete', 'success', 'done', 'finished', 'stop_sequence', 'end', 'ok'):
        return '', meta, True
    return result, meta, False


def parse_antigravity_output(data):
    obj = _terminal_json_dict(data)
    if not isinstance(obj, dict):
        return '', {}, True
    meta = {k: obj[k] for k in ('conversation_id', 'status', 'response', 'duration_seconds',
                                'num_turns', 'usage', 'denied_actions',
                                'conversationId', 'sessionId') if k in obj}
    if obj.get('error') or obj.get('is_error') or obj.get('errors'):
        return '', meta, True
    status = obj.get('status')
    if status is None or str(status).strip().lower() not in ('success', 'ok', 'completed', 'complete', 'done'):
        return '', meta, True
    denied = obj.get('denied_actions')
    if denied:
        if isinstance(denied, (list, dict, str)):
            if len(denied) > 0:
                return '', meta, True
        elif denied:
            return '', meta, True
    result = obj.get('response', '')
    if not isinstance(result, str):
        result = ''
    result = result.strip()
    if not result:
        return '', meta, True
    return result, meta, False


def classify_handoff(text, mode, step_count=0, step_budget=None):
    """Transport success is separate from worker-reported delivery and acceptance."""
    matches = list(re.finditer(r'^SQUAD_STATUS: (complete|partial|blocked|needs_context)[ \t]*$', text, re.M))
    if matches:
        text = text[matches[0].start():].strip()
        status = matches[0].group(1)
    else:
        status = 'unreported'
    capped = step_budget is not None and step_count >= step_budget
    limit_notice = not matches and bool(re.search(r'^(?:maximum|max) steps.{0,80}(?:reached|exhausted)', text.lstrip(), re.I))
    if capped or limit_notice:
        status = 'partial'
    return text, status, capped or limit_notice


def lock_path_for(workspace):
    h = hashlib.sha256(str(workspace).encode()).hexdigest()[:32]
    return Path(tempfile.gettempdir()) / f'subscription-squad-{h}.lock'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--provider', choices=['muse', 'grok', 'grok-build', 'antigravity'], required=True)
    parser.add_argument('--variant', default='xhigh')
    parser.add_argument('--steps', type=int, default=None, help='Muse model-step budget: 5..120; default 60; split broad work before increasing')
    parser.add_argument('--mode', choices=['ask', 'work'], default='ask')
    parser.add_argument('--prompt-file', type=Path)
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--check', action='store_true')
    trust = parser.add_mutually_exclusive_group()
    trust.add_argument('--trust', action='store_true', help='explicitly trust this workspace in Cursor')
    trust.add_argument('--no-trust', dest='trust', action='store_false')
    parser.set_defaults(trust=False)
    parser.add_argument('--timeout', type=float, default=900, help='total worker runtime seconds; default 900')
    parser.add_argument('--allow-path', action='append', default=[], help='owned relative file/directory; repeat; no other content may change')
    parser.add_argument('prompt', nargs='*')
    args = parser.parse_args(argv)
    if args.timeout <= 0 or not math.isfinite(args.timeout):
        parser.error('--timeout must be positive and finite')
    if args.steps is not None and not 5 <= args.steps <= 120:
        parser.error('--steps must be between 5 and 120')
    if args.steps is not None and args.provider != 'muse':
        parser.error('--steps applies only to Muse')
    step_budget = args.steps if args.steps is not None else 60
    if args.variant != 'xhigh':
        parser.error('only --variant xhigh is supported')
    workspace = args.workspace.expanduser().resolve(strict=True)
    if not workspace.is_dir():
        parser.error('workspace must be a directory')
    provider = args.provider
    if provider == 'muse':
        model_requested = MUSE_MODEL
        provider_variant = MUSE_VARIANT
        provider_effort = 'xhigh'
    elif provider == 'grok':
        model_requested = GROK_MODEL
        provider_variant = 'xhigh'
        provider_effort = 'xhigh'
    elif provider == 'grok-build':
        model_requested = GROK_BUILD_MODEL
        provider_variant = 'xhigh'
        provider_effort = GROK_BUILD_EFFORT
    else:
        model_requested = ANTIGRAVITY_MODEL
        provider_variant = ANTIGRAVITY_EFFORT
        provider_effort = ANTIGRAVITY_EFFORT
    if provider != 'grok' and args.trust:
        parser.error('--trust applies only to grok (Cursor) provider')
    if provider == 'grok' and args.mode == 'work':
        parser.error('grok provider supports ask mode only; implementation belongs to Muse')
    if provider == 'muse':
        opencode_bin = resolve_opencode_bin()
        if not opencode_bin or not os.access(opencode_bin, os.X_OK):
            parser.error('opencode CLI not found or not executable')
        if args.check:
            check_env = sanitized_provider_env()
            check_env['OPENCODE_CONFIG_CONTENT'] = json.dumps(build_opencode_config('ask', [], step_budget))
            raw = preflight([opencode_bin, 'models', 'opencode-go', '--verbose'], min(args.timeout, 30), env=check_env)
            if not muse_inventory_ok(raw):
                raise ValueError(f'exact Muse model variant is not available: {MUSE_MODEL} variant {MUSE_VARIANT}')
            print(f'subscription_squad_check=ok provider=muse model={MUSE_MODEL} variant={MUSE_VARIANT} bin={opencode_bin}')
            return 0
        cursor_bin = None
        grok_build_bin = None
        agy_bin = None
    elif provider == 'grok':
        cursor_bin = resolve_cursor_bin()
        if not cursor_bin or not os.access(cursor_bin, os.X_OK):
            parser.error('Cursor CLI (agent or cursor-agent) not found or not executable')
        if args.check:
            raw = preflight(cursor_base_argv(cursor_bin) + ['models'], min(args.timeout, 30))
            if not grok_inventory_ok(raw):
                raise ValueError(f'exact Grok model ID is not available: {GROK_MODEL}')
            print(f'subscription_squad_check=ok provider=grok model={GROK_MODEL} bin={cursor_bin}')
            return 0
        opencode_bin = None
        grok_build_bin = None
        agy_bin = None
    elif provider == 'grok-build':
        grok_build_bin = resolve_grok_build_bin()
        if not grok_build_bin or not os.access(grok_build_bin, os.X_OK):
            parser.error('Grok Build CLI (grok) not found or not executable')
        if args.check:
            raw = preflight([grok_build_bin, 'models'], min(args.timeout, 30))
            if not grok_build_inventory_ok(raw):
                raise ValueError(f'exact Grok Build model ID is not available: {GROK_BUILD_MODEL}')
            print(f'subscription_squad_check=ok provider=grok-build model={GROK_BUILD_MODEL} reasoning-effort={GROK_BUILD_EFFORT} bin={grok_build_bin}')
            return 0
        opencode_bin = None
        cursor_bin = None
        agy_bin = None
    else:
        agy_bin = resolve_antigravity_bin()
        if not agy_bin or not os.access(agy_bin, os.X_OK):
            parser.error('Antigravity CLI (agy) not found or not executable')
        if args.check:
            raw = preflight([agy_bin, 'models'], min(args.timeout, 30))
            if not antigravity_inventory_ok(raw):
                raise ValueError(f'exact Antigravity model ID is not available: {ANTIGRAVITY_MODEL}')
            print(f'subscription_squad_check=ok provider=antigravity model={ANTIGRAVITY_MODEL} effort={ANTIGRAVITY_EFFORT} bin={agy_bin}')
            return 0
        opencode_bin = None
        cursor_bin = None
        grok_build_bin = None
    root_check = git(workspace, 'rev-parse', '--show-toplevel')
    if root_check.returncode or Path(os.fsdecode(root_check.stdout).strip()).resolve() != workspace:
        parser.error('--workspace must be the Git checkout root')
    if args.prompt_file and args.prompt:
        parser.error('use only one prompt source')
    if args.prompt_file:
        prompt = args.prompt_file.read_text()
    elif args.prompt:
        prompt = ' '.join(args.prompt)
    elif sys.stdin.isatty():
        parser.error('prompt is required')
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        parser.error('prompt is empty')
    owned = []
    for raw in args.allow_path:
        rel = Path(raw)
        if any(c in raw for c in '*?['):
            parser.error('--allow-path must be literal, not a glob')
        if rel.is_absolute() or '..' in rel.parts or str(rel) in ('.', ''):
            parser.error('--allow-path must name a bounded workspace-relative file/directory')
        if '.git' in rel.parts:
            parser.error('Git internals cannot be an owned edit path')
        if not (workspace / rel).resolve().is_relative_to(workspace):
            parser.error('owned path escapes workspace')
        owned.append(rel)
    if args.mode == 'ask' and owned:
        parser.error('ask mode does not permit editing ownership')
    if args.mode == 'work' and not owned:
        parser.error('work mode requires --allow-path for its owned scope')
    if args.run_id and not args.run_dir:
        parser.error('--run-id requires --run-dir')
    if not args.run_dir:
        parser.error('--run-dir is required for worker runs and must be fresh and outside the workspace')
    run_arg = args.run_dir.expanduser().resolve()
    if run_arg == workspace or run_arg.is_relative_to(workspace) or workspace.is_relative_to(run_arg):
        parser.error('--run-dir must be fresh and outside the workspace')
    if run_arg.exists():
        parser.error('--run-dir must be fresh and must not already exist')
    run_arg.mkdir(parents=True, exist_ok=False, mode=0o700)
    run = run_arg.resolve()
    if run == workspace or run.is_relative_to(workspace) or workspace.is_relative_to(run):
        parser.error('--run-dir must be fresh and outside the workspace')
    lock_path = lock_path_for(workspace)
    lock_fh = open(lock_path, 'a+')
    try:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_fh.close()
            raise ValueError(f'another worker holds the workspace lock for {workspace} (parallel workers require separate workspaces)')
        before = snapshot(workspace, run)
        index_before = index_snapshot(workspace)
        atomic_json(run/'index-before.json', index_before)
        atomic_json(run/'before.json', before)
        status_before = digest(git(workspace, 'status', '--porcelain=v1', '-z').stdout)
        head_before = git(workspace, 'rev-parse', 'HEAD').stdout.decode().strip()
        provider_bin = {'muse': opencode_bin, 'grok': cursor_bin,
                        'grok-build': grok_build_bin, 'antigravity': agy_bin}[provider]
        receipt = {'schema': 'subscription-squad-worker-run/v1', 'run_id': args.run_id or run.name,
                   'workspace': str(workspace), 'provider': provider, 'provider_bin': provider_bin,
                   'model': model_requested,
                   'model_requested': model_requested, 'variant': provider_variant, 'effort': provider_effort,
                   'mode': args.mode,
                   'prompt_sha256': digest(build_final_prompt(prompt, args.mode, owned).encode()), 'started_at_utc': now(),
                   'owned_paths': [str(p) for p in owned], 'timeout_seconds': args.timeout, 'step_budget': step_budget if provider == 'muse' else None,
                   'trust': args.trust, 'status': 'running', 'git_status_before_sha256': status_before,
                   'head_before': head_before}
        atomic_json(run/'receipt.json', receipt)
        final_prompt = build_final_prompt(prompt, args.mode, owned)
        if provider == 'muse':
            command = [opencode_bin, 'run', '--pure', '--dir', str(workspace), '--model', MUSE_MODEL,
                       '--variant', 'xhigh', '--format', 'json', '--agent', 'squad-worker', final_prompt]
            child_env = sanitized_provider_env()
            child_env['OPENCODE_CONFIG_CONTENT'] = json.dumps(build_opencode_config(args.mode, owned, step_budget))
            child_cwd = None
        elif provider == 'grok':
            command = cursor_base_argv(cursor_bin) + ['--print', '--output-format', 'json', '--workspace', str(workspace), '--model', GROK_MODEL]
            if args.trust:
                command.append('--trust')
            if args.mode == 'ask':
                command += ['--mode', 'ask']
            command.append(final_prompt)
            child_env = sanitized_provider_env()
            child_cwd = None
        elif provider == 'grok-build':
            perm_mode = 'plan' if args.mode == 'ask' else 'acceptEdits'
            command = [grok_build_bin, '--cwd', str(workspace), '--model', GROK_BUILD_MODEL,
                       '--reasoning-effort', GROK_BUILD_EFFORT, '--permission-mode', perm_mode,
                       '--no-subagents', '--disable-web-search', '--output-format', 'json',
                       '--single', final_prompt]
            child_env = sanitized_provider_env()
            child_cwd = None
        else:
            agy_mode = 'plan' if args.mode == 'ask' else 'accept-edits'
            print_timeout = f'{int(args.timeout)}s'
            command = [agy_bin, '--output-format', 'json', '--model', ANTIGRAVITY_MODEL,
                       '--effort', ANTIGRAVITY_EFFORT, '--mode', agy_mode,
                       '--print-timeout', print_timeout, f'--print={final_prompt}']
            child_env = sanitized_provider_env()
            child_cwd = str(workspace)
        process = None
        started = time.monotonic()
        code = 1
        outcome = 'error'
        try:
            with (run/'output.log').open('wb') as output:
                process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, start_new_session=True, env=child_env,
                                           cwd=child_cwd)
                receipt['pid'] = process.pid
                atomic_json(run/'receipt.json', receipt)
                try:
                    code = process.wait(timeout=args.timeout)
                    outcome = 'candidate' if code == 0 else 'worker_failed'
                except subprocess.TimeoutExpired:
                    code, outcome = 124, 'timeout'
                except (InterruptedError, KeyboardInterrupt):
                    code, outcome = 130, 'interrupted'
                finally:
                    stop_group(process)
        except (OSError, InterruptedError, KeyboardInterrupt) as exc:
            receipt['error'] = str(exc)
            if isinstance(exc, (InterruptedError, KeyboardInterrupt)):
                code, outcome = 130, 'interrupted'
        finally:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                after = snapshot(workspace, run)
                atomic_json(run/'after.json', after)
                index_after = index_snapshot(workspace)
                atomic_json(run/'index-after.json', index_after)
                content_changed = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
                index_changed = {k for k in index_before.keys() | index_after.keys() if index_before.get(k) != index_after.get(k)}
                changed = sorted(content_changed | index_changed)
                outside = [k for k in changed if not any(Path(k) == p or p in Path(k).parents for p in owned)]
                head_after = git(workspace, 'rev-parse', 'HEAD').stdout.decode().strip()
                receipt.update(changed_paths=changed, index_changed_paths=sorted(index_changed), out_of_scope_paths=outside,
                               protected_content_unchanged=(not outside and not index_changed and head_after == head_before),
                               head_after=head_after,
                               git_status_after_sha256=digest(git(workspace, 'status', '--porcelain=v1', '-z').stdout))
                if outside or index_changed or head_after != head_before:
                    receipt['scope_violation'] = True
                    if index_changed:
                        receipt['index_violation'] = True
                    if code == 0:
                        code, outcome = 3, 'scope_violation'
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                receipt['preservation_error'] = str(exc)
                receipt['protected_content_unchanged'] = None
                if code == 0:
                    code, outcome = 3, 'unverified_preservation'
            try:
                raw_out = (run/'output.log').read_bytes() if (run/'output.log').exists() else b''
                if provider == 'muse':
                    result_text, native_meta, saw_error = parse_muse_output(raw_out)
                elif provider == 'grok':
                    result_text, native_meta, saw_error = parse_grok_output(raw_out)
                elif provider == 'grok-build':
                    result_text, native_meta, saw_error = parse_grok_build_output(raw_out)
                else:
                    result_text, native_meta, saw_error = parse_antigravity_output(raw_out)
                result_text, work_status, step_limit_reached = classify_handoff(result_text, args.mode, native_meta.get('step_count', 0), step_budget if provider == 'muse' else None)
                receipt.update(work_status=work_status, step_count=native_meta.get('step_count'), step_limit_reached=step_limit_reached)
                (run/'result.txt').write_text(result_text + ('' if (not result_text or result_text.endswith('\n')) else '\n'))
                model_reported = _scalar_model_reported(native_meta)
                session_native = (native_meta.get('sessionID') or native_meta.get('session_id') or native_meta.get('sessionId')
                                  or native_meta.get('session') or native_meta.get('conversation_id') or native_meta.get('conversationId'))
                usage_native = native_meta.get('usage') or native_meta.get('tokens') or native_meta.get('cost')
                # Record native metadata only when present; never fabricate.
                if model_reported is not None:
                    receipt['model_reported'] = model_reported
                else:
                    receipt['model_reported'] = None
                if session_native is not None:
                    receipt['session_native'] = session_native
                if usage_native is not None:
                    receipt['usage_native'] = usage_native
                receipt['native_meta'] = native_meta
                receipt['result_sha256'] = digest(result_text.encode())
                receipt['output_error_event'] = bool(saw_error)
                if code == 0 and (saw_error or not result_text.strip()):
                    receipt['empty_or_error_output'] = True
                    code, outcome = 1, 'worker_failed'
                    if saw_error:
                        receipt['error'] = receipt.get('error') or 'provider reported error event'
                    else:
                        receipt['error'] = receipt.get('error') or 'empty result from provider'
                if code == 0 and work_status in ('partial', 'blocked', 'needs_context'):
                    code, outcome = 4, 'incomplete'
            except OSError as exc:
                receipt['preservation_error'] = str(exc)
                if code == 0:
                    code, outcome = 3, 'unverified_preservation'
            receipt.update(status=outcome, exit_code=code, elapsed_seconds=round(time.monotonic()-started, 3), finished_at_utc=now())
            output = run/'output.log'
            receipt['output_sha256'] = digest(output.read_bytes()) if output.exists() else None
            atomic_json(run/'receipt.json', receipt)
            (run/'run.env').write_text('\n'.join(f'{k}={str(receipt.get(k, "")).lower() if isinstance(receipt.get(k), bool) else receipt.get(k, "")}' for k in ['provider', 'model', 'mode', 'run_id', 'exit_code', 'protected_content_unchanged'])+'\n')
            print(f'subscription_squad_run_dir={run}')
            print(json.dumps({'status': outcome, 'work_status': receipt.get('work_status'), 'step_count': receipt.get('step_count'), 'model': model_requested, 'changed_paths': receipt.get('changed_paths', []), 'elapsed_seconds': receipt.get('elapsed_seconds'), 'exit_code': code, 'receipt': str(run/'receipt.json'), 'result': str(run/'result.txt')}, separators=(',', ':')))
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_fh.close()
    except Exception:
        try:
            lock_fh.close()
        except OSError:
            pass
        raise
    return code if code >= 0 else 128-code


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired, InterruptedError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        raise SystemExit(2)
