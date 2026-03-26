"""
Multi-Agent Coordination Module

Handles:
- Parallel agent execution
- Agent output aggregation
- Context sharing between agents
- Dependency management
- Fallback strategies
- Escalation handling
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging

from src.models.validation import EscalationLevel

logger = logging.getLogger(__name__)


class AgentExecutionMode(Enum):
    """Agent execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class EscalationType(Enum):
    """Types of escalations."""
    SAFETY_VIOLATION = "safety_violation"
    BUDGET_EXCEEDED = "budget_exceeded"
    LOW_CONFIDENCE = "low_confidence"
    TECHNICAL_COMPLEXITY = "technical_complexity"
    APPROVAL_REQUIRED = "approval_required"
    SYSTEM_FAILURE = "system_failure"


class Escalation:
    """Escalation record."""
    
    def __init__(
        self,
        escalation_id: str,
        escalation_type: EscalationType,
        severity: EscalationLevel,
        description: str,
        context: Dict[str, Any],
        created_at: datetime,
        resolved: bool = False
    ):
        self.escalation_id = escalation_id
        self.escalation_type = escalation_type
        self.severity = severity
        self.description = description
        self.context = context
        self.created_at = created_at
        self.resolved = resolved
        self.resolved_at: Optional[datetime] = None
        self.resolution_notes: Optional[str] = None
    
    def resolve(self, notes: str):
        """Mark escalation as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now()
        self.resolution_notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "escalation_id": self.escalation_id,
            "escalation_type": self.escalation_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes
        }


class AgentCoordinator:
    """
    Coordinates multi-agent execution with dependency management.
    
    Features:
    - Parallel execution where possible
    - Sequential execution with dependencies
    - Context sharing between agents
    - Fallback strategies on failure
    """
    
    def __init__(self):
        """Initialize agent coordinator."""
        self.execution_history: List[Dict[str, Any]] = []
    
    def execute_agents_parallel(
        self,
        agent_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple agents in parallel.
        
        Args:
            agent_tasks: List of agent tasks with format:
                {
                    "agent_name": str,
                    "agent_func": callable,
                    "args": tuple,
                    "kwargs": dict
                }
        
        Returns:
            List of results from each agent
        """
        logger.info(f"Executing {len(agent_tasks)} agents in parallel")
        
        results = []
        start_time = datetime.now()
        
        for task in agent_tasks:
            try:
                agent_name = task["agent_name"]
                agent_func = task["agent_func"]
                args = task.get("args", ())
                kwargs = task.get("kwargs", {})
                
                logger.info(f"Executing agent: {agent_name}")
                result = agent_func(*args, **kwargs)
                
                results.append({
                    "agent_name": agent_name,
                    "success": True,
                    "result": result,
                    "error": None
                })
                
            except Exception as e:
                logger.error(f"Agent {task['agent_name']} failed: {e}")
                results.append({
                    "agent_name": task["agent_name"],
                    "success": False,
                    "result": None,
                    "error": str(e)
                })
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Parallel execution completed in {duration:.2f}s")
        
        # Record execution
        self.execution_history.append({
            "mode": AgentExecutionMode.PARALLEL.value,
            "agents": [t["agent_name"] for t in agent_tasks],
            "duration_seconds": duration,
            "timestamp": start_time.isoformat()
        })
        
        return results
    
    def execute_agents_sequential(
        self,
        agent_tasks: List[Dict[str, Any]],
        stop_on_failure: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute agents sequentially with optional early stopping.
        
        Args:
            agent_tasks: List of agent tasks
            stop_on_failure: Stop execution if any agent fails
        
        Returns:
            List of results from each agent
        """
        logger.info(f"Executing {len(agent_tasks)} agents sequentially")
        
        results = []
        start_time = datetime.now()
        
        for task in agent_tasks:
            try:
                agent_name = task["agent_name"]
                agent_func = task["agent_func"]
                args = task.get("args", ())
                kwargs = task.get("kwargs", {})
                
                # Pass previous results as context if requested
                if task.get("use_previous_context"):
                    kwargs["previous_results"] = results
                
                logger.info(f"Executing agent: {agent_name}")
                result = agent_func(*args, **kwargs)
                
                results.append({
                    "agent_name": agent_name,
                    "success": True,
                    "result": result,
                    "error": None
                })
                
            except Exception as e:
                logger.error(f"Agent {task['agent_name']} failed: {e}")
                results.append({
                    "agent_name": task["agent_name"],
                    "success": False,
                    "result": None,
                    "error": str(e)
                })
                
                if stop_on_failure:
                    logger.warning("Stopping sequential execution due to failure")
                    break
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Sequential execution completed in {duration:.2f}s")
        
        # Record execution
        self.execution_history.append({
            "mode": AgentExecutionMode.SEQUENTIAL.value,
            "agents": [t["agent_name"] for t in agent_tasks],
            "duration_seconds": duration,
            "timestamp": start_time.isoformat()
        })
        
        return results
    
    def aggregate_results(
        self,
        results: List[Dict[str, Any]],
        aggregation_strategy: str = "merge"
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.
        
        Args:
            results: List of agent results
            aggregation_strategy: Strategy for aggregation (merge, vote, priority)
        
        Returns:
            Aggregated result
        """
        logger.info(f"Aggregating {len(results)} results using {aggregation_strategy} strategy")
        
        if aggregation_strategy == "merge":
            # Merge all results into single dict
            aggregated = {
                "agents": [],
                "combined_data": {},
                "all_successful": all(r["success"] for r in results)
            }
            
            for result in results:
                aggregated["agents"].append(result["agent_name"])
                if result["success"] and result["result"]:
                    aggregated["combined_data"][result["agent_name"]] = result["result"]
            
            return aggregated
        
        elif aggregation_strategy == "priority":
            # Return first successful result
            for result in results:
                if result["success"]:
                    return result["result"]
            
            return {"error": "All agents failed"}
        
        else:
            raise ValueError(f"Unknown aggregation strategy: {aggregation_strategy}")
    
    def apply_fallback_strategy(
        self,
        failed_agent: str,
        fallback_func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Apply fallback strategy when agent fails.
        
        Args:
            failed_agent: Name of failed agent
            fallback_func: Fallback function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Fallback result
        """
        logger.warning(f"Applying fallback strategy for failed agent: {failed_agent}")
        
        try:
            result = fallback_func(*args, **kwargs)
            logger.info("Fallback strategy succeeded")
            return {
                "success": True,
                "result": result,
                "fallback_used": True
            }
        except Exception as e:
            logger.error(f"Fallback strategy failed: {e}")
            return {
                "success": False,
                "result": None,
                "fallback_used": True,
                "error": str(e)
            }


class EscalationManager:
    """
    Manages workflow escalations.
    
    Features:
    - Escalation creation and tracking
    - Notification system
    - Workflow pause/resume
    - Escalation resolution
    """
    
    def __init__(self):
        """Initialize escalation manager."""
        self.escalations: Dict[str, Escalation] = {}
        self.escalation_counter = 1000
    
    def create_escalation(
        self,
        escalation_type: EscalationType,
        severity: EscalationLevel,
        description: str,
        context: Dict[str, Any]
    ) -> Escalation:
        """
        Create new escalation.
        
        Args:
            escalation_type: Type of escalation
            severity: Severity level
            description: Description of issue
            context: Additional context
        
        Returns:
            Created escalation
        """
        escalation_id = f"ESC-{self.escalation_counter:06d}"
        self.escalation_counter += 1
        
        escalation = Escalation(
            escalation_id=escalation_id,
            escalation_type=escalation_type,
            severity=severity,
            description=description,
            context=context,
            created_at=datetime.now()
        )
        
        self.escalations[escalation_id] = escalation
        
        logger.warning(
            f"Escalation created: {escalation_id} "
            f"[{escalation_type.value}] - {description}"
        )
        
        # Send notifications
        self._send_notifications(escalation)
        
        return escalation
    
    def resolve_escalation(
        self,
        escalation_id: str,
        resolution_notes: str
    ) -> bool:
        """
        Resolve an escalation.
        
        Args:
            escalation_id: Escalation ID
            resolution_notes: Resolution notes
        
        Returns:
            True if resolved successfully
        """
        if escalation_id not in self.escalations:
            logger.error(f"Escalation not found: {escalation_id}")
            return False
        
        escalation = self.escalations[escalation_id]
        escalation.resolve(resolution_notes)
        
        logger.info(f"Escalation resolved: {escalation_id}")
        
        return True
    
    def get_active_escalations(
        self,
        session_id: Optional[str] = None
    ) -> List[Escalation]:
        """
        Get active (unresolved) escalations.
        
        Args:
            session_id: Optional session ID filter
        
        Returns:
            List of active escalations
        """
        active = [
            esc for esc in self.escalations.values()
            if not esc.resolved
        ]
        
        if session_id:
            active = [
                esc for esc in active
                if esc.context.get("session_id") == session_id
            ]
        
        return active
    
    def should_pause_workflow(self, escalation: Escalation) -> bool:
        """
        Determine if workflow should be paused for escalation.
        
        Args:
            escalation: Escalation
        
        Returns:
            True if workflow should pause
        """
        # Pause for critical escalations
        if escalation.severity in [EscalationLevel.CRITICAL, EscalationLevel.SAFETY_OFFICER, EscalationLevel.DIRECTOR]:
            return True
        
        # Pause for safety violations
        if escalation.escalation_type == EscalationType.SAFETY_VIOLATION:
            return True
        
        # Pause for budget exceeded (requires approval)
        if escalation.escalation_type == EscalationType.BUDGET_EXCEEDED:
            return True
        
        return False
    
    def _send_notifications(self, escalation: Escalation):
        """
        Send notifications for escalation.
        
        Args:
            escalation: Escalation to notify about
        """
        # Determine recipients based on severity
        recipients = self._get_notification_recipients(escalation)
        
        logger.info(
            f"Sending escalation notifications to: {', '.join(recipients)}"
        )
        
        # In production, this would send actual notifications (email, SMS, etc.)
        notification_message = (
            f"Escalation {escalation.escalation_id}: "
            f"{escalation.description}"
        )
        
        for recipient in recipients:
            logger.info(f"  -> {recipient}: {notification_message}")
    
    def _get_notification_recipients(
        self,
        escalation: Escalation
    ) -> List[str]:
        """
        Get notification recipients based on escalation severity.
        
        Args:
            escalation: Escalation
        
        Returns:
            List of recipient IDs
        """
        if escalation.severity in [EscalationLevel.SAFETY_OFFICER, EscalationLevel.CRITICAL]:
            return ["safety-officer", "supervisor", "manager"]
        
        elif escalation.severity == EscalationLevel.DIRECTOR:
            return ["director", "manager"]
        
        elif escalation.severity == EscalationLevel.MANAGER:
            return ["manager", "supervisor"]
        
        elif escalation.severity == EscalationLevel.SUPERVISOR:
            return ["supervisor"]
        
        else:
            return []
    
    def get_escalation_summary(self) -> Dict[str, Any]:
        """
        Get summary of all escalations.
        
        Returns:
            Escalation summary statistics
        """
        total = len(self.escalations)
        active = len([e for e in self.escalations.values() if not e.resolved])
        resolved = total - active
        
        by_type = {}
        by_severity = {}
        
        for escalation in self.escalations.values():
            # Count by type
            esc_type = escalation.escalation_type.value
            by_type[esc_type] = by_type.get(esc_type, 0) + 1
            
            # Count by severity
            severity = escalation.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_escalations": total,
            "active_escalations": active,
            "resolved_escalations": resolved,
            "by_type": by_type,
            "by_severity": by_severity
        }
