"""
Pydantic Schemas for Inter-Agent Communication

Provides type-safe, validated data structures for all agent interactions.
Uses Pydantic for automatic JSON schema generation and validation.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RequestTypeEnum(str, Enum):
    """Request type enumeration."""
    DIAGNOSIS = "diagnosis"
    PROCUREMENT = "procurement"
    GUIDANCE = "guidance"


class IssueTypeEnum(str, Enum):
    """Issue type enumeration."""
    HARDWARE_DEFECT = "hardware_defect"
    INSTALLATION_ERROR = "installation_error"
    NETWORK_FAILURE = "network_failure"
    ELECTRICAL_MALFUNCTION = "electrical_malfunction"
    ENVIRONMENTAL = "environmental"


class SeverityEnum(str, Enum):
    """Severity enumeration."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentTypeEnum(str, Enum):
    """Agent type enumeration."""
    DIAGNOSIS = "diagnosis"
    ACTION = "action"
    GUIDANCE = "guidance"


# ============================================================================
# Request/Response Schemas
# ============================================================================

class AgentRequest(BaseModel):
    """Base schema for agent requests."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    request_id: str = Field(..., description="Unique request identifier")
    session_id: str = Field(..., description="Session identifier")
    technician_id: str = Field(..., description="Technician identifier")
    site_id: str = Field(..., description="Site identifier")
    request_type: RequestTypeEnum = Field(..., description="Type of request")
    timestamp: datetime = Field(default_factory=datetime.now, description="Request timestamp")
    
    @field_validator('request_id', 'session_id', 'technician_id', 'site_id')
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate ID fields are not empty."""
        if not v or not v.strip():
            raise ValueError("ID fields cannot be empty")
        return v.strip()


class AgentResponse(BaseModel):
    """Base schema for agent responses."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    response_id: str = Field(..., description="Unique response identifier")
    request_id: str = Field(..., description="Original request identifier")
    session_id: str = Field(..., description="Session identifier")
    agent_type: AgentTypeEnum = Field(..., description="Agent that generated response")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Human-readable message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response data")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")


# ============================================================================
# Diagnosis Schemas
# ============================================================================

class DiagnosisRequest(AgentRequest):
    """Schema for diagnosis requests."""
    request_type: RequestTypeEnum = Field(default=RequestTypeEnum.DIAGNOSIS, frozen=True)
    
    image_data: Optional[Dict[str, Any]] = Field(None, description="Image data")
    telemetry_data: Optional[Dict[str, Any]] = Field(None, description="Telemetry data")
    site_context: Dict[str, Any] = Field(..., description="Site context information")
    description: str = Field(..., description="Issue description from technician")
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is not empty."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v.strip()


class DiagnosisResponse(AgentResponse):
    """Schema for diagnosis responses."""
    agent_type: AgentTypeEnum = Field(default=AgentTypeEnum.DIAGNOSIS, frozen=True)
    
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    issue_type: Optional[IssueTypeEnum] = Field(None, description="Identified issue type")
    severity: Optional[SeverityEnum] = Field(None, description="Issue severity")
    root_cause: Optional[str] = Field(None, description="Root cause analysis")
    requires_parts: bool = Field(default=False, description="Whether parts are needed")
    recommended_parts: List[str] = Field(default_factory=list, description="Recommended parts")
    safety_concerns: List[str] = Field(default_factory=list, description="Safety concerns identified")
    escalation_required: bool = Field(default=False, description="Whether escalation is needed")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    @field_validator('escalation_reason')
    @classmethod
    def validate_escalation_reason(cls, v: Optional[str], info) -> Optional[str]:
        """Validate escalation reason is provided when escalation is required."""
        if info.data.get('escalation_required') and not v:
            raise ValueError("Escalation reason required when escalation_required is True")
        return v


# ============================================================================
# Procurement Schemas
# ============================================================================

class ProcurementRequest(AgentRequest):
    """Schema for procurement requests."""
    request_type: RequestTypeEnum = Field(default=RequestTypeEnum.PROCUREMENT, frozen=True)
    
    diagnosis_result: Dict[str, Any] = Field(..., description="Diagnosis result")
    required_parts: List[str] = Field(..., min_length=1, description="Required parts list")
    urgency: str = Field(..., description="Urgency level")
    budget_limit: Optional[float] = Field(None, ge=0, description="Budget limit if any")
    
    @field_validator('required_parts')
    @classmethod
    def validate_required_parts(cls, v: List[str]) -> List[str]:
        """Validate required parts list is not empty."""
        if not v:
            raise ValueError("Required parts list cannot be empty")
        return v


class ProcurementResponse(AgentResponse):
    """Schema for procurement responses."""
    agent_type: AgentTypeEnum = Field(default=AgentTypeEnum.ACTION, frozen=True)
    
    parts_found: List[Dict[str, Any]] = Field(default_factory=list, description="Parts found")
    total_cost: float = Field(..., ge=0, description="Total cost")
    po_number: Optional[str] = Field(None, description="Purchase order number")
    approval_status: str = Field(..., description="Approval status")
    estimated_delivery: Optional[str] = Field(None, description="Estimated delivery date")
    budget_exceeded: bool = Field(default=False, description="Whether budget was exceeded")
    
    @field_validator('total_cost')
    @classmethod
    def validate_total_cost(cls, v: float) -> float:
        """Validate total cost is non-negative."""
        if v < 0:
            raise ValueError("Total cost cannot be negative")
        return v


# ============================================================================
# Guidance Schemas
# ============================================================================

class GuidanceRequest(AgentRequest):
    """Schema for guidance requests."""
    request_type: RequestTypeEnum = Field(default=RequestTypeEnum.GUIDANCE, frozen=True)
    
    diagnosis_result: Dict[str, Any] = Field(..., description="Diagnosis result")
    procurement_result: Optional[Dict[str, Any]] = Field(None, description="Procurement result if any")
    technician_skill_level: str = Field(..., description="Technician skill level")
    
    @field_validator('technician_skill_level')
    @classmethod
    def validate_skill_level(cls, v: str) -> str:
        """Validate skill level is valid."""
        valid_levels = ["novice", "intermediate", "advanced", "expert"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Skill level must be one of: {', '.join(valid_levels)}")
        return v.lower()


class GuidanceResponse(AgentResponse):
    """Schema for guidance responses."""
    agent_type: AgentTypeEnum = Field(default=AgentTypeEnum.GUIDANCE, frozen=True)
    
    total_steps: int = Field(..., ge=1, description="Total number of steps")
    estimated_duration_minutes: int = Field(..., ge=1, description="Estimated duration")
    skill_level_required: str = Field(..., description="Required skill level")
    safety_precautions: List[str] = Field(default_factory=list, description="Safety precautions")
    steps: List[Dict[str, Any]] = Field(..., min_length=1, description="Repair steps")
    repair_complete: bool = Field(default=False, description="Whether repair is complete")
    
    @field_validator('steps')
    @classmethod
    def validate_steps(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate steps list is not empty."""
        if not v:
            raise ValueError("Steps list cannot be empty")
        return v


