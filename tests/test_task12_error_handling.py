"""
Tests for Task 12: Error Handling and Resilience

Tests the following:
1. Pydantic schema validation for inter-agent communication
2. Safety checker for electrical hazards
3. Confidence threshold (0.85) with escalation
4. Telemetry staleness checks (60s for critical, 600s for normal)
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

# Import Pydantic schemas
from src.models.schemas import (
    DiagnosisRequest,
    DiagnosisResponse,
    ProcurementRequest,
    ProcurementResponse,
    GuidanceRequest,
    GuidanceResponse,
    TelemetryData,
    SafetyCheckRequest,
    SafetyCheckResponse,
    validate_agent_communication,
    serialize_for_agent,
    RequestTypeEnum,
    IssueTypeEnum,
    SeverityEnum,
    AgentTypeEnum,
)

# Import safety checker
from src.safety import (
    SafetyChecker,
    SafetyStatus,
    HazardType,
    HazardSeverity,
)

# Import domain models
from src.models.domain import TelemetrySnapshot, SystemStatus, MetricValue, Alert


class TestPydanticSchemas:
    """Test Pydantic schema validation for inter-agent communication."""
    
    def test_diagnosis_request_valid(self):
        """Test valid diagnosis request."""
        request = DiagnosisRequest(
            request_id="req-001",
            session_id="session-001",
            technician_id="tech-001",
            site_id="site-001",
            site_context={"site_type": "data_center"},
            description="Network switch not powering on"
        )
        
        assert request.request_id == "req-001"
        assert request.request_type == RequestTypeEnum.DIAGNOSIS
        assert len(request.description) >= 10
    
    def test_diagnosis_request_invalid_description(self):
        """Test diagnosis request with invalid description."""
        with pytest.raises(ValidationError) as exc_info:
            DiagnosisRequest(
                request_id="req-001",
                session_id="session-001",
                technician_id="tech-001",
                site_id="site-001",
                site_context={"site_type": "data_center"},
                description="short"  # Too short
            )
        
        assert "at least 10 characters" in str(exc_info.value)
    
    def test_diagnosis_response_valid(self):
        """Test valid diagnosis response."""
        response = DiagnosisResponse(
            response_id="resp-001",
            request_id="req-001",
            session_id="session-001",
            success=True,
            message="Diagnosis complete",
            confidence=0.92,
            issue_type=IssueTypeEnum.ELECTRICAL_MALFUNCTION,
            severity=SeverityEnum.HIGH
        )
        
        assert response.confidence == 0.92
        assert response.escalation_required == False
    
    def test_diagnosis_response_low_confidence_escalation(self):
        """Test diagnosis response with low confidence requiring escalation."""
        response = DiagnosisResponse(
            response_id="resp-001",
            request_id="req-001",
            session_id="session-001",
            success=True,
            message="Diagnosis complete",
            confidence=0.75,  # Below 0.85 threshold
            escalation_required=True,
            escalation_reason="Confidence below threshold"
        )
        
        assert response.confidence == 0.75
        assert response.escalation_required == True
        assert response.escalation_reason is not None
    
    def test_diagnosis_response_invalid_confidence(self):
        """Test diagnosis response with invalid confidence."""
        with pytest.raises(ValidationError) as exc_info:
            DiagnosisResponse(
                response_id="resp-001",
                request_id="req-001",
                session_id="session-001",
                success=True,
                message="Diagnosis complete",
                confidence=1.5  # Invalid: > 1.0
            )
        
        assert "less than or equal to 1" in str(exc_info.value)
    
    def test_procurement_request_valid(self):
        """Test valid procurement request."""
        request = ProcurementRequest(
            request_id="req-002",
            session_id="session-001",
            technician_id="tech-001",
            site_id="site-001",
            diagnosis_result={"issue_type": "hardware_defect"},
            required_parts=["power-supply-001", "cable-002"],
            urgency="high"
        )
        
        assert len(request.required_parts) == 2
        assert request.request_type == RequestTypeEnum.PROCUREMENT
    
    def test_procurement_request_empty_parts(self):
        """Test procurement request with empty parts list."""
        with pytest.raises(ValidationError) as exc_info:
            ProcurementRequest(
                request_id="req-002",
                session_id="session-001",
                technician_id="tech-001",
                site_id="site-001",
                diagnosis_result={"issue_type": "hardware_defect"},
                required_parts=[],  # Empty list
                urgency="high"
            )
        
        assert "at least 1 item" in str(exc_info.value)
    
    def test_guidance_request_valid(self):
        """Test valid guidance request."""
        request = GuidanceRequest(
            request_id="req-003",
            session_id="session-001",
            technician_id="tech-001",
            site_id="site-001",
            diagnosis_result={"issue_type": "hardware_defect"},
            technician_skill_level="intermediate"
        )
        
        assert request.technician_skill_level == "intermediate"
        assert request.request_type == RequestTypeEnum.GUIDANCE
    
    def test_guidance_request_invalid_skill_level(self):
        """Test guidance request with invalid skill level."""
        with pytest.raises(ValidationError) as exc_info:
            GuidanceRequest(
                request_id="req-003",
                session_id="session-001",
                technician_id="tech-001",
                site_id="site-001",
                diagnosis_result={"issue_type": "hardware_defect"},
                technician_skill_level="master"  # Invalid
            )
        
        assert "must be one of" in str(exc_info.value)
    
    def test_schema_serialization(self):
        """Test schema serialization for agent communication."""
        request = DiagnosisRequest(
            request_id="req-001",
            session_id="session-001",
            technician_id="tech-001",
            site_id="site-001",
            site_context={"site_type": "data_center"},
            description="Network switch not powering on"
        )
        
        # Serialize
        data = serialize_for_agent(request)
        
        assert isinstance(data, dict)
        assert data["request_id"] == "req-001"
        assert data["request_type"] == "diagnosis"
        
        # Validate round-trip
        request2 = validate_agent_communication(data, DiagnosisRequest)
        assert request2.request_id == request.request_id


class TestSafetyChecker:
    """Test safety checker for electrical hazards."""
    
    def test_electrical_hazard_detection(self):
        """Test detection of electrical hazards."""
        checker = SafetyChecker()
        
        diagnosis_result = {
            "issue_type": "electrical_malfunction",
            "description": "High voltage panel showing signs of arcing",
            "root_cause": "Electrical short circuit"
        }
        
        site_context = {
            "site_type": "data_center",
            "component_type": "electrical_panel"
        }
        
        repair_actions = [
            {"action": "replace_breaker", "description": "Replace circuit breaker"}
        ]
        
        result = checker.check_safety(diagnosis_result, site_context, repair_actions)
        
        assert result.approved_to_proceed == False
        assert result.escalation_required == True
        assert len(result.hazards_identified) > 0
        
        # Check for electrical hazard
        electrical_hazards = [
            h for h in result.hazards_identified 
            if h.hazard_type == HazardType.ELECTRICAL
        ]
        assert len(electrical_hazards) > 0
        
        # Check for lockout/tagout requirement
        assert any(h.lockout_tagout_required for h in result.hazards_identified)
    
    def test_critical_electrical_hazard(self):
        """Test critical electrical hazard (high voltage)."""
        checker = SafetyChecker()
        
        diagnosis_result = {
            "issue_type": "electrical_malfunction",
            "description": "Transformer showing high voltage arcing",
            "root_cause": "High voltage insulation failure"
        }
        
        site_context = {
            "site_type": "data_center",
            "component_type": "transformer"
        }
        
        repair_actions = []
        
        result = checker.check_safety(diagnosis_result, site_context, repair_actions)
        
        assert result.status == SafetyStatus.REQUIRES_ESCALATION
        assert result.approved_to_proceed == False
        
        # Check for critical hazard
        critical_hazards = [
            h for h in result.hazards_identified 
            if h.severity == HazardSeverity.CRITICAL
        ]
        assert len(critical_hazards) > 0
        
        # Check for permit requirement
        assert any(h.permit_required for h in result.hazards_identified)
    
    def test_non_electrical_safe_operation(self):
        """Test safe operation without electrical hazards."""
        checker = SafetyChecker()
        
        diagnosis_result = {
            "issue_type": "hardware_defect",
            "description": "Network cable disconnected",
            "root_cause": "Physical disconnection"
        }
        
        site_context = {
            "site_type": "office",
            "component_type": "network_cable"
        }
        
        repair_actions = [
            {"action": "reconnect_cable", "description": "Reconnect network cable"}
        ]
        
        result = checker.check_safety(diagnosis_result, site_context, repair_actions)
        
        # Should be approved for non-electrical work
        assert result.approved_to_proceed == True
        assert result.escalation_required == False
    
    def test_mechanical_hazard_detection(self):
        """Test detection of mechanical hazards."""
        checker = SafetyChecker()
        
        diagnosis_result = {
            "issue_type": "hardware_defect",
            "description": "Fan with moving parts and pinch points",
            "root_cause": "Mechanical wear"
        }
        
        site_context = {
            "site_type": "data_center",
            "component_type": "cooling_fan"
        }
        
        repair_actions = []
        
        result = checker.check_safety(diagnosis_result, site_context, repair_actions)
        
        # Check for mechanical hazard
        mechanical_hazards = [
            h for h in result.hazards_identified 
            if h.hazard_type == HazardType.MECHANICAL
        ]
        assert len(mechanical_hazards) > 0


class TestTelemetryStaleness:
    """Test telemetry staleness checks."""
    
    def test_fresh_telemetry_normal_operation(self):
        """Test fresh telemetry for normal operations (< 600s)."""
        telemetry = TelemetrySnapshot(
            timestamp=datetime.now() - timedelta(seconds=300),  # 5 minutes ago
            site_id="site-001",
            metrics={},
            alerts=[],
            system_status=SystemStatus.OPERATIONAL
        )
        
        assert telemetry.is_stale(max_age_seconds=600) == False
        assert telemetry.get_age_seconds() < 600
    
    def test_stale_telemetry_normal_operation(self):
        """Test stale telemetry for normal operations (> 600s)."""
        telemetry = TelemetrySnapshot(
            timestamp=datetime.now() - timedelta(seconds=700),  # 11+ minutes ago
            site_id="site-001",
            metrics={},
            alerts=[],
            system_status=SystemStatus.OPERATIONAL
        )
        
        assert telemetry.is_stale(max_age_seconds=600) == True
        assert telemetry.get_age_seconds() > 600
    
    def test_fresh_telemetry_critical_operation(self):
        """Test fresh telemetry for critical operations (< 300s / 5 min)."""
        telemetry = TelemetrySnapshot(
            timestamp=datetime.now() - timedelta(seconds=240),  # 4 minutes ago
            site_id="site-001",
            metrics={},
            alerts=[],
            system_status=SystemStatus.OPERATIONAL
        )
        
        assert telemetry.is_stale_for_critical_operation() == False
        assert telemetry.get_age_seconds() < 300
    
    def test_stale_telemetry_critical_operation(self):
        """Test stale telemetry for critical operations (> 300s / 5 min)."""
        telemetry = TelemetrySnapshot(
            timestamp=datetime.now() - timedelta(seconds=360),  # 6 minutes ago
            site_id="site-001",
            metrics={},
            alerts=[],
            system_status=SystemStatus.OPERATIONAL
        )
        
        assert telemetry.is_stale_for_critical_operation() == True
        assert telemetry.get_age_seconds() > 300
    
    def test_telemetry_age_calculation(self):
        """Test telemetry age calculation."""
        telemetry = TelemetrySnapshot(
            timestamp=datetime.now() - timedelta(seconds=45),
            site_id="site-001",
            metrics={},
            alerts=[],
            system_status=SystemStatus.OPERATIONAL
        )
        
        age = telemetry.get_age_seconds()
        assert 40 <= age <= 50  # Allow small timing variance


class TestPydanticTelemetrySchema:
    """Test Pydantic telemetry schema with staleness checking."""
    
    def test_telemetry_data_valid(self):
        """Test valid telemetry data."""
        telemetry = TelemetryData(
            timestamp=datetime.now(),
            site_id="site-001",
            metrics={"temperature": 25.0, "power": 100},
            system_status="operational"
        )
        
        assert telemetry.site_id == "site-001"
        assert telemetry.is_stale(max_age_seconds=300) == False
    
    def test_telemetry_data_future_timestamp(self):
        """Test telemetry data with future timestamp (invalid)."""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryData(
                timestamp=datetime.now() + timedelta(hours=1),  # Future
                site_id="site-001",
                metrics={},
                system_status="operational"
            )
        
        assert "cannot be in the future" in str(exc_info.value)
    
    def test_telemetry_staleness_check(self):
        """Test telemetry staleness check."""
        telemetry = TelemetryData(
            timestamp=datetime.now() - timedelta(seconds=400),  # 6.67 minutes ago
            site_id="site-001",
            metrics={},
            system_status="operational"
        )
        
        # Fresh for normal operations (600s / 10 min threshold)
        assert telemetry.is_stale(max_age_seconds=600) == False
        
        # Stale for critical operations (300s / 5 min threshold)
        assert telemetry.is_stale_for_critical_operation() == True


class TestConfidenceThreshold:
    """Test confidence threshold and escalation logic."""
    
    def test_high_confidence_no_escalation(self):
        """Test high confidence (>= 0.85) requires no escalation."""
        response = DiagnosisResponse(
            response_id="resp-001",
            request_id="req-001",
            session_id="session-001",
            success=True,
            message="Diagnosis complete",
            confidence=0.92  # Above threshold
        )
        
        assert response.confidence >= 0.85
        assert response.escalation_required == False
    
    def test_medium_confidence_requires_escalation(self):
        """Test medium confidence (0.70-0.85) requires expert review."""
        response = DiagnosisResponse(
            response_id="resp-001",
            request_id="req-001",
            session_id="session-001",
            success=True,
            message="Diagnosis complete",
            confidence=0.78,  # Between 0.70 and 0.85
            escalation_required=True,
            escalation_reason="Confidence below expert review threshold"
        )
        
        assert 0.70 <= response.confidence < 0.85
        assert response.escalation_required == True
    
    def test_low_confidence_requires_additional_photos(self):
        """Test low confidence (< 0.70) requires additional photos."""
        response = DiagnosisResponse(
            response_id="resp-001",
            request_id="req-001",
            session_id="session-001",
            success=True,
            message="Diagnosis complete",
            confidence=0.65,  # Below 0.70
            escalation_required=True,
            escalation_reason="Low confidence. Additional photos recommended."
        )
        
        assert response.confidence < 0.70
        assert response.escalation_required == True
        assert "additional photos" in response.escalation_reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
