"""
Workflow Persistence Module

Handles:
- Checkpoint persistence for crash recovery
- Workflow state serialization/deserialization
- Workflow resumption from saved state
- State validation and integrity checks
"""

import json
import os
from typing import Dict, Optional, Any
from datetime import datetime
import logging

from src.models.workflow import WorkflowState, WorkflowPhase

logger = logging.getLogger(__name__)


class WorkflowPersistence:
    """
    Manages workflow state persistence for crash recovery.
    
    Features:
    - Automatic checkpoint saving at phase transitions
    - State serialization to JSON
    - Workflow resumption from checkpoints
    - State integrity validation
    """
    
    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        """
        Initialize workflow persistence.
        
        Args:
            checkpoint_dir: Directory for checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir
        
        # Create checkpoint directory if it doesn't exist
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
            logger.info(f"Created checkpoint directory: {checkpoint_dir}")
    
    def save_checkpoint(
        self,
        workflow_state: WorkflowState
    ) -> bool:
        """
        Save workflow state checkpoint.
        
        Args:
            workflow_state: Workflow state to save
            
        Returns:
            True if saved successfully
        """
        try:
            checkpoint_file = self._get_checkpoint_path(workflow_state.session_id)
            
            # Serialize workflow state
            state_data = self._serialize_workflow_state(workflow_state)
            
            # Write to file
            with open(checkpoint_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.info(
                f"Saved checkpoint for session {workflow_state.session_id} "
                f"at phase {workflow_state.current_phase.value}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    def load_checkpoint(
        self,
        session_id: str
    ) -> Optional[WorkflowState]:
        """
        Load workflow state from checkpoint.
        
        Args:
            session_id: Session ID
            
        Returns:
            Workflow state or None if not found
        """
        try:
            checkpoint_file = self._get_checkpoint_path(session_id)
            
            if not os.path.exists(checkpoint_file):
                logger.warning(f"No checkpoint found for session {session_id}")
                return None
            
            # Read from file
            with open(checkpoint_file, 'r') as f:
                state_data = json.load(f)
            
            # Deserialize workflow state
            workflow_state = self._deserialize_workflow_state(state_data)
            
            logger.info(
                f"Loaded checkpoint for session {session_id} "
                f"at phase {workflow_state.current_phase.value}"
            )
            
            return workflow_state
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def delete_checkpoint(self, session_id: str) -> bool:
        """
        Delete checkpoint for completed workflow.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted successfully
        """
        try:
            checkpoint_file = self._get_checkpoint_path(session_id)
            
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
                logger.info(f"Deleted checkpoint for session {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
            return False
    
    def list_checkpoints(self) -> list:
        """
        List all available checkpoints.
        
        Returns:
            List of session IDs with checkpoints
        """
        try:
            checkpoints = []
            
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.json'):
                    session_id = filename.replace('.json', '')
                    checkpoints.append(session_id)
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []
    
    def _get_checkpoint_path(self, session_id: str) -> str:
        """Get checkpoint file path for session."""
        return os.path.join(self.checkpoint_dir, f"{session_id}.json")
    
    def _serialize_workflow_state(
        self,
        workflow_state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Serialize workflow state to dictionary.
        
        Args:
            workflow_state: Workflow state
            
        Returns:
            Serialized state
        """
        return {
            "session_id": workflow_state.session_id,
            "current_phase": workflow_state.current_phase.value,
            "start_time": workflow_state.start_time.isoformat() if workflow_state.start_time else None,
            "end_time": workflow_state.end_time.isoformat() if workflow_state.end_time else None,
            "last_activity": workflow_state.last_activity.isoformat() if workflow_state.last_activity else None,
            "technician_id": workflow_state.technician_id,
            "site_id": workflow_state.site_id,
            "diagnosis_state": workflow_state.diagnosis_state,
            "procurement_state": workflow_state.procurement_state,
            "guidance_state": workflow_state.guidance_state,
            "escalations": workflow_state.escalations,
            "metadata": workflow_state.metadata
        }
    
    def _deserialize_workflow_state(
        self,
        state_data: Dict[str, Any]
    ) -> WorkflowState:
        """
        Deserialize workflow state from dictionary.
        
        Args:
            state_data: Serialized state
            
        Returns:
            Workflow state
        """
        workflow_state = WorkflowState(
            session_id=state_data["session_id"],
            current_phase=WorkflowPhase(state_data["current_phase"]),
            start_time=datetime.fromisoformat(state_data["start_time"]) if state_data.get("start_time") else datetime.now(),
            last_activity=datetime.fromisoformat(state_data["last_activity"]) if state_data.get("last_activity") else datetime.now(),
            technician_id=state_data.get("technician_id"),
            site_id=state_data.get("site_id")
        )
        
        # Restore phase-specific states
        workflow_state.diagnosis_state = state_data.get("diagnosis_state")
        workflow_state.procurement_state = state_data.get("procurement_state")
        workflow_state.guidance_state = state_data.get("guidance_state")
        workflow_state.escalations = state_data.get("escalations", [])
        workflow_state.metadata = state_data.get("metadata", {})
        
        if state_data.get("end_time"):
            workflow_state.end_time = datetime.fromisoformat(state_data["end_time"])
        
        return workflow_state
    
    def validate_checkpoint(self, session_id: str) -> bool:
        """
        Validate checkpoint integrity.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if checkpoint is valid
        """
        try:
            workflow_state = self.load_checkpoint(session_id)
            
            if not workflow_state:
                return False
            
            # Basic validation checks
            if not workflow_state.session_id:
                logger.error("Invalid checkpoint: missing session_id")
                return False
            
            if not workflow_state.current_phase:
                logger.error("Invalid checkpoint: missing current_phase")
                return False
            
            if not workflow_state.start_time:
                logger.error("Invalid checkpoint: missing start_time")
                return False
            
            logger.info(f"Checkpoint validation passed for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Checkpoint validation failed: {e}")
            return False


