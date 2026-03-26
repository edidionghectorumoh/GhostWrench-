# Autonomous Field Engineer - Documentation

Welcome to the Autonomous Field Engineer documentation. This directory contains comprehensive guides, API documentation, and architecture information.

## Quick Links

### Getting Started
- [Deployment Guide](../deployment/README.md) - Deploy the system
- [Migration Guide](../deployment/MIGRATION_GUIDE.md) - Migrate to Linux laptop
- [Smoke Test](../smoke_test.py) - Verify deployment

### API Documentation
- [OpenAPI Specification](api/openapi.yaml) - REST API reference
- [Authentication Guide](guides/authentication.md) - Security and auth

### Developer Guides
- [Adding Equipment Types](guides/adding-equipment-types.md) - Extend RAG system
- [Troubleshooting Guide](guides/troubleshooting.md) - Common issues and solutions

### Architecture
- [System Overview](architecture/system-overview.md) - High-level architecture
- [Cloud Judge Architecture](cloud_judge_architecture.md) - Validation system
- [RAG System](rag_system.md) - Technical manual retrieval

### Agent Documentation
- [Diagnosis Agent](diagnosis_agent.md) - Multimodal diagnosis
- [Action Agent](action_agent.md) - Parts procurement
- [Guidance Agent](../src/agents/GuidanceAgent.py) - Repair guidance

## Documentation Structure

```
docs/
├── README.md                          # This file
├── api/
│   └── openapi.yaml                   # REST API specification
├── architecture/
│   └── system-overview.md             # System architecture
├── guides/
│   ├── adding-equipment-types.md      # RAG system guide
│   ├── authentication.md              # Security guide
│   └── troubleshooting.md             # Problem solving
├── cloud_judge_architecture.md        # Judge system
├── diagnosis_agent.md                 # Diagnosis agent
├── action_agent.md                    # Action agent
├── rag_system.md                      # RAG system
└── session_summaries/                 # Development logs
    ├── session_summary_2026-02-27.md
    ├── session_summary_2026-02-28.md
    └── session_summary_2026-02-28_task16.md
```

## For M.Res Students

### Research-Relevant Documentation

**System Architecture:**
- [System Overview](architecture/system-overview.md) - Complete architecture
- [Cloud Judge Architecture](cloud_judge_architecture.md) - Validation approach
- [RAG System](rag_system.md) - Knowledge retrieval

**Implementation Details:**
- [Diagnosis Agent](diagnosis_agent.md) - Multimodal AI diagnosis
- [Action Agent](action_agent.md) - Agentic procurement
- [Thought Logger](../src/orchestration/ThoughtLogger.py) - Reasoning capture

**Deployment:**
- [Migration Guide](../deployment/MIGRATION_GUIDE.md) - Linux laptop setup
- [Deployment Guide](../deployment/README.md) - Production deployment

### Key Concepts

**Multi-Agent Architecture:**
The system uses three specialized agents:
1. **Diagnosis Agent** (Nova Pro) - Analyzes equipment photos
2. **Action Agent** (Nova Act) - Handles procurement workflows
3. **Guidance Agent** (Nova Sonic) - Provides voice-guided repair

**Cloud-Based Validation:**
All agent outputs are validated by a cloud judge using:
- Amazon Nova Pro for multimodal analysis
- Claude 3.5 Sonnet for complex reasoning
- Safety checker for hazard detection

**RAG System:**
Technical manuals are indexed in Weaviate for:
- Semantic search of repair procedures
- Image similarity matching
- Hybrid text + image retrieval

**Observability:**
Complete reasoning chains captured in structured logs:
- Thought-Action-Observation loops
- Agent decision-making process
- Validation results and escalations

## API Usage Examples

### Submit Diagnosis Request

```bash
curl -X POST http://localhost:8000/api/v1/diagnosis \
  -H "X-API-Key: your_api_key" \
  -F "image=@equipment_photo.jpg" \
  -F "site_id=site-001" \
  -F "technician_id=tech-001"
```

### Check Workflow Status

```bash
curl -H "X-API-Key: your_api_key" \
  http://localhost:8000/api/v1/workflow/session-123/status
```

### Get Repair Guidance

```bash
curl -H "X-API-Key: your_api_key" \
  http://localhost:8000/api/v1/guidance/session-123
```

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd autonomous-field-engineer

# Configure environment
cp .env.example .env
nano .env  # Add AWS credentials

