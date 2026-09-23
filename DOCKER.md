# Running the pipeline in Docker

The image pins the Python version and dependencies so the screening and
analysis scripts run the same way on any machine. Code is baked into the image;
`data/`, `figures/`, `report/` and the sibling `../supplementary/` are mounted,
so every output lands on the host and interrupted runs resume from the JSONL
checkpoints.

## Setup

1. Copy `.env.example` to `.env` and fill in the keys. Only the model
   calls need them (`MISTRAL_API_KEY` for Mistral, `ANTHROPIC_API_KEY` for
   Sonnet); enumeration, analysis and plotting need no keys.
2. Build the image:
   ```bash
   docker compose build
   ```

## Running

Every script runs from `code/` inside the container:

```bash
docker compose run --rm pipeline python synergy_gate.py      # enumerate and date the synerg* pool
docker compose run --rm pipeline python sampling.py          # draw the 1,000-paper sample
docker compose run --rm pipeline python run_sample.py mistral
docker compose run --rm pipeline python run_sample.py sonnet
docker compose run --rm pipeline python analyse_screening.py
docker compose run --rm pipeline python plot_results.py
```

The earlier term-score-stratified analysis is preserved at git tag
`stratified-v4` and in `archive/stratified_v4/`.

Omit the command for an interactive shell: `docker compose run --rm pipeline`.

## Notes

- Results append to `data/screening_v5/`, so a restarted run skips cells that
  already succeeded.
- `plot_results.py` and `export_prompts.py` write into `../supplementary/`,
  which must exist next to this folder.
- The Typst report (`report/automated_analysis.typ`) is not built in the
  container.
- Request pacing and retry limits live in `code/model_clients.py` and
  `code/wave_dispatch.py`.