# ============================================================================
# Telemetry Schemas
# ============================================================================

class TelemetryData(BaseModel):
    """Schema for telemetry data with staleness checking."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    timestamp: datetime = Field(..., description="Telemetry timestamp")
    site_id: str = Field(..., description="Site identifier")
    metrics: Dict[str, Any] = Field(..., description="Telemetry metrics")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Active alerts")
    system_status: str = Field(..., description="System status")
    
    def is_stale(self, max_age_seconds: int = 600) -> bool:
        """
        Check if telemetry data is stale.
        
        Args:
            max_age_seconds: Maximum age in seconds
                - 300 (5 min) for critical operations
                - 600 (10 min, default) for normal operations
            
        Returns:
            True if data is stale
        """
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > max_age_seconds
    
    def is_stale_for_critical_operation(self) -> bool:
        """
        Check if telemetry is stale for critical operations (5-minute threshold).
        
        Returns:
            True if data is too old for critical operations
        """
        return self.is_stale(max_age_seconds=300)
    
    def get_age_seconds(self) -> float:
        """Get age of telemetry data in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is not in the future."""
        if v > datetime.now():
            raise ValueError("Timestamp cannot be in the future")
        return v


# ============================================================================
# Safety Schemas
# ============================================================================

class SafetyCheckRequest(BaseModel):
    """Schema for safety check requests."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    check_id: str = Field(..., description="Safety check identifier")
    diagnosis_result: Dict[str, Any] = Field(..., description="Diagnosis result")
    site_context: Dict[str, Any] = Field(..., description="Site context")
    repair_actions: List[Dict[str, Any]] = Field(..., description="Planned repair actions")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")


class SafetyCheckResponse(BaseModel):
    """Schema for safety check responses."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    check_id: str = Field(..., description="Safety check identifier")
    timestamp: datetime = Field(..., description="Check timestamp")
    status: str = Field(..., description="Safety status")
    hazards_identified: List[Dict[str, Any]] = Field(default_factory=list, description="Hazards")
    violations: List[str] = Field(default_factory=list, description="Violations")
    required_actions: List[str] = Field(default_factory=list, description="Required actions")
    approved_to_proceed: bool = Field(..., description="Whether work can proceed")
    escalation_required: bool = Field(default=False, description="Whether escalation needed")
    escalation_reason: Optional[str] = Field(None, description="Escalation reason")


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_agent_communication(
    data: Dict[str, Any],
    schema_class: type[BaseModel]
) -> BaseModel:
    """
    Validate inter-agent communication data against schema.
    
    Args:
        data: Data to validate
        schema_class: Pydantic schema class
        
    Returns:
        Validated Pydantic model instance
        
    Raises:
        ValidationError: If validation fails
    """
    return schema_class(**data)


def serialize_for_agent(model: BaseModel) -> Dict[str, Any]:
    """
    Serialize Pydantic model for agent communication.
    
    Args:
        model: Pydantic model instance
        
    Returns:
        JSON-serializable dictionary
    """
    return model.model_dump(mode='json')
