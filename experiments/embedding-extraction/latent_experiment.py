#!/usr/bin/env python3
"""
Latent Space Memory Experiment

Extracts fragments from memory shards, embeds them, clusters with HDBSCAN,
filters by coherence, and synthesizes insights.

Usage:
    python latent_experiment.py extract --passages 50
    python latent_experiment.py embed
    python latent_experiment.py cluster --min-cluster-size 5
    python latent_experiment.py synthesize --threshold 0.60
    python latent_experiment.py run --passages 50  # all steps
"""

import argparse
import asyncio
import json
import os
from datetime import datetime
from itertools import combinations
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import asyncpg
import httpx
import numpy as np
from numpy.typing import NDArray
from sklearn.cluster import HDBSCAN

# Configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "kp3"
DB_USER = "kp3"
DB_PASSWORD = "kp3"

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen3-embedding:4b"

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Default file paths
DEFAULT_FRAGMENTS_FILE = "fragments.json"
DEFAULT_EMBEDDED_FILE = "fragments_embedded.json"
DEFAULT_CLUSTERS_FILE = "clusters.json"
DEFAULT_OUTPUT_FILE = "experiment_output.md"

EXTRACTION_SYSTEM_PROMPT = """You are an AI agent recalling specific things you learned from a conversation. Not personality summaries - actual moments, facts, and realizations.

Extract across three dimensions:
- HUMAN: Specific observations about Mark from this conversation
- WORLD: Facts, tools, places, projects, constraints encountered
- SELF: What I learned about how to work with Mark

Format: Each fragment 5-12 words. Compress aggressively. One per line. No categories.

Use proper nouns (Mark, Kairix, San Francisco), never pronouns except "I" for self.

BAD (generic): "Mark expresses emotional vulnerability while maintaining determination"
GOOD (specific): "Mark surprised himself admitting isolation mid-sentence"

BAD (verbose): "Mark framed risk-taking as 'going on a limb' - he sees vulnerability as a literal exposure"
GOOD (compressed): "Mark frames vulnerability as literal exposure"

BAD (missing world): [no world facts extracted]
GOOD (world fact): "ElevenLabs offers phone number integration for voice"
GOOD (world fact): "Twilio can route calls to custom voice backends"
GOOD (world fact): "SF housing often skips income verification for credit-worthy renters"

BAD (missing self): [no agent learning extracted]
GOOD (self): "I should give Mark concrete steps when frustrated"
GOOD (self): "validating Mark's quick fixes helps him move forward"
GOOD (self): "I shifted from problem-solver to collaborator mid-conversation"
"""

SYNTHESIS_SYSTEM_PROMPT = """You are synthesizing a cluster of related observations into a single coherent insight.

These fragments emerged from an AI agent's reflections across many conversations. They clustered together because they share semantic meaning. Your job: distill what this cluster represents.

Output format:
- CONCEPT: 3-7 word label for what this cluster captures
- UNDERSTANDING: 2-3 sentences synthesizing the pattern, written from the agent's perspective ("I've learned...", "Mark tends to...", "When X happens...")
- CONFIDENCE: high/medium/low based on cluster coherence

If fragments don't actually cohere (noise cluster), output:
- CONCEPT: NOISE
- UNDERSTANDING: [skip]
- CONFIDENCE: low
"""


# =============================================================================
# Step 1: Extract
# =============================================================================


async def fetch_passages(n: int) -> list[dict]:
    """Sample N random memory_shard passages from KP3."""
    print(f"Fetching {n} random memory_shard passages...")
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    try:
        rows = await conn.fetch(
            """
            SELECT id::text, content
            FROM passages
            WHERE passage_type = 'memory_shard'
            ORDER BY random()
            LIMIT $1
            """,
            n,
        )
        return [{"id": row["id"], "content": row["content"]} for row in rows]
    finally:
        await conn.close()


async def extract_fragments_deepseek(
    client: httpx.AsyncClient,
    passage: dict,
    api_key: str,
) -> list[str]:
    """Extract fragments from a single passage via DeepSeek."""
    response = await client.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": passage["content"]},
            ],
            "temperature": 0.3,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    # Parse lines, filter empty
    fragments = [line.strip() for line in content.strip().split("\n") if line.strip()]
    # Remove any bullet markers
    fragments = [f.lstrip("- •").strip() for f in fragments]
    return [f for f in fragments if f]


