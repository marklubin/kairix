#!/usr/bin/env python3
"""Run 25 fold iterations and output readable results."""

import asyncio
import json
import subprocess
import sys
from datetime import datetime

SHARDS = [
    "496f3f6d-525e-4c6e-a9fc-ccefe788b6ce",
    "00027682-810d-41de-b984-b31bef74b568",
    "0018409c-e8aa-4e3e-8a39-c5f37b87e0df",
    "004788b6-26ab-4637-ab28-bfe0d5c3a14b",
    "004b4a5c-50a5-4da4-8071-81beeaa0940e",
    "00583a93-01db-4b23-8dce-a962eeace0d1",
    "005a0794-bcd4-4f4a-9db7-1af16e2a90d6",
    "0090d372-41bd-4224-9eba-ed66f318ea78",
    "009dc65f-5b9b-4a45-ab74-966086eb0ea8",
    "00b76ed4-760c-4a67-b376-370e08db50a3",
]


def get_passage_content(shard_id: str) -> str:
    """Get passage content from database."""
    result = subprocess.run(
        ["ssh", "salinas",
         f"podman exec -i $(podman ps --filter name=postgres -q | head -1) psql -U kp3 -d kp3 -t -c \"SELECT content FROM passages WHERE id = '{shard_id}'\""],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_block_content(ref_name: str) -> str:
    """Get the current block content for a ref."""
    import re

    # Get passage ID for ref
    result = subprocess.run(
        ["uv", "run", "kp3", "sql", f"SELECT passage_id FROM passage_refs WHERE name = '{ref_name}'"],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if not output:
        return ""

    # Extract UUID from format like (UUID('abc-123'),)
    uuid_match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", output)
    if not uuid_match:
        return ""
    passage_id = uuid_match.group(0)

    # Get content via psql directly for cleaner output
    result = subprocess.run(
        ["ssh", "salinas",
         f"podman exec -i $(podman ps --filter name=postgres -q | head -1) psql -U kp3 -d kp3 -t -c \"SELECT content FROM passages WHERE id = '{passage_id}'\""],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def json_to_bullets(json_str: str, block_type: str) -> str:
    """Convert JSON block to bullet list format."""
    try:
        # Clean up the string - psql output has trailing + on each line
        lines = json_str.split('\n')
        cleaned_lines = [line.rstrip().rstrip('+').rstrip() for line in lines]
        json_str = '\n'.join(cleaned_lines).strip()

        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return f"[Parse error for {block_type}: {e}]"

    lines = []

    if block_type == "human":
        lines.append(f"**Narrative**: {data.get('narrative', 'N/A')[:500]}...")
        lines.append(f"**Life Context**: {data.get('current_life_context', 'N/A')}")
        lines.append(f"**Emotional Baseline**: {data.get('emotional_baseline', 'N/A')}")
        if data.get('core_values'):
            lines.append(f"**Core Values**: {', '.join(data['core_values'][:10])}")
        if data.get('open_threads'):
            lines.append("**Open Threads**:")
            for t in data['open_threads'][:5]:
                lines.append(f"  - {t}")

    elif block_type == "persona":
        lines.append(f"**Relationship Reflection**: {data.get('relationship_reflection', 'N/A')[:500]}...")
        lines.append(f"**Voice**: {data.get('voice', 'N/A')}")
        lines.append(f"**Stance**: {data.get('stance_toward_human', 'N/A')}")
        if data.get('learned_preferences'):
            lines.append("**Learned Preferences** (first 5):")
            for p in data['learned_preferences'][:5]:
                lines.append(f"  - {p}")

    elif block_type == "world":
        lines.append(f"**Version**: {data.get('version', 'N/A')}")
        if data.get('active_projects'):
            lines.append("**Active Projects**:")
            for p in data['active_projects']:
                name = p.get('name', 'Unknown')
                status = p.get('status', 'unknown')
                count = p.get('occurrence_count', 0)
                lines.append(f"  - {name} ({status}, seen {count}x)")
        else:
            lines.append("**Active Projects**: None")

        if data.get('key_entities'):
            lines.append("**Key Entities**:")
            for e in data['key_entities']:
                name = e.get('name', 'Unknown')
                count = e.get('occurrence_count', 0)
                lines.append(f"  - {name} (seen {count}x)")
        else:
            lines.append("**Key Entities**: None")

        if data.get('recurring_themes'):
            lines.append("**Recurring Themes**:")
            for t in data['recurring_themes']:
                name = t.get('name', 'Unknown')
                count = t.get('occurrence_count', 0)
                lines.append(f"  - {name} (seen {count}x)")
        else:
            lines.append("**Recurring Themes**: None")

        if data.get('key_insights'):
            lines.append("**Key Insights**:")
            for i in data['key_insights'][:3]:
                lines.append(f"  - {i[:150]}...")

    return "\n".join(lines)


def run_step(shard_id: str) -> str:
    """Run a world model step and return the log output."""
    result = subprocess.run(
        ["uv", "run", "kp3", "world-model", "step", shard_id,
         "--ref-prefix", "corindel", "--branch", "experiment-5"],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def main():
    output_file = "/Users/mark/kairix/kp3/fold_output_exp5.md"

    with open(output_file, "w") as f:
        # Header
        f.write("# World Model Fold Test - 10 Iterations (Natural Reflection)\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("Branch: corindel/experiment-5\n\n")

        # Prompts section
        f.write("---\n\n## PROMPTS\n\n")

        f.write("### Human Block\n")
        f.write("Focus on narrative understanding, core values, life context, emotional baseline, patterns, open threads.\n\n")

        f.write("### Persona Block\n")
        f.write("Focus on relationship reflection, voice, stance, learned preferences.\n\n")

        f.write("### World Block\n")
        f.write("**Conservative approach**: Only track MAJOR projects, CORE people, FOUNDATIONAL themes.\n")
        f.write("Default is to change nothing. Most passages = zero additions.\n\n")

        f.write("---\n\n## ITERATIONS\n\n")

        for i, shard_id in enumerate(SHARDS, 1):
            print(f"Processing {i}/25: {shard_id}")

            # Get input passage
            input_content = get_passage_content(shard_id)

            # Run the step
            log = run_step(shard_id)

            # Get resulting blocks
            human_content = get_block_content("corindel/human/experiment-5")
            persona_content = get_block_content("corindel/persona/experiment-5")
            world_content = get_block_content("corindel/world/experiment-5")

            # Write to file
            f.write(f"### Iteration {i}: {shard_id[:8]}...\n\n")

            f.write("**INPUT PASSAGE:**\n")
            f.write(f"> {input_content[:800]}{'...' if len(input_content) > 800 else ''}\n\n")

            f.write("**HUMAN BLOCK:**\n")
            f.write(json_to_bullets(human_content, "human"))
            f.write("\n\n")

            f.write("**PERSONA BLOCK:**\n")
            f.write(json_to_bullets(persona_content, "persona"))
            f.write("\n\n")

            f.write("**WORLD BLOCK:**\n")
            f.write(json_to_bullets(world_content, "world"))
            f.write("\n\n")

            f.write("---\n\n")
            f.flush()

    print(f"Done! Output in {output_file}")


if __name__ == "__main__":
    main()
