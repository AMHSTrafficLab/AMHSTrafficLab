"""Main-matrix DL/DE classification and aggregation (paper D.4.2-D.4.3)."""
import math
import statistics


def numeric(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def aggregate(results, *, formal):
    done = [r for r in results if r['status'] == 'done']
    ca = {}
    for r in done:
        if r['control'] == 'hold':
            ca.setdefault((r['scene'], r['method']), {})[r['seed']] = r['observed']['kpi_statistics']['throughput_tasks_per_hour']
    classifications, rows = [], []
    grouped = {}
    for r in results:
        grouped.setdefault((r['scene'], r['method'], r['control']), []).append(r)
    for (scene, method, control), group in sorted(grouped.items()):
        own, dijkstra = ca.get((scene, method), {}), ca.get((scene, 'D'), {})
        reference_ready = (formal and set(own) == set(range(10)) and set(dijkstra) == set(range(10))
                           and all(numeric(v) for v in [*own.values(), *dijkstra.values()]))
        survivors = []
        dl_count, de_count, classified = 0, 0, 0
        for r in group:
            record = dict(run_id=r['run_id'], scene=scene, method=method, control=control,
                          seed=r['seed'], status=r['status'], DL=None, DE=None, throughput_reference=None)
            if r['status'] == 'done':
                observed = r['observed']
                kpi = observed['kpi_statistics']
                record['DE'] = len(observed['deadlock_events']) > 0
                de_count += int(record['DE'])
                if reference_ready:
                    reference = max(own[r['seed']], dijkstra[r['seed']],
                                    statistics.median(own.values()), statistics.median(dijkstra.values()))
                    throughput = kpi['throughput_tasks_per_hour']
                    gridlock = kpi['gridlock_active_at_end']
                    if not numeric(throughput) or not isinstance(gridlock, bool):
                        raise ValueError('Invalid throughput or gridlock field')
                    record['throughput_reference'] = reference
                    record['DL'] = gridlock or throughput < reference / 2
                    classified += 1
                    dl_count += int(record['DL'])
                    if not record['DL']:
                        survivors.append(observed)
            classifications.append(record)
        complete = (len(group) == 10 and {r['seed'] for r in group} == set(range(10))
                    and all(r['status'] == 'done' for r in group))
        ready = complete and reference_ready and classified == 10
        row = dict(scene=scene, method=method, control=control, expected_seeds=10,
                   completed_seeds=sum(r['status'] == 'done' for r in group),
                   aggregation_status='complete' if ready else 'incomplete_or_smoke',
                   DE=de_count if complete else None, DL=dl_count if ready else None,
                   noncollapse_seeds=len(survivors) if ready else None)
        # Empty cells remain missing when all seeds collapse; no fabricated zeros.
        if ready and survivors:
            keys = set.intersection(*(set(o['kpi_statistics']) for o in survivors))
            for key in sorted(keys):
                values = [o['kpi_statistics'][key] for o in survivors]
                if all(numeric(v) for v in values):
                    row[f'mean.{key}'] = statistics.mean(values)
            latencies = [o['routing_performance']['metrics']['routing_call']['mean_ms'] for o in survivors]
            if all(numeric(v) for v in latencies):
                row['mean.routing_latency_ms'] = statistics.mean(latencies)
        rows.append(row)
    return classifications, rows
