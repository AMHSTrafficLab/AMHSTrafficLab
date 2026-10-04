"""Run the classical and learned main matrices using an installed wheel."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time

import reproduction_support as common
from paper_statistics import aggregate

ROOT = Path(__file__).resolve().parent
CONTROLS = {'off': 'off', 'fixed_water_level_hold': 'hold', 'fixed_water_level_rebalance': 'rebalance'}


def select_runs(matrix, mode, cases=None, smoke_until=20):
    kinds = ['classical', 'learned'] if matrix == 'all' else [matrix]
    runs = []
    for kind in kinds:
        planned = common.plan(kind)
        expected_methods = ({'D', 'KD', 'CD', 'PFD', 'EDR', 'CBR'} if kind == 'classical'
                            else {'QLBWR', 'QECV', 'BRQ', 'NQ', 'DQN', 'GDQN', 'MAPPO'})
        keys = set()
        for r in planned:
            r.update(scene=r['labels']['scene'], method=r['profile']['method'],
                     control=CONTROLS[r['profile']['area_control_policy']], seed=r['profile']['seed'], speed=600)
            key = (r['scene'], r['method'], r['control'], r['seed'])
            if key in keys or r['until'] != 20000:
                raise ValueError('Duplicate case or changed formal horizon')
            keys.add(key)
        scenes = {'S100', 'S150', 'M175', 'M200', 'M225', 'L275', 'L300'}
        expected = {(s, m, c, z) for s in scenes for m in expected_methods
                    for c in CONTROLS.values() for z in range(10)}
        if keys != expected:
            raise ValueError(f'Formal matrix does not match the required Cartesian product: {kind}')
        runs.extend(planned)
    if mode == 'smoke':
        if cases:
            unknown = set(cases) - {r['case'] for r in runs}
            if unknown:
                raise ValueError(f'Unknown smoke cases: {sorted(unknown)}')
            runs = [r for r in runs if r['case'] in cases and r['seed'] == 0]
        else:
            # One case per method, cycling across all seven scenes and three modes.
            methods = list(dict.fromkeys(r['method'] for r in runs))
            scenes = ['S100', 'S150', 'M175', 'M200', 'M225', 'L275', 'L300']
            controls = ['off', 'hold', 'rebalance']
            runs = [next(r for r in runs if r['method'] == method and r['seed'] == 0
                         and r['scene'] == scenes[i % 7] and r['control'] == controls[i % 3])
                    for i, method in enumerate(methods)]
        runs = [dict(r, until=float(smoke_until)) for r in runs]
    return runs


def execute(run, output, provenance, resume, timeout, stop):
    directory = output / 'runs' / run['run_id']
    token = common.identity(dict(run=run, provenance=provenance))
    if resume:
        cached = common.valid_result(directory, token)
        if cached:
            return cached
    result = {key: run[key] for key in ('run_id', 'case', 'matrix', 'scene', 'method', 'control', 'seed', 'until')}
    result.update(identity=token, status='failed', output_hashes={})
    if stop.is_set():
        result['error'] = 'Interrupted before start'
        return result
    directory.mkdir(parents=True, exist_ok=True)
    attempt = directory / f'attempt-{time.time_ns()}'
    attempt.mkdir()
    profile = json.loads(json.dumps(run['profile']))
    profile.update(loop_cache_path=str(attempt / 'loops_cache.json'), log_path=str(attempt / 'simulation.log'))
    if 'pfd_cache_dir' in profile.get('routing_options', {}):
        profile['routing_options']['pfd_cache_dir'] = str(attempt / 'pfd-cache')
    common.write_json(attempt / 'profile.json', profile)
    common.write_json(attempt / 'request.json', dict(profile_path=str(attempt / 'profile.json'),
                                                   until=run['until'], speed=run['speed']))
    boot = "import runpy,sys; p=sys.argv.pop(1); runpy.run_path(p,run_name='__main__')"
    command = [sys.executable, '-I', '-c', boot, str(ROOT / 'matrix_worker.py'),
               str(attempt / 'request.json'), str(attempt / 'observed.json')]
    started = time.monotonic()
    try:
        with (attempt / 'console.log').open('w') as log:
            with subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT) as process:
                while process.poll() is None:
                    if stop.is_set() or (timeout is not None and time.monotonic() - started > timeout):
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        raise RuntimeError('Interrupted' if stop.is_set() else 'Run timed out')
                    stop.wait(0.2)
                if process.returncode:
                    raise RuntimeError(f'Worker exited with code {process.returncode}; see console.log')
        observed = json.loads((attempt / 'observed.json').read_text())
        if (not math.isfinite(observed['simulated_seconds']) or
                abs(observed['simulated_seconds'] - run['until']) > 1 / 30 + 1e-7):
            raise ValueError('Unexpected simulated horizon')
        for key in ('throughput_tasks_per_hour', 'gridlock_active_at_end'):
            if key not in observed['kpi_statistics']:
                raise ValueError(f'Missing required result field: {key}')
        if 'routing_call' not in observed['routing_performance']['metrics']:
            raise ValueError('Missing routing performance data')
        result.update(status='done', observed=observed)
        # Cache files are disposable; hash the effective profile, request, log and results.
        result['output_hashes'] = {str(p.relative_to(directory)): common.digest(p) for p in
                                  [attempt / name for name in ('profile.json', 'request.json', 'console.log', 'observed.json')]}
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        result['error'] = str(error)
    result['wall_seconds'] = time.monotonic() - started
    common.write_json(directory / 'result.json', result)
    print(f"{result['status']}: {run['run_id']}", flush=True)
    return result


def write_csv(path, rows):
    keys = sorted({key for row in rows for key in row})
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def summarize(output, runs, results, mode, matrix):
    common.write_json(output / 'results.json', results)
    rows = []
    for r in results:
        row = {k: r[k] for k in ('run_id', 'scene', 'method', 'control', 'seed', 'until', 'status')}
        if r['status'] == 'done':
            observed = r['observed']
            row['simulated_seconds'] = observed['simulated_seconds']
            row.update({f'kpi.{k}': v for k, v in observed['kpi_statistics'].items()
                        if v is None or isinstance(v, (str, int, float, bool))})
            row['routing_latency_ms'] = observed['routing_performance']['metrics']['routing_call']['mean_ms']
        rows.append(row)
    write_csv(output / 'runs.csv', rows)
    classification, aggregates = aggregate(results, formal=mode == 'full')
    write_csv(output / 'classification.csv', classification)
    write_csv(output / 'aggregate.csv', aggregates)
    complete = len(results) == len(runs) and all(r['status'] == 'done' for r in results)
    report = dict(mode=mode, matrix=matrix, planned_runs=len(runs), completed_runs=sum(r['status'] == 'done' for r in results),
                  execution_complete=complete, all_main_runs_complete=complete and mode == 'full' and matrix == 'all',
                  aggregation_complete=complete and all(r['aggregation_status'] == 'complete' for r in aggregates),
                  paper_results_compared=False,
                  note='Smoke runs check execution only. Learned-only runs lack Dijkstra CA references.')
    common.write_json(output / 'reproduction-report.json', report)
    print(json.dumps(report, indent=2))
    return 0 if complete else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['plan', 'smoke', 'full'], default='plan')
    parser.add_argument('--matrix', choices=['all', 'classical', 'learned'], default='all')
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--timeout', type=float)
    parser.add_argument('--smoke-until', type=float, default=20)
    parser.add_argument('--case', action='append', help='Exact case ID, repeatable, smoke only')
    args = parser.parse_args(argv)
    if args.workers < 1 or not math.isfinite(args.smoke_until) or args.smoke_until <= 0:
        parser.error('workers and smoke-until must be positive and finite')
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error('timeout must be positive and finite')
    if args.case and args.mode != 'smoke':
        parser.error('--case is only permitted in smoke mode')
    inputs = common.verify_manifest(ROOT / 'manifests/inputs.sha256')
    runs = select_runs(args.matrix, args.mode, args.case, args.smoke_until)
    if args.mode == 'plan':
        print(json.dumps(dict(mode='plan', expected_runs=len(runs), until=20000,
                             seeds=list(range(10)), matrices=args.matrix), indent=2))
        return 0
    if args.wheel is None:
        parser.error('--wheel is required for execution')
    if any(r['matrix'] == 'learned' for r in runs):
        inputs.update(common.verify_manifest(ROOT / 'manifests/checkpoints.sha256'))
    environment = common.wheel_environment(args.wheel.resolve())
    provenance = dict(environment=environment, inputs=inputs, workers=args.workers,
                      hardware=dict(cpu=platform.processor(), logical_cpus=os.cpu_count(), machine=platform.machine()),
                      scripts={p: common.digest(ROOT / p) for p in
                               ['reproduce_all.py', 'reproduction_support.py', 'matrix_worker.py', 'paper_statistics.py']})
    output = (args.output or ROOT / 'outputs' / f'{args.mode}-{args.matrix}').resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = dict(provenance=provenance, mode=args.mode, plan_identity=common.identity(runs))
    manifest_path = output / 'manifest.json'
    if manifest_path.exists():
        if not args.resume or json.loads(manifest_path.read_text()) != manifest:
            raise ValueError('Manifest mismatch or missing --resume; use a new output directory')
    elif any(output.iterdir()):
        raise ValueError('New output directory must be empty')
    common.write_json(manifest_path, manifest)
    common.write_json(output / 'plan.json', runs)
    write_csv(output / 'plan.csv', [{k: r[k] for k in
              ('run_id', 'scene', 'method', 'control', 'seed', 'until')} for r in runs])
    stop = threading.Event()
    pool = ThreadPoolExecutor(max_workers=args.workers)
    futures = [pool.submit(execute, r, output, provenance, args.resume, args.timeout, stop) for r in runs]
    results = []
    try:
        for future in as_completed(futures):
            results.append(future.result())
    except BaseException:
        stop.set()
        for future in futures:
            future.cancel()
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    order = {r['run_id']: i for i, r in enumerate(runs)}
    results.sort(key=lambda r: order[r['run_id']])
    return summarize(output, runs, results, args.mode, args.matrix)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('Interrupted. Completed cases are retained; repeat with --resume.', file=sys.stderr)
        raise SystemExit(130)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
