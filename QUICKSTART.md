# Quick Start Guide

## What We Have Now

The Autonomous Field Engineer system is 55% complete with all core components working:

✅ Multi-agent orchestration layer  
✅ AI agents (Diagnosis, Action, Guidance)  
✅ Cloud Judge validation  
✅ RAG system with Weaviate  
✅ External systems integration  
✅ Production CLI interface  
✅ 29/29 tests passing  

## Try It Right Now

### 1. Run the System Demo (2 minutes)
```bash
python examples/orchestration_demo.py
```
This shows all components initializing and demonstrates system capabilities.

### 2. Try the CLI Interface (1 minute)
```bash
# Get help
python main.py --help

# Check session status
python main.py status --session session-123

# Start voice guidance
python main.py guidance --session session-123
```

### 3. Run the Tests (1 minute)
```bash
pytest tests/ -v
```
All 29 tests should pass.

## What's Next

### Task 11: Integration Tests (Next Session)
Run comprehensive integration tests to validate all components work together end-to-end.

### Task 12: Error Recovery
Implement error handling for:
- Low confidence diagnosis
- Inventory system unavailability
- Judge offline scenarios
- Safety violations
- Budget overruns

### Task 13: Performance Optimizations
Optimize:
- Image processing (target: <10s at p95)
- RAG system queries (target: <500ms)
- Judge validation (target: <2s at p95)
- Voice processing (target: <1s at p95)

## Key Files

### Production Code
- `main.py` - CLI interface for field technicians
- `src/orchestration/OrchestrationLayer.py` - Main orchestration logic
- `src/agents/` - AI agents (Diagnosis, Action, Guidance)
- `src/external/` - External system clients

### Examples & Demos
- `examples/orchestration_demo.py` - Full system demonstration
- `examples/external_systems_example.py` - External systems demo
- `examples/diagnosis_agent_example.py` - Diagnosis agent demo

### Documentation
- `docs/session_handoff_2026-02-27.md` - Comprehensive handoff
- `docs/ACCOMPLISHMENTS.md` - What we built today
- `README.md` - Project overview
- `.kiro/specs/autonomous-field-engineer/tasks.md` - Task list

## System Architecture

```
┌─────────────────────────────────────────┐
│     CLI Interface (main.py)             │
│  Field Technician Command-Line Tool     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Orchestration Layer                │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ Workflow: INTAKE → DIAGNOSIS →     │ │
│  │ PROCUREMENT → GUIDANCE → COMPLETE  │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Diagnosis │ │  Action  │ │Guidance │ │
│  │  Agent   │ │  Agent   │ │  Agent  │ │
│  │(Nova Pro)│ │(Nova Act)│ │(Nova    │ │
│  │          │ │          │ │ Sonic)  │ │
│  └──────────┘ └──────────┘ └─────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Cloud Judge (Claude + Nova Pro)   │ │
│  │  Safety • Budget • SOP • Quality   │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌──▼───┐  ┌───▼────┐
│  RAG  │  │Extern│  │Workflow│
│System │  │ al   │  │Persist │
│       │  │System│  │        │
│Weaviate│  │  s   │  │Checkpt │
└───────┘  └──────┘  └────────┘
```

## Environment Setup

### Prerequisites
- Python 3.10+
- Docker (for Weaviate)
- AWS credentials (for Bedrock)

### Virtual Environment
```bash
# Already set up in ../afe-env
# Activate it:
source ../afe-env/bin/activate  # Linux/Mac
..\afe-env\Scripts\activate     # Windows
```

### Weaviate
```bash
# Start Weaviate
docker-compose up -d

# Check status
docker-compose ps

# Should show: localhost:8080 (healthy)
```

### AWS Credentials
```bash
# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

## Troubleshooting

### Issue: Weaviate not running
```bash
docker-compose up -d
# Wait 10 seconds for startup
curl http://localhost:8080/v1/.well-known/ready
```

### Issue: Tests failing
```bash
# Check Weaviate is running
docker-compose ps

# Reinstall dependencies
pip install -r requirements.txt

# Run tests with verbose output
pytest tests/ -v
```

### Issue: CLI not working
```bash
# Check Python version
python --version  # Should be 3.10+

# Check virtual environment
which python  # Should point to afe-env

# Reinstall dependencies
pip install -r requirements.txt
```

## Performance Notes

### First Run (with model downloads)
- Initialization: ~20 seconds
- Model downloads: ~500MB (one-time)

### Subsequent Runs (with cached models)
- Initialization: ~5 seconds
- All operations: Fast

### Test Suite
- Duration: ~45 seconds
- Tests: 29/29 passing

## Project Status

### Completed (10/18 tasks)
✅ Tasks 1-10: Core system implementation

### Current Focus
⏳ Task 11: Integration tests

### Remaining
⏭️ Tasks 12-18: Error recovery, optimization, deployment

**Progress**: 55% complete

## Questions?

Check the documentation:
- `docs/session_handoff_2026-02-27.md` - Detailed handoff
- `docs/ACCOMPLISHMENTS.md` - Today's achievements
- `README.md` - Project overview

---
*Last Updated: February 27, 2026*  
*Status: Ready for Integration Testing*
