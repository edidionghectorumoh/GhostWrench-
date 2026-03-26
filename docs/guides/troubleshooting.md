# Troubleshooting Guide

Common issues and solutions for the Autonomous Field Engineer system.

## Table of Contents

- [Deployment Issues](#deployment-issues)
- [Weaviate Issues](#weaviate-issues)
- [AWS Bedrock Issues](#aws-bedrock-issues)
- [Agent Issues](#agent-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)

## Deployment Issues

### Docker Compose Won't Start

**Symptoms:**
- `docker-compose up` fails
- Services won't start
- Port conflicts

**Solutions:**

1. **Check Docker is running:**
```bash
docker ps
# If error, start Docker Desktop or Docker daemon
```

2. **Check port availability:**
```bash
# Check if ports 8000 or 8080 are in use
netstat -an | grep 8000
netstat -an | grep 8080

# Kill processes using these ports or change ports in docker-compose.yml
```

3. **Clean up old containers:**
```bash
docker-compose down -v
docker system prune -a
docker-compose up -d
```

4. **Check logs:**
```bash
docker-compose logs
```

### Services Keep Restarting

**Symptoms:**
- Containers restart repeatedly
- Health checks failing

**Solutions:**

1. **Check resource limits:**
```bash
# View resource usage
docker stats

# If out of memory, increase Docker memory allocation
# Docker Desktop: Settings > Resources > Memory
```

2. **Check health check logs:**
```bash
docker-compose logs orchestration
docker-compose logs weaviate
```

3. **Verify dependencies:**
```bash
# Ensure Weaviate is healthy before orchestration starts
docker-compose ps
```

### Environment Variables Not Loading

**Symptoms:**
- AWS credentials not found
- Configuration errors

**Solutions:**

1. **Verify .env file exists:**
```bash
ls -la .env
```

2. **Check .env format:**
```bash
# Correct format (no spaces around =)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Incorrect format
AWS_ACCESS_KEY_ID = your_key  # ❌ spaces
```

3. **Restart services after .env changes:**
```bash
docker-compose down
docker-compose up -d
```

## Weaviate Issues

### Cannot Connect to Weaviate

**Symptoms:**
- Connection refused errors
- Timeout errors
- RAG system failures

**Solutions:**

1. **Check Weaviate is running:**
```bash
docker-compose ps weaviate
curl http://localhost:8080/v1/.well-known/ready
```

2. **Check Weaviate logs:**
```bash
docker-compose logs weaviate
```

3. **Restart Weaviate:**
```bash
docker-compose restart weaviate
```

4. **Verify network connectivity:**
```bash
# From orchestration container
docker-compose exec orchestration ping weaviate
```

### Schema Not Created

**Symptoms:**
- No classes in Weaviate
- Manual ingestion fails
- Empty search results

**Solutions:**

1. **Check schema:**
```python
from src.rag.RAGSystem import RAGSystem

rag = RAGSystem(weaviate_url="http://localhost:8080")
schema = rag.get_schema_info()
print(schema)
```

2. **Recreate schema:**
```python
# Delete and recreate
rag.delete_schema()
rag.create_schema()
```

3. **Verify Weaviate version:**
```bash
curl http://localhost:8080/v1/meta
```

### Search Returns No Results

**Symptoms:**
- Empty search results
- Low relevance scores
- Missing manuals

**Solutions:**

1. **Verify data is ingested:**
```python
stats = rag.get_statistics()
print(f"Total objects: {stats['total_objects']}")
```

2. **Test with exact match:**
```python
# Try exact equipment type
results = rag.retrieve_relevant_sections(
    query="power supply",
    equipment_type="network_switch",  # Exact match
    limit=10
)
```

3. **Check embeddings:**
```bash
# Verify CLIP model is loaded
docker-compose logs orchestration | grep "CLIP"
```

4. **Re-index data:**
```bash
python scripts/reindex_manuals.py
```

## AWS Bedrock Issues

### Access Denied Errors

**Symptoms:**
- `AccessDeniedException` errors
- Model not available errors
- Authentication failures

**Solutions:**

1. **Verify AWS credentials:**
```bash
# Test credentials
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "...",
#     "Account": "123456789012",
#     "Arn": "..."
# }
```

2. **Check Bedrock model access:**
```bash
# List available models
aws bedrock list-foundation-models --region us-east-1

# Check specific model
aws bedrock get-foundation-model \
  --model-identifier amazon.nova-pro-v1:0 \
  --region us-east-1
```

3. **Enable models in AWS Console:**
- Go to AWS Bedrock console
- Navigate to "Model access"
- Request access for: Nova Pro, Nova Act, Claude 3.5 Sonnet

4. **Verify IAM permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*"
      ]
    }
  ]
}
```

### Rate Limiting Errors

**Symptoms:**
- `ThrottlingException` errors
- Slow responses
- Timeouts

**Solutions:**

1. **Implement exponential backoff:**
```python
# Already implemented in agents
# Check retry configuration in config.py
```

2. **Request quota increase:**
- AWS Console > Service Quotas
- Search for "Bedrock"
- Request increase for model invocations

3. **Reduce concurrent requests:**
```yaml
# In docker-compose.yml
orchestration:
  deploy:
    replicas: 1  # Reduce replicas
