"""Version-bound matrix worker using only the installed compiled wheel."""
import json
import math
from pathlib import Path
import sys
import time


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, 'item'):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main():
    from amhslab.config import load_profile
    import model.AMHSSimulation as kernel
    if not kernel.__file__.endswith('.so'):
        raise RuntimeError('Compiled wheel required')
    request = json.loads(Path(sys.argv[1]).read_text())
    profile, report = load_profile(request['profile_path'])
    if profile is None:
        raise ValueError(report.render())
    started = time.monotonic()
    sim = kernel.AMHSSimulation(**profile)
    try:
        total = math.ceil(request['until'] / sim.dt)
        completed = 0
        while completed < total:
            count = min(request['speed'], total - completed)
            sim.run(count)
            completed += count
        if sim.frame_count != total or abs(sim.now - request['until']) > sim.dt + 1e-7:
            raise RuntimeError('Simulation did not reach the requested horizon')
        wall = time.monotonic() - started
        result = dict(simulated_seconds=float(sim.now), frames=sim.frame_count,
                      wall_seconds=wall, kpi_statistics=sim.amhs.kpi_statistics(now_time=sim.now),
                      experiment_report=sim.amhs.experiment_report(now_time=sim.now),
                      deadlock_events=list(sim.amhs.deadlock_log),
                      routing_performance=sim.amhs.routing_performance.snapshot(
                          simulated_seconds=float(sim.now), wall_seconds=wall),
                      router_diagnostics=sim.amhs.router.get_diagnostics())
        Path(sys.argv[2]).write_text(json.dumps(clean(result), indent=2, allow_nan=False) + '\n')
    finally:
        sim.amhs.router.close()


if __name__ == '__main__':
    main()
