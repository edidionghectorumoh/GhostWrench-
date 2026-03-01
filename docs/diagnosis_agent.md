# DiagnosisAgent Documentation

## Overview

The `DiagnosisAgent` is a multimodal AI agent that analyzes site photos and telemetry data to diagnose infrastructure issues. It uses Amazon Nova Pro via AWS Bedrock for visual analysis and integrates with the RAG system for reference comparison.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DiagnosisAgent                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Nova Pro API │    │  RAG System  │    │  Telemetry   │ │
│  │   (Bedrock)  │    │  Integration │    │  Analyzer    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │        │
│         └────────────────────┴────────────────────┘        │
│                              │                             │
│                    ┌─────────▼─────────┐                   │
│                    │  Diagnosis Result │                   │
│                    └───────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Multimodal Image Analysis
- Analyzes site photos using Amazon Nova Pro
- Identifies equipment types automatically
- Detects hardware defects, installation errors, and malfunctions
- Provides confidence scores for each diagnosis

### 2. RAG Integration
- Retrieves relevant technical manual sections
- Compares site photos with reference images
- Identifies deviations from standard configurations
- Links to specific manual sections for repair guidance

### 3. Telemetry Correlation
- Analyzes time-series telemetry data
- Detects anomalies and baseline deviations
- Correlates visual evidence with telemetry patterns
- Adjusts confidence based on telemetry availability

### 4. Multi-Issue Detection
- Identifies multiple concurrent issues
- Prioritizes issues by severity
- Provides separate diagnosis for each issue
- Handles complex site scenarios

## API Reference

### DiagnosisAgent Class

#### `__init__(rag_system: Optional[RAGSystem] = None)`

Initialize the diagnosis agent.

**Parameters:**
- `rag_system` (Optional[RAGSystem]): RAG system instance for reference comparison. If None, creates a new instance.

**Example:**
```python
from src.agents.DiagnosisAgent import DiagnosisAgent
from src.rag.RAGSystem import RAGSystem

# With custom RAG system
rag = RAGSystem()
agent = DiagnosisAgent(rag_system=rag)

# With default RAG system
agent = DiagnosisAgent()
```

---

#### `diagnose_issue(diagnosis_input: DiagnosisInput) -> DiagnosisResult`

Perform multimodal diagnosis of infrastructure issue.

**Parameters:**
- `diagnosis_input` (DiagnosisInput): Input containing site context, images, technician notes, and optional telemetry

**Returns:**
- `DiagnosisResult`: Comprehensive diagnosis with issue type, confidence, root cause, required parts, and escalation info

**Example:**
```python
from src.models.agents import DiagnosisInput
from src.models.domain import SiteContext, ImageData

diagnosis_input = DiagnosisInput(
    site_context=SiteContext(
        site_id="SITE-001",
        location="Building A, Network Closet",
        equipment_type="network_switch",
        technician_id="TECH-123",
        skill_level="intermediate"
    ),
    images=[ImageData(...)],
    technician_notes="Switch showing amber lights",
    telemetry=None
)

result = agent.diagnose_issue(diagnosis_input)
print(f"Issue: {result.issue_type}, Confidence: {result.confidence}")
```

---

#### `compare_with_reference_materials(diagnosis_result: DiagnosisResult, site_context: SiteContext) -> Dict[str, Any]`

Compare diagnosis with reference materials from RAG system.

**Parameters:**
- `diagnosis_result` (DiagnosisResult): Initial diagnosis result
- `site_context` (SiteContext): Site context for equipment type filtering

**Returns:**
- `Dict[str, Any]`: Comparison results with deviations and manual sections

**Example:**
```python
result = agent.diagnose_issue(diagnosis_input)
comparison = agent.compare_with_reference_materials(result, site_context)

if comparison['deviations_found']:
    print("Deviations from standard configuration:")
    for deviation in comparison['deviations']:
        print(f"  - {deviation}")
```

---

#### `analyze_telemetry(telemetry: TelemetrySnapshot, site_context: SiteContext) -> Dict[str, Any]`

Analyze telemetry data for anomalies and patterns.

**Parameters:**
- `telemetry` (TelemetrySnapshot): Telemetry data with metrics and alerts
- `site_context` (SiteContext): Site context for baseline comparison

**Returns:**
- `Dict[str, Any]`: Analysis results with anomalies and confidence adjustment

**Example:**
```python
from src.models.domain import TelemetrySnapshot

telemetry = TelemetrySnapshot(
    timestamp=datetime.now(timezone.utc),
    metrics={"cpu_temperature": 85.5, "fan_speed_rpm": 0},
    alerts=["HIGH_TEMPERATURE", "FAN_FAILURE"],
    baseline_metrics={"cpu_temperature": 45.0, "fan_speed_rpm": 3000}
)

analysis = agent.analyze_telemetry(telemetry, site_context)
print(f"Anomalies: {analysis['anomalies']}")
print(f"Confidence adjustment: {analysis['confidence_adjustment']}")
```

---

#### `detect_multiple_issues(diagnosis_input: DiagnosisInput) -> List[DiagnosisResult]`

Detect and diagnose multiple concurrent issues.

**Parameters:**
- `diagnosis_input` (DiagnosisInput): Input with multiple images or complex scenarios

**Returns:**
- `List[DiagnosisResult]`: List of diagnosis results, one per detected issue

**Example:**
```python
# Multiple images showing different issues
diagnosis_input = DiagnosisInput(
    site_context=site_context,
    images=[network_image, power_image],
    technician_notes="Multiple issues observed",
    telemetry=None
)

issues = agent.detect_multiple_issues(diagnosis_input)
for i, issue in enumerate(issues, 1):
    print(f"Issue {i}: {issue.issue_type} (Priority: {issue.priority})")
```

