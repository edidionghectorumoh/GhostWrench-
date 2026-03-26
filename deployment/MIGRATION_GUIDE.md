# Linux Laptop Migration Guide

Quick guide for M.Res AI students migrating the Autonomous Field Engineer system to a local Linux laptop.

## Prerequisites

- Linux laptop (Ubuntu 22.04+ or similar)
- Docker and Docker Compose installed
- 8GB RAM minimum (16GB recommended)
- AWS account with Bedrock access
- Internet connection for AWS API calls

## One-Command Migration

### 1. Clone Repository

```bash
git clone <repository-url>
cd autonomous-field-engineer
```

### 2. Configure AWS Credentials

```bash
cp .env.example .env
nano .env  # Edit with your AWS credentials
```

Required variables:
```bash
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
```

### 3. Start System

```bash
docker-compose up -d
```

This single command:
- Starts Weaviate vector database with health checks
- Starts orchestration layer with resource limits
- Configures structured logging for agent reasoning
- Sets up persistent volumes for logs and checkpoints

### 4. Verify Deployment

```bash
# Quick smoke test (no API calls)
python smoke_test.py

# Full smoke test (includes Bedrock API calls)
python smoke_test.py --full
```

## Resource Management

The docker-compose.yml includes Linux-specific resource limits to keep your laptop responsive:

- **Weaviate**: Max 2 CPU cores, 2GB RAM
- **Orchestration**: Max 2 CPU cores, 4GB RAM

These limits prevent heavy RAG indexing from overwhelming your laptop.

## Observability

### Agent Reasoning Logs

View live Thought-Action-Observation loops:

```bash
# Tail live reasoning logs
tail -f logs/agent_thoughts.jsonl | jq .

# Filter by session
cat logs/agent_thoughts.jsonl | jq 'select(.session_id == "session-123")'

# Filter by agent type (diagnosis, action, guidance, judge)
cat logs/agent_thoughts.jsonl | jq 'select(.agent_type == "diagnosis")'
```

### Application Logs

```bash
# View orchestration logs
docker-compose logs -f orchestration

# View Weaviate logs
docker-compose logs -f weaviate
```

### Audit Trails

```bash
# Query audit database
sqlite3 audit_logs/judgments.db "SELECT * FROM judgments LIMIT 10;"
```

## Data Persistence

All data is persisted in local directories:

- `./audit_logs/` - Judge validation audit logs (SQLite)
- `./.checkpoints/` - Workflow state checkpoints
- `./logs/` - Agent reasoning logs (JSONL)
- Docker volume `weaviate_data` - Vector database

## Troubleshooting

### Weaviate Won't Start

```bash
# Check logs
docker-compose logs weaviate

# Restart service
docker-compose restart weaviate
```

### Out of Memory

If your laptop runs out of memory:

1. Reduce resource limits in `docker-compose.yml`
2. Close other applications
3. Consider upgrading RAM

### Bedrock Access Denied

1. Check AWS credentials in `.env`
2. Verify Bedrock model access in AWS console
3. Ensure region supports Bedrock (us-east-1 recommended)

### Smoke Test Fails

```bash
# Check environment variables
python smoke_test.py

# View detailed errors
docker-compose logs orchestration
```

## Development Workflow

### Making Changes

```bash
# Edit code
nano src/orchestration/OrchestrationLayer.py

# Restart orchestration service
docker-compose restart orchestration

# View logs
docker-compose logs -f orchestration
```

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run test suite
pytest tests/

# Run specific test
pytest tests/test_integration_workflows.py -v
```

### Debugging Agent Reasoning

The structured logs capture complete reasoning chains:

```bash
# Find all diagnosis decisions for a session
cat logs/agent_thoughts.jsonl | jq 'select(.session_id == "session-123" and .agent_type == "diagnosis")'

# Find all escalations
cat logs/agent_thoughts.jsonl | jq 'select(.action == "create_escalation")'

# Find safety violations
cat logs/agent_thoughts.jsonl | jq 'select(.action == "handle_safety_violation")'
```

## Performance Tips

### Optimize for Laptop

1. **Reduce Docker memory**: Edit resource limits in `docker-compose.yml`
2. **Disable validation during development**: Set `ENABLE_VALIDATION=false` in `.env`
3. **Use local cache**: Weaviate caches queries automatically
4. **Monitor resources**: Use `docker stats` to track usage

### Speed Up RAG Indexing

```bash
# Increase Weaviate resources temporarily
docker-compose down
# Edit docker-compose.yml: increase Weaviate memory to 4GB
docker-compose up -d
```

## Stopping the System

```bash
# Stop services (keeps data)
docker-compose stop

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove everything including data
docker-compose down -v
```

## Next Steps

1. **Index technical manuals**: Add equipment manuals to Weaviate
2. **Configure external systems**: Set up inventory/procurement clients
3. **Test workflows**: Run integration tests
4. **Customize agents**: Modify agent behavior in `src/agents/`

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Run smoke test: `python smoke_test.py`
3. Review troubleshooting section above
4. Check AWS Bedrock service status

## Architecture Notes

This system uses:
- **Cloud-based judge**: Amazon Bedrock (Nova Pro + Claude 3.5 Sonnet)
- **Local RAG**: Weaviate vector database
- **Structured logging**: JSON logs for agent reasoning
- **Persistent state**: Checkpoints for crash recovery

The cloud judge eliminates the need for local GPU resources while providing better accuracy and scalability.
