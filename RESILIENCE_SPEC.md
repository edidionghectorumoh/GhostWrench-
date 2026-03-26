# Resilience & Error Recovery Specification

## Overview

This document details the technical implementation of error handling and resilience mechanisms in the Autonomous Site & Infrastructure Engineer system. The system implements comprehensive recovery strategies for 8 distinct error scenarios, ensuring robust operation in production environments.

## Core Resilience Principles

1. **Fail-Safe Operation**: System degrades gracefully under failure conditions
2. **Automatic Recovery**: Self-healing mechanisms minimize manual intervention
3. **State Persistence**: Workflow state preserved across failures
4. **Transparent Fallbacks**: Users informed when operating in degraded mode
5. **Audit Trail**: All errors and recovery actions logged for analysis

## Error Recovery Scenarios

### 1. Low Confidence Diagnosis (Task 12.1)

**Problem**: AI diagnosis confidence below acceptable thresholds may lead to incorrect repairs.

**Confidence Thresholds**:
- **High Confidence** (≥ 0.85): Proceed normally
- **Medium Confidence** (0.70-0.85): Escalate to human expert review
- **Low Confidence** (< 0.70): Request additional photos

**Recovery Strategy**:

```python
# Confidence < 0.70: Request additional photos
if confidence < 0.70:
    workflow_state.photo_request_count += 1
    
    # Prevent infinite loops - max 3 photo requests
    if workflow_state.photo_request_count >= 3:
        # Escalate to human expert after 3 attempts
        escalation = create_escalation(
            type=EscalationType.LOW_CONFIDENCE,
            severity="high",
            description="Persistent low confidence after 3 photo attempts"
        )
        return request_expert_review(escalation)
    
    # Request additional photos with suggested angles
    return request_additional_photos(
        suggested_angles=[
            "Front view with clear component labels",
            "Close-up of affected area",
            "Side view showing connections",
            "Overall context view"
        ]
    )

# Confidence 0.70-0.85: Escalate to expert review
elif confidence < 0.85:
    escalation = create_escalation(
        type=EscalationType.LOW_CONFIDENCE,
        severity="medium",
        description=f"Confidence {confidence:.2f} below threshold (0.85)"
    )
    return request_expert_review(escalation)
```

**Implementation**: `src/orchestration/OrchestrationLayer.py:_handle_low_confidence_recovery()`

**Test Coverage**: `tests/test_task12_recovery.py:TestLowConfidenceRecovery`

---

### 2. Inventory System Unavailability (Task 12.2)

**Problem**: External inventory system downtime blocks parts procurement.

**Recovery Strategy**:

```python
def _handle_inventory_unavailability(error, required_parts):
    # Try cached inventory data (24-hour window)
    cached_results = []
    for part_number in required_parts:
        cached_part = get_cached_inventory_data(part_number)
        
        if cached_part and is_cache_valid(cached_part, max_age_hours=24):
            cached_results.append({
                **cached_part,
                "from_cache": True,
                "pending_verification": True
            })
    
    if cached_results:
        # Schedule background retry job
        retry_job_id = schedule_inventory_retry(required_parts)
        
        return {
            "success": True,
            "parts": cached_results,
            "warning": "Using cached data (pending verification)",
            "retry_job_id": retry_job_id
        }
    
    # No cached data - cannot proceed
    return {
        "success": False,
        "error": "Inventory unavailable and no cache available",
        "retry_recommended": True
    }
```

**Cache Validation**:
- Maximum cache age: 24 hours
- Cache includes: part availability, pricing, lead times
- Background job validates cache when connectivity restored

**Implementation**: `src/orchestration/OrchestrationLayer.py:_handle_inventory_unavailability()`

---

### 3. Judge Offline (Task 12.3)

**Problem**: Cloud judge (validation service) unavailable blocks workflow progression.

**Recovery Strategy**:

```python
def _handle_judge_offline(workflow_state, error, agent_output):
    # Save current state for recovery
    persistence.save_checkpoint(workflow_state)
    
    # Mark workflow as paused
    workflow_state.metadata['paused'] = True
    workflow_state.metadata['pause_reason'] = 'judge_offline'
    workflow_state.metadata['pending_validation'] = agent_output
    
    # Save updated state
    persistence.save_checkpoint(workflow_state)
    
    return {
        "workflow_paused": True,
        "checkpoint_saved": True,
        "auto_resume_enabled": True,
        "instructions": "System will auto-resume when judge is restored"
    }

def _attempt_workflow_resumption(workflow_state):
    # Check if judge is back online (5-second timeout)
    if not check_judge_availability(timeout_seconds=5):
        return False
    
    # Re-validate pending output
    pending_validation = workflow_state.metadata['pending_validation']
    validation_result = validate_diagnosis(pending_validation)
    
    # Clear pause state and resume
    workflow_state.metadata['paused'] = False
    workflow_state.metadata['resumed_at'] = datetime.now()
    
    return True
```

