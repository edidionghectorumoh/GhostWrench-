"""
Thought Logger

Structured JSON logging for agent reasoning (Thought-Action-Observation loops).
Captures the complete reasoning chain for debugging, auditing, and analysis.

Log Format:
{
    "timestamp": "2026-02-28T10:30:45.123Z",
    "session_id": "session-abc123",
    "agent_type": "diagnosis",
    "phase": "diagnosis",
    "thought": "Equipment shows signs of hardware failure...",
    "action": "analyze_image",
    "observation": "Confidence: 0.92, Issue: hardware_defect",
    "metadata": {...}
}
"""

import json
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum


class AgentPhase(str, Enum):
    """Agent workflow phases."""
    INTAKE = "intake"
    DIAGNOSIS = "diagnosis"
    PROCUREMENT = "procurement"
    GUIDANCE = "guidance"
    COMPLETION = "completion"


class ThoughtLogger:
    """
    Structured logger for agent reasoning chains.
    
    Logs Thought-Action-Observation (TAO) loops to JSONL format for:
    - Debugging agent behavior
    - Auditing decision-making
    - Training data collection
    - Performance analysis
    """
    
    def __init__(
        self,
        log_path: str = "/app/logs/agent_thoughts.jsonl",
        enabled: bool = True
    ):
        """
        Initialize thought logger.
        
        Args:
            log_path: Path to JSONL log file
            enabled: Enable/disable logging
        """
        self.log_path = Path(log_path)
        self.enabled = enabled
        
        # Create log directory if it doesn't exist
        if self.enabled:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up Python logger for errors
        self.logger = logging.getLogger(__name__)
    
    def log_thought(
        self,
        session_id: str,
        agent_type: str,
        phase: AgentPhase,
        thought: str,
        action: Optional[str] = None,
        observation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a Thought-Action-Observation entry.
        
        Args:
            session_id: Session ID
            agent_type: Agent type (diagnosis, action, guidance)
            phase: Workflow phase
            thought: Agent's reasoning/thought process
            action: Action taken (optional)
            observation: Result/observation from action (optional)
            metadata: Additional context (optional)
        """
        if not self.enabled:
            return
        
        try:
            entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "session_id": session_id,
                "agent_type": agent_type,
                "phase": phase.value if isinstance(phase, AgentPhase) else phase,
                "thought": thought,
                "action": action,
                "observation": observation,
                "metadata": metadata or {}
            }
            
            # Append to JSONL file
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to log thought: {e}")
    
    def log_diagnosis_reasoning(
        self,
        session_id: str,
        thought: str,
        image_analysis: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        issue_type: Optional[str] = None
    ):
        """
        Log diagnosis agent reasoning.
        
        Args:
            session_id: Session ID
            thought: Reasoning process
            image_analysis: Image analysis results
            confidence: Diagnosis confidence
            issue_type: Identified issue type
        """
        observation = None
        if confidence is not None and issue_type:
            observation = f"Confidence: {confidence:.2f}, Issue: {issue_type}"
        
        self.log_thought(
            session_id=session_id,
            agent_type="diagnosis",
            phase=AgentPhase.DIAGNOSIS,
            thought=thought,
            action="analyze_image",
            observation=observation,
            metadata={
                "image_analysis": image_analysis,
                "confidence": confidence,
                "issue_type": issue_type
            }
        )
    
    def log_procurement_reasoning(
        self,
        session_id: str,
        thought: str,
        parts_searched: Optional[List[str]] = None,
        total_cost: Optional[float] = None,
        approval_required: Optional[bool] = None
    ):
        """
        Log action agent procurement reasoning.
        
        Args:
            session_id: Session ID
            thought: Reasoning process
            parts_searched: Parts searched
            total_cost: Total procurement cost
            approval_required: Whether approval is required
        """
        observation = None
        if total_cost is not None:
            observation = f"Total cost: ${total_cost:.2f}"
            if approval_required:
                observation += " (approval required)"
        
        self.log_thought(
            session_id=session_id,
            agent_type="action",
            phase=AgentPhase.PROCUREMENT,
            thought=thought,
            action="search_inventory",
            observation=observation,
            metadata={
                "parts_searched": parts_searched,
                "total_cost": total_cost,
                "approval_required": approval_required
            }
        )
    
    def log_guidance_reasoning(
        self,
        session_id: str,
        thought: str,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        safety_check: Optional[bool] = None
    ):
        """
        Log guidance agent reasoning.
        
        Args:
            session_id: Session ID
            thought: Reasoning process
            current_step: Current step number
            total_steps: Total number of steps
            safety_check: Safety check result
        """
        observation = None
        if current_step is not None and total_steps is not None:
            observation = f"Step {current_step}/{total_steps}"
            if safety_check is not None:
                observation += f", Safety: {'✓' if safety_check else '✗'}"
        
        self.log_thought(
            session_id=session_id,
            agent_type="guidance",
            phase=AgentPhase.GUIDANCE,
            thought=thought,
            action="generate_step",
            observation=observation,
            metadata={
                "current_step": current_step,
                "total_steps": total_steps,
                "safety_check": safety_check
            }
        )
    
    def log_validation_reasoning(
        self,
        session_id: str,
        thought: str,
        validation_type: str,
        approved: bool,
        violations: Optional[List[str]] = None
    ):
        """
        Log judge validation reasoning.
        
        Args:
            session_id: Session ID
            thought: Reasoning process
            validation_type: Type of validation (safety, budget, sop)
            approved: Whether validation passed
            violations: List of violations if any
        """
        observation = f"Validation: {'APPROVED' if approved else 'REJECTED'}"
        if violations:
            observation += f", Violations: {len(violations)}"
        
        self.log_thought(
            session_id=session_id,
            agent_type="judge",
            phase=AgentPhase.DIAGNOSIS,  # Phase depends on when validation occurs
            thought=thought,
            action=f"validate_{validation_type}",
            observation=observation,
            metadata={
                "validation_type": validation_type,
                "approved": approved,
                "violations": violations or []
            }
        )
    
    def log_escalation(
        self,
        session_id: str,
        escalation_type: str,
        severity: str,
        description: str
    ):
        """
        Log escalation event.
        
        Args:
            session_id: Session ID
            escalation_type: Type of escalation
            severity: Severity level
            description: Escalation description
        """
        self.log_thought(
            session_id=session_id,
            agent_type="orchestration",
            phase=AgentPhase.DIAGNOSIS,  # Phase depends on when escalation occurs
            thought=f"Escalation required: {description}",
            action="create_escalation",
            observation=f"Type: {escalation_type}, Severity: {severity}",
            metadata={
                "escalation_type": escalation_type,
                "severity": severity,
                "description": description
            }
        )
    
    def query_logs(
        self,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        phase: Optional[AgentPhase] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query thought logs with filters.
        
        Args:
            session_id: Filter by session ID
            agent_type: Filter by agent type
            phase: Filter by phase
            limit: Maximum number of entries to return
            
        Returns:
            List of matching log entries
        """
        if not self.log_path.exists():
            return []
        
        try:
            entries = []
            with open(self.log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    
                    # Apply filters
                    if session_id and entry.get("session_id") != session_id:
                        continue
                    if agent_type and entry.get("agent_type") != agent_type:
                        continue
                    if phase and entry.get("phase") != phase.value:
                        continue
                    
                    entries.append(entry)
                    
                    if len(entries) >= limit:
                        break
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to query logs: {e}")
            return []
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of reasoning for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Summary statistics
        """
        entries = self.query_logs(session_id=session_id, limit=10000)
        
        if not entries:
            return {"session_id": session_id, "total_entries": 0}
        
        # Calculate statistics
        agent_counts = {}
        phase_counts = {}
        
        for entry in entries:
            agent_type = entry.get("agent_type", "unknown")
            phase = entry.get("phase", "unknown")
            
            agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        return {
            "session_id": session_id,
            "total_entries": len(entries),
            "agent_counts": agent_counts,
            "phase_counts": phase_counts,
            "first_entry": entries[0].get("timestamp") if entries else None,
            "last_entry": entries[-1].get("timestamp") if entries else None
        }
