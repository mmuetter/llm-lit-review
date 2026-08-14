"""Run the multiverse screening: domain classification then the outcome grid.

Results append to JSONL after every call, so an interrupted run resumes by
skipping completed (pmid, model, task) cells.
"""

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from model_clients import build_clients
from prompts import DOMAIN_SCHEMA, OUTCOME_PROMPTS, OUTCOME_SCHEMA, domain_prompt, outcome_prompt
from sampling import build_sample, load_sample

RESULTS_DIR = Path(__file__).parent.parent / "data" / "screening_multiverse"
DOMAIN_TASK = "domain"
WORKERS_PER_CLIENT = 8
TARGET_PROGRESS_UPDATES = 20
BANNER_WIDTH = 72

STAGE_TITLES = {
    "domain": "STAGE 3 — DOMAIN CLASSIFICATION",
    "outcome": "STAGE 4 — OUTCOME GRID",
}


def log(message):
    """Write one progress line to stderr."""
    print(message, file=sys.stderr, flush=True)


def banner(title, subtitle):
    """Print a stage header block."""
    log("")
    log("=" * BANNER_WIDTH)
    log(f"  {title}")
    log(f"  {subtitle}")
    log("=" * BANNER_WIDTH)


def format_duration(seconds):
    """Render a duration as minutes and seconds."""
    if seconds < 90:
        return f"{seconds:.0f}s"
    return f"{seconds / 60:.1f}min"


