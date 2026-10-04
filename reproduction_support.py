"""Shared planning, hashing and installed-wheel verification helpers."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import zipfile

import yaml

ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def verify_manifest(path):
    entries = {}
    for line in path.read_text().splitlines():
        expected, relative = line.split('  ', 1)
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError(f'Missing or invalid input: {relative}')
        if relative in entries or digest(target) != expected:
            raise ValueError(f'Input checksum mismatch or duplicate: {relative}')
        entries[relative] = expected
    return entries


def render(value, labels):
    if isinstance(value, dict):
        return {key: render(item, labels) for key, item in value.items()}
    if isinstance(value, list):
        return [render(item, labels) for item in value]
    if isinstance(value, str):
        match = re.fullmatch(r'\{label\.([^}]+)\}', value)
        if match:
            return labels[match[1]]
        return re.sub(r'\{label\.([^}]+)\}', lambda m: str(labels[m[1]]), value)
    return value


def plan(matrix):
    spec = yaml.safe_load((ROOT / f'experiments/routing_{matrix}.yaml').read_text())
    base = json.loads((ROOT / spec['config_path']).read_text())
    axes = spec['matrix']
    runs = []
    for choices in itertools.product(*(axes['axes'][key] for key in axes['product'])):
        labels, profile = {}, dict(base)
        case = '__'.join(option['id'] for option in choices)
        for option in choices:
            labels.update(option['labels'])
            profile.update(option['params'])
        profile.update(spec['fixed'])
        for seed in spec['seeds']:
            params = render({**profile, 'seed': seed}, labels)
            runs.append(dict(run_id=f'{matrix}__{case}__seed-{seed}', case=case,
                             matrix=matrix, labels=labels, profile=params,
                             until=float(spec['run']['until'])))
    if len({r['run_id'] for r in runs}) != len(runs):
        raise ValueError('Duplicate run identifiers')
    return runs


def wheel_environment(wheel):
    # -I excludes the delivery directory and PYTHONPATH from import resolution.
    probe = '''import importlib.metadata as m, importlib.util as u, json, platform
d=m.distribution('amhslab')
print(json.dumps({'version':d.version,'location':str(d.locate_file('')),
'module':u.find_spec('amhslab').origin,'kernel':u.find_spec('model.AMHSSimulation').origin,
'python':platform.python_version(),'platform':platform.platform(),
'dependencies':sorted((x.metadata['Name'],x.version) for x in m.distributions())}))'''
    process = subprocess.run([sys.executable, '-I', '-c', probe], cwd=ROOT,
                             capture_output=True, text=True, check=True)
    facts = json.loads(process.stdout)
    location = Path(facts['location']).resolve()
    for name in ('module', 'kernel'):
        path = Path(facts[name]).resolve()
        if not path.is_relative_to(location):
            raise ValueError(f'{name} is not imported from the installed distribution')
    if not facts['kernel'].endswith('.so'):
        raise ValueError('A compiled Linux wheel is required; source imports are rejected')
    # Match installed payload to the supplied wheel, not just its version string.
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith('/') or name.endswith('.dist-info/RECORD'):
                continue
            if '.data/' in name:
                raise ValueError('Unsupported wheel data layout; update the verifier explicitly')
            target = location / name
            if not target.is_file() or digest(target) != hashlib.sha256(archive.read(name)).hexdigest():
                raise ValueError(f'Installed wheel content differs: {name}')
    subprocess.run([sys.executable, '-I', '-m', 'pip', 'check'], check=True)
    facts['wheel_sha256'] = digest(wheel)
    return facts


def valid_result(directory, token):
    try:
        result = json.loads((directory / 'result.json').read_text())
        if result['identity'] != token or result['status'] != 'done':
            return None
        for rel, expected in result['output_hashes'].items():
            if digest(directory / rel) != expected:
                return None
        if not result['output_hashes']:
            return None
        return result
    except (OSError, ValueError, KeyError):
        return None