async def cmd_extract(args: argparse.Namespace) -> None:
    """Extract fragments from passages."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        return

    # Fetch passages
    passages = await fetch_passages(args.passages)
    print(f"Fetched {len(passages)} passages")

    if not passages:
        print("No memory_shard passages found!")
        return

    # Extract fragments
    all_fragments = []
    async with httpx.AsyncClient() as client:
        for i, passage in enumerate(passages):
            print(f"Extracting passage {i + 1}/{len(passages)}...")
            try:
                fragments = await extract_fragments_deepseek(client, passage, api_key)
                for f in fragments:
                    all_fragments.append({
                        "text": f,
                        "source_passage_id": passage["id"],
                    })
            except Exception as e:
                print(f"  Error extracting from passage {passage['id']}: {e}")

    print(f"Extracted {len(all_fragments)} fragments")

    # Save
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(all_fragments, f, indent=2)
    print(f"Saved to {output_path}")


# =============================================================================
# Step 2: Embed
# =============================================================================


async def embed_fragment(
    client: httpx.AsyncClient,
    text: str,
) -> list[float]:
    """Embed a single fragment via Ollama."""
    response = await client.post(
        f"{OLLAMA_HOST}/api/embed",
        json={
            "model": OLLAMA_MODEL,
            "input": text,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


async def cmd_embed(args: argparse.Namespace) -> None:
    """Embed fragments."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run 'extract' first.")
        return

    with open(input_path) as f:
        fragments = json.load(f)

    print(f"Loaded {len(fragments)} fragments")

    async with httpx.AsyncClient() as client:
        for i, frag in enumerate(fragments):
            print(f"Embedding fragment {i + 1}/{len(fragments)}...")
            try:
                embedding = await embed_fragment(client, frag["text"])
                frag["embedding"] = embedding
            except Exception as e:
                print(f"  Error embedding fragment: {e}")
                frag["embedding"] = None

    # Filter out failed embeddings
    embedded = [f for f in fragments if f.get("embedding") is not None]
    print(f"Successfully embedded {len(embedded)}/{len(fragments)} fragments")

    # Save
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(embedded, f, indent=2)
    print(f"Saved to {output_path}")


# =============================================================================
# Step 3: Cluster
# =============================================================================


def compute_cluster_coherence(embeddings: NDArray[np.floating]) -> float:
    """Compute mean pairwise cosine similarity for a cluster."""
    if len(embeddings) < 2:
        return 1.0
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / (norms + 1e-10)
    # Compute pairwise cosine similarities
    similarities = []
    for i, j in combinations(range(len(embeddings)), 2):
        sim = np.dot(normalized[i], normalized[j])
        similarities.append(sim)
    return float(np.mean(similarities))


