"""
Validation models for the Local LLM Judge.
Defines validation criteria, judgment results, and safety/compliance structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class AgentType(str, Enum):
    """AI agent type classification."""
    DIAGNOSIS = "diagnosis"
    ACTION = "action"
    GUIDANCE = "guidance"


class EscalationLevel(str, Enum):
    """Escalation level for human oversight."""
    NONE = "none"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    DIRECTOR = "director"
    SAFETY_OFFICER = "safety_officer"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """Validation violation type."""
    SAFETY = "safety"
    SOP = "sop"
    BUDGET = "budget"
    QUALITY = "quality"


class ApprovalLevel(str, Enum):
    """Approval authority level."""
    TECHNICIAN = "technician"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    DIRECTOR = "director"


@dataclass
class AgentOutput:
    """
    Output from an AI agent for validation.
    """
    agent_type: AgentType
    output_data: Any
    confidence: float
    timestamp: datetime
    session_id: str
    
    def __post_init__(self):
        """Validate agent output."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Invalid confidence: {self.confidence}")


@dataclass
class SafetyRule:
    """Safety rule for validation."""
    rule_id: str
    description: str
    severity: str  # "critical", "high", "medium", "low"
    applies_to: List[str]  # List of equipment types or scenarios


@dataclass
class SOPPolicy:
    """Standard Operating Procedure policy."""
    policy_id: str
    title: str
    description: str
    version: str
    mandatory_steps: List[str]


@dataclass
class BudgetLimits:
    """Budget constraints for validation."""
    max_amount: float
    approval_level: ApprovalLevel
    site_id: str
    fiscal_year: Optional[int] = None


@dataclass
class QualityThreshold:
    """Quality threshold for validation."""
    min_confidence: float = 0.80
    min_reference_coverage: float = 0.70
    max_uncertainty: float = 0.30


@dataclass
class RegulatoryRequirement:
    """Regulatory compliance requirement."""
    requirement_id: str
    regulation_name: str
    description: str
    mandatory: bool


@dataclass
class ValidationCriteria:
    """
    Criteria for validating agent outputs.
    """
    safety_rules: List[SafetyRule] = field(default_factory=list)
    sop_policies: List[SOPPolicy] = field(default_factory=list)
    budget_limits: Optional[BudgetLimits] = None
    quality_thresholds: Optional[QualityThreshold] = None
    regulatory_requirements: List[RegulatoryRequirement] = field(default_factory=list)


@dataclass
class Violation:
    """Validation violation details."""
    violation_type: ViolationType
    rule_id: str
    reason: str
    severity: str  # "critical", "high", "medium", "low"


@dataclass
class Hazard:
    """Identified safety hazard."""
    hazard_id: str
    hazard_type: str
    description: str
    severity: str
    mitigation: str


@dataclass
class SafetyJudgment:
    """
    Safety validation judgment from Local Judge.
    """
    is_safe: bool
    hazards_identified: List[Hazard]
    required_precautions: List[str]
    ppe_required: List[str]
    lockout_tagout_needed: bool
    permit_required: bool


@dataclass
class SOPViolation:
    """SOP compliance violation."""
    policy_id: str
    violation_description: str
    missing_step: Optional[str] = None
    deviation_details: Optional[str] = None


@dataclass
class Deviation:
    """Deviation from standard procedure."""
    deviation_id: str
    description: str
    severity: str
    justification: Optional[str] = None


@dataclass
class ComplianceJudgment:
    """
    SOP compliance validation judgment from Local Judge.
    """
    is_compliant: bool
    sop_violations: List[SOPViolation]
    missing_steps: List[str]
    deviations_from_standard: List[Deviation]
    approved_with_conditions: bool
    conditions: Optional[List[str]] = None


@dataclass
class CostBreakdown:
    """Detailed cost breakdown."""
    parts_cost: float
    labor_cost: float
    shipping_cost: float
    tax: float
    total: float


@dataclass
class BudgetJudgment:
    """
    Budget validation judgment from Local Judge.
    """
    within_budget: bool
    total_cost: float
    budget_limit: float
    approval_level_required: ApprovalLevel
    cost_breakdown: CostBreakdown
    alternatives_considered: bool


@dataclass
class JudgmentResult:
    """
    Complete validation judgment from Local LLM Judge.
    
    Validation Rules:
    - approved must be boolean
    - if approved is false, violations must be non-empty
    - reasoning must provide human-readable explanation
    """
    approved: bool
    confidence: float
    reasoning: str
    violations: List[Violation]
    recommendations: List[str]
    requires_human_review: bool
    escalation_level: EscalationLevel = EscalationLevel.NONE
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate judgment result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Invalid confidence: {self.confidence}")
        if not self.approved and not self.violations:
            raise ValueError("Rejected judgments must have violations")
