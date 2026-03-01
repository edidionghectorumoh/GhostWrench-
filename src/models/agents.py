"""
Agent interface models for the Autonomous Field Engineer system.
Defines request/response structures for AI agents and their interactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from .domain import ImageData, TelemetrySnapshot, SiteContext, Component, Tool, SkillLevel


class RequestType(str, Enum):
    """Field request type classification."""
    DIAGNOSIS = "diagnosis"
    GUIDANCE = "guidance"
    PROCUREMENT = "procurement"


class ResponseStatus(str, Enum):
    """Field response status."""
    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"


class IssueType(str, Enum):
    """Diagnosis issue type classification."""
    HARDWARE_DEFECT = "hardware_defect"
    INSTALLATION_ERROR = "installation_error"
    NETWORK_FAILURE = "network_failure"
    ELECTRICAL_MALFUNCTION = "electrical_malfunction"
    ENVIRONMENTAL = "environmental"


class Severity(str, Enum):
    """Issue severity level."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Urgency(str, Enum):
    """Action urgency level."""
    EMERGENCY = "emergency"
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"


class VoiceIntent(str, Enum):
    """Voice command intent classification."""
    NEXT_STEP = "next_step"
    REPEAT = "repeat"
    CLARIFICATION = "clarification"
    EMERGENCY = "emergency"
    COMPLETION = "completion"
    SAFETY_ACKNOWLEDGED = "safety_acknowledged"


class ActionType(str, Enum):
    """Action type for agentic operations."""
    INVENTORY_SEARCH = "inventory_search"
    COST_ESTIMATE = "cost_estimate"
    PURCHASE_REQUEST = "purchase_request"
    TELEMETRY_QUERY = "telemetry_query"


class ActionStatus(str, Enum):
    """Action execution status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass
class FieldRequest:
    """
    Request from field technician to the system.
    """
    session_id: str
    technician_id: str
    site_id: str
    request_type: RequestType
    image_data: Optional[ImageData] = None
    voice_input: Optional[bytes] = None  # AudioData
    telemetry_data: Optional[TelemetrySnapshot] = None


@dataclass
class ManualReference:
    """Reference to technical manual section."""
    manual_id: str
    section_id: str
    title: str
    page_number: Optional[int] = None
    relevance_score: float = 0.0


@dataclass
class AnnotatedImage:
    """Image with annotations marking identified issues."""
    image_id: str
    original_image: bytes
    annotations: List[Dict[str, Any]]  # List of annotation objects
    annotated_image: Optional[bytes] = None


@dataclass
class Action:
    """Recommended action from diagnosis."""
    action_id: str
    action_type: str
    description: str
    urgency: Urgency
    requires_parts: bool = False
    estimated_duration_minutes: Optional[int] = None


@dataclass
class DiagnosisResult:
    """
    Result from multimodal diagnosis agent.
    
    Validation Rules:
    - confidence must be between 0.0 and 1.0
    - affected_components must be non-empty
    - reference_manual_sections must contain at least one reference
    - if severity is critical, recommended_actions must be non-empty
    """
    issue_id: str
    issue_type: IssueType
    severity: Severity
    confidence: float
    description: str
    affected_components: List[Component]
    root_cause: str
    visual_evidence: AnnotatedImage
    reference_manual_sections: List[ManualReference]
    recommended_actions: List[Action]
    
    def __post_init__(self):
        """Validate diagnosis result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Invalid confidence: {self.confidence}")
        if not self.affected_components:
            raise ValueError("affected_components cannot be empty")
        if not self.reference_manual_sections:
            raise ValueError("reference_manual_sections cannot be empty")
        if self.severity == Severity.CRITICAL and not self.recommended_actions:
            raise ValueError("Critical severity requires recommended_actions")


@dataclass
class ComparisonResult:
    """Result from comparing site image with reference materials."""
    deviations_found: List[Dict[str, Any]]
    compliance_status: str  # "compliant", "non_compliant", "partial"
    reference_images: List[Dict[str, Any]]
    annotated_differences: AnnotatedImage


@dataclass
class DiagnosisInput:
    """Input for diagnosis agent."""
    image_data: ImageData
    equipment_type: Optional[str] = None
    site_context: Optional[SiteContext] = None
    telemetry_data: Optional[TelemetrySnapshot] = None
    technician_notes: Optional[str] = None


@dataclass
class ActionResult:
    """Result from action agent execution."""
    action_id: str
    status: ActionStatus
    data: Any
    execution_time: float
    errors: Optional[List[str]] = None


@dataclass
class InventorySearchResult:
    """Result from inventory search."""
    matched_parts: List[Any]  # List[Part]
    alternative_parts: List[Any]  # List[Part]
    lead_times: Dict[str, int]  # part_number -> days
    suppliers: List[Dict[str, Any]]


@dataclass
class PurchaseRequest:
    """Purchase request for parts procurement."""
    request_id: str
    parts: List[Any]  # List[Part]
    total_cost: float
    justification: str
    urgency: Urgency
    site_id: str
    technician_id: str
    approval_status: str  # "pending", "approved", "rejected"
    estimated_delivery: Optional[datetime] = None


@dataclass
class SafetyWarning:
    """Safety warning for repair procedure."""
    warning_id: str
    severity: Severity
    description: str
    required_ppe: List[str]
    hazard_type: str


@dataclass
class SOPReference:
    """Reference to Standard Operating Procedure."""
    sop_id: str
    title: str
    version: str
    section: Optional[str] = None


@dataclass
class GuidanceStep:
    """Single step in repair guidance."""
    step_number: int
    instruction: str
    voice_script: str
    visual_aid: Optional[str] = None  # Image reference
    safety_checks: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    troubleshooting_tips: List[str] = field(default_factory=list)
    estimated_time: int = 0  # minutes


@dataclass
class RepairGuide:
    """Complete repair guide for technician."""
    guide_id: str
    issue_id: str
    steps: List[GuidanceStep]
    estimated_duration: int  # minutes
    required_tools: List[Tool]
    safety_warnings: List[SafetyWarning]
    sop_references: List[SOPReference]
    skill_level_required: SkillLevel


@dataclass
class VoiceResponse:
    """Response from voice guidance agent."""
    transcription: str
    intent: VoiceIntent
    audio_response: bytes
    text_response: str
    requires_human_escalation: bool = False


@dataclass
class SafetyValidation:
    """Safety validation result."""
    is_compliant: bool
    violations: List[str]
    required_ppe: List[str]
    environmental_hazards: List[str]
    lockout_tagout_required: bool


@dataclass
class FieldResponse:
    """Response to field technician request."""
    session_id: str
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    next_phase: Optional[str] = None
    status: Optional[ResponseStatus] = None
    diagnosis: Optional[DiagnosisResult] = None
    actions: Optional[List[ActionResult]] = None
    guidance: Optional[RepairGuide] = None
    validation_status: Optional[Any] = None  # ValidationResult
    error_message: Optional[str] = None
