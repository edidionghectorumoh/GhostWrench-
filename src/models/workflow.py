"""
Workflow state models for the Autonomous Field Engineer system.
Defines workflow phases, state tracking, and escalation handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from .agents import DiagnosisResult, PurchaseRequest, RepairGuide
from .validation import JudgmentResult


class WorkflowPhase(str, Enum):
    """Workflow phase enumeration."""
    INTAKE = "intake"
    DIAGNOSIS = "diagnosis"
    PROCUREMENT = "procurement"
    GUIDANCE = "guidance"
    COMPLETION = "completion"


class EscalationType(str, Enum):
    """Escalation type classification."""
    SAFETY = "safety"
    COMPLEXITY = "complexity"
    BUDGET = "budget"
    AUTHORIZATION = "authorization"


@dataclass
class DiagnosisState:
    """
    State tracking for diagnosis phase.
    """
    images_submitted: List[Any] = field(default_factory=list)  # List[ImageData]
    diagnosis_results: List[DiagnosisResult] = field(default_factory=list)
    confirmed_issues: List[DiagnosisResult] = field(default_factory=list)
    rejected_diagnoses: List[DiagnosisResult] = field(default_factory=list)


@dataclass
class ProcurementState:
    """
    State tracking for procurement phase.
    """
    required_parts: List[Any] = field(default_factory=list)  # List[Part]
    purchase_requests: List[PurchaseRequest] = field(default_factory=list)
    approval_status: Dict[str, str] = field(default_factory=dict)  # request_id -> status
    estimated_delivery_date: Optional[datetime] = None


@dataclass
class GuidanceState:
    """
    State tracking for guidance phase.
    """
    active_guide: Optional[RepairGuide] = None
    current_step: int = 0
    completed_steps: List[int] = field(default_factory=list)
    skipped_steps: List[int] = field(default_factory=list)
    failed_steps: List[int] = field(default_factory=list)
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


@dataclass
class EscalationResolution:
    """Resolution details for an escalation."""
    resolved_by: str
    resolved_at: datetime
    resolution_notes: str
    approved: bool


@dataclass
class Escalation:
    """
    Escalation record for situations requiring human oversight.
    
    Validation Rules:
    - escalations must be resolved before workflow can complete
    """
    escalation_id: str
    reason: str
    escalation_type: EscalationType
    escalated_to: str
    escalated_at: datetime
    resolution: Optional[EscalationResolution] = None
    
    def is_resolved(self) -> bool:
        """Check if escalation has been resolved."""
        return self.resolution is not None


@dataclass
class WorkflowState:
    """
    Complete workflow state tracking.
    
    Validation Rules:
    - session_id must be unique per field visit
    - last_activity must be updated on every interaction
    - current_phase transitions must follow: intake → diagnosis → procurement → guidance → completion
    - judge_validations array must contain at least one validation per phase transition
    """
    session_id: str
    current_phase: WorkflowPhase
    start_time: datetime
    last_activity: datetime
    technician_id: str
    site_id: str
    
    # Phase-specific state
    diagnosis_state: Optional[DiagnosisState] = None
    procurement_state: Optional[ProcurementState] = None
    guidance_state: Optional[GuidanceState] = None
    
    # Validation tracking
    judge_validations: List[JudgmentResult] = field(default_factory=list)
    
    # Escalation tracking
    escalations: List[Escalation] = field(default_factory=list)
    
    # Workflow completion
    end_time: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def can_transition_to(self, next_phase: WorkflowPhase) -> bool:
        """
        Check if transition to next phase is valid.
        
        Valid transitions:
        - intake → diagnosis
        - diagnosis → procurement
        - diagnosis → guidance (if no parts needed)
        - procurement → guidance
        - guidance → completion
        """
        valid_transitions = {
            WorkflowPhase.INTAKE: [WorkflowPhase.DIAGNOSIS],
            WorkflowPhase.DIAGNOSIS: [WorkflowPhase.PROCUREMENT, WorkflowPhase.GUIDANCE],
            WorkflowPhase.PROCUREMENT: [WorkflowPhase.GUIDANCE],
            WorkflowPhase.GUIDANCE: [WorkflowPhase.COMPLETION],
            WorkflowPhase.COMPLETION: [],
        }
        
        return next_phase in valid_transitions.get(self.current_phase, [])
    
    def has_unresolved_escalations(self) -> bool:
        """Check if there are any unresolved escalations."""
        return any(not esc.is_resolved() for esc in self.escalations)
    
    def get_validation_for_phase(self, phase: WorkflowPhase) -> Optional[JudgmentResult]:
        """Get the most recent validation for a specific phase."""
        # This would need to track phase in JudgmentResult
        # For now, return the most recent validation
        return self.judge_validations[-1] if self.judge_validations else None
