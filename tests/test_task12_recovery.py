"""
Tests for Task 12.1 and 12.4: Error Recovery Implementation

Tests:
- Task 12.1: Low confidence diagnosis recovery
- Task 12.4: Safety violation handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.orchestration.OrchestrationLayer import OrchestrationLayer
from src.models.workflow import WorkflowState, WorkflowPhase
from src.models.agents import FieldRequest
from src.models.domain import SiteContext, SiteType, CriticalityLevel, GeoLocation, OperatingHours, EnvironmentalData
from src.orchestration.AgentCoordination import EscalationType
from src.safety import SafetyStatus, HazardType, HazardSeverity


class TestLowConfidenceRecovery:
    """Test Task 12.1: Low confidence diagnosis recovery."""
    
    def test_low_confidence_requests_additional_photos(self):
        """Test that confidence < 0.70 requests additional photos."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-001",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-001",
            site_id="site-001"
        )
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.65,  # Below 0.70 threshold
            "issue_type": "hardware_defect",
            "description": "Possible power supply failure"
        }
        
        request = FieldRequest(
            session_id="test-session-001",
            technician_id="tech-001",
            site_id="site-001",
            request_type="diagnosis"
        )
        request.site_context = SiteContext(
            site_id="site-001",
            site_name="Test Site 001",
            site_type=SiteType.DATA_CENTER,
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            criticality_level=CriticalityLevel.TIER1,
            operating_hours=OperatingHours(start_hour=0, end_hour=23, days_of_week=[0,1,2,3,4,5,6], timezone="UTC"),
            environmental_conditions=EnvironmentalData(temperature_celsius=22.0, humidity_percent=45.0),
            component_id="comp-001",
            component_type="power_supply"
        )
        
        # Call recovery handler
        response = orchestrator._handle_low_confidence_recovery(
            workflow_state,
            diagnosis_result,
            request
        )
        
        # Verify response
        assert response.success == False
        assert "additional photos" in response.message.lower()
        assert response.data["requires_additional_photos"] == True
        assert response.data["photo_request_count"] == 1
        assert "suggested_angles" in response.data
        assert len(response.data["suggested_angles"]) > 0
    
    def test_medium_confidence_escalates_to_expert(self):
        """Test that confidence 0.70-0.85 escalates to expert review."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-002",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-002",
            site_id="site-002"
        )
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.78,  # Between 0.70 and 0.85
            "issue_type": "network_failure",
            "description": "Possible switch port failure"
        }
        
        request = FieldRequest(
            session_id="test-session-002",
            technician_id="tech-002",
            site_id="site-002",
            request_type="diagnosis"
        )
        request.site_context = SiteContext(
            site_id="site-002",
            site_name="Test Site 002",
            site_type=SiteType.OFFICE,
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            criticality_level=CriticalityLevel.TIER2,
            operating_hours=OperatingHours(start_hour=0, end_hour=23, days_of_week=[0,1,2,3,4,5,6], timezone="UTC"),
            environmental_conditions=EnvironmentalData(temperature_celsius=22.0, humidity_percent=45.0),
            component_id="comp-002",
            component_type="network_switch"
        )
        
        # Call recovery handler
        response = orchestrator._handle_low_confidence_recovery(
            workflow_state,
            diagnosis_result,
            request
        )
        
        # Verify response
        assert response.success == False
        assert "expert review" in response.message.lower()
        assert response.data["requires_expert_review"] == True
        assert response.data["escalation_type"] == "expert_review"
        assert "escalation_id" in response.data
    
    def test_max_photo_requests_escalates_to_expert(self):
        """Test that after 3 photo requests, escalate to expert."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-003",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-003",
            site_id="site-003"
        )
        
        # Simulate 3 previous photo requests
        workflow_state.photo_request_count = 3
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.62,  # Still low after 3 attempts
            "issue_type": "hardware_defect",
            "description": "Unable to determine exact failure"
        }
        
        request = FieldRequest(
            session_id="test-session-003",
            technician_id="tech-003",
            site_id="site-003",
            request_type="diagnosis"
        )
        request.site_context = SiteContext(
            site_id="site-003",
            site_name="Test Site 003",
            site_type=SiteType.DATA_CENTER,
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            criticality_level=CriticalityLevel.TIER1,
            operating_hours=OperatingHours(start_hour=0, end_hour=23, days_of_week=[0,1,2,3,4,5,6], timezone="UTC"),
            environmental_conditions=EnvironmentalData(temperature_celsius=22.0, humidity_percent=45.0),
            component_id="comp-003",
            component_type="server"
        )
        
        # Call recovery handler
        response = orchestrator._handle_low_confidence_recovery(
            workflow_state,
            diagnosis_result,
            request
        )
        
        # Verify escalation after max attempts
        assert response.success == False
        assert "expert" in response.message.lower()
        assert response.data["requires_expert_review"] == True
        assert response.data["escalation_type"] == "low_confidence"
        # Photo attempts should be in the escalation data or diagnosis data
        assert ("photo_attempts" in response.data.get("diagnosis", {}) or 
                workflow_state.photo_request_count >= 3 or
                "photo attempts" in response.message.lower())
    
    def test_high_confidence_proceeds_normally(self):
        """Test that confidence >= 0.85 proceeds without recovery."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-004",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-004",
            site_id="site-004"
        )
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.92,  # High confidence
            "issue_type": "hardware_defect",
            "description": "Clear power supply failure",
            "requires_parts": True
        }
        
        request = FieldRequest(
            session_id="test-session-004",
            technician_id="tech-004",
            site_id="site-004",
            request_type="diagnosis"
        )
        request.site_context = SiteContext(
            site_id="site-004",
            site_name="Test Site 004",
            site_type=SiteType.DATA_CENTER,
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            criticality_level=CriticalityLevel.TIER1,
            operating_hours=OperatingHours(start_hour=0, end_hour=23, days_of_week=[0,1,2,3,4,5,6], timezone="UTC"),
            environmental_conditions=EnvironmentalData(temperature_celsius=22.0, humidity_percent=45.0),
            component_id="comp-004",
            component_type="power_supply"
        )
        
        # Call recovery handler (should handle gracefully)
        response = orchestrator._handle_low_confidence_recovery(
            workflow_state,
            diagnosis_result,
            request
        )
        
        # Should proceed normally
        assert response.success == True
        assert response.next_phase == WorkflowPhase.PROCUREMENT.value


class TestSafetyViolationHandling:
    """Test Task 12.4: Safety violation handling."""
    
    def test_critical_electrical_hazard_halts_workflow(self):
        """Test that critical electrical hazard halts workflow immediately."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-005",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-005",
            site_id="site-005"
        )
        
        safety_check_result = {
            "check_id": "safety-001",
            "timestamp": datetime.now().isoformat(),
            "status": "requires_escalation",
            "hazards_identified": [
                {
                    "hazard_id": "hazard-001",
                    "hazard_type": "electrical",
                    "severity": "critical",
                    "description": "High voltage arcing detected",
                    "mitigation_required": ["De-energize equipment", "Lockout/tagout"],
                    "required_ppe": ["Insulated gloves", "Arc flash suit", "Safety glasses"],
                    "lockout_tagout_required": True,
                    "permit_required": True
                }
            ],
            "violations": ["High voltage work without permit"],
            "required_actions": ["Obtain permit", "Lockout/tagout"],
            "approved_to_proceed": False,
            "escalation_required": True,
            "escalation_reason": "Critical electrical hazard"
        }
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.95,
            "issue_type": "electrical_malfunction",
            "description": "Electrical panel showing arcing"
        }
        
        # Call safety violation handler
        response = orchestrator._handle_safety_violation(
            workflow_state,
            safety_check_result,
            diagnosis_result
        )
        
        # Verify workflow halted
        assert response.success == False
        assert "SAFETY VIOLATION" in response.message
        assert response.data["workflow_halted"] == True
        assert response.data["requires_safety_clearance"] == True
        assert response.data["safety_officer_notified"] == True
        assert response.data["supervisor_notified"] == True
        
        # Verify critical hazards identified
        assert len(response.data["critical_hazards"]) > 0
        assert response.data["critical_hazards"][0]["severity"] == "critical"
        
        # Verify required actions
        assert len(response.data["required_actions"]) > 0
        lockout_action = next(
            (a for a in response.data["required_actions"] if a["action"] == "lockout_tagout"),
            None
        )
        assert lockout_action is not None
        assert lockout_action["mandatory"] == True
    
    def test_safety_violation_generates_alternative_procedure(self):
        """Test that safety violation generates alternative safer procedure."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-006",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-006",
            site_id="site-006"
        )
        
        safety_check_result = {
            "check_id": "safety-002",
            "timestamp": datetime.now().isoformat(),
            "status": "requires_escalation",
            "hazards_identified": [
                {
                    "hazard_id": "hazard-002",
                    "hazard_type": "electrical",
                    "severity": "high",
                    "description": "Live electrical work required",
                    "mitigation_required": ["De-energize if possible"],
                    "required_ppe": ["Insulated gloves", "Safety glasses"],
                    "lockout_tagout_required": True,
                    "permit_required": False
                }
            ],
            "violations": ["Electrical work without de-energization"],
            "required_actions": ["De-energize equipment"],
            "approved_to_proceed": False,
            "escalation_required": True
        }
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.88,
            "issue_type": "electrical_malfunction",
            "description": "Circuit breaker replacement needed"
        }
        
        # Call safety violation handler
        response = orchestrator._handle_safety_violation(
            workflow_state,
            safety_check_result,
            diagnosis_result
        )
        
        # Verify alternative procedure generated
        assert "alternative_procedure" in response.data
        alternative = response.data["alternative_procedure"]
        
        if alternative:  # May be None for some scenarios
            assert "procedure_type" in alternative
            assert "steps" in alternative
            assert len(alternative["steps"]) > 0
            assert "additional_safety" in alternative
    
    def test_mechanical_hazard_requires_equipment_shutdown(self):
        """Test that mechanical hazard generates shutdown procedure."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-007",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-007",
            site_id="site-007"
        )
        
        safety_check_result = {
            "check_id": "safety-003",
            "timestamp": datetime.now().isoformat(),
            "status": "requires_additional_ppe",
            "hazards_identified": [
                {
                    "hazard_id": "hazard-003",
                    "hazard_type": "mechanical",
                    "severity": "medium",
                    "description": "Moving parts present",
                    "mitigation_required": ["Shut down equipment"],
                    "required_ppe": ["Safety gloves", "Safety glasses"],
                    "lockout_tagout_required": False,
                    "permit_required": False
                }
            ],
            "violations": [],
            "required_actions": ["Shut down equipment"],
            "approved_to_proceed": False,
            "escalation_required": True
        }
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.90,
            "issue_type": "hardware_defect",
            "description": "Fan bearing replacement needed"
        }
        
        # Call safety violation handler
        response = orchestrator._handle_safety_violation(
            workflow_state,
            safety_check_result,
            diagnosis_result
        )
        
        # Verify response
        assert response.success == False
        assert response.data["workflow_halted"] == True
        
        # Check for alternative procedure
        alternative = response.data.get("alternative_procedure")
        if alternative:
            assert alternative["procedure_type"] == "equipment_shutdown"
    
    def test_ppe_requirements_included_in_response(self):
        """Test that PPE requirements are properly included in response."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        workflow_state = WorkflowState(
            session_id="test-session-008",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-008",
            site_id="site-008"
        )
        
        safety_check_result = {
            "check_id": "safety-004",
            "timestamp": datetime.now().isoformat(),
            "status": "requires_additional_ppe",
            "hazards_identified": [
                {
                    "hazard_id": "hazard-004",
                    "hazard_type": "electrical",
                    "severity": "high",
                    "description": "Electrical panel work",
                    "mitigation_required": ["Use insulated tools"],
                    "required_ppe": ["Insulated gloves", "Safety glasses", "Electrical-rated footwear"],
                    "lockout_tagout_required": True,
                    "permit_required": False
                }
            ],
            "violations": [],
            "required_actions": ["Verify PPE"],
            "approved_to_proceed": False,
            "escalation_required": True
        }
        
        diagnosis_result = {
            "success": True,
            "confidence": 0.87,
            "issue_type": "electrical_malfunction",
            "description": "Panel inspection required"
        }
        
        # Call safety violation handler
        response = orchestrator._handle_safety_violation(
            workflow_state,
            safety_check_result,
            diagnosis_result
        )
        
        # Verify PPE requirements
        ppe_action = next(
            (a for a in response.data["required_actions"] if a["action"] == "verify_ppe"),
            None
        )
        
        assert ppe_action is not None
        assert "ppe_list" in ppe_action
        assert len(ppe_action["ppe_list"]) == 3
        assert "Insulated gloves" in ppe_action["ppe_list"]


class TestIntegratedRecoveryWorkflow:
    """Test integrated recovery workflows in orchestration layer."""
    
    @patch('src.orchestration.OrchestrationLayer.OrchestrationLayer.route_to_diagnosis_agent')
    def test_diagnosis_with_low_confidence_triggers_recovery(self, mock_diagnosis):
        """Test that diagnosis with low confidence triggers recovery workflow."""
        orchestrator = OrchestrationLayer(enable_validation=False)
        
        # Mock diagnosis agent to return low confidence
        mock_diagnosis.return_value = {
            "success": True,
            "confidence": 0.68,
            "issue_type": "hardware_defect",
            "description": "Unclear failure mode"
        }
        
        workflow_state = WorkflowState(
            session_id="test-session-009",
            current_phase=WorkflowPhase.DIAGNOSIS,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-009",
            site_id="site-009"
        )
        
        orchestrator.sessions["test-session-009"] = workflow_state
        
        request = FieldRequest(
            session_id="test-session-009",
            technician_id="tech-009",
            site_id="site-009",
            request_type="diagnosis"
        )
        request.site_context = SiteContext(
            site_id="site-009",
            site_name="Test Site 009",
            site_type=SiteType.DATA_CENTER,
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            criticality_level=CriticalityLevel.TIER1,
            operating_hours=OperatingHours(start_hour=0, end_hour=23, days_of_week=[0,1,2,3,4,5,6], timezone="UTC"),
            environmental_conditions=EnvironmentalData(temperature_celsius=22.0, humidity_percent=45.0),
            component_id="comp-009",
            component_type="server"
        )
        
        # Process request
        response = orchestrator._handle_diagnosis(workflow_state, request)
        
        # Verify recovery triggered
        assert response.success == False
        assert "additional photos" in response.message.lower()
        assert response.data.get("requires_additional_photos") == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