---

## Issue Types

The agent can detect the following issue types:

- `hardware_defect`: Physical component failure or damage
- `installation_error`: Incorrect installation or configuration
- `network_failure`: Network connectivity or routing issues
- `electrical_malfunction`: Power or electrical system problems
- `environmental`: Temperature, humidity, or environmental issues
- `unknown`: Unable to determine specific issue type

## Confidence Scoring

Confidence scores range from 0.0 to 1.0:

- **0.90 - 1.00**: High confidence, proceed with diagnosis
- **0.80 - 0.89**: Good confidence, minor verification recommended
- **0.70 - 0.79**: Moderate confidence, additional photos recommended
- **< 0.70**: Low confidence, escalation required

## Escalation Criteria

The agent automatically determines escalation requirements based on:

1. **Low Confidence**: Confidence < 0.80 for critical equipment
2. **Safety Concerns**: Electrical, high voltage, or hazardous conditions
3. **High Complexity**: Multiple concurrent issues or unclear root cause
4. **Missing Information**: Insufficient visual or telemetry data

## Integration with Other Components

### RAG System Integration

The DiagnosisAgent integrates with the RAG system to:
- Retrieve relevant technical manual sections
- Compare site photos with reference images
- Identify configuration deviations
- Link to repair procedures

### Telemetry Integration

When telemetry data is available, the agent:
- Correlates visual evidence with metrics
- Detects anomalies and baseline deviations
- Adjusts confidence based on data quality
- Identifies patterns indicating specific failures

### Cloud Judge Integration

Diagnosis results are validated by the Cloud Judge for:
- Safety compliance
- SOP adherence
- Escalation appropriateness
- Quality assurance

## Performance Characteristics

- **Target Latency**: < 10 seconds at p95
- **Image Processing**: Supports JPEG, PNG formats up to 2048x1536
- **Concurrent Requests**: Handles multiple diagnosis requests in parallel
- **Retry Logic**: Automatic retry with exponential backoff for API failures

## Error Handling

The agent handles the following error scenarios:

1. **API Failures**: Retries with exponential backoff (max 3 attempts)
2. **Invalid Images**: Returns error with guidance for re-capture
3. **Missing Equipment Type**: Attempts automatic identification
4. **RAG System Unavailable**: Proceeds without reference comparison
5. **Telemetry Unavailable**: Proceeds with visual analysis only

## Best Practices

### For Optimal Results

1. **Image Quality**: Provide clear, well-lit photos from multiple angles
2. **Technician Notes**: Include detailed observations and context
3. **Telemetry Data**: Include when available for higher confidence
4. **Equipment Type**: Specify equipment type if known

### For Safety

1. **Always Review**: Human review required before executing repairs
2. **Escalation**: Follow escalation recommendations
3. **Safety Checks**: Verify safety compliance before proceeding
4. **Documentation**: Maintain audit trail of all diagnoses

## Example Workflows

### Basic Diagnosis Workflow

```python
# 1. Create diagnosis input
diagnosis_input = DiagnosisInput(
    site_context=site_context,
    images=[image],
    technician_notes="Issue description",
    telemetry=None
)

# 2. Perform diagnosis
result = agent.diagnose_issue(diagnosis_input)

# 3. Check confidence and escalation
if result.confidence < 0.80 or result.escalation_required:
    print(f"Escalation required: {result.escalation_reason}")
else:
    print(f"Diagnosis complete: {result.description}")
```

### Enhanced Diagnosis with RAG

```python
# 1. Perform diagnosis
result = agent.diagnose_issue(diagnosis_input)

# 2. Compare with reference materials
comparison = agent.compare_with_reference_materials(result, site_context)

# 3. Review deviations
if comparison['deviations_found']:
    for deviation in comparison['deviations']:
        print(f"Deviation: {deviation}")
```

### Diagnosis with Telemetry

```python
# 1. Include telemetry in input
diagnosis_input = DiagnosisInput(
    site_context=site_context,
    images=[image],
    technician_notes="Issue description",
    telemetry=telemetry_snapshot
)

# 2. Perform diagnosis (telemetry automatically analyzed)
result = agent.diagnose_issue(diagnosis_input)

# 3. Review telemetry correlation
print(f"Confidence: {result.confidence}")
print(f"Telemetry correlation: {result.supporting_evidence}")
```

## Troubleshooting

### Low Confidence Scores

**Problem**: Diagnosis returns confidence < 0.70

**Solutions:**
- Capture additional photos from different angles
- Provide more detailed technician notes
- Include telemetry data if available
- Verify image quality and lighting

### Missing Equipment Type

**Problem**: Equipment type not automatically identified

**Solutions:**
- Manually specify equipment type in site context
- Capture closer photos of equipment labels
- Include equipment model/serial number in notes

### RAG System Not Finding References

**Problem**: No relevant manual sections found

**Solutions:**
- Verify equipment type is correct
- Check if manuals are ingested for this equipment
- Use generic equipment type for broader search
- Proceed without reference comparison if necessary

## Future Enhancements

Planned improvements for future versions:

1. **Video Analysis**: Support for video input for dynamic issues
2. **3D Reconstruction**: Generate 3D models from multiple photos
3. **Predictive Maintenance**: Identify issues before failure
4. **Thermal Imaging**: Support for thermal camera input
5. **AR Overlay**: Augmented reality annotations for technicians

## Related Documentation

- [RAG System Documentation](./rag_system.md)
- [Cloud Judge Architecture](./cloud_judge_architecture.md)
- [Data Models Reference](../src/models/README.md)
- [API Examples](../examples/diagnosis_agent_example.py)
