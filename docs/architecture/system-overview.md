# System Architecture Overview

## Introduction

The Autonomous Field Engineer (AFE) is a multi-agent AI system designed to assist field technicians with equipment diagnosis, parts procurement, and repair guidance. The system leverages Amazon Bedrock's Nova models for AI capabilities and uses a cloud-based validation architecture.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Field Technician                          │
│                     (Mobile Device / Tablet)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS/REST API
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Orchestration Layer                           │
│                  (Python FastAPI Service)                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Workflow   │  │    Agent     │  │  Escalation  │         │
│  │  Management  │  │ Coordination │  │  Management  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────┬────────┬────────┬────────┬────────┬────────┬────────────┘
       │        │        │        │        │        │
       │        │        │        │        │        │
   ┌───▼───┐┌──▼───┐┌───▼───┐┌───▼───┐┌──▼───┐┌───▼────┐
   │Diagno-││Action││Guidan-││Cloud  ││ RAG  ││External│
   │sis    ││Agent ││ce     ││Judge  ││System││Systems │
   │Agent  ││      ││Agent  ││       ││      ││        │
   └───┬───┘└──┬───┘└───┬───┘└───┬───┘└──┬───┘└───┬────┘
       │       │        │        │       │        │
       │       │        │        │       │        │
   ┌───▼───────▼────────▼────────▼───────▼────────▼────┐
   │              Amazon Bedrock (AWS)                  │
   │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
   │  │Nova Pro  │  │Nova Act  │  │Claude 3.5│        │
   │  │(Diagnosis│  │(Actions) │  │(Validate)│        │
   │  └──────────┘  └──────────┘  └──────────┘        │
   └────────────────────────────────────────────────────┘
```

## Core Components

### 1. Orchestration Layer

**Purpose:** Coordinates the multi-agent workflow and manages session state.

**Key Responsibilities:**
- Request routing to appropriate agents
- Workflow phase management (Intake → Diagnosis → Procurement → Guidance → Completion)
- Validation gate enforcement
- Session persistence and recovery
- Escalation handling

**Technology:**
- Python 3.11+
- FastAPI for REST API
- SQLite for audit logs
- JSON for checkpoints

**Key Files:**
- `src/orchestration/OrchestrationLayer.py` - Main orchestration logic
- `src/orchestration/WorkflowPersistence.py` - State persistence
- `src/orchestration/AgentCoordination.py` - Multi-agent coordination
- `src/orchestration/ThoughtLogger.py` - Reasoning logs

### 2. Diagnosis Agent

**Purpose:** Analyzes equipment photos to identify issues and recommend repairs.

**Key Capabilities:**
- Multimodal image analysis
- Equipment type identification
- Issue classification (hardware defect, installation error, network failure, etc.)
- Confidence scoring
- Reference material comparison via RAG

**AI Model:** Amazon Nova Pro (multimodal)

**Key Files:**
- `src/agents/DiagnosisAgent.py`
- `docs/diagnosis_agent.md`

### 3. Action Agent

**Purpose:** Executes procurement workflows including inventory search and purchase requests.

**Key Capabilities:**
- Inventory database search
- Alternative parts identification
- Cost estimation
- Purchase request generation
- Approval workflow integration

**AI Model:** Amazon Nova Act (agentic tool-calling)

**Key Files:**
- `src/agents/ActionAgent.py`
- `docs/action_agent.md`

### 4. Guidance Agent

**Purpose:** Provides step-by-step repair guidance tailored to technician skill level.

**Key Capabilities:**
- Repair guide generation
- Voice command processing
- Speech synthesis
- Safety check integration
- Session state tracking

**AI Model:** Amazon Nova 2 Sonic (voice interaction)

**Key Files:**
- `src/agents/GuidanceAgent.py`

### 5. Cloud Judge

**Purpose:** Validates agent outputs for safety, SOP compliance, and budget constraints.

**Key Capabilities:**
- Safety hazard detection
- SOP compliance checking
- Budget validation
- Quality assessment
- Escalation level determination

**AI Models:**
- Amazon Nova Pro (multimodal analysis)
- Claude 3.5 Sonnet (complex reasoning)

**Key Files:**
- `src/judge/cloud_judge.py`
- `src/judge/audit_logger.py`
- `src/safety/safety_checker.py`

### 6. RAG System

**Purpose:** Retrieves relevant technical manual sections and reference images.

**Key Capabilities:**
- Vector-based semantic search
- Image similarity search
- Hybrid text + image search
- Query result caching
- Manual ingestion pipeline

**Technology:**
- Weaviate vector database
- CLIP for image embeddings
- Sentence transformers for text embeddings

**Key Files:**
- `src/rag/RAGSystem.py`
- `docs/rag_system.md`

### 7. External Systems

**Purpose:** Integrates with enterprise systems for inventory, procurement, telemetry, and maintenance logs.

**Key Integrations:**
- Inventory System (parts database)
- Procurement System (purchase orders)
- Telemetry System (equipment metrics)
- Maintenance Log System (repair history)

**Key Files:**
- `src/external/ExternalSystemsAdapter.py`
- `src/external/InventoryClient.py`
- `src/external/ProcurementClient.py`
- `src/external/TelemetryClient.py`
- `src/external/MaintenanceLogClient.py`

## Data Flow

### Typical Workflow

```
1. Technician submits photo + site context
   ↓
2. Orchestration Layer creates session
   ↓
3. Diagnosis Agent analyzes image
   ↓
4. RAG System retrieves reference materials
   ↓
5. Cloud Judge validates diagnosis
   ↓
6. Action Agent searches inventory (if parts needed)
   ↓
7. Cloud Judge validates procurement
   ↓
8. Guidance Agent generates repair steps
   ↓
9. Technician follows voice-guided repair
   ↓
10. Maintenance record created on completion
```

### Workflow Phases

```
INTAKE
  ↓
DIAGNOSIS (with validation gate)
  ↓
PROCUREMENT (if parts needed, with validation gate)
  ↓
GUIDANCE
  ↓
COMPLETION
```

### Validation Gates

At each phase transition, the Cloud Judge validates:
- **Safety:** No hazardous procedures without proper PPE/permits
- **SOP Compliance:** Procedures follow standard operating procedures
- **Budget:** Costs within authorized limits
- **Quality:** Output meets quality standards

## Data Models

### Core Domain Models

**SiteContext:**
- Site identification and location
- Criticality level
- Operating hours
- Environmental conditions
- Component information

**ImageData:**
- Raw image bytes
- Resolution and metadata
- Capture timestamp and location
- Device information

**WorkflowState:**
- Session ID and phase
- Technician and site IDs
- Diagnosis, procurement, and guidance states
- Escalations and metadata

### Agent Models

**DiagnosisResult:**
- Issue type and confidence
- Recommended actions
- Required parts
- Estimated repair time

**ProcurementResult:**
- Parts list with costs
- Supplier information
- Delivery estimates
- Approval status

**RepairGuide:**
- Step-by-step instructions
- Safety notes
- Required tools
- Estimated duration

## Security Architecture

### Authentication & Authorization

- API key authentication for REST endpoints
- AWS IAM roles for Bedrock access
- Role-based access control for escalations

### Data Protection

- TLS/HTTPS for all external communication
- Encrypted storage for sensitive data
- Audit logging for all validations
- PII redaction in logs

### Network Security

- Private VPC for AWS resources
- Security groups for service isolation
- Network policies for container communication

## Scalability

### Horizontal Scaling

- Stateless orchestration layer (can run multiple replicas)
- Load balancer for request distribution
- Session state in persistent storage

### Vertical Scaling

- Configurable resource limits per service
- Auto-scaling based on CPU/memory usage
- Separate scaling for Weaviate and orchestration

### Performance Targets

- Diagnosis: < 10 seconds (p95)
- Inventory search: < 3 seconds (p95)
- Judge validation: < 2 seconds (p95)
- Voice response: < 1 second (p95)
- End-to-end workflow: < 90 seconds (p95)

## Reliability

### Fault Tolerance

- Checkpoint persistence for crash recovery
- Automatic workflow resumption
- Circuit breakers for external systems
- Retry logic with exponential backoff

### Error Recovery

- Low confidence diagnosis → Request additional photos or escalate
- Inventory unavailable → Use cached data with pending verification
- Judge offline → Pause workflow and resume on recovery
- Safety violations → Immediate halt and escalation
- Budget exceeded → Approval workflow queueing
- Voice recognition failure → Text input fallback
- Missing manuals → Fuzzy matching and generic procedures
- Delayed delivery → Expedited shipping or alternatives

### Monitoring

- Health checks for all services
- Structured logging (JSON format)
- Thought-Action-Observation logs for agent reasoning
- Performance metrics (latency, throughput, error rates)
- Alerting for critical failures

## Deployment

### Development

```bash
docker-compose up -d
python smoke_test.py
```

### Production

- AWS ECS/EKS for container orchestration
- Application Load Balancer for traffic distribution
- CloudWatch for monitoring and alerting
- S3 for image storage and manual archives
- RDS for audit logs (production alternative to SQLite)

### Infrastructure as Code

- Terraform templates in `deployment/aws/terraform/`
- CloudFormation templates available
- Monitoring configuration in `deployment/monitoring/`

## Technology Stack

### Backend

- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **AI Platform:** Amazon Bedrock
- **Vector Database:** Weaviate
- **Audit Storage:** SQLite (dev), RDS (prod)
- **Caching:** In-memory (dev), Redis (prod)

### AI Models

- **Amazon Nova Pro:** Multimodal diagnosis
- **Amazon Nova Act:** Agentic actions
- **Amazon Nova 2 Sonic:** Voice interaction
- **Claude 3.5 Sonnet:** Complex reasoning and validation
- **CLIP:** Image embeddings
- **Sentence Transformers:** Text embeddings

### Infrastructure

- **Containers:** Docker, Docker Compose
- **Orchestration:** AWS ECS/EKS
- **Storage:** S3, EBS volumes
- **Networking:** VPC, ALB, Security Groups
- **Monitoring:** CloudWatch, CloudWatch Logs

## Development Workflow

### Local Development

1. Clone repository
2. Configure AWS credentials in `.env`
3. Start services: `docker-compose up -d`
4. Run smoke test: `python smoke_test.py`
5. Make changes and test
6. Run test suite: `pytest tests/`

### Testing Strategy

- **Unit Tests:** Individual component testing
- **Integration Tests:** End-to-end workflow testing
- **Property Tests:** Universal correctness properties
- **Smoke Tests:** Deployment verification

### CI/CD Pipeline

1. Code commit triggers build
2. Run linting and type checking
3. Run unit tests
4. Build Docker images
5. Run integration tests
6. Deploy to staging
7. Run smoke tests
8. Deploy to production (manual approval)

## Future Enhancements

### Planned Features

- Real-time collaboration between technicians
- Predictive maintenance based on telemetry
- AR overlay for repair guidance
- Offline mode with local model inference
- Multi-language support
- Mobile app (iOS/Android)

### Performance Optimizations

- Image compression pipeline
- RAG query result pre-caching
- Batch validation for multiple requests
- Edge caching for common queries

### Integration Expansions

- CMDB integration for asset tracking
- Ticketing system integration (ServiceNow, Jira)
- Training system integration for skill tracking
- Supply chain integration for parts forecasting

## References

- [API Documentation](../api/openapi.yaml)
- [Deployment Guide](../../deployment/README.md)
- [Migration Guide](../../deployment/MIGRATION_GUIDE.md)
- [Troubleshooting Guide](../guides/troubleshooting.md)
- [Adding Equipment Types](../guides/adding-equipment-types.md)
