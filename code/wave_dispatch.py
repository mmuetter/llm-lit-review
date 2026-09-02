"""Wave-based dispatch: burst fast, retry only the stragglers at safer rates.

Each wave attempts every still-pending unit exactly once, at a fixed dispatch
interval. Whatever fails carries into the next, slower wave, rather than each
cell retrying independently and competing with fresh cells for the same
rate-limited queue.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from model_clients import MistralClient, RateLimiter
from run_screening import build_prompt, format_duration, log, make_writer

WAVE_INTERVALS_SECONDS = [0.5, 1.0, 2.0, 4.0]
WORKERS_PER_WAVE = 8


def attempt_unit(unit, client, writer):
    """Classify one unit once; return whether it failed."""
    prompt, schema = build_prompt(unit["paper"], unit["task"])
    record = {"pmid": unit["pmid"], "model": unit["model"], "task": unit["task"]}
    try:
        record["result"] = client.classify_once(prompt, schema)
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
    writer(record)
    return "error" in record


def run_wave(units, interval, writer):
    """Attempt every unit once at a fixed interval; return the ones that failed."""
    client = MistralClient()
    client.limiter = RateLimiter(interval)
    failed_lock = threading.Lock()
    failed = []

    def worker(unit):
        if attempt_unit(unit, client, writer):
            with failed_lock:
                failed.append(unit)

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=WORKERS_PER_WAVE) as pool:
        list(pool.map(worker, units))
    elapsed = format_duration(time.monotonic() - started)
    log(f"  wave @ {interval}s: {len(units) - len(failed)}/{len(units)} succeeded "
        f"in {elapsed} ({len(failed)} to retry)")
    return failed


def dispatch_waves(units, path):
    """Run all waves in sequence, retrying only what the previous wave missed."""
    writer = make_writer(path, threading.Lock())
    pending = units
    for interval in WAVE_INTERVALS_SECONDS:
        if not pending:
            break
        log(f"[wave dispatch] {len(pending)} units @ {interval}s spacing")
        pending = run_wave(pending, interval, writer)
    if pending:
        log(f"  {len(pending)} units failed after all waves")
    return len(units) - len(pending)