```

### Model Response Errors

**Symptoms:**
- Invalid JSON responses
- Parsing errors
- Unexpected output format

**Solutions:**

1. **Check model version:**
```python
# Verify model ID in config.py
NOVA_PRO_MODEL_ID = "amazon.nova-pro-v1:0"
```

2. **Validate request format:**
```python
# Check request body matches model requirements
# See AWS Bedrock documentation for model-specific formats
```

3. **Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Agent Issues

### Diagnosis Agent Failures

**Symptoms:**
- Low confidence scores
- Incorrect diagnoses
- Image analysis errors

**Solutions:**

1. **Check image quality:**
```python
# Verify image is valid
from PIL import Image
img = Image.open("test_image.jpg")
print(f"Size: {img.size}, Format: {img.format}")
```

2. **Test with reference images:**
```bash
# Use known good images from test suite
python -m pytest tests/test_integration_workflows.py::TestHappyPathWorkflow::test_diagnosis_phase -v
```

3. **Check RAG system:**
```python
# Verify manuals are available
results = rag.retrieve_relevant_sections(
    query="network switch",
    limit=5
)
print(f"Found {len(results)} results")
```

4. **Review thought logs:**
```bash
# Check agent reasoning
cat logs/agent_thoughts.jsonl | jq 'select(.agent_type == "diagnosis")'
```

### Procurement Agent Failures

**Symptoms:**
- Parts not found
- Inventory errors
- Cost calculation errors

**Solutions:**

1. **Check inventory client:**
```python
from src.external import MockInventoryClient

client = MockInventoryClient()
parts = client.search_parts("network switch")
print(f"Found {len(parts)} parts")
```

2. **Verify part numbers:**
```python
# Check part number format
part = client.get_part_details("PART-001")
print(part)
```

3. **Test cost calculation:**
```python
# Verify cost calculation logic
total = sum(part['cost'] for part in parts)
print(f"Total cost: ${total:.2f}")
```

### Guidance Agent Failures

**Symptoms:**
- No repair steps generated
- Incomplete guidance
- Safety check failures

**Solutions:**

1. **Check diagnosis state:**
```python
# Verify diagnosis completed
workflow_state = orchestration.get_workflow_state(session_id)
print(f"Diagnosis: {workflow_state.diagnosis_state}")
```

2. **Test guidance generation:**
```python
from src.agents.GuidanceAgent import GuidanceAgent

agent = GuidanceAgent()
guidance = agent.generate_guidance(request)
print(f"Steps: {len(guidance['steps'])}")
```

3. **Review safety checks:**
```bash
# Check safety checker logs
cat logs/agent_thoughts.jsonl | jq 'select(.action == "validate_safety")'
```

## Performance Issues

### Slow Diagnosis

**Symptoms:**
- Diagnosis takes > 30 seconds
- Timeouts
- High latency

**Solutions:**

1. **Check network latency:**
```bash
# Test AWS Bedrock latency
time aws bedrock invoke-model \
  --model-id amazon.nova-pro-v1:0 \
  --body '{"messages":[{"role":"user","content":[{"text":"test"}]}]}' \
  --region us-east-1 \
  output.json
```

2. **Optimize image size:**
```python
# Compress images before upload
from PIL import Image