class ProgressReporter:
    """Thread-safe per-model progress counter for one stage."""

    def __init__(self, label, model_totals):
        self.label = label
        self.model_totals = model_totals
        self.model_done = {name: 0 for name in model_totals}
        self.failures = {name: 0 for name in model_totals}
        self.started = time.monotonic()
        self.lock = threading.Lock()
        self.interval = max(1, sum(model_totals.values()) // TARGET_PROGRESS_UPDATES)

    @property
    def total(self):
        return sum(self.model_totals.values())

    @property
    def done(self):
        return sum(self.model_done.values())

    @property
    def failed(self):
        return sum(self.failures.values())

    def record(self, model, failed=False):
        """Register one completed unit and print progress periodically."""
        with self.lock:
            self.model_done[model] += 1
            self.failures[model] += failed
            if self.done % self.interval == 0 or self.done == self.total:
                log(self._progress_line())

    def _model_column(self, name):
        """Render one model's completion count, marking failures."""
        done, total = self.model_done[name], self.model_totals[name]
        failed = self.failures[name]
        return f"{name} {done}/{total}" + (f" ({failed} err)" if failed else "")

    def _progress_line(self):
        """Render the periodic progress line for this stage."""
        elapsed = time.monotonic() - self.started
        rate = self.done / elapsed if elapsed else 0
        remaining = (self.total - self.done) / rate if rate else 0
        columns = " | ".join(self._model_column(n) for n in self.model_totals)
        return (f"  [{self.label}] {columns} | {self.done}/{self.total} "
                f"({100 * self.done / self.total:.0f}%) {rate:.1f}/s "
                f"eta {format_duration(remaining)}")

    def summary(self):
        """Render the stage completion summary."""
        elapsed = time.monotonic() - self.started
        state = "complete" if not self.failed else f"complete with {self.failed} failures"
        return f"  ✓ {self.label} {state}: {self.done} calls in {format_duration(elapsed)}"


def checkpoint_path(stage):
    """Return the JSONL checkpoint path for a stage."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR / f"{stage}.jsonl"


def unit_key(record):
    """Return the identity of one work unit."""
    return (record["pmid"], record["model"], record["task"])


def load_completed(path):
    """Return the keys of cells that succeeded, so failures are retried."""
    if not path.exists():
        return set()
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {unit_key(r) for r in records if "result" in r}


def make_units(papers, client, tasks):
    """Build one work unit per paper and task for a single client."""
    return [{"pmid": p["pmid"], "model": client.name, "task": task, "paper": p}
            for p in papers for task in tasks]


def build_prompt(paper, task):
    """Render the prompt and schema for a work unit's task."""
    if task == DOMAIN_TASK:
        return domain_prompt(paper), DOMAIN_SCHEMA
    return outcome_prompt(paper, task), OUTCOME_SCHEMA


def execute_unit(unit, client, writer, progress):
    """Classify one unit and append the result to the checkpoint."""
    prompt, schema = build_prompt(unit["paper"], unit["task"])
    record = {"pmid": unit["pmid"], "model": unit["model"], "task": unit["task"]}
    try:
        record["result"] = client.classify(prompt, schema)
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
    writer(record)
    progress.record(unit["model"], failed="error" in record)


def make_writer(path, lock):
    """Return a thread-safe append-one-record-per-line writer."""
    def write(record):
        with lock, path.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
    return write


def run_client(units, client, writer, progress):
    """Run one client's units through its own thread pool."""
    with ThreadPoolExecutor(max_workers=WORKERS_PER_CLIENT) as pool:
        futures = [pool.submit(execute_unit, u, client, writer, progress) for u in units]
        for future in futures:
            future.result()


def pending_units(papers, clients, tasks, completed):
    """Return units for every client that are not already completed."""
    all_units = [u for client in clients for u in make_units(papers, client, tasks)]
    return [u for u in all_units if unit_key(u) not in completed]


def stage_subtitle(papers, tasks, units, completed_count):
    """Describe a stage's scope for the header banner."""
    resumed = f", {completed_count} already done" if completed_count else ""
    return (f"{len(papers)} papers x {len(tasks)} prompt(s) x 2 models "
            f"= {len(units)} calls pending{resumed}")


def run_stage(stage, papers, clients, tasks):
    """Run one stage across all clients in parallel, resuming if interrupted."""
    path = checkpoint_path(stage)
    completed = load_completed(path)
    units = pending_units(papers, clients, tasks, completed)
    banner(STAGE_TITLES[stage], stage_subtitle(papers, tasks, units, len(completed)))
    if not units:
        log("  ✓ nothing to do — already complete")
        return path
    dispatch_units(units, clients, path, stage)
    return path


def dispatch_units(units, clients, path, stage):
    """Run both arms concurrently and report progress until they finish."""
    totals = {c.name: sum(1 for u in units if u["model"] == c.name) for c in clients}
    progress = ProgressReporter(stage, totals)
    writer = make_writer(path, threading.Lock())
    with ThreadPoolExecutor(max_workers=len(clients)) as pool:
        per_client = [[u for u in units if u["model"] == c.name] for c in clients]
        list(pool.map(lambda pair: run_client(pair[0], pair[1], writer, progress),
                      zip(per_client, clients)))
    log(progress.summary())


def resolve_sample(size, reuse):
    """Load the saved sample or draw a fresh one of the requested size."""
    if reuse:
        papers, payload = load_sample()
        return papers[:size], payload
    return build_sample(size)


def parse_args():
    """Parse command-line options for the screening run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=25)
    parser.add_argument("--stage", choices=["domain", "outcome", "both"], default="both")
    parser.add_argument("--reuse-sample", action="store_true")
    return parser.parse_args()


def print_run_plan(papers, payload, stages):
    """Print the overall run plan before any calls are made."""
    banner("MULTIVERSE SCREENING RUN",
           f"{len(papers)} papers (drew {payload['n_drawn']}, seed {payload['seed']}) "
           f"| stages: {', '.join(stages)}")


def main():
    """Draw the sample and run the requested screening stages."""
    args = parse_args()
    papers, payload = resolve_sample(args.size, args.reuse_sample)
    stages = ["domain", "outcome"] if args.stage == "both" else [args.stage]
    print_run_plan(papers, payload, stages)
    clients = build_clients()
    started = time.monotonic()
    for stage in stages:
        tasks = [DOMAIN_TASK] if stage == "domain" else list(OUTCOME_PROMPTS)
        run_stage(stage, papers, clients, tasks)
    log(f"\nAll stages finished in {format_duration(time.monotonic() - started)}")


if __name__ == "__main__":
    main()
