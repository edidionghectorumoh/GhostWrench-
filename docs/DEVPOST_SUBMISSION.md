# GhostWrench: Autonomous Field Engineer

## Devpost Submission — Amazon Nova AI Hackathon

**Category:** Agentic AI
**Submitter Type:** Professional Developer
**Repository:** https://github.com/edidionghectorumoh/GhostWrench-
**Hashtag:** #AmazonNova

---

## Project Summary

GhostWrench is a cyber-physical AI agent system that transforms how field technicians diagnose, procure parts for, and repair industrial infrastructure. A technician snaps a photo of failing equipment, and GhostWrench's multi-agent pipeline takes over — identifying the fault, sourcing replacement parts, and delivering hands-free voice-guided repair instructions — all validated through safety gates before any action reaches the field.

The system orchestrates four Amazon Nova foundation models and Claude 3.5 Sonnet across five workflow phases, each gated by a cloud-based validation judge that enforces safety protocols, SOP compliance, and budget constraints in real time.

## How It Works

GhostWrench operates as a five-phase agentic workflow:

1. **INTAKE** — The technician submits an equipment photo and site context through a Chainlit web interface. The orchestration layer validates the request and initializes a persistent workflow session.

2. **DIAGNOSIS** — The DiagnosisAgent sends the equipment image to Amazon Nova 2 Lite via the Converse API with Extended Thinking enabled (`reasoningConfig: medium`). Nova 2 Lite performs chain-of-thought reasoning over the image and technician notes, cross-referenced against technical manuals retrieved by a RAG system powered by Amazon Nova Multimodal Embeddings. The agent returns a structured diagnosis with issue type, severity, root cause, and a confidence score. If confidence falls below 0.85, the system automatically requests additional photos or escalates to a human expert — preventing unreliable diagnoses from propagating downstream.

3. **PROCUREMENT** — The ActionAgent uses Amazon Nova Act to navigate a mock inventory portal via browser automation, searching for parts, adding them to a cart, and submitting purchase requests. Screenshots are captured at each step for audit transparency. If the portal is unavailable, the agent falls back to a tool-calling procurement flow. The CloudJudge validates the total cost against budget constraints before approving.

4. **GUIDANCE** — The GuidanceAgent uses Amazon Nova 2 Sonic to deliver voice-guided repair instructions. The technician speaks commands ("next step", "repeat", "help") and receives spoken responses. Before any guidance reaches the technician's earpiece, the response text passes through a CloudJudge safety gate — if the guidance contradicts a safety protocol (e.g., suggesting high-voltage work without a permit), the system intercepts it and directs the technician to consult their supervisor.

5. **COMPLETION** — A maintenance record is generated, the workflow state is checkpointed, and the session closes.

## Amazon Nova Models Used

| Model | Role | API |
|-------|------|-----|
| **Nova 2 Lite** | Multimodal diagnosis with Extended Thinking | Converse API (`reasoningConfig: medium`) |
| **Nova 2 Sonic** | Speech-to-text transcription and text-to-speech guidance | Converse API (audio content blocks) |
| **Nova Multimodal Embeddings** | Unified text + image embeddings for RAG retrieval | InvokeModel API |
| **Nova Act** | Browser automation for inventory portal procurement | Nova Act API |
| **Claude 3.5 Sonnet** | Validation judge for safety, SOP, and budget gates | InvokeModel API |

## What Makes It Agentic

GhostWrench is not a single-model wrapper. It is a coordinated multi-agent system where each agent has a distinct role, and a validation judge arbitrates every decision before it affects the physical world:

- **Autonomous decision-making**: The orchestration layer routes requests through agents based on workflow state, confidence thresholds, and validation outcomes — without human intervention for routine cases.
- **Safety-first architecture**: The CloudJudge enforces a list of Prohibited Field Actions (high-voltage without permit, confined-space without buddy, lockout/tagout bypass, etc.) via a system prompt injected into every Nova 2 Lite validation call. Any match triggers immediate escalation to a safety officer.
- **Extended Thinking**: Nova 2 Lite's `reasoningConfig` with `medium` budget gives the DiagnosisAgent a chain-of-thought reasoning step, improving diagnostic accuracy on ambiguous equipment images.
- **Graceful degradation**: Circuit breakers protect external system calls. Stale telemetry is detected and handled (60-second threshold for critical operations). Failed agents don't crash the workflow — they escalate.
- **Persistent state**: Workflow checkpoints allow sessions to survive crashes and reconnections. The Chainlit UI restores pending escalations on reconnect.

## Cyber-Physical Impact

GhostWrench targets a real gap in industrial maintenance: field technicians working alone on critical infrastructure, often in hazardous environments, with limited access to expertise. The system:

- Reduces diagnostic time by providing instant AI-powered analysis of equipment photos against technical manuals
- Prevents unsafe field actions through automated safety validation before any instruction reaches the technician
- Enables hands-free operation during repairs via voice-guided instructions — the technician's hands stay on the equipment, not a screen
- Creates auditable maintenance records automatically, improving compliance and institutional knowledge

The "cyber-physical" nature is the key differentiator: GhostWrench doesn't just generate text — it validates actions against real-world safety constraints before they're executed in physical environments where mistakes have physical consequences.

## Technology Stack

- **Runtime:** Python 3.10+, Chainlit 2.10 (web UI)
- **AI Models:** Amazon Nova 2 Lite, Nova 2 Sonic, Nova Multimodal Embeddings, Nova Act, Claude 3.5 Sonnet (all via Amazon Bedrock)
- **Vector Database:** Weaviate (self-hosted, HNSW index)
- **Persistence:** SQLite (audit logs), in-memory session store with checkpoint serialization
- **Testing:** pytest, Hypothesis (property-based testing strategies)

## Repository Access

Please add the following as collaborators for judging:
- `testing@devpost.com`
- `Amazon-Nova-hackathon@amazon.com`

---

*Built for the Amazon Nova AI Hackathon, March 2026. #AmazonNova*
