#!/usr/bin/env python3
"""Import CSV data into Neo4j using kairix-core models."""

import csv
import sys
from datetime import datetime

from neomodel import config, db

from kairix_core.types.neo4j import SourceDocument, Concept, Agent, Embedding, Summary, MemoryShard

config.DATABASE_URL = "bolt://neo4j:password@localhost:7687/kairix"
csv.field_size_limit(sys.maxsize)

def parse_value(value, type_func=str):
    """Generic parser for CSV values."""
    if not value or value == "":
        return None if type_func is not list else []
    try:
        if type_func is list:
            return [float(x.strip()) for x in value.strip("[]").split(",") if x.strip()]
        elif type_func == datetime:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return type_func(value)
    except Exception as e: # noqa
        return None if type_func is list else []

def main():
    csv_file = "/Users/mark/db.csv"
    print("Installing labels and importing...")
    
    db.install_all_labels()
    
    nodes = {}
    rels = []
    
    # Model mapping
    models = {
        "SourceDocument": lambda r: SourceDocument(
            uid=r["uid"], 
            source_label=r.get("source_label", ""),
            source_type=r.get("source_type", ""),
            content=r.get("content", "")
        ),
        "Agent": lambda r: Agent(name=r["name"]),
        "Concept": lambda r: Concept(
            name=r["name"],
            type=r["type"],
            embedding=parse_value(r.get("embedding", ""), list),
            encounters=[d for d in [parse_value(e, datetime) for e in r.get("encounters", "").strip("[]").split(",")] if d]
        ) if len(parse_value(r.get("embedding", ""), list)) == 128 else None,
        "Embedding": lambda r: Embedding(
            uid=r["uid"],
            embedding_model=r.get("embedding_model", ""),
            vector=parse_value(r.get("vector", ""), list)
        ) if len(parse_value(r.get("vector", ""), list)) == 768 else None,
        "Summary": lambda r: Summary(
            uid=r["uid"],
            summary_text=r.get("summary_text", ""),
            extractions_performed=r.get("extractions_performed", "").strip("[]").split(","),
            approximate_date=parse_value(r.get("approximate_date", ""), datetime)
        ),
        "MemoryShard": lambda r: MemoryShard(
            uid=r["uid"],
            shard_contents=r.get("shard_contents", ""),
            vector_address=parse_value(r.get("vector_address", ""), list),
            created_at=parse_value(r.get("created_at", ""), datetime)
        ) if len(parse_value(r.get("vector_address", ""), list)) == 768 else None,
    }
    
    with open(csv_file, "r") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i % 1000 == 0:
                print(f"Row {i}...")
            
            # Create nodes
            label = row.get("_labels", "").strip(":")
            if label in models and row.get("_id"):
                try:
                    node = models[label](row)
                    if node:
                        node.save()
                        nodes[row["_id"]] = node
                except Exception as e:
                    print(f"Error: {label} {row.get('_id')}: {e}")
            
            # Store relationships
            if all(row.get(k) for k in ["_start", "_end", "_type"]):
                rels.append(row)
    
    # Create relationships
    print(f"\nCreating {len(rels)} relationships...")
    for row in rels:
        try:
            start, end = nodes.get(row["_start"]), nodes.get(row["_end"])
            if start and end and row["_type"] == "semantic_linkage":
                rel = start.link.connect(end)
                rel.linkage_type = row.get("linkage_type", "related")
                rel.weight = int(row.get("weight", "1"))
                rel.observations = [d for d in [parse_value(o, datetime) for o in row.get("observations", "").strip("[]").split(",")] if d]
                if row.get("related_at"):
                    rel.related_at = parse_value(row["related_at"], datetime)
                rel.save()
        except Exception as e:
            print(f"Rel error: {e}")
    
    print("\nDone! Node counts:")
    results, meta = db.cypher_query("MATCH (n) RETURN labels(n)[0], count(n)")
    for label, count in results:
        print(f"  {label}: {count}")

if __name__ == "__main__":
    main()
