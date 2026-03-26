# GhostWrench — Autonomous Field Engineer

A cyber-physical AI agent system for field infrastructure maintenance, built for the [Amazon Nova AI Hackathon](https://amazon-nova.devpost.com/). GhostWrench orchestrates Amazon Nova 2 Lite, Nova 2 Sonic, Nova Multimodal Embeddings, Nova Act, and Claude 3.5 Sonnet to automate equipment diagnosis, parts procurement, and hands-free voice-guided repair — all validated through safety gates before any action reaches the field.

**Category:** Agentic AI &nbsp;|&nbsp; **Hashtag:** #AmazonNova &nbsp;|&nbsp; **UI:** Chainlit 2.10

## How to Run

### Prerequisites

- Python 3.10+
- Docker (for Weaviate vector database)
- AWS account with Bedrock access enabled for Nova 2 Lite, Nova 2 Sonic, Nova Multimodal Embeddings, Nova Act, and Claude 3.5 Sonnet

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example env file and fill in your AWS credentials:

```bash
cp .env.example .env
# Edit .env with your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
```

### 3. Start Weaviate Vector Database

```bash
docker-compose up -d
```

### 4. Launch the Chainlit Web UI

```bash
chainlit run chainlit_app.py -w
```

This starts the GhostWrench web interface at `http://localhost:8000`. From here you can:

- Type a description of an equipment issue or upload an equipment photo
- Watch the multi-agent workflow progress through INTAKE → DIAGNOSIS → PROCUREMENT → GUIDANCE → COMPLETION
- Use voice commands during the GUIDANCE phase (next, repeat, help, emergency)
- Type **demo** as your first message to run a guided walkthrough of all five phases with model annotations

### 5. (Optional) Start the Mock Inventory Portal

For the Nova Act procurement demo:

```bash
python mock_portal/server.py
```

This serves the mock inventory portal at `http://localhost:8501`.

### 6. Run Tests

```bash
pytest tests/
```

### 7. Use the CLI Interface

```bash
python main.py --help
python main.py status --session session-123
python main.py guidance --session session-123
```

## Architecture

GhostWrench operates as a five-phase agentic workflow, each gated by a cloud-based validation judge:

```
Technician submits photo
    ↓
┌─────────────────────────────────────────────────────────┐
│ INTAKE → DIAGNOSIS → PROCUREMENT → GUIDANCE → COMPLETION│
│            ↕              ↕            ↕                 │
│        CloudJudge     CloudJudge   CloudJudge            │
│      (safety gate)  (budget gate) (voice safety)         │
└─────────────────────────────────────────────────────────┘
```

### Agents

| Agent | Model | Role |
|-------|-------|------|
| **DiagnosisAgent** | Amazon Nova 2 Lite | Multimodal image analysis with Extended Thinking (`reasoningConfig: medium`) via Converse API. Cross-references equipment photos against technical manuals retrieved by visual RAG. |
| **ActionAgent** | Amazon Nova Act | Browser automation for inventory portal procurement. Navigates, searches, and submits purchase requests with screenshot capture at each step. Falls back to tool-calling if portal is unavailable. |
| **GuidanceAgent** | Amazon Nova 2 Sonic | Voice-guided repair instructions via speech-to-text and text-to-speech. Technicians speak commands ("next step", "repeat", "help") and receive spoken responses. |
| **CloudJudge** | Claude 3.5 Sonnet + Nova 2 Lite | Validates every agent output for safety, SOP compliance, and budget constraints. Enforces Prohibited Field Actions list via system prompt. |

### RAG System

| Component | Model | Purpose |
|-----------|-------|---------|
| **Text + Image Embeddings** | Amazon Nova Multimodal Embeddings | Unified 1024-dim vector space for both text (manual sections) and images (equipment photos). Enables visual RAG — retrieving the right manual page by comparing what the technician sees to reference images. |
| **Vector Store** | Weaviate (self-hosted) | HNSW index with query caching (1-hour TTL) |

## Amazon Nova Models

| Model | Model ID | API |
|-------|----------|-----|
| Nova 2 Lite | `us.amazon.nova-2-lite-v1:0` | Converse API (with `reasoningConfig`) |
| Nova 2 Sonic | `us.amazon.nova-2-sonic-v1:0` | Converse API (audio content blocks) |
| Nova Multimodal Embeddings | `amazon.nova-2-multimodal-embeddings-v1:0` | InvokeModel API |
| Nova Act | `us.amazon.nova-act-v1:0` | Nova Act API |
| Claude 3.5 Sonnet | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | InvokeModel API |

## Safety Architecture

GhostWrench enforces safety at every layer:

- **Confidence gates**: Diagnoses below 0.85 confidence trigger expert review or additional photo requests. Max 3 photo attempts before mandatory escalation.
- **Prohibited Field Actions**: Hardcoded list (high-voltage without permit, confined-space without buddy, lockout/tagout bypass, etc.) injected as a system prompt into every CloudJudge validation call. Any match triggers immediate escalation to a safety officer.
- **Voice safety intercept**: GuidanceAgent responses pass through CloudJudge before text-to-speech synthesis. Unsafe guidance is replaced with a safe fallback message.
- **Extended Thinking**: Nova 2 Lite's `reasoningConfig` with `medium` budget enables chain-of-thought reasoning on ambiguous equipment images, reducing misdiagnosis risk.
- **Circuit breakers**: External system calls are protected against cascading failures.
- **Telemetry staleness**: 60-second threshold for critical operations, 300-second for normal.

## Project Structure

```
.
├── chainlit_app.py      # Chainlit web UI (primary interface)
├── main.py              # CLI interface
├── config.py            # Model IDs and Bedrock client configuration
├── mock_portal/         # Mock inventory portal for Nova Act demo
│   ├── index.html
│   └── server.py
├── src/
│   ├── agents/          # DiagnosisAgent, ActionAgent, GuidanceAgent
│   ├── judge/           # CloudJudge + audit logger
│   ├── models/          # Pydantic data models and validation schemas
│   ├── rag/             # RAGSystem (Weaviate + Nova Multimodal Embeddings)
│   ├── orchestration/   # OrchestrationLayer, workflow persistence, coordination
│   └── external/        # External system clients (inventory, procurement, telemetry)
├── tests/               # pytest + Hypothesis property-based testing
│   └── strategies/      # Custom Hypothesis strategies for Chainlit properties
├── docs/                # Documentation, submission materials
├── deployment/          # Terraform, monitoring, migration guides
└── docker-compose.yml   # Weaviate setup
```

## Current Status

✅ All 19 required implementation tasks complete
✅ 45 core tests passing
✅ Nova 2 model migrations (Lite, Sonic, Multimodal Embeddings) complete
✅ Chainlit 2.10 web UI with image upload, voice, escalation handling, demo mode
✅ CloudJudge safety gates with Prohibited Field Actions
✅ Extended Thinking enabled on DiagnosisAgent
✅ Mock inventory portal for Nova Act demo
✅ Session persistence and reconnection

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture with Mermaid diagrams
- [RESILIENCE_SPEC.md](RESILIENCE_SPEC.md) — Error recovery and resilience mechanisms
- [Devpost Submission](docs/DEVPOST_SUBMISSION.md) — Hackathon submission description
- [Blog Post Outline](docs/BLOG_POST_OUTLINE.md) — builder.aws.com blog post outline
- [API Documentation](docs/api/openapi.yaml)
- [Troubleshooting Guide](docs/guides/troubleshooting.md)

## Development

```bash
# Start Weaviate
docker-compose up -d

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest --cov=src tests/
```

## Repository Access (Hackathon Judges)

If this repository is private, the following accounts have been granted read access:
- `testing@devpost.com`
- `Amazon-Nova-hackathon@amazon.com`

## License

Proprietary — All rights reserved.

---

*Built for the [Amazon Nova AI Hackathon](https://amazon-nova.devpost.com/), March 2026. #AmazonNova*