def cmd_cluster(args: argparse.Namespace) -> None:
    """Cluster embedded fragments."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run 'embed' first.")
        return

    with open(input_path) as f:
        fragments = json.load(f)

    print(f"Loaded {len(fragments)} embedded fragments")

    # Cluster
    print(f"Clustering with HDBSCAN (min_cluster_size={args.min_cluster_size}, "
          f"min_samples={args.min_samples}, metric={args.metric}, "
          f"method={args.cluster_selection_method})...")
    embeddings = np.array([f["embedding"] for f in fragments])
    clusterer = HDBSCAN(
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        metric=args.metric,
        cluster_selection_method=args.cluster_selection_method,
    )
    labels = clusterer.fit_predict(embeddings)

    # Group by cluster
    clusters: dict[int, list[dict]] = {}
    for frag, label in zip(fragments, labels):
        label_int = int(label)
        if label_int not in clusters:
            clusters[label_int] = []
        # Don't store embedding in cluster output (too large)
        clusters[label_int].append({
            "text": frag["text"],
            "source_passage_id": frag["source_passage_id"],
        })

    # Compute coherence
    cluster_data = {}
    for label, frags in clusters.items():
        # Get embeddings for this cluster
        indices = [i for i, l in enumerate(labels) if l == label]
        cluster_embeddings = embeddings[indices]
        coherence = compute_cluster_coherence(cluster_embeddings)

        cluster_data[str(label)] = {
            "fragments": frags,
            "coherence": coherence,
            "size": len(frags),
        }

        status = "noise" if label == -1 else f"coherence: {coherence:.3f}"
        print(f"  Cluster {label}: {len(frags)} fragments, {status}")

    # Summary
    n_clusters = len([l for l in clusters if l != -1])
    n_noise = len(clusters.get(-1, []))
    print(f"\nFound {n_clusters} clusters + {n_noise} noise points")

    # Save
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(cluster_data, f, indent=2)
    print(f"Saved to {output_path}")


# =============================================================================
# Step 4: Synthesize
# =============================================================================


async def synthesize_cluster(
    client: httpx.AsyncClient,
    fragments: list[dict],
    api_key: str,
) -> str:
    """Synthesize a cluster of fragments via DeepSeek."""
    fragment_text = "\n".join(f"- {f['text']}" for f in fragments)
    response = await client.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Fragments in this cluster:\n\n{fragment_text}"},
            ],
            "temperature": 0.3,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_markdown_output(
    clusters: dict[str, dict],
    threshold: float,
) -> str:
    """Generate markdown output."""
    # Count stats
    total_fragments = sum(c["size"] for c in clusters.values())
    n_clusters = len([l for l in clusters if l != "-1"])
    above_threshold = sum(
        1 for label, data in clusters.items()
        if label != "-1" and data["coherence"] >= threshold
    )

    lines = [
        "# Latent Space Memory Experiment",
        "",
        f"Date: {datetime.now().isoformat()}",
        f"Fragments: {total_fragments}",
        f"Clusters found: {n_clusters}",
        f"Clusters above threshold: {above_threshold}",
        "",
    ]

    # Qualifying clusters (sorted by coherence descending)
    qualifying = [
        (label, data)
        for label, data in clusters.items()
        if label != "-1" and data["coherence"] >= threshold
    ]
    qualifying.sort(key=lambda x: x[1]["coherence"], reverse=True)

    if qualifying:
        lines.append("## Cluster Results")
        lines.append("")
        for i, (label, data) in enumerate(qualifying, 1):
            coherence_flag = " (medium)" if data["coherence"] < 0.75 else ""
            lines.append(f"### Cluster {i} (coherence: {data['coherence']:.3f}){coherence_flag}")
            lines.append("")
            lines.append("**Fragments:**")
            for frag in data["fragments"]:
                lines.append(f"- {frag['text']}")
            lines.append("")
            if "synthesis" in data:
                lines.append("**Synthesis:**")
                lines.append(data["synthesis"])
                lines.append("")
            lines.append("---")
            lines.append("")

    # Noise/low-coherence clusters
    noise_clusters = [
        (label, data)
        for label, data in clusters.items()
        if label == "-1" or data["coherence"] < threshold
    ]
    if noise_clusters:
        lines.append(f"## Noise Clusters (coherence < {threshold:.2f})")
        lines.append("")
        for label, data in noise_clusters:
            cluster_name = "HDBSCAN Noise" if label == "-1" else f"Cluster {label}"
            lines.append(f"### {cluster_name} (coherence: {data['coherence']:.3f})")
            for frag in data["fragments"]:
                lines.append(f"- {frag['text']}")
            lines.append("")

    return "\n".join(lines)


async def cmd_synthesize(args: argparse.Namespace) -> None:
    """Synthesize qualifying clusters."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        return

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run 'cluster' first.")
        return

    with open(input_path) as f:
        clusters = json.load(f)

    # Find qualifying clusters
    qualifying = [
        (label, data)
        for label, data in clusters.items()
        if label != "-1" and data["coherence"] >= args.threshold
    ]

    print(f"Found {len(qualifying)} clusters above threshold {args.threshold}")

    # Synthesize
    async with httpx.AsyncClient() as client:
        for label, data in qualifying:
            print(f"Synthesizing cluster {label} (coherence: {data['coherence']:.3f})...")
            try:
                synthesis = await synthesize_cluster(client, data["fragments"], api_key)
                clusters[label]["synthesis"] = synthesis
            except Exception as e:
                print(f"  Error: {e}")
                clusters[label]["synthesis"] = f"Error: {e}"

    # Save updated clusters
    with open(input_path, "w") as f:
        json.dump(clusters, f, indent=2)

    # Generate markdown
    markdown = generate_markdown_output(clusters, args.threshold)
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        f.write(markdown)
    print(f"Saved to {output_path}")


# =============================================================================
# Run all steps
# =============================================================================