class PhaseTransitionManager:
    """
    Manages workflow phase transitions with validation.
    
    Features:
    - Phase transition validation
    - Automatic checkpoint saving
    - Transition history tracking
    """
    
    def __init__(self, persistence: WorkflowPersistence):
        """
        Initialize phase transition manager.
        
        Args:
            persistence: Workflow persistence instance
        """
        self.persistence = persistence
    
    def transition_phase(
        self,
        workflow_state: WorkflowState,
        target_phase: WorkflowPhase,
        save_checkpoint: bool = True
    ) -> bool:
        """
        Transition workflow to target phase.
        
        Args:
            workflow_state: Current workflow state
            target_phase: Target phase
            save_checkpoint: Save checkpoint after transition
            
        Returns:
            True if transition successful
        """
        logger.info(
            f"Attempting phase transition: {workflow_state.current_phase.value} "
            f"-> {target_phase.value}"
        )
        
        # Validate transition
        if not workflow_state.can_transition_to(target_phase):
            logger.error(
                f"Invalid phase transition: {workflow_state.current_phase.value} "
                f"-> {target_phase.value}"
            )
            return False
        
        # Record transition in metadata
        if "phase_transitions" not in workflow_state.metadata:
            workflow_state.metadata["phase_transitions"] = []
        
        workflow_state.metadata["phase_transitions"].append({
            "from_phase": workflow_state.current_phase.value,
            "to_phase": target_phase.value,
            "timestamp": datetime.now().isoformat()
        })
        
        # Perform transition
        workflow_state.current_phase = target_phase
        workflow_state.last_activity = datetime.now()
        
        # Save checkpoint
        if save_checkpoint:
            self.persistence.save_checkpoint(workflow_state)
        
        logger.info(f"Phase transition successful: now in {target_phase.value}")
        
        return True
    
    def get_transition_history(
        self,
        workflow_state: WorkflowState
    ) -> list:
        """
        Get phase transition history.
        
        Args:
            workflow_state: Workflow state
            
        Returns:
            List of transitions
        """
        return workflow_state.metadata.get("phase_transitions", [])
    
    def can_resume_workflow(
        self,
        workflow_state: WorkflowState
    ) -> bool:
        """
        Check if workflow can be resumed.
        
        Args:
            workflow_state: Workflow state
            
        Returns:
            True if workflow can be resumed
        """
        # Cannot resume completed workflows
        if workflow_state.current_phase == WorkflowPhase.COMPLETION:
            if workflow_state.end_time:
                logger.warning("Cannot resume completed workflow")
                return False
        
        # Check if workflow is stale (> 24 hours old)
        if workflow_state.last_activity:
            age = datetime.now() - workflow_state.last_activity
            if age.total_seconds() > 86400:  # 24 hours
                logger.warning(f"Workflow is stale (age: {age})")
                return False
        
        return True
