clean:
    rm -rf dist uv.lock .venv && uv cache clean
    
build: lint test
      uv build

test:
    uv run pytest --cov=src

lint: fix ruff 
      uv run ty src --pretty
ruff:
    uv run ruff check
fix:
    uv run ruff check --fix

add pkg:
      uv add {{pkg}}

add-dev pkg:
      uv add {{pkg}} --dev

install:
      uv sync

remove pkg:
      uv remove {{pkg}}
clear-source-documents:
      echo "MATCH (n:SourceDocument) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-agents:
      echo "MATCH (n:Agent) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-memory-shards:
      echo "MATCH (n:MemoryShard) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-summaries:
      echo "MATCH (n:Summary) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-embeddings:
      echo "MATCH (n:Embedding) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-neo4j: clear-embeddings clear-summaries clear-memory-shards clear-agents clear-source-documents
      echo "Neo4j cleared!"

mac-env:
    pwd && cp env/mac.env .env
default-env:
    cp env/default.env .env