async def cmd_run(args: argparse.Namespace) -> None:
    """Run all steps in sequence."""
    # Extract
    print("\n=== Step 1: Extract ===\n")
    extract_args = argparse.Namespace(
        passages=args.passages,
        output=DEFAULT_FRAGMENTS_FILE,
    )
    await cmd_extract(extract_args)

    # Embed
    print("\n=== Step 2: Embed ===\n")
    embed_args = argparse.Namespace(
        input=DEFAULT_FRAGMENTS_FILE,
        output=DEFAULT_EMBEDDED_FILE,
    )
    await cmd_embed(embed_args)

    # Cluster
    print("\n=== Step 3: Cluster ===\n")
    cluster_args = argparse.Namespace(
        input=DEFAULT_EMBEDDED_FILE,
        output=DEFAULT_CLUSTERS_FILE,
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        metric=args.metric,
        cluster_selection_method=args.cluster_selection_method,
    )
    cmd_cluster(cluster_args)

    # Synthesize
    print("\n=== Step 4: Synthesize ===\n")
    synth_args = argparse.Namespace(
        input=DEFAULT_CLUSTERS_FILE,
        output=args.output,
        threshold=args.threshold,
    )
    await cmd_synthesize(synth_args)

    print(f"\n✓ Done! Results in {args.output}")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Latent Space Memory Experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  extract    Fetch passages and extract fragments via DeepSeek
  embed      Embed fragments via Ollama
  cluster    Cluster with HDBSCAN and compute coherence
  synthesize Synthesize qualifying clusters via DeepSeek
  run        Run all steps in sequence

Example:
  python latent_experiment.py extract --passages 50
  python latent_experiment.py embed
  python latent_experiment.py cluster --min-cluster-size 5
  python latent_experiment.py synthesize --threshold 0.65
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Extract
    p_extract = subparsers.add_parser("extract", help="Extract fragments from passages")
    p_extract.add_argument("-n", "--passages", type=int, default=50, help="Number of passages")
    p_extract.add_argument("-o", "--output", default=DEFAULT_FRAGMENTS_FILE, help="Output file")

    # Embed
    p_embed = subparsers.add_parser("embed", help="Embed fragments")
    p_embed.add_argument("-i", "--input", default=DEFAULT_FRAGMENTS_FILE, help="Input file")
    p_embed.add_argument("-o", "--output", default=DEFAULT_EMBEDDED_FILE, help="Output file")

    # Cluster
    p_cluster = subparsers.add_parser("cluster", help="Cluster embedded fragments")
    p_cluster.add_argument("-i", "--input", default=DEFAULT_EMBEDDED_FILE, help="Input file")
    p_cluster.add_argument("-o", "--output", default=DEFAULT_CLUSTERS_FILE, help="Output file")
    p_cluster.add_argument("--min-cluster-size", type=int, default=4, help="Min points to form cluster")
    p_cluster.add_argument("--min-samples", type=int, default=2, help="Min points in neighborhood")
    p_cluster.add_argument("--metric", default="cosine", help="Distance metric")
    p_cluster.add_argument("--cluster-selection-method", default="leaf", help="eom or leaf")

    # Synthesize
    p_synth = subparsers.add_parser("synthesize", help="Synthesize clusters")
    p_synth.add_argument("-i", "--input", default=DEFAULT_CLUSTERS_FILE, help="Input file")
    p_synth.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE, help="Output file")
    p_synth.add_argument("-t", "--threshold", type=float, default=0.60, help="Coherence threshold")

    # Run all
    p_run = subparsers.add_parser("run", help="Run all steps")
    p_run.add_argument("-n", "--passages", type=int, default=50, help="Number of passages")
    p_run.add_argument("-t", "--threshold", type=float, default=0.60, help="Coherence threshold")
    p_run.add_argument("--min-cluster-size", type=int, default=4, help="Min points to form cluster")
    p_run.add_argument("--min-samples", type=int, default=2, help="Min points in neighborhood")
    p_run.add_argument("--metric", default="cosine", help="Distance metric")
    p_run.add_argument("--cluster-selection-method", default="leaf", help="eom or leaf")
    p_run.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE, help="Output file")

    args = parser.parse_args()

    if args.command == "extract":
        asyncio.run(cmd_extract(args))
    elif args.command == "embed":
        asyncio.run(cmd_embed(args))
    elif args.command == "cluster":
        cmd_cluster(args)
    elif args.command == "synthesize":
        asyncio.run(cmd_synthesize(args))
    elif args.command == "run":
        asyncio.run(cmd_run(args))


if __name__ == "__main__":
    main()
