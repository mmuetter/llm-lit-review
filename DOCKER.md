# Docker Setup for Reproducible Screening

This project uses Docker to ensure reproducible screening of paper abstracts using the Mistral API.

## Prerequisites

- Docker and Docker Compose installed
- Mistral API key saved to `~/.mistral_key`

## Setup

1. **Add your Mistral API key:**
   ```bash
   echo "your-mistral-api-key" > ~/.mistral_key
   ```

2. **Build the Docker image:**
   ```bash
   docker-compose build
   ```

## Running Screening

### Screen 100 papers:
```bash
docker-compose run screening python code/screen_100.py
```

### Screen all papers:
```bash
docker-compose run screening python code/screen_all.py
```

### Run Jupyter notebook (recommended for analysis):
```bash
docker-compose up jupyter
```

Then open `http://localhost:8888` in your browser. Token is printed in console output.

The notebook (`analysis.ipynb`) loads results and generates visualizations with full transparency.

## Outputs

Results are mounted to your local directories:
- `data/` — screening results, papers, metadata
- `figures/` — generated visualizations (PDFs)
- `report/` — analysis reports (markdown)

## Notes

- API key is mounted read-only from host
- All outputs persist locally even after container exits
- Delay between requests: 2-3 seconds (configurable in code)
- Mistral model: claude-large-latest, temperature 0.1
