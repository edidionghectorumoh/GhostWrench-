"""
Tests for data models.
"""

import pytest
from datetime import datetime

from src.models.domain import (
    SiteContext,
    SiteType,
    CriticalityLevel,
    GeoLocation,
    OperatingHours,
    EnvironmentalData,
    ImageData,
    ImageMetadata,
    Part,
)
from src.models.workflow import (
    WorkflowState,
    WorkflowPhase,
    DiagnosisState,
)
from src.models.validation import (
    AgentOutput,
    AgentType,
    JudgmentResult,
    EscalationLevel,
)


class TestDomainModels:
    """Test domain data models."""
    
    def test_geo_location_valid(self):
        """Test valid GeoLocation creation."""
        loc = GeoLocation(latitude=40.7128, longitude=-74.0060)
        assert loc.latitude == 40.7128
        assert loc.longitude == -74.0060
    
    def test_geo_location_invalid_latitude(self):
        """Test invalid latitude raises error."""
        with pytest.raises(ValueError):
            GeoLocation(latitude=100.0, longitude=0.0)
    
    def test_image_data_valid_resolution(self):
        """Test ImageData with valid resolution."""
        image = ImageData(
            image_id="img-001",
            raw_image=b"fake_image_data",
            resolution={"width": 1920, "height": 1080},
            capture_timestamp=datetime.now(),
            capture_location=GeoLocation(40.0, -74.0),
            metadata=ImageMetadata(device_model="iPhone", orientation="landscape"),
        )
        assert image.resolution["width"] == 1920
    
    def test_image_data_invalid_resolution(self):
        """Test ImageData with invalid resolution raises error."""
        with pytest.raises(ValueError):
            ImageData(
                image_id="img-001",
                raw_image=b"fake_image_data",
                resolution={"width": 800, "height": 600},  # Below minimum
                capture_timestamp=datetime.now(),
                capture_location=GeoLocation(40.0, -74.0),
                metadata=ImageMetadata(device_model="iPhone", orientation="landscape"),
            )
    
    def test_part_valid(self):
        """Test Part creation with valid data."""
        part = Part(
            part_number="PWR-001",
            description="Power Supply",
            manufacturer="Cisco",
            category="power",
            unit_cost=450.00,
            quantity_available=10,
            warehouse_location="WH-01",
            lead_time_days=3,
        )
        assert part.unit_cost == 450.00
    
    def test_part_invalid_cost(self):
        """Test Part with negative cost raises error."""
        with pytest.raises(ValueError):
            Part(
                part_number="PWR-001",
                description="Power Supply",
                manufacturer="Cisco",
                category="power",
                unit_cost=-100.00,  # Invalid
                quantity_available=10,
                warehouse_location="WH-01",
                lead_time_days=3,
            )


class TestWorkflowModels:
    """Test workflow state models."""
    
    def test_workflow_state_creation(self):
        """Test WorkflowState creation."""
        state = WorkflowState(
            session_id="session-001",
            current_phase=WorkflowPhase.INTAKE,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-001",
            site_id="site-001",
        )
        assert state.current_phase == WorkflowPhase.INTAKE
    
    def test_workflow_phase_transition_valid(self):
        """Test valid phase transition."""
        state = WorkflowState(
            session_id="session-001",
            current_phase=WorkflowPhase.INTAKE,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-001",
            site_id="site-001",
        )
        assert state.can_transition_to(WorkflowPhase.DIAGNOSIS)
    
    def test_workflow_phase_transition_invalid(self):
        """Test invalid phase transition."""
        state = WorkflowState(
            session_id="session-001",
            current_phase=WorkflowPhase.INTAKE,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="tech-001",
            site_id="site-001",
        )
        assert not state.can_transition_to(WorkflowPhase.COMPLETION)


class TestValidationModels:
    """Test validation models."""
    
    def test_agent_output_valid(self):
        """Test AgentOutput creation."""
        output = AgentOutput(
            agent_type=AgentType.DIAGNOSIS,
            output_data={"test": "data"},
            confidence=0.85,
            timestamp=datetime.now(),
            session_id="session-001",
        )
        assert output.confidence == 0.85
    
    def test_agent_output_invalid_confidence(self):
        """Test AgentOutput with invalid confidence raises error."""
        with pytest.raises(ValueError):
            AgentOutput(
                agent_type=AgentType.DIAGNOSIS,
                output_data={"test": "data"},
                confidence=1.5,  # Invalid (> 1.0)
                timestamp=datetime.now(),
                session_id="session-001",
            )
    
    def test_judgment_result_approved(self):
        """Test JudgmentResult for approved output."""
        judgment = JudgmentResult(
            approved=True,
            confidence=0.90,
            reasoning="All criteria satisfied",
            violations=[],
            recommendations=[],
            requires_human_review=False,
            escalation_level=EscalationLevel.NONE,
        )
        assert judgment.approved
        assert len(judgment.violations) == 0
    
    def test_judgment_result_rejected_requires_violations(self):
        """Test JudgmentResult rejected without violations raises error."""
        with pytest.raises(ValueError):
            JudgmentResult(
                approved=False,
                confidence=0.90,
                reasoning="Rejected",
                violations=[],  # Should have violations
                recommendations=[],
                requires_human_review=True,
                escalation_level=EscalationLevel.SUPERVISOR,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
