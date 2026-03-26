# Autonomous Field Engineer - Deployment Guide

## Overview

This system uses a cloud-based judge architecture with Amazon Bedrock (Nova Pro and Claude 3.5 Sonnet) rather than a local LLM judge. This provides better scalability and eliminates the need for local GPU resources.

## Architecture

- **Orchestration Layer**: Python-based service coordinating all agents
- **Cloud Judge**: Amazon Bedrock (Nova Pro + Claude 3.5 Sonnet)
- **RAG System**: Weaviate vector database for technical manuals
- **Agents**: Diagnosis, Action, and Guidance agents

## Prerequisites

- Docker and Docker Compose
- AWS Account with Bedrock access
- Python 3.11+
- 8GB RAM minimum (16GB recommended)
- Internet connection for AWS Bedrock API calls

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd autonomous-field-engineer
cp .env.example .env
```

### 2. Configure AWS Credentials

Edit `.env` file with your AWS credentials:

```bash
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- Weaviate vector database (port 8080)
- Orchestration layer service (port 8000)

### 4. Verify Deployment

```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs -f orchestration

# Run smoke test (quick check without API calls)
python smoke_test.py

# Run full smoke test (includes Bedrock API calls)
python smoke_test.py --full
```

The smoke test verifies:
- Environment variables are set
- Weaviate connection and schema
- AWS credentials validity
- Bedrock model access (Nova Pro, Claude 3.5 Sonnet) - full test only
- System configuration
- Safe diagnosis workflow - full test only

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_DEFAULT_REGION` | AWS region | us-east-1 |
| `ENABLE_VALIDATION` | Enable judge validation | true |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FORMAT` | Log format (text/json) | json |
| `WEAVIATE_URL` | Weaviate endpoint | http://weaviate:8080 |
| `ENABLE_THOUGHT_LOGGING` | Enable agent reasoning logs | true |
| `THOUGHT_LOG_PATH` | Path to thought logs | /app/logs/agent_thoughts.jsonl |

### AWS Bedrock Models

The system requires access to:
- **Amazon Nova Pro**: Multimodal diagnosis
- **Amazon Nova Act**: Agentic actions
- **Claude 3.5 Sonnet**: Complex reasoning and validation

Ensure these models are enabled in your AWS Bedrock console.

## Data Persistence

- **Audit Logs**: `./audit_logs/judgments.db` (SQLite)
- **Checkpoints**: `./.checkpoints/` (workflow state)
- **Weaviate Data**: Docker volume `weaviate_data`
- **Agent Reasoning Logs**: `./logs/agent_thoughts.jsonl` (Thought-Action-Observation loops)

### Agent Reasoning Logs

The system captures structured JSON logs of agent reasoning chains (Thought-Action-Observation loops) for:
- Debugging agent behavior
- Auditing decision-making
- Training data collection
- Performance analysis

Each log entry contains:
```json
{
  "timestamp": "2026-02-28T10:30:45.123Z",
  "session_id": "session-abc123",
  "agent_type": "diagnosis",
  "phase": "diagnosis",
  "thought": "Equipment shows signs of hardware failure...",
  "action": "analyze_image",
  "observation": "Confidence: 0.92, Issue: hardware_defect",
  "metadata": {...}
}
```

View reasoning logs:
```bash
# Tail live reasoning logs
tail -f logs/agent_thoughts.jsonl | jq .

# Filter by session
cat logs/agent_thoughts.jsonl | jq 'select(.session_id == "session-123")'

# Filter by agent type
cat logs/agent_thoughts.jsonl | jq 'select(.agent_type == "diagnosis")'
```

## Monitoring

### Application Logs

```bash
# View orchestration logs
docker-compose logs -f orchestration

# View Weaviate logs
docker-compose logs -f weaviate
```

### Health Checks

```bash
# Check Weaviate health
curl http://localhost:8080/v1/.well-known/ready

# Check orchestration service (if API endpoint exists)
curl http://localhost:8000/health
```

## Troubleshooting

### Weaviate Connection Issues

```bash
# Restart Weaviate
docker-compose restart weaviate

# Check Weaviate logs
docker-compose logs weaviate
```

### AWS Bedrock Access Issues

1. Verify AWS credentials are correct
2. Check Bedrock model access in AWS console
3. Verify region supports Bedrock
4. Check IAM permissions for Bedrock API calls

### Performance Issues

- Increase Docker memory allocation (Settings > Resources)
- Check network latency to AWS Bedrock
- Monitor Weaviate resource usage

## Scaling

### Horizontal Scaling

The orchestration layer can be scaled horizontally:

```yaml
orchestration:
  deploy:
    replicas: 3
```

### Weaviate Scaling

For production, consider:
- Weaviate Cloud Services (managed)
- Multi-node Weaviate cluster
- Separate Weaviate instance per region

## Security

### Best Practices

1. **Never commit `.env` file** - use `.env.example` as template
2. **Use IAM roles** in production instead of access keys
3. **Enable Weaviate authentication** for production
4. **Use HTTPS** for all external endpoints
5. **Rotate AWS credentials** regularly
6. **Audit log access** - monitor `audit_logs/judgments.db`

### Network Security

```yaml
# Production docker-compose.yml additions
services:
  orchestration:
    networks:
      - afe_network
      - external_network
    # Only expose necessary ports
```

## Backup and Recovery

### Backup Audit Logs

```bash
# Backup SQLite database
cp audit_logs/judgments.db audit_logs/judgments.db.backup

# Automated backup
0 2 * * * cp /path/to/audit_logs/judgments.db /backup/location/
```

### Backup Weaviate Data

```bash
# Export Weaviate data
docker-compose exec weaviate weaviate-backup create

# Restore from backup
docker-compose exec weaviate weaviate-backup restore
```

## Production Deployment

See `deployment/aws/` for:
- Terraform/CloudFormation templates
- ECS/EKS deployment configurations
- Load balancer setup
- Auto-scaling policies

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Review troubleshooting section above
- Check AWS Bedrock service status
- Verify network connectivity