img = Image.open("large_image.jpg")
img.thumbnail((2048, 1536))
img.save("compressed_image.jpg", quality=85)
```

3. **Enable caching:**
```python
# Check cache configuration
# Weaviate caches queries automatically
```

4. **Monitor resource usage:**
```bash
docker stats
```

### High Memory Usage

**Symptoms:**
- Out of memory errors
- System slowdown
- Container crashes

**Solutions:**

1. **Check memory limits:**
```yaml
# In docker-compose.yml
services:
  orchestration:
    deploy:
      resources:
        limits:
          memory: 4G  # Increase if needed
```

2. **Monitor memory usage:**
```bash
docker stats --no-stream
```

3. **Reduce batch sizes:**
```python
# Process fewer items at once
BATCH_SIZE = 10  # Reduce from 100
```

4. **Clear caches:**
```bash
# Restart services to clear memory
docker-compose restart
```

### Slow RAG Queries

**Symptoms:**
- Manual search takes > 5 seconds
- Timeout errors
- High CPU usage

**Solutions:**

1. **Check index size:**
```python
stats = rag.get_statistics()
print(f"Objects: {stats['total_objects']}")
```

2. **Optimize HNSW parameters:**
```python
# Tune for your data size
# See Weaviate documentation
```

3. **Use query caching:**
```python
# Already implemented with 1-hour TTL
# Check cache hit rate in logs
```

4. **Reduce result limit:**
```python
# Request fewer results
results = rag.retrieve_relevant_sections(
    query="...",
    limit=5  # Reduce from 10
)
```

## Data Issues

### Checkpoint Corruption

**Symptoms:**
- Cannot resume workflow
- State loading errors
- Data inconsistency

**Solutions:**

1. **Check checkpoint files:**
```bash
ls -lh .checkpoints/
```

2. **Validate checkpoint:**
```python
import json

with open('.checkpoints/session-123.json') as f:
    checkpoint = json.load(f)
    print(f"Valid: {checkpoint.get('session_id')}")
```

3. **Delete corrupted checkpoint:**
```bash
rm .checkpoints/session-123.json
```

4. **Restart workflow:**
```python
# Create new session
response = orchestration.process_field_request(request)
```

### Audit Log Issues

**Symptoms:**
- Missing audit entries
- Database locked errors
- Query failures

**Solutions:**

1. **Check database:**
```bash
sqlite3 audit_logs/judgments.db "SELECT COUNT(*) FROM judgments;"
```

2. **Verify permissions:**
```bash
ls -l audit_logs/judgments.db
chmod 644 audit_logs/judgments.db
```

3. **Backup and recreate:**
```bash
cp audit_logs/judgments.db audit_logs/judgments.db.backup
rm audit_logs/judgments.db
# Database will be recreated on next write
```

### Thought Log Issues

**Symptoms:**
- No reasoning logs
- Malformed JSON
- Missing entries

**Solutions:**

1. **Check log file:**
```bash
tail -f logs/agent_thoughts.jsonl
```

2. **Validate JSON:**
```bash
cat logs/agent_thoughts.jsonl | jq . > /dev/null
# If error, find malformed line
```

3. **Enable logging:**
```bash
# In .env
ENABLE_THOUGHT_LOGGING=true
```

4. **Check permissions:**
```bash
ls -l logs/agent_thoughts.jsonl
chmod 644 logs/agent_thoughts.jsonl
```

## Getting Help

### Diagnostic Information

When reporting issues, include:

1. **System information:**
```bash
python smoke_test.py > diagnostic.txt 2>&1
```

2. **Logs:**
```bash
docker-compose logs > docker-logs.txt
```

3. **Configuration:**
```bash
# Sanitize .env (remove credentials)
cat .env | sed 's/=.*/=***/' > config.txt
```

4. **Version information:**
```bash
docker-compose version
python --version
aws --version
```

### Support Channels

- GitHub Issues: https://github.com/your-repo/issues
- Email: support@example.com
- Documentation: https://docs.example.com
- Slack: #afe-support

### Emergency Procedures

For critical production issues:

1. **Stop affected services:**
```bash
docker-compose stop orchestration
```

2. **Check system health:**
```bash
python smoke_test.py
```

3. **Review recent changes:**
```bash
git log --oneline -10
```

4. **Rollback if needed:**
```bash
git checkout <previous-commit>
docker-compose up -d
```

5. **Contact on-call engineer:**
- Phone: +1-XXX-XXX-XXXX
- Pager: engineer@pagerduty.com
