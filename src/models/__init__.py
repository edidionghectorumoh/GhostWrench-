"""
Data models package for Autonomous Field Engineer system.
"""

from .domain import (
    SiteContext,
    Component,
    ImageData,
    TelemetrySnapshot,
    Part,
    Tool,
    SkillLevel,
    GeoLocation,
    OperatingHours,
    EnvironmentalData,
    ImageMetadata,
    MetricValue,
    Alert,
    SystemStatus,
    Specification,
    MaintenanceSchedule,
)

from .workflow import (
    WorkflowState,
    DiagnosisState,
    ProcurementState,
    GuidanceState,
    Escalation,
    EscalationResolution,
)

from .agents import (
    FieldRequest,
    FieldResponse,
    DiagnosisInput,
    DiagnosisResult,
    ActionResult,
    GuidanceStep,
    RepairGuide,
    ComparisonResult,
    Action,
    InventorySearchResult,
    PurchaseRequest,
    VoiceResponse,
    SafetyValidation,
)

from .validation import (
    AgentOutput,
    ValidationCriteria,
    JudgmentResult,
    SafetyJudgment,
    ComplianceJudgment,
    BudgetJudgment,
    SafetyRule,
    SOPPolicy,
    BudgetLimits,
    QualityThreshold,
    Violation,
)

__all__ = [
    # Domain models
    "SiteContext",
    "Component",
    "ImageData",
    "TelemetrySnapshot",
    "Part",
    "Tool",
    "SkillLevel",
    "GeoLocation",
    "OperatingHours",
    "EnvironmentalData",
    "ImageMetadata",
    "MetricValue",
    "Alert",
    "SystemStatus",
    "Specification",
    "MaintenanceSchedule",
    # Workflow models
    "WorkflowState",
    "DiagnosisState",
    "ProcurementState",
    "GuidanceState",
    "Escalation",
    "EscalationResolution",
    # Agent models
    "FieldRequest",
    "FieldResponse",
    "DiagnosisInput",
    "DiagnosisResult",
    "ActionResult",
    "GuidanceStep",
    "RepairGuide",
    "ComparisonResult",
    "Action",
    "InventorySearchResult",
    "PurchaseRequest",
    "VoiceResponse",
    "SafetyValidation",
    # Validation models
    "AgentOutput",
    "ValidationCriteria",
    "JudgmentResult",
    "SafetyJudgment",
    "ComplianceJudgment",
    "BudgetJudgment",
    "SafetyRule",
    "SOPPolicy",
    "BudgetLimits",
    "QualityThreshold",
    "Violation",
]
