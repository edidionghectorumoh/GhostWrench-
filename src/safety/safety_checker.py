"""
Safety Checker Module

Mandatory safety validation for all field operations, with special focus on
electrical hazards and high-risk scenarios.

This module enforces safety compliance before any repair work begins.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HazardType(str, Enum):
    """Types of safety hazards."""
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    CHEMICAL = "chemical"
    THERMAL = "thermal"
    RADIATION = "radiation"
    FALL = "fall"
    CONFINED_SPACE = "confined_space"
    ENVIRONMENTAL = "environmental"


class HazardSeverity(str, Enum):
    """Severity levels for hazards."""
    CRITICAL = "critical"  # Immediate danger to life
    HIGH = "high"  # Serious injury possible
    MEDIUM = "medium"  # Moderate injury possible
    LOW = "low"  # Minor injury possible


class SafetyStatus(str, Enum):
    """Safety check status."""
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_ESCALATION = "requires_escalation"
    REQUIRES_ADDITIONAL_PPE = "requires_additional_ppe"


@dataclass
class SafetyHazard:
    """Identified safety hazard."""
    hazard_id: str
    hazard_type: HazardType
    severity: HazardSeverity
    description: str
    mitigation_required: List[str]
    required_ppe: List[str]
    lockout_tagout_required: bool = False
    permit_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "mitigation_required": self.mitigation_required,
            "required_ppe": self.required_ppe,
            "lockout_tagout_required": self.lockout_tagout_required,
            "permit_required": self.permit_required
        }


@dataclass
class SafetyCheckResult:
    """Result of safety check."""
    check_id: str
    timestamp: datetime
    status: SafetyStatus
    hazards_identified: List[SafetyHazard]
    violations: List[str]
    required_actions: List[str]
    approved_to_proceed: bool
    escalation_required: bool
    escalation_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_id": self.check_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "hazards_identified": [h.to_dict() for h in self.hazards_identified],
            "violations": self.violations,
            "required_actions": self.required_actions,
            "approved_to_proceed": self.approved_to_proceed,
            "escalation_required": self.escalation_required,
            "escalation_reason": self.escalation_reason
        }


class SafetyChecker:
    """
    Mandatory safety checker for all field operations.
    
    Enforces safety compliance with special focus on electrical hazards.
    """
    
    # Electrical voltage thresholds (volts)
    LOW_VOLTAGE_THRESHOLD = 50  # Below this is generally safe
    HIGH_VOLTAGE_THRESHOLD = 1000  # Above this requires special permits
    
    # Electrical hazard keywords
    ELECTRICAL_KEYWORDS = [
        "electrical", "electric", "voltage", "power", "circuit", "breaker",
        "panel", "transformer", "wire", "wiring", "outlet", "socket",
        "high voltage", "live wire", "energized", "current", "amperage"
    ]
    
    def __init__(self):
        """Initialize safety checker."""
        self.check_count = 0
        logger.info("Safety Checker initialized")
    
    def check_safety(
        self,
        diagnosis_result: Dict[str, Any],
        site_context: Dict[str, Any],
        repair_actions: List[Dict[str, Any]]
    ) -> SafetyCheckResult:
        """
        Perform comprehensive safety check.
        
        Args:
            diagnosis_result: Diagnosis from agent
            site_context: Site context information
            repair_actions: Planned repair actions
            
        Returns:
            Safety check result
        """
        self.check_count += 1
        check_id = f"safety-check-{self.check_count}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Performing safety check {check_id}")
        
        hazards = []
        violations = []
        required_actions = []
        
        # Check for electrical hazards (MANDATORY)
        electrical_hazards = self._check_electrical_hazards(
            diagnosis_result,
            site_context,
            repair_actions
        )
        hazards.extend(electrical_hazards)
        
        # Check for other hazards
        other_hazards = self._check_other_hazards(
            diagnosis_result,
            site_context,
            repair_actions
        )
        hazards.extend(other_hazards)
        
        # Determine if work can proceed
        approved_to_proceed = True
        escalation_required = False
        escalation_reason = None
        status = SafetyStatus.APPROVED
        
        # Check for critical hazards
        critical_hazards = [h for h in hazards if h.severity == HazardSeverity.CRITICAL]
        if critical_hazards:
            approved_to_proceed = False
            escalation_required = True
            escalation_reason = f"Critical hazards identified: {len(critical_hazards)}"
            status = SafetyStatus.REQUIRES_ESCALATION
            violations.append("Critical safety hazards require safety officer approval")
            required_actions.append("Escalate to safety officer for approval")
        
        # Check for high-severity electrical hazards
        high_electrical = [
            h for h in electrical_hazards 
            if h.severity in [HazardSeverity.CRITICAL, HazardSeverity.HIGH]
        ]
        if high_electrical:
            if not escalation_required:
                escalation_required = True
                escalation_reason = "High-voltage electrical work requires safety officer approval"
                status = SafetyStatus.REQUIRES_ESCALATION
            violations.append("Electrical work requires additional safety measures")
            required_actions.append("Obtain electrical work permit")
            required_actions.append("Verify lockout/tagout procedures")
        
        # Compile required PPE
        all_required_ppe = set()
        for hazard in hazards:
            all_required_ppe.update(hazard.required_ppe)
        
        if all_required_ppe:
            required_actions.append(f"Ensure PPE available: {', '.join(all_required_ppe)}")
        
        # Check for lockout/tagout requirements
        loto_required = any(h.lockout_tagout_required for h in hazards)
        if loto_required:
            required_actions.append("Perform lockout/tagout procedure before work begins")
        
        # Check for permit requirements
        permit_required = any(h.permit_required for h in hazards)
        if permit_required:
            required_actions.append("Obtain required work permits before proceeding")
        
        result = SafetyCheckResult(
            check_id=check_id,
            timestamp=datetime.now(),
            status=status,
            hazards_identified=hazards,
            violations=violations,
            required_actions=required_actions,
            approved_to_proceed=approved_to_proceed and not escalation_required,
            escalation_required=escalation_required,
            escalation_reason=escalation_reason
        )
        
        logger.info(
            f"Safety check {check_id} complete: "
            f"Status={status.value}, Hazards={len(hazards)}, "
            f"Approved={result.approved_to_proceed}"
        )
        
        return result
    
    def _check_electrical_hazards(
        self,
        diagnosis_result: Dict[str, Any],
        site_context: Dict[str, Any],
        repair_actions: List[Dict[str, Any]]
    ) -> List[SafetyHazard]:
        """
        Check for electrical hazards (MANDATORY).
        
        This is the most critical safety check for field operations.
        """
        hazards = []
        
        # Check diagnosis description for electrical keywords
        description = diagnosis_result.get("description", "").lower()
        root_cause = diagnosis_result.get("root_cause", "").lower()
        issue_type = diagnosis_result.get("issue_type", "").lower()
        
        combined_text = f"{description} {root_cause} {issue_type}"
        
        # Check for electrical keywords
        electrical_detected = any(
            keyword in combined_text 
            for keyword in self.ELECTRICAL_KEYWORDS
        )
        
        if electrical_detected or issue_type == "electrical_malfunction":
            # Determine severity based on voltage indicators
            severity = HazardSeverity.HIGH  # Default for electrical work
            
            if any(word in combined_text for word in ["high voltage", "transformer", "panel"]):
                severity = HazardSeverity.CRITICAL
            elif any(word in combined_text for word in ["outlet", "socket", "low voltage"]):
                severity = HazardSeverity.MEDIUM
            
            hazard = SafetyHazard(
                hazard_id=f"elec-{len(hazards)+1}",
                hazard_type=HazardType.ELECTRICAL,
                severity=severity,
                description="Electrical hazard detected in repair work",
                mitigation_required=[
                    "Verify power is de-energized",
                    "Use voltage tester to confirm no voltage present",
                    "Follow lockout/tagout procedures",
                    "Maintain safe working distance"
                ],
                required_ppe=[
                    "Insulated gloves (rated for voltage)",
                    "Safety glasses with side shields",
                    "Electrical-rated footwear",
                    "Arc-rated clothing (if high voltage)"
                ],
                lockout_tagout_required=True,
                permit_required=(severity == HazardSeverity.CRITICAL)
            )
            hazards.append(hazard)
            
            logger.warning(
                f"Electrical hazard detected: Severity={severity.value}, "
                f"LOTO Required=True"
            )
        
        # Check component type
        component_type = site_context.get("component_type", "").lower()
        if any(word in component_type for word in ["power", "electrical", "circuit", "breaker"]):
            if not hazards:  # Don't duplicate if already detected
                hazard = SafetyHazard(
                    hazard_id=f"elec-comp-{len(hazards)+1}",
                    hazard_type=HazardType.ELECTRICAL,
                    severity=HazardSeverity.HIGH,
                    description=f"Working on electrical component: {component_type}",
                    mitigation_required=[
                        "De-energize equipment before work",
                        "Verify zero energy state",
                        "Use appropriate tools for electrical work"
                    ],
                    required_ppe=[
                        "Insulated gloves",
                        "Safety glasses",
                        "Electrical-rated footwear"
                    ],
                    lockout_tagout_required=True,
                    permit_required=False
                )
                hazards.append(hazard)
        
        return hazards
    
    def _check_other_hazards(
        self,
        diagnosis_result: Dict[str, Any],
        site_context: Dict[str, Any],
        repair_actions: List[Dict[str, Any]]
    ) -> List[SafetyHazard]:
        """Check for non-electrical hazards."""
        hazards = []
        
        # Check for mechanical hazards
        description = diagnosis_result.get("description", "").lower()
        if any(word in description for word in ["moving parts", "rotating", "pinch point", "crush"]):
            hazard = SafetyHazard(
                hazard_id=f"mech-{len(hazards)+1}",
                hazard_type=HazardType.MECHANICAL,
                severity=HazardSeverity.MEDIUM,
                description="Mechanical hazard: Moving parts or pinch points",
                mitigation_required=[
                    "Ensure equipment is powered off",
                    "Lock out energy sources",
                    "Keep hands clear of moving parts"
                ],
                required_ppe=["Safety gloves", "Safety glasses"],
                lockout_tagout_required=True,
                permit_required=False
            )
            hazards.append(hazard)
        
        # Check for thermal hazards
        if any(word in description for word in ["hot", "heat", "burn", "temperature"]):
            hazard = SafetyHazard(
                hazard_id=f"thermal-{len(hazards)+1}",
                hazard_type=HazardType.THERMAL,
                severity=HazardSeverity.MEDIUM,
                description="Thermal hazard: Hot surfaces or equipment",
                mitigation_required=[
                    "Allow equipment to cool before work",
                    "Use heat-resistant tools",
                    "Maintain safe distance from hot surfaces"
                ],
                required_ppe=["Heat-resistant gloves", "Safety glasses"],
                lockout_tagout_required=False,
                permit_required=False
            )
            hazards.append(hazard)
        
        # Check for fall hazards based on site type
        site_type = site_context.get("site_type", "").lower()
        if "data_center" in site_type or "warehouse" in site_type:
            # Check if work involves elevated areas
            if any(word in description for word in ["rack", "ceiling", "overhead", "ladder"]):
                hazard = SafetyHazard(
                    hazard_id=f"fall-{len(hazards)+1}",
                    hazard_type=HazardType.FALL,
                    severity=HazardSeverity.HIGH,
                    description="Fall hazard: Work at elevation",
                    mitigation_required=[
                        "Use proper ladder or lift equipment",
                        "Ensure stable footing",
                        "Use fall protection if above 6 feet"
                    ],
                    required_ppe=["Safety harness (if >6ft)", "Non-slip footwear"],
                    lockout_tagout_required=False,
                    permit_required=False
                )
                hazards.append(hazard)
        
        return hazards
    
    def validate_ppe_availability(
        self,
        required_ppe: List[str],
        available_ppe: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Validate that required PPE is available.
        
        Args:
            required_ppe: List of required PPE items
            available_ppe: List of available PPE items
            
        Returns:
            Tuple of (all_available, missing_items)
        """
        missing = []
        for item in required_ppe:
            if item not in available_ppe:
                missing.append(item)
        
        return (len(missing) == 0, missing)