# Start services
docker-compose up -d

# Verify deployment
python smoke_test.py
```

### 2. Make Changes

```bash
# Edit code
nano src/orchestration/OrchestrationLayer.py

# Restart service
docker-compose restart orchestration

# View logs
docker-compose logs -f orchestration
```

### 3. Test Changes

```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_integration_workflows.py::TestHappyPathWorkflow -v

# Check diagnostics
python -m pytest tests/ --tb=short
```

### 4. Review Agent Reasoning

```bash
# View live reasoning logs
tail -f logs/agent_thoughts.jsonl | jq .

# Filter by session
cat logs/agent_thoughts.jsonl | jq 'select(.session_id == "session-123")'

# Find escalations
cat logs/agent_thoughts.jsonl | jq 'select(.action == "create_escalation")'
```

## Common Tasks

### Add New Equipment Type

1. Prepare technical manual (PDF) and reference images
2. Create metadata.json with equipment specifications
3. Ingest manual: `python scripts/ingest_manual.py --manual manual.pdf ...`
4. Ingest images: `python scripts/ingest_images.py --directory images/ ...`
5. Test retrieval: `python scripts/test_rag.py --equipment-type network_switch`

See [Adding Equipment Types Guide](guides/adding-equipment-types.md) for details.

### Debug Diagnosis Issues

1. Check agent reasoning logs:
```bash
cat logs/agent_thoughts.jsonl | jq 'select(.agent_type == "diagnosis")'
```

2. Verify RAG system has manuals:
```python
from src.rag.RAGSystem import RAGSystem
rag = RAGSystem()
stats = rag.get_statistics()
print(f"Manuals indexed: {stats['total_objects']}")
```

3. Test with known good image:
```bash
pytest tests/test_integration_workflows.py::TestHappyPathWorkflow::test_diagnosis_phase -v
```

### Troubleshoot Deployment

1. Run smoke test:
```bash
python smoke_test.py --full
```

2. Check service health:
```bash
docker-compose ps
docker-compose logs
```

3. Verify AWS access:
```bash
aws bedrock list-foundation-models --region us-east-1
```

See [Troubleshooting Guide](guides/troubleshooting.md) for more solutions.

## Performance Monitoring

### View Metrics

```bash
# Docker resource usage
docker stats

# Service logs
docker-compose logs -f orchestration

# Agent reasoning performance
cat logs/agent_thoughts.jsonl | jq 'select(.metadata.duration_ms > 1000)'
```

### Optimize Performance

1. **Image compression:** Reduce image size before upload
2. **RAG caching:** Results cached for 1 hour automatically
3. **Resource limits:** Adjust in docker-compose.yml
4. **Batch processing:** Process multiple requests together

See [System Overview](architecture/system-overview.md) for performance targets.

## Security

### Best Practices

1. **Never commit credentials** - Use .env file (gitignored)
2. **Rotate API keys** every 90 days
3. **Use HTTPS** in production
4. **Enable audit logging** for all operations
5. **Review security logs** regularly

See [Authentication Guide](guides/authentication.md) for details.

### Audit Logs

```bash
# View audit logs
sqlite3 audit_logs/judgments.db "SELECT * FROM judgments ORDER BY timestamp DESC LIMIT 10;"

# Security events
cat logs/agent_thoughts.jsonl | jq 'select(.action == "handle_safety_violation")'
```

## Contributing

### Documentation Standards

- Use Markdown for all documentation
- Include code examples with syntax highlighting
- Add diagrams for complex concepts (Mermaid or ASCII)
- Keep examples up-to-date with code changes
- Test all code examples before committing

### Code Documentation

- Docstrings for all public functions and classes
- Type hints for function parameters and returns
- Inline comments for complex logic
- README in each major directory

## Support

### Getting Help

- **Documentation:** Start here in docs/
- **Troubleshooting:** See [Troubleshooting Guide](guides/troubleshooting.md)
- **API Reference:** See [OpenAPI Spec](api/openapi.yaml)
- **GitHub Issues:** Report bugs and request features
- **Email:** support@example.com

### Reporting Issues

Include:
1. System information: `python smoke_test.py > diagnostic.txt`
2. Logs: `docker-compose logs > logs.txt`
3. Steps to reproduce
4. Expected vs actual behavior

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- Amazon Bedrock for AI models
- Weaviate for vector database
- FastAPI for web framework
- Docker for containerization