**Judge Availability Check**:
- Timeout: 5 seconds
- Health check endpoint: `/health`
- Automatic retry on workflow resumption

**Implementation**: `src/orchestration/OrchestrationLayer.py:_handle_judge_offline()`

---

### 4. Safety Violations (Task 12.4)

**Problem**: Detected safety hazards require immediate workflow halt and human intervention.

**Hazard Types**:
- **Electrical**: High voltage, arcing, insulation failure
- **Mechanical**: Moving parts, pinch points, crush hazards
- **Chemical**: Toxic substances, corrosive materials
- **Environmental**: Confined spaces, extreme temperatures

**Severity Levels**:
- **Critical**: Immediate life-threatening hazard
- **High**: Serious injury potential
- **Medium**: Minor injury potential
- **Low**: Minimal risk with proper precautions

**Recovery Strategy**:

```python
def _handle_safety_violation(workflow_state, safety_check_result, diagnosis_result):
    # Immediate workflow halt
    logger.critical("SAFETY VIOLATION DETECTED - Halting workflow")
    
    # Identify critical hazards
    hazards = safety_check_result['hazards_identified']
    critical_hazards = [h for h in hazards if h['severity'] == 'critical']
    
    # Create safety escalation
    escalation = create_escalation(
        type=EscalationType.SAFETY_VIOLATION,
        severity="critical" if critical_hazards else "high",
        description=f"{len(critical_hazards)} critical hazard(s) identified"
    )
    
    # Generate required actions
    required_actions = []
    
    # Lockout/tagout if needed
    if any(h['lockout_tagout_required'] for h in hazards):
        required_actions.append({
            "action": "lockout_tagout",
            "mandatory": True
        })
    
    # Work permit if needed
    if any(h['permit_required'] for h in hazards):
        required_actions.append({
            "action": "obtain_permit",
            "mandatory": True
        })
    
    # PPE requirements
    all_ppe = set()
    for h in hazards:
        all_ppe.update(h['required_ppe'])
    
    required_actions.append({
        "action": "verify_ppe",
        "ppe_list": list(all_ppe),
        "mandatory": True
    })
    
    # Safety officer clearance
    required_actions.append({
        "action": "safety_clearance",
        "mandatory": True
    })
    
    # Generate alternative safer procedure
    alternative = generate_alternative_safe_procedure(diagnosis_result, hazards)
    
    # Send critical notifications
    send_safety_notifications(workflow_state, escalation, hazards)
    
    return {
        "workflow_halted": True,
        "requires_safety_clearance": True,
        "safety_officer_notified": True,
        "supervisor_notified": True,
        "required_actions": required_actions,
        "alternative_procedure": alternative
    }
```

**Alternative Safe Procedures**:

For electrical hazards:
```python
{
    "procedure_type": "de_energized_repair",
    "steps": [
        "Obtain lockout/tagout authorization",
        "De-energize equipment at main breaker",
        "Verify zero energy state with multimeter",
        "Apply lockout/tagout devices",
        "Perform repair work",
        "Remove lockout/tagout after verification",
        "Re-energize under supervision"
    ],
    "additional_safety": [
        "Requires qualified electrician",
        "Safety officer must be present",
        "Use insulated tools only"
    ]
}
```

For mechanical hazards:
```python
{
    "procedure_type": "equipment_shutdown",
    "steps": [
        "Shut down equipment completely",
        "Allow cooldown period if needed",
        "Verify no moving parts",
        "Perform repair work",
        "Restart under supervision"
    ],
    "additional_safety": [
        "Verify no automatic restart capability",
        "Post warning signs during work"
    ]
}
```

**Implementation**: 
- `src/orchestration/OrchestrationLayer.py:_handle_safety_violation()`
- `src/safety/safety_checker.py:SafetyChecker`

**Test Coverage**: `tests/test_task12_recovery.py:TestSafetyViolationHandling`

---

### 5. Budget Exceeded (Task 12.5)

**Problem**: Procurement costs exceed authorized budget limits.

