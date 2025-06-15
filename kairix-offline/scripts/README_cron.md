# Conversation Ingestion Cron Job

This script provides automated daily ingestion of conversation data with dual storage to SQLite and Neo4j.

## Features

- Scans a configured directory for new conversation files (JSON, TXT, LOG)
- Stores raw conversation data in SQLite for efficient querying
- Processes conversations through the existing pipeline (chunking, summarization, embedding)
- Maintains compatibility with Neo4j for graph-based memory storage
- Idempotent processing - files are tracked by checksum to avoid reprocessing
- System broadcast alerts on Neo4j failures using `wall` command

## Configuration

Set these environment variables in your `.env` file:

```bash
# SQLite Database Configuration
SQLITE_DB_PATH="./data/conversations.db"

# Cron Job Configuration  
CHAT_LOGS_PATH="./data/chat_logs"
CRON_ENABLED="true"
```

## Usage

### Manual Execution
```bash
uv run python scripts/conversation_ingestion_cron.py
```

### Cron Schedule
Add to your crontab for daily execution at 2 AM:
```bash
0 2 * * * /usr/bin/env python /path/to/scripts/conversation_ingestion_cron.py
```

### Creating Test Data
```bash
uv run python scripts/create_sample_conversations.py
```

## Monitoring

The Gradio UI includes a "Cron Monitoring" tab that shows:
- Job history with status, file counts, and errors
- Manual "Run Job Now" button
- Real-time job output

Access via the mem-ui interface after starting:
```bash
uv run python src/kairix_offline/ui/mem_ui.py
```

## Database Schema

### SQLite Tables
- `conversations` - Raw conversation content and metadata
- `conversation_fragments` - Chunked conversation pieces  
- `summaries` - Generated summaries for each fragment
- `embeddings` - Vector embeddings (stored as packed binary)
- `cron_jobs` - Job execution history
- `processing_status` - Per-conversation processing state

### Data Flow
1. Scan directory for new files
2. Calculate checksum and check for duplicates
3. Store raw content in SQLite
4. Process through chunking → summarization → embedding pipeline
5. Store results in both SQLite and Neo4j
6. Track job status and any errors

## Error Handling

- Neo4j failures don't stop SQLite storage
- Failed files are tracked but don't stop the job
- System broadcast alerts on critical errors
- All errors logged to job history

## Testing

Run the integration tests:
```bash
uv run pytest tests/integration/test_conversation_ingestion_simple.py -v
```