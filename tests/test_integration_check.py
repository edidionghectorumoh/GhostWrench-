"""
Integration check to verify all components can be imported and initialized.
"""

import pytest


class TestImports:
    """Test that all modules can be imported."""
    
    def test_import_models(self):
        """Test importing data models."""
        from src.models import (
            SiteContext,
            Component,
            ImageData,
            WorkflowState,
            AgentOutput,
            ValidationCriteria,
        )
        assert SiteContext is not None
        assert Component is not None
        assert ImageData is not None
        assert WorkflowState is not None
        assert AgentOutput is not None
        assert ValidationCriteria is not None
    
    def test_import_judge(self):
        """Test importing cloud judge."""
        from src.judge.cloud_judge import CloudJudge
        from src.judge.audit_logger import AuditLogger
        assert CloudJudge is not None
        assert AuditLogger is not None
    
    def test_import_rag(self):
        """Test importing RAG system."""
        from src.rag.RAGSystem import RAGSystem
        assert RAGSystem is not None
    
    def test_import_config(self):
        """Test importing config."""
        import config
        assert config.bedrock_runtime is not None
        assert config.NOVA_PRO_MODEL_ID is not None
        assert config.CLAUDE_SONNET_MODEL_ID is not None


class TestComponentInitialization:
    """Test that components can be initialized (without external dependencies)."""
    
    def test_audit_logger_init(self):
        """Test AuditLogger initialization."""
        from src.judge.audit_logger import AuditLogger
        
        # Initialize with test database
        logger = AuditLogger(db_path="test_audit.db")
        assert logger is not None
        
        # Get statistics (should be empty)
        stats = logger.get_statistics()
        assert stats['total_judgments'] == 0
        
        # Cleanup
        import os
        if os.path.exists("test_audit.db"):
            os.remove("test_audit.db")
    
    def test_workflow_state_transitions(self):
        """Test workflow state transitions."""
        from src.models.workflow import WorkflowState, WorkflowPhase
        from datetime import datetime
        
        state = WorkflowState(
            session_id="test-session",
            current_phase=WorkflowPhase.INTAKE,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id="test-tech",
            site_id="test-site",
        )
        
        # Test valid transitions
        assert state.can_transition_to(WorkflowPhase.DIAGNOSIS)
        
        # Update phase
        state.current_phase = WorkflowPhase.DIAGNOSIS
        assert state.can_transition_to(WorkflowPhase.PROCUREMENT)
        assert state.can_transition_to(WorkflowPhase.GUIDANCE)


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_config_values(self):
        """Test config has required values."""
        import config
        
        assert config.AWS_REGION == "us-east-1"
        assert "nova" in config.NOVA_PRO_MODEL_ID.lower()
        assert "claude" in config.CLAUDE_SONNET_MODEL_ID.lower()
        assert config.MODEL_CONFIG is not None
        assert "nova_pro" in config.MODEL_CONFIG
        assert "claude_sonnet" in config.MODEL_CONFIG


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