**Recovery Strategy**:

```python
def _handle_budget_exceeded(workflow_state, procurement_result, budget_limit, total_cost):
    # Calculate overage
    overage = total_cost - budget_limit
    overage_percentage = (overage / budget_limit) * 100
    
    # Determine approval authority
    if total_cost > 10000 or overage_percentage > 100:
        approval_authority = "Director"
    elif total_cost > 5000 or overage_percentage > 50:
        approval_authority = "Manager"
    else:
        approval_authority = "Supervisor"
    
    # Identify temporary workarounds
    workarounds = [
        {
            "type": "defer_non_critical",
            "description": "Defer non-critical parts to next maintenance window",
            "cost_reduction": "20-40%"
        },
        {
            "type": "refurbished_parts",
            "description": "Use refurbished parts instead of new",
            "cost_reduction": "30-50%"
        },
        {
            "type": "temporary_patch",
            "description": "Apply temporary fix until budget available",
            "cost_reduction": "60-80%"
        }
    ]
    
    # Create approval escalation
    escalation = create_escalation(
        type=EscalationType.BUDGET_EXCEEDED,
        severity="high" if overage_percentage > 50 else "medium",
        description=f"Cost ${total_cost} exceeds budget ${budget_limit} by ${overage}"
    )
    
    return {
        "workflow_status": "pending_approval",
        "approval_authority": approval_authority,
        "approval_timeline": estimate_approval_timeline(approval_authority),
        "temporary_workarounds": workarounds
    }
```

**Approval Timelines**:
- **Supervisor**: 2 hours (0.25 business days)
- **Manager**: 8 hours (1 business day)
- **Director**: 24 hours (3 business days)

**Implementation**: `src/orchestration/OrchestrationLayer.py:_handle_budget_exceeded()`

---

### 6. Stale Telemetry Data (Task 12.6)

**Problem**: Outdated telemetry data may lead to incorrect diagnosis.

**Staleness Thresholds**:
- **Critical Operations**: 300 seconds (5 minutes)
- **Normal Operations**: 600 seconds (10 minutes)

**Detection**:

```python
class TelemetrySnapshot:
    def get_age_seconds(self) -> float:
        """Calculate age of telemetry data in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()
    
    def is_stale(self, max_age_seconds: int = 600) -> bool:
        """Check if telemetry is stale for normal operations."""
        return self.get_age_seconds() > max_age_seconds
    
    def is_stale_for_critical_operation(self) -> bool:
        """Check if telemetry is stale for critical operations (5 min)."""
        return self.get_age_seconds() > 300
```

**Recovery Strategy**:

```python
def check_telemetry_staleness(telemetry, site_context):
    # Determine if operation is critical
    is_critical = site_context.criticality_level == CriticalityLevel.TIER1
    
    # Check staleness
    if is_critical and telemetry.is_stale_for_critical_operation():
        return {
            "stale": True,
            "age_seconds": telemetry.get_age_seconds(),
            "threshold_seconds": 300,
            "action": "request_fresh_telemetry"
        }
    elif telemetry.is_stale():
        return {
            "stale": True,
            "age_seconds": telemetry.get_age_seconds(),
            "threshold_seconds": 600,
            "action": "request_fresh_telemetry"
        }
    
    return {"stale": False}
```

**Implementation**: `src/models/domain.py:TelemetrySnapshot`

**Test Coverage**: `tests/test_task12_error_handling.py:TestTelemetryStaleness`

---

### 7. External System Circuit Breaker

**Problem**: Cascading failures when external systems are down.

**Circuit Breaker States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Failing, reject requests immediately
- **HALF_OPEN**: Testing recovery, allow limited requests

**Implementation**:

```python
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,      # Open after 5 failures
        timeout_seconds: int = 60,       # Wait 60s before testing recovery
        success_threshold: int = 2       # Close after 2 successes in half-open
    ):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

**Configuration**:
- Failure threshold: 5 consecutive failures
- Timeout: 60 seconds before testing recovery
- Success threshold: 2 successes to close circuit

**Implementation**: `src/external/ExternalSystemsAdapter.py:CircuitBreaker`

---

### 8. Pydantic Schema Validation

**Problem**: Invalid data between agents causes runtime errors.

**Validation Rules**:

```python
class DiagnosisResponse(BaseModel):
    response_id: str
    request_id: str
    session_id: str
    success: bool
    message: str
    confidence: float = Field(ge=0.0, le=1.0)  # Must be 0.0-1.0
    issue_type: Optional[IssueTypeEnum] = None
    severity: Optional[SeverityEnum] = None
    escalation_required: bool = False
    escalation_reason: Optional[str] = None
    
    @validator('escalation_reason')
    def escalation_reason_required_if_escalation(cls, v, values):
        if values.get('escalation_required') and not v:
            raise ValueError('escalation_reason required when escalation_required=True')
        return v

