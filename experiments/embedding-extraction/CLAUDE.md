# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a one-off experiment for extracting semantic fragments from memory shards, embedding them, clustering with HDBSCAN, and synthesizing insights from coherent clusters.

## Commands

```bash
# Install dependencies
uv sync

# Run experiment
uv run python latent_experiment.py --passages 100 --threshold 0.65 --output results.md

# Re-run clustering only (reuse extracted fragments)
uv run python latent_experiment.py --reuse-state

# Lint
uv run ruff check --fix && uv run ruff format
```

## Required Environment

- `DEEPSEEK_API_KEY` - API key for DeepSeek (extraction and synthesis)
- KP3 postgres running at localhost:5432 (database: kp3, user: kp3, password: kp3)
- Ollama running at localhost:11434 with `qwen3-embedding:4b` model

## Pipeline

1. Sample N random `memory_shard` passages from KP3
2. Extract 5-12 word fragments via DeepSeek (HUMAN/WORLD/SELF dimensions)
3. Embed each fragment via Ollama qwen3-embedding
4. Cluster with HDBSCAN (min_cluster_size=5)
5. Compute coherence (mean pairwise cosine similarity)
6. Synthesize clusters with coherence >= threshold via DeepSeek
7. Output markdown report

## Intermediate State

The script saves `{output}.state.json` with fragments and embeddings. Use `--reuse-state` to skip extraction/embedding and re-run clustering with different parameters.
