# Cloud-Based Judge Architecture

## Overview

The Cloud-Based Judge is a validation layer that uses Amazon Bedrock models (Nova Pro and Claude 3.5 Sonnet) to validate all AI agent outputs for safety, SOP compliance, budget constraints, and quality thresholds before execution.

## Architecture

### Cloud-Based Design

Unlike a local judge running on a technician's laptop, the Cloud Judge leverages AWS Bedrock's managed AI services for:
- **Scalability**: Handle validation for 100+ concurrent technicians
- **Model Access**: Use latest Amazon Nova Pro and Claude 3.5 Sonnet models
- **Reliability**: AWS-managed infrastructure with high availability
- **Performance**: Optimized inference with < 2 second latency

### Model Selection

1. **Claude 3.5 Sonnet** - Primary reasoning engine
   - Complex safety analysis
   - SOP compliance evaluation
   - Recommendation generation
   - Human-readable explanations

2. **Amazon Nova Pro** - Multimodal analysis (future)
   - Visual safety assessment
   - Image-based compliance checking
   - Reference material comparison

## Components

### CloudJudge (`src/judge/cloud_judge.py`)

Main validation interface that:
- Connects to AWS Bedrock via `config.py`
- Routes validation tasks to appropriate models
- Implements specialized validation methods
- Generates structured judgments

### AuditLogger (`src/judge/audit_logger.py`)

SQLite-based audit logging:
- Local audit trail for compliance
- 7-year retention
- Sync capability to central system
- Statistics and reporting

## Key Features

### Validation Types

1. **Safety Validation**
   ```python
   safety_judgment = judge.validate_diagnosis_safety(diagnosis)
   ```
   - Identifies hazards
   - Determines required PPE
   - Checks lockout/tagout requirements
   - Assesses permit needs

2. **SOP Compliance**
   ```python
   compliance_judgment = judge.validate_sop_compliance(repair_guide)
   ```
   - Validates procedures against SOPs
   - Checks for missing steps
   - Identifies deviations

3. **Budget Validation**
   ```python
   budget_judgment = judge.validate_budget_constraints(purchase_request)
   ```
   - Enforces budget limits
   - Determines approval levels
   - Provides cost breakdowns

4. **Quality Validation**
   - Confidence threshold checking
   - Reference coverage validation
   - Uncertainty assessment

### Escalation Levels

- **None**: No escalation needed
- **Supervisor**: Minor SOP or quality issues
- **Safety Officer**: Safety violations
- **Management**: Budget overruns or complex issues

## Usage

### Basic Validation

```python
from src.judge.cloud_judge import CloudJudge
from src.models.validation import AgentOutput, ValidationCriteria

# Initialize judge (uses config.py for Bedrock client)
judge = CloudJudge()

# Validate agent output
judgment = judge.validate_agent_output(agent_output, criteria)

if judgment.approved:
    execute_action()
else:
    escalate_to_human(judgment.escalation_level)
```

### Specialized Validations

```python
# Safety validation using Claude
safety_judgment = judge.validate_diagnosis_safety(diagnosis)

# SOP compliance using Claude
compliance_judgment = judge.validate_sop_compliance(repair_guide)

# Budget validation
budget_judgment = judge.validate_budget_constraints(purchase_request)
```

## Configuration

### AWS Setup

1. Configure AWS credentials:
   ```bash
   aws configure
   ```

2. Ensure Bedrock access in us-east-1:
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

3. Verify model access:
   - `us.amazon.nova-pro-v1:0`
   - `us.anthropic.claude-3-5-sonnet-20241022-v2:0`

### Judge Configuration

The judge automatically uses the Bedrock client from `config.py`:

```python
# config.py
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

NOVA_PRO_MODEL_ID = "us.amazon.nova-pro-v1:0"
CLAUDE_SONNET_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

## Performance

- **Validation Latency**: < 2 seconds (p95) with Claude
- **Scalability**: 100+ concurrent validations
- **Availability**: AWS-managed 99.9% uptime
- **Cost**: Pay-per-use Bedrock pricing

## Advantages Over Local Judge

1. **No Local Setup**: No Ollama or local model installation
2. **Latest Models**: Always use newest Claude and Nova versions
3. **Scalability**: Handle enterprise-scale deployments
4. **Reliability**: AWS-managed infrastructure
5. **Performance**: Optimized inference endpoints

## Compliance

- **Audit Retention**: 7 years (local SQLite)
- **Data Privacy**: Bedrock data handling policies
- **Sync Capability**: Optional central system sync
- **Incident Investigation**: Complete audit trail

## Error Handling

### Bedrock API Failures

```python
try:
    judgment = judge.validate_agent_output(output, criteria)
except RuntimeError as e:
    logger.error(f"Bedrock API failed: {e}")
    # Fallback to conservative validation
    halt_workflow()
```

### Network Issues

```python
# Implement retry logic with exponential backoff
import time
for attempt in range(3):
    try:
        judgment = judge.validate_agent_output(output, criteria)
        break
    except Exception:
        time.sleep(2 ** attempt)
```

## Testing

Run the example script:

```bash
python examples/cloud_judge_example.py
```

Expected output:
- Safety validation results from Claude
- Agent output validation
- Audit log statistics

## Cost Optimization

1. **Batch Validations**: Group similar validations
2. **Caching**: Cache validation results for identical inputs
3. **Model Selection**: Use Nova for simpler tasks, Claude for complex reasoning
4. **Prompt Optimization**: Minimize token usage in prompts

## Future Enhancements

1. **Nova Vision Integration**: Use Nova Pro for image-based safety checks
2. **Prompt Caching**: Bedrock prompt caching for repeated validations
3. **Batch API**: Use Bedrock batch inference for cost savings
4. **Custom Models**: Fine-tune models on company-specific SOPs
5. **Real-time Monitoring**: CloudWatch metrics for validation performance

## References

- Design Document: `.kiro/specs/autonomous-field-engineer/design.md`
- Requirements: Requirements 2.1-2.8, 6.1-6.8, 11.1-11.7
- Tasks: Task 2.1-2.2 in `tasks.md`
- AWS Bedrock: https://aws.amazon.com/bedrock/
- Claude 3.5 Sonnet: https://www.anthropic.com/claude
- Amazon Nova: https://aws.amazon.com/ai/generative-ai/nova/