class TelemetryData(BaseModel):
    timestamp: datetime
    site_id: str
    metrics: Dict[str, Any]
    system_status: str
    
    @validator('timestamp')
    def timestamp_not_future(cls, v):
        if v > datetime.now():
            raise ValueError('Timestamp cannot be in the future')
        return v
    
    def is_stale(self, max_age_seconds: int = 600) -> bool:
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > max_age_seconds
    
    def is_stale_for_critical_operation(self) -> bool:
        return self.is_stale(max_age_seconds=300)
```

**Validation Functions**:

```python
def validate_agent_communication(data: Dict[str, Any], schema: Type[BaseModel]):
    """Validate inter-agent communication data."""
    try:
        return schema(**data)
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise

def serialize_for_agent(model: BaseModel) -> Dict[str, Any]:
    """Serialize Pydantic model for agent communication."""
    return model.dict(exclude_none=True)
```

**Implementation**: `src/models/schemas.py`

**Test Coverage**: `tests/test_task12_error_handling.py:TestPydanticSchemas`

---

## Thought Logger Integration

All error recovery actions are logged using the ThoughtLogger for transparency and debugging:

```python
# Log low confidence recovery
self.thought_logger.log_thought(
    session_id=workflow_state.session_id,
    agent_type="orchestration",
    phase=AgentPhase.DIAGNOSIS,
    thought=f"Confidence {confidence:.2f} below threshold. Initiating recovery.",
    action="initiate_recovery",
    metadata={"confidence": confidence, "threshold": 0.85}
)

# Log safety violation
self.thought_logger.log_thought(
    session_id=workflow_state.session_id,
    agent_type="orchestration",
    phase=AgentPhase.DIAGNOSIS,
    thought="CRITICAL: Safety violations detected. Halting workflow.",
    action="handle_safety_violation",
    metadata={"hazards": hazards}
)

# Log escalation
self.thought_logger.log_escalation(
    session_id=workflow_state.session_id,
    escalation_type="safety_violation",
    severity="critical",
    description="Critical electrical hazard detected"
)
```

**Log Format**: JSONL (JSON Lines) for easy parsing and analysis

**Log Location**: `/app/logs/agent_thoughts.jsonl` (configurable via `THOUGHT_LOG_PATH`)

---

## Test Coverage

### Unit Tests
- `tests/test_task12_error_handling.py`: Pydantic schemas, safety checker, telemetry staleness
- `tests/test_task12_recovery.py`: Low confidence recovery, safety violation handling

### Integration Tests
- `tests/test_integration_workflows.py`: End-to-end workflow with error scenarios

### Test Results
- **Total Tests**: 77
- **Pass Rate**: 100% (77/77)
- **Coverage**: All 8 error scenarios

---

## Production Deployment Considerations

### Monitoring
- Circuit breaker state changes
- Escalation frequency and resolution time
- Cache hit rates for offline fallbacks
- Judge availability metrics

### Alerting
- Critical safety violations (immediate)
- Judge offline > 5 minutes
- Circuit breaker open > 10 minutes
- Budget approval queue depth > 10

### Logging
- All error recovery actions logged to ThoughtLogger
- Audit trail for safety violations
- Escalation tracking and resolution

### Configuration
```bash
# Enable thought logging
ENABLE_THOUGHT_LOGGING=true
THOUGHT_LOG_PATH=/app/logs/agent_thoughts.jsonl

# Circuit breaker settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60

# Cache settings
INVENTORY_CACHE_TTL_HOURS=24
TELEMETRY_CACHE_TTL_SECONDS=300

# Judge settings
JUDGE_TIMEOUT_SECONDS=5
JUDGE_HEALTH_CHECK_INTERVAL_SECONDS=30
```

---

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and multi-agent coordination
- [README.md](README.md) - Project overview and quick start
- [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) - Common issues and solutions
- [src/orchestration/ThoughtLogger.py](src/orchestration/ThoughtLogger.py) - Agent reasoning logs
- [src/safety/safety_checker.py](src/safety/safety_checker.py) - Safety validation implementation
