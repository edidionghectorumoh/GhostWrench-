"""
Orchestration Layer

This module coordinates the multi-agent workflow for field repairs:
- Routes requests to appropriate agents (Diagnosis, Action, Guidance)
- Manages workflow state and phase transitions
- Enforces validation gates using Cloud Judge
- Handles session management and persistence
- Implements escalation handling
- Enables multi-agent coordination

Workflow Phases:
1. INTAKE - Initial request processing
2. DIAGNOSIS - Multimodal diagnosis with Nova Pro
3. PROCUREMENT - Parts procurement with Nova Act
4. GUIDANCE - Voice-guided repair with Nova Sonic
5. COMPLETION - Finalization and record creation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
import uuid
import os

from src.models.workflow import WorkflowState, WorkflowPhase
from src.models.agents import FieldRequest, FieldResponse
from src.models.validation import AgentOutput, AgentType, ValidationCriteria
from src.agents.DiagnosisAgent import DiagnosisAgent
from src.agents.ActionAgent import ActionAgent
from src.agents.GuidanceAgent import GuidanceAgent
from src.judge.cloud_judge import CloudJudge
from src.rag.RAGSystem import RAGSystem
from src.external import (
    MockInventoryClient,
    MockProcurementClient,
    MockTelemetryClient,
    MockMaintenanceLogClient
)
from src.orchestration.WorkflowPersistence import WorkflowPersistence, PhaseTransitionManager
from src.orchestration.AgentCoordination import (
    AgentCoordinator,
    EscalationManager,
    EscalationType,
    Escalation
)
from src.orchestration.ThoughtLogger import ThoughtLogger, AgentPhase

logger = logging.getLogger(__name__)


class OrchestrationLayer:
    """
    Orchestration layer for multi-agent field repair workflow.
    
    Coordinates:
    - Diagnosis Agent (Nova Pro)
    - Action Agent (Nova Act)
    - Guidance Agent (Nova Sonic)
    - Cloud Judge (Claude + Nova Pro)
    - RAG System (Weaviate)
    - External Systems (Inventory, Procurement, Telemetry, Maintenance)
    """
    
    def __init__(
        self,
        rag_system: Optional[RAGSystem] = None,
        cloud_judge: Optional[CloudJudge] = None,
        inventory_client: Optional[Any] = None,
        procurement_client: Optional[Any] = None,
        telemetry_client: Optional[Any] = None,
        maintenance_client: Optional[Any] = None,
        enable_validation: bool = True
    ):
        """
        Initialize orchestration layer.
        
        Args:
            rag_system: RAG system for technical manuals
            cloud_judge: Cloud judge for validation
            inventory_client: Inventory system client
            procurement_client: Procurement system client
            telemetry_client: Telemetry system client
            maintenance_client: Maintenance log client
            enable_validation: Enable judge validation gates
        """
        logger.info("Initializing Orchestration Layer")
        
        # Initialize components
        self.rag_system = rag_system or RAGSystem(
            weaviate_url="http://localhost:8080"
        )
        
        self.cloud_judge = cloud_judge or CloudJudge()
        
        # Initialize external system clients
        self.inventory_client = inventory_client or MockInventoryClient()
        self.procurement_client = procurement_client or MockProcurementClient()
        self.telemetry_client = telemetry_client or MockTelemetryClient()
        self.maintenance_client = maintenance_client or MockMaintenanceLogClient()
        
        # Initialize agents
        self.diagnosis_agent = DiagnosisAgent(
            rag_system=self.rag_system
        )
        
        self.action_agent = ActionAgent()
        
        self.guidance_agent = GuidanceAgent(cloud_judge=self.cloud_judge)
        
        self.enable_validation = enable_validation
        
        # Initialize persistence and phase management
        self.persistence = WorkflowPersistence()
        self.phase_manager = PhaseTransitionManager(self.persistence)
        
        # Initialize coordination and escalation
        self.agent_coordinator = AgentCoordinator()
        self.escalation_manager = EscalationManager()
        
        # Initialize thought logger for agent reasoning
        thought_log_enabled = os.getenv("ENABLE_THOUGHT_LOGGING", "true").lower() == "true"
        thought_log_path = os.getenv("THOUGHT_LOG_PATH", "/app/logs/agent_thoughts.jsonl")
        self.thought_logger = ThoughtLogger(
            log_path=thought_log_path,
            enabled=thought_log_enabled
        )
        
        # Session storage (in production, use persistent storage)
        self.sessions: Dict[str, WorkflowState] = {}
        
        logger.info("Orchestration Layer initialized successfully")
    
    def process_field_request(
        self,
        request: FieldRequest
    ) -> FieldResponse:
        """
        Process a field request through the complete workflow.
        
        Args:
            request: Field request from technician
            
        Returns:
            Field response with results
        """
        logger.info(f"Processing field request: {request.request_type}")
        
        # Create or retrieve session
        session_id = request.session_id or str(uuid.uuid4())
        
        if session_id not in self.sessions:
            # Try to load from checkpoint first
            workflow_state = self.persistence.load_checkpoint(session_id)
            
            if workflow_state and self.phase_manager.can_resume_workflow(workflow_state):
                logger.info(f"Resuming workflow from checkpoint: {session_id}")
                self.sessions[session_id] = workflow_state
            else:
                workflow_state = self._initialize_workflow(session_id, request)
        else:
            workflow_state = self.sessions[session_id]
        
        try:
            # Route based on current phase
            if workflow_state.current_phase == WorkflowPhase.INTAKE:
                response = self._handle_intake(workflow_state, request)
            
            elif workflow_state.current_phase == WorkflowPhase.DIAGNOSIS:
                response = self._handle_diagnosis(workflow_state, request)
            
            elif workflow_state.current_phase == WorkflowPhase.PROCUREMENT:
                response = self._handle_procurement(workflow_state, request)
            
            elif workflow_state.current_phase == WorkflowPhase.GUIDANCE:
                response = self._handle_guidance(workflow_state, request)
            
            elif workflow_state.current_phase == WorkflowPhase.COMPLETION:
                response = self._handle_completion(workflow_state, request)
            
            else:
                raise ValueError(f"Unknown workflow phase: {workflow_state.current_phase}")
            
            # Update session
            self.sessions[session_id] = workflow_state
            
            # Save checkpoint
            self.persistence.save_checkpoint(workflow_state)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return FieldResponse(
                session_id=session_id,
                success=False,
                message=f"Error: {str(e)}",
                data={},
                next_phase=workflow_state.current_phase.value
            )
    
    def _initialize_workflow(
        self,
        session_id: str,
        request: FieldRequest
    ) -> WorkflowState:
        """
        Initialize workflow state for new session.
        
        Args:
            session_id: Session ID
            request: Initial request
            
        Returns:
            Initialized workflow state
        """
        logger.info(f"Initializing workflow for session {session_id}")
        
        workflow_state = WorkflowState(
            session_id=session_id,
            current_phase=WorkflowPhase.INTAKE,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            technician_id=request.technician_id,
            site_id=request.site_id or None
        )
        
        return workflow_state
    
    def _handle_intake(
        self,
        workflow_state: WorkflowState,
        request: FieldRequest
    ) -> FieldResponse:
        """
        Handle intake phase - validate request and transition to diagnosis.
        
        Args:
            workflow_state: Current workflow state
            request: Field request
            
        Returns:
            Response with next steps
        """
        logger.info(f"Handling INTAKE phase for session {workflow_state.session_id}")
        
        # Validate request has required data
        if not request.site_id:
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message="Site context is required",
                data={},
                next_phase=WorkflowPhase.INTAKE.value
            )
        
        # Transition to diagnosis
        if workflow_state.can_transition_to(WorkflowPhase.DIAGNOSIS):
            self.phase_manager.transition_phase(
                workflow_state,
                WorkflowPhase.DIAGNOSIS,
                save_checkpoint=True
            )
            
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=True,
                message="Request accepted. Ready for diagnosis.",
                data={
                    "site_id": request.site_id,
                    "technician_id": request.technician_id
                },
                next_phase=WorkflowPhase.DIAGNOSIS.value
            )
        else:
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message="Cannot transition to diagnosis phase",
                data={},
                next_phase=workflow_state.current_phase.value
            )
    
    def _handle_diagnosis(
        self,
        workflow_state: WorkflowState,
        request: FieldRequest
    ) -> FieldResponse:
        """
        Handle diagnosis phase - analyze issue with Diagnosis Agent.
        
        Args:
            workflow_state: Current workflow state
            request: Field request
            
        Returns:
            Response with diagnosis results
        """
        logger.info(f"Handling DIAGNOSIS phase for session {workflow_state.session_id}")
        
        # Log thought: Starting diagnosis
        self.thought_logger.log_thought(
            session_id=workflow_state.session_id,
            agent_type="orchestration",
            phase=AgentPhase.DIAGNOSIS,
            thought="Initiating diagnosis phase. Routing request to diagnosis agent for multimodal analysis.",
            action="route_to_diagnosis_agent",
            metadata={"site_id": request.site_id or None}
        )
        
        # Route to diagnosis agent
        diagnosis_result = self.route_to_diagnosis_agent(request)
        
        if not diagnosis_result.get("success"):
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message="Diagnosis failed",
                data=diagnosis_result,
                next_phase=WorkflowPhase.DIAGNOSIS.value
            )
        
        # Check confidence and handle low confidence recovery (Task 12.1)
        confidence = diagnosis_result.get("confidence", 0.0)
        issue_type = diagnosis_result.get("issue_type", "unknown")
        
        # Log diagnosis result
        self.thought_logger.log_diagnosis_reasoning(
            session_id=workflow_state.session_id,
            thought=f"Diagnosis completed with confidence {confidence:.2f}. Issue identified as {issue_type}.",
            confidence=confidence,
            issue_type=issue_type,
            image_analysis=diagnosis_result.get("image_analysis")
        )
        
        if confidence < 0.85:
            logger.info(f"Low/medium confidence detected ({confidence:.2f}). Initiating recovery.")
            self.thought_logger.log_thought(
                session_id=workflow_state.session_id,
                agent_type="orchestration",
                phase=AgentPhase.DIAGNOSIS,
                thought=f"Confidence {confidence:.2f} below threshold (0.85). Initiating low confidence recovery procedure.",
                action="initiate_recovery",
                metadata={"confidence": confidence, "threshold": 0.85}
            )
            return self._handle_low_confidence_recovery(
                workflow_state,
                diagnosis_result,
                request
            )
        
        # Validate with judge if enabled
        if self.enable_validation:
            self.thought_logger.log_thought(
                session_id=workflow_state.session_id,
                agent_type="orchestration",
                phase=AgentPhase.DIAGNOSIS,
                thought="Diagnosis confidence acceptable. Routing to cloud judge for safety and SOP validation.",
                action="validate_with_judge",
                metadata={"confidence": confidence}
            )
            
            validation_result = self._validate_diagnosis(diagnosis_result)
            
            # Log validation result
            self.thought_logger.log_validation_reasoning(
                session_id=workflow_state.session_id,
                thought=f"Judge validation completed. Result: {'APPROVED' if validation_result.get('approved') else 'REJECTED'}",
                validation_type="diagnosis",
                approved=validation_result.get("approved", False),
                violations=validation_result.get("violations", [])
            )
            
            # Check for safety violations (Task 12.4)
            if validation_result.get("safety_violations"):
                logger.warning("Safety violations detected during diagnosis validation")
                self.thought_logger.log_thought(
                    session_id=workflow_state.session_id,
                    agent_type="orchestration",
                    phase=AgentPhase.DIAGNOSIS,
                    thought="CRITICAL: Safety violations detected. Halting workflow and initiating safety escalation.",
                    action="handle_safety_violation",
                    metadata={"hazards": validation_result.get("hazards_identified", [])}
                )
                return self._handle_safety_violation(
                    workflow_state,
                    validation_result.get("safety_check_result", {}),
                    diagnosis_result
                )
            
            if not validation_result.get("approved"):
                return FieldResponse(
                    session_id=workflow_state.session_id,
                    success=False,
                    message="Diagnosis validation failed",
                    data={
                        "diagnosis": diagnosis_result,
                        "validation": validation_result
                    },
                    next_phase=WorkflowPhase.DIAGNOSIS.value
                )
        
        # Store diagnosis in workflow state
        workflow_state.diagnosis_state = diagnosis_result
        
        # Transition to procurement if parts needed
        if diagnosis_result.get("requires_parts"):
            if workflow_state.can_transition_to(WorkflowPhase.PROCUREMENT):
                workflow_state.current_phase = WorkflowPhase.PROCUREMENT
                workflow_state.last_activity = datetime.now()
                next_phase = WorkflowPhase.PROCUREMENT.value
            else:
                next_phase = WorkflowPhase.DIAGNOSIS.value
        else:
            # Skip procurement, go to guidance
            if workflow_state.can_transition_to(WorkflowPhase.GUIDANCE):
                workflow_state.current_phase = WorkflowPhase.GUIDANCE
                workflow_state.last_activity = datetime.now()
                next_phase = WorkflowPhase.GUIDANCE.value
            else:
                next_phase = WorkflowPhase.DIAGNOSIS.value
        
        return FieldResponse(
            session_id=workflow_state.session_id,
            success=True,
            message="Diagnosis completed successfully",
            data=diagnosis_result,
            next_phase=next_phase
        )
    def _handle_low_confidence_recovery(
        self,
        workflow_state: WorkflowState,
        diagnosis_result: Dict[str, Any],
        request: FieldRequest
    ) -> FieldResponse:
        """
        Handle low confidence diagnosis recovery.

        Recovery strategies:
        - Confidence < 0.70: Request additional photos from multiple angles
        - Confidence 0.70-0.85: Escalate to human expert review
        - Track photo attempts to prevent infinite loops

        Args:
            workflow_state: Current workflow state
            diagnosis_result: Diagnosis result with low confidence
            request: Original field request

        Returns:
            Response with recovery instructions
        """
        confidence = diagnosis_result.get("confidence", 0.0)

        # Track photo request attempts
        if not hasattr(workflow_state, 'photo_request_count'):
            workflow_state.photo_request_count = 0

        # Confidence < 0.70: Request additional photos
        if confidence < 0.70:
            workflow_state.photo_request_count += 1

            # Prevent infinite loops - max 3 photo requests
            if workflow_state.photo_request_count >= 3:
                logger.warning(
                    f"Max photo requests reached ({workflow_state.photo_request_count}). "
                    "Escalating to human expert."
                )

                # Create escalation
                escalation = self.handle_escalation(
                    session_id=workflow_state.session_id,
                    escalation_type=EscalationType.LOW_CONFIDENCE,
                    severity="high",
                    description=(
                        f"Persistent low confidence after {workflow_state.photo_request_count} "
                        "photo attempts. Human expert review required."
                    ),
                    context={
                        "confidence": confidence,
                        "photo_attempts": workflow_state.photo_request_count,
                        "diagnosis": diagnosis_result
                    }
                )

                return FieldResponse(
                    session_id=workflow_state.session_id,
                    success=False,
                    message=(
                        "Unable to achieve confident diagnosis after multiple attempts. "
                        "Escalated to human expert for review."
                    ),
                    data={
                        "escalation_id": escalation.escalation_id,
                        "escalation_type": "low_confidence",
                        "requires_expert_review": True,
                        "diagnosis": diagnosis_result
                    },
                    next_phase=WorkflowPhase.DIAGNOSIS.value
                )

            # Request additional photos
            logger.info(
                f"Low confidence ({confidence:.2f}). Requesting additional photos "
                f"(attempt {workflow_state.photo_request_count}/3)"
            )

            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message=(
                    f"Diagnosis confidence ({confidence:.2f}) is low. "
                    "Please provide additional photos from multiple angles for better accuracy."
                ),
                data={
                    "requires_additional_photos": True,
                    "photo_request_count": workflow_state.photo_request_count,
                    "suggested_angles": [
                        "Front view with clear component labels",
                        "Close-up of affected area",
                        "Side view showing connections",
                        "Overall context view"
                    ],
                    "current_diagnosis": diagnosis_result
                },
                next_phase=WorkflowPhase.DIAGNOSIS.value
            )

        # Confidence 0.70-0.85: Escalate to expert review
        elif confidence < 0.85:
            logger.info(
                f"Medium confidence ({confidence:.2f}). Escalating to human expert review."
            )

            # Create escalation
            escalation = self.handle_escalation(
                session_id=workflow_state.session_id,
                escalation_type=EscalationType.LOW_CONFIDENCE,
                severity="medium",
                description=(
                    f"Diagnosis confidence ({confidence:.2f}) below expert review threshold (0.85). "
                    "Human expert review required before proceeding."
                ),
                context={
                    "confidence": confidence,
                    "diagnosis": diagnosis_result
                }
            )

            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message=(
                    f"Diagnosis confidence ({confidence:.2f}) requires expert review. "
                    "Workflow paused pending human expert confirmation."
                ),
                data={
                    "escalation_id": escalation.escalation_id,
                    "escalation_type": "expert_review",
                    "requires_expert_review": True,
                    "diagnosis": diagnosis_result,
                    "expert_review_instructions": (
                        "Please review the diagnosis and either: "
                        "1) Confirm and proceed, "
                        "2) Request additional information, or "
                        "3) Provide corrected diagnosis"
                    )
                },
                next_phase=WorkflowPhase.DIAGNOSIS.value
            )

        # Confidence >= 0.85: Should not reach here, but handle gracefully
        else:
            logger.warning(
                f"_handle_low_confidence_recovery called with high confidence ({confidence:.2f})"
            )
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=True,
                message="Diagnosis confidence is acceptable",
                data=diagnosis_result,
                next_phase=WorkflowPhase.PROCUREMENT.value if diagnosis_result.get("requires_parts") else WorkflowPhase.GUIDANCE.value
            )

    
    def _handle_procurement(
        self,
        workflow_state: WorkflowState,
        request: FieldRequest
    ) -> FieldResponse:
        """
        Handle procurement phase - procure parts with Action Agent.
        
        Args:
            workflow_state: Current workflow state
            request: Field request
            
        Returns:
            Response with procurement results
        """
        logger.info(f"Handling PROCUREMENT phase for session {workflow_state.session_id}")
        
        # Route to action agent
        procurement_result = self.route_to_action_agent(request)
        
        if not procurement_result.get("success"):
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message="Procurement failed",
                data=procurement_result,
                next_phase=WorkflowPhase.PROCUREMENT.value
            )
        
        # Validate with judge if enabled
        if self.enable_validation:
            validation_result = self._validate_procurement(procurement_result)
            
            if not validation_result.get("approved"):
                return FieldResponse(
                    session_id=workflow_state.session_id,
                    success=False,
                    message="Procurement validation failed",
                    data={
                        "procurement": procurement_result,
                        "validation": validation_result
                    },
                    next_phase=WorkflowPhase.PROCUREMENT.value
                )
        
        # Store procurement in workflow state
        workflow_state.procurement_state = procurement_result
        
        # Transition to guidance
        if workflow_state.can_transition_to(WorkflowPhase.GUIDANCE):
            workflow_state.current_phase = WorkflowPhase.GUIDANCE
            workflow_state.last_activity = datetime.now()
            next_phase = WorkflowPhase.GUIDANCE.value
        else:
            next_phase = WorkflowPhase.PROCUREMENT.value
        
        return FieldResponse(
            session_id=workflow_state.session_id,
            success=True,
            message="Procurement completed successfully",
            data=procurement_result,
            next_phase=next_phase
        )
    
    def _handle_guidance(
        self,
        workflow_state: WorkflowState,
        request: FieldRequest
    ) -> FieldResponse:
        """
        Handle guidance phase - provide repair guidance with Guidance Agent.
        
        Args:
            workflow_state: Current workflow state
            request: Field request
            
        Returns:
            Response with guidance
        """
        logger.info(f"Handling GUIDANCE phase for session {workflow_state.session_id}")
        
        # Route to guidance agent
        guidance_result = self.route_to_guidance_agent(request)
        
        if not guidance_result.get("success"):
            return FieldResponse(
                session_id=workflow_state.session_id,
                success=False,
                message="Guidance generation failed",
                data=guidance_result,
                next_phase=WorkflowPhase.GUIDANCE.value
            )
        
        # Store guidance in workflow state
        workflow_state.guidance_state = guidance_result
        
        # Check if repair is complete
        if guidance_result.get("repair_complete"):
            # Transition to completion
            if workflow_state.can_transition_to(WorkflowPhase.COMPLETION):
                workflow_state.current_phase = WorkflowPhase.COMPLETION
                workflow_state.last_activity = datetime.now()
                next_phase = WorkflowPhase.COMPLETION.value
            else:
                next_phase = WorkflowPhase.GUIDANCE.value
        else:
            next_phase = WorkflowPhase.GUIDANCE.value
        
        return FieldResponse(
            session_id=workflow_state.session_id,
            success=True,
            message="Guidance provided",
            data=guidance_result,
            next_phase=next_phase
        )
    
    def _handle_completion(
        self,
        workflow_state: WorkflowState,
        request: FieldRequest
    ) -> FieldResponse:
        """
        Handle completion phase - finalize and create maintenance record.
        
        Args:
            workflow_state: Current workflow state
            request: Field request
            
        Returns:
            Response with completion details
        """
        logger.info(f"Handling COMPLETION phase for session {workflow_state.session_id}")
        
        # Create maintenance record
        maintenance_record = self._create_maintenance_record(workflow_state, request)
        
        # Mark workflow as complete
        workflow_state.end_time = datetime.now()
        workflow_state.last_activity = datetime.now()
        
        return FieldResponse(
            session_id=workflow_state.session_id,
            success=True,
            message="Workflow completed successfully",
            data={
                "maintenance_record": maintenance_record,
                "workflow_summary": self._generate_workflow_summary(workflow_state)
            },
            next_phase=WorkflowPhase.COMPLETION.value
        )
    
    def route_to_diagnosis_agent(self, request: FieldRequest) -> Dict[str, Any]:
        """Route request to diagnosis agent, adapting FieldRequest → DiagnosisInput."""
        logger.info("Routing to Diagnosis Agent")
        from src.models.agents import DiagnosisInput
        try:
            diagnosis_input = DiagnosisInput(
                image_data=request.image_data,
                equipment_type=None,
                site_context=None,
                telemetry_data=None,
                technician_notes=None,
            )
            result = self.diagnosis_agent.diagnose_issue(diagnosis_input)
            # Convert DiagnosisResult dataclass to dict for downstream use
            if hasattr(result, '__dict__'):
                return {"success": True, **vars(result)}
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Diagnosis agent failed: {e}")
            return {"success": False, "error": str(e)}

    def route_to_action_agent(self, request: FieldRequest) -> Dict[str, Any]:
        """Route request to action agent for procurement."""
        logger.info("Routing to Action Agent")
        try:
            prompt = (
                f"Procure parts for site {request.site_id}. "
                f"Technician: {request.technician_id}. "
                f"Request type: {request.request_type.value if request.request_type else 'diagnosis'}."
            )
            result = self.action_agent._call_nova_act(prompt)
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Action agent failed: {e}")
            return {"success": False, "error": str(e)}

    def route_to_guidance_agent(self, request: FieldRequest) -> Dict[str, Any]:
        """Route request to guidance agent for repair guidance."""
        logger.info("Routing to Guidance Agent")
        try:
            # Use text-based guidance generation
            prompt = (
                f"Generate repair guidance for site {request.site_id}. "
                f"Technician: {request.technician_id}."
            )
            text_response = self.guidance_agent._call_nova_sonic_text(prompt)
            return {"success": True, "guidance": text_response, "repair_complete": False}
        except Exception as e:
            logger.error(f"Guidance agent failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_diagnosis(self, diagnosis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate diagnosis with cloud judge and safety checker.
        
        Performs:
        1. Safety hazard checking (mandatory for all diagnoses)
        2. Cloud judge validation (SOP compliance, quality)
        
        Args:
            diagnosis_result: Diagnosis result to validate
            
        Returns:
            Validation result with safety check included
        """
        logger.info("Validating diagnosis with Cloud Judge and Safety Checker")
        
        # Step 1: Perform mandatory safety check (Task 12.4)
        from src.safety import SafetyChecker
        
        safety_checker = SafetyChecker()
        safety_check_result = safety_checker.check_safety(
            diagnosis_result=diagnosis_result,
            site_context=diagnosis_result.get("site_context", {}),
            repair_actions=diagnosis_result.get("recommended_actions", [])
        )
        
        # Convert safety check result to dict
        safety_check_dict = safety_check_result.to_dict()
        
        # Check for safety violations
        has_safety_violations = (
            not safety_check_result.approved_to_proceed or
            safety_check_result.escalation_required or
            len(safety_check_result.hazards_identified) > 0
        )
        
        # Step 2: Perform cloud judge validation
        agent_output = AgentOutput(
            agent_type=AgentType.DIAGNOSIS,
            output_data=diagnosis_result,
            confidence=diagnosis_result.get("confidence", 0.0),
            timestamp=datetime.now(),
            session_id=diagnosis_result.get("session_id", "unknown")
        )
        
        criteria = ValidationCriteria(
            check_safety=True,
            check_sop_compliance=True,
            check_budget=False,
            check_quality=True
        )
        
        judgment = self.cloud_judge.validate_agent_output(agent_output, criteria)
        
        # Combine results
        return {
            "approved": judgment.approved and safety_check_result.approved_to_proceed,
            "confidence": judgment.confidence,
            "reasoning": judgment.reasoning,
            "violations": judgment.violations,
            "safety_violations": has_safety_violations,
            "safety_check_result": safety_check_dict,
            "safety_status": safety_check_result.status.value,
            "hazards_identified": [h.to_dict() for h in safety_check_result.hazards_identified]
        }
    
    def _validate_procurement(self, procurement_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate procurement with cloud judge."""
        logger.info("Validating procurement with Cloud Judge")
        
        agent_output = AgentOutput(
            agent_type=AgentType.ACTION,
            output_data=procurement_result,
            confidence=1.0,
            timestamp=datetime.now(),
            session_id=procurement_result.get("session_id", "unknown")
        )
        
        criteria = ValidationCriteria(
            check_safety=False,
            check_sop_compliance=True,
            check_budget=True,
            check_quality=False
        )
        
        judgment = self.cloud_judge.validate_agent_output(agent_output, criteria)
        
        return {
            "approved": judgment.approved,
            "confidence": judgment.confidence,
            "reasoning": judgment.reasoning,
            "violations": judgment.violations
        }
    
    def _create_maintenance_record(
        self,
        workflow_state: WorkflowState,
        request: FieldRequest
    ) -> Dict[str, Any]:
        """Create maintenance record for completed workflow."""
        logger.info("Creating maintenance record")
        
        # Extract parts used from procurement state
        parts_used = []
        if workflow_state.procurement_state:
            parts_used = workflow_state.procurement_state.get("parts", [])
        
        # Calculate duration
        duration_minutes = 0
        if workflow_state.start_time and workflow_state.end_time:
            duration = workflow_state.end_time - workflow_state.start_time
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Create record
        record = self.maintenance_client.create_record(
            site_id=workflow_state.site_id or "unknown",
            component_id=getattr(request, "component_id", "unknown"),
            technician_id=workflow_state.technician_id or "unknown",
            activity_type="repair",
            description=f"Field repair completed via autonomous system",
            parts_used=parts_used,
            duration_minutes=duration_minutes,
            outcome="success"
        )
        
        return record
    
    def _generate_workflow_summary(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """Generate summary of workflow execution."""
        return {
            "session_id": workflow_state.session_id,
            "start_time": workflow_state.start_time.isoformat() if workflow_state.start_time else None,
            "end_time": workflow_state.end_time.isoformat() if workflow_state.end_time else None,
            "duration_minutes": int((workflow_state.end_time - workflow_state.start_time).total_seconds() / 60) if workflow_state.start_time and workflow_state.end_time else 0,
            "phases_completed": [
                WorkflowPhase.INTAKE.value,
                WorkflowPhase.DIAGNOSIS.value,
                WorkflowPhase.PROCUREMENT.value if workflow_state.procurement_state else None,
                WorkflowPhase.GUIDANCE.value,
                WorkflowPhase.COMPLETION.value
            ],
            "technician_id": workflow_state.technician_id,
            "site_id": workflow_state.site_id
        }
    
    def get_workflow_state(self, session_id: str) -> Optional[WorkflowState]:
        """Get workflow state for session."""
        return self.sessions.get(session_id)
    
    def update_workflow_state(
        self,
        session_id: str,
        workflow_state: WorkflowState
    ):
        """Update workflow state for session."""
        self.sessions[session_id] = workflow_state
        workflow_state.last_activity = datetime.now()
    
    def handle_escalation(
        self,
        session_id: str,
        escalation_type: EscalationType,
        severity: Any,
        description: str,
        context: Dict[str, Any]
    ) -> Escalation:
        """
        Handle workflow escalation.
        
        Args:
            session_id: Session ID
            escalation_type: Type of escalation
            severity: Severity level
            description: Description
            context: Additional context
        
        Returns:
            Created escalation
        """
        # Add session ID to context
        context["session_id"] = session_id
        
        # Log escalation thought
        self.thought_logger.log_escalation(
            session_id=session_id,
            escalation_type=escalation_type.value if hasattr(escalation_type, 'value') else str(escalation_type),
            severity=str(severity),
            description=description
        )
        
        # Create escalation
        escalation = self.escalation_manager.create_escalation(
            escalation_type=escalation_type,
            severity=severity,
            description=description,
            context=context
        )
        
        # Check if workflow should pause
        if self.escalation_manager.should_pause_workflow(escalation):
            logger.warning(f"Pausing workflow {session_id} due to escalation")
            
            # Add escalation to workflow state
            if session_id in self.sessions:
                workflow_state = self.sessions[session_id]
                workflow_state.escalations.append(escalation.to_dict())
                
                # Save checkpoint
                self.persistence.save_checkpoint(workflow_state)
        
        return escalation
    
    def get_active_escalations(
        self,
        session_id: Optional[str] = None
    ) -> List[Escalation]:
        """Get active escalations for session or all."""
        return self.escalation_manager.get_active_escalations(session_id)
    
    def resolve_escalation(
        self,
        escalation_id: str,
        resolution_notes: str
    ) -> bool:
        """Resolve an escalation."""
        return self.escalation_manager.resolve_escalation(
            escalation_id,
            resolution_notes
        )

    def _handle_safety_violation(
        self,
        workflow_state: WorkflowState,
        safety_check_result: Dict[str, Any],
        diagnosis_result: Dict[str, Any]
    ) -> FieldResponse:
        """
        Handle safety violation detection (Task 12.4).
        
        Safety violation handling:
        - Immediate workflow halt on safety violation
        - Critical alert notifications to safety officer and supervisor
        - Safety clearance requirement before continuation
        - Alternative procedure generation with stricter safety constraints
        
        Args:
            workflow_state: Current workflow state
            safety_check_result: Safety check result from SafetyChecker
            diagnosis_result: Original diagnosis result
            
        Returns:
            Response with safety violation details and required actions
        """
        logger.critical(
            f"SAFETY VIOLATION DETECTED in session {workflow_state.session_id}. "
            "Halting workflow immediately."
        )
        
        # Extract safety information
        hazards = safety_check_result.get("hazards_identified", [])
        violations = safety_check_result.get("violations", [])
        status = safety_check_result.get("status", "rejected")
        
        # Identify critical hazards
        critical_hazards = [
            h for h in hazards 
            if h.get("severity") == "critical"
        ]
        
        # Determine escalation severity
        if critical_hazards:
            escalation_severity = "critical"
            escalation_description = (
                f"CRITICAL SAFETY VIOLATION: {len(critical_hazards)} critical hazard(s) identified. "
                "Immediate safety officer intervention required."
            )
        else:
            escalation_severity = "high"
            escalation_description = (
                f"Safety violation detected: {len(hazards)} hazard(s) identified. "
                "Safety officer approval required before proceeding."
            )
        
        # Create safety escalation
        escalation = self.handle_escalation(
            session_id=workflow_state.session_id,
            escalation_type=EscalationType.SAFETY_VIOLATION,
            severity=escalation_severity,
            description=escalation_description,
            context={
                "safety_check": safety_check_result,
                "diagnosis": diagnosis_result,
                "hazards": hazards,
                "violations": violations,
                "critical_hazard_count": len(critical_hazards)
            }
        )
        
        # Generate required actions
        required_actions = []
        
        # Lockout/tagout requirements
        lockout_required = any(
            h.get("lockout_tagout_required", False) 
            for h in hazards
        )
        if lockout_required:
            required_actions.append({
                "action": "lockout_tagout",
                "description": "Perform lockout/tagout procedure before any work",
                "mandatory": True
            })
        
        # Permit requirements
        permit_required = any(
            h.get("permit_required", False) 
            for h in hazards
        )
        if permit_required:
            required_actions.append({
                "action": "obtain_permit",
                "description": "Obtain work permit from safety officer",
                "mandatory": True
            })
        
        # PPE requirements
        all_required_ppe = set()
        for hazard in hazards:
            all_required_ppe.update(hazard.get("required_ppe", []))
        
        if all_required_ppe:
            required_actions.append({
                "action": "verify_ppe",
                "description": f"Verify and don required PPE: {', '.join(all_required_ppe)}",
                "mandatory": True,
                "ppe_list": list(all_required_ppe)
            })
        
        # Safety officer clearance
        required_actions.append({
            "action": "safety_clearance",
            "description": "Obtain safety officer clearance before proceeding",
            "mandatory": True
        })
        
        # Generate alternative safer procedure if possible
        alternative_procedure = self._generate_alternative_safe_procedure(
            diagnosis_result,
            hazards
        )
        
        # Send critical notifications
        self._send_safety_notifications(
            workflow_state,
            escalation,
            hazards,
            critical_hazards
        )
        
        return FieldResponse(
            session_id=workflow_state.session_id,
            success=False,
            message=(
                "SAFETY VIOLATION: Workflow halted due to safety concerns. "
                "Safety officer clearance required before proceeding."
            ),
            data={
                "escalation_id": escalation.escalation_id,
                "escalation_type": "safety_violation",
                "safety_status": status,
                "hazards_identified": hazards,
                "critical_hazards": critical_hazards,
                "violations": violations,
                "required_actions": required_actions,
                "alternative_procedure": alternative_procedure,
                "workflow_halted": True,
                "requires_safety_clearance": True,
                "safety_officer_notified": True,
                "supervisor_notified": True
            },
            next_phase=WorkflowPhase.DIAGNOSIS.value
        )
    
    def _generate_alternative_safe_procedure(
        self,
        diagnosis_result: Dict[str, Any],
        hazards: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate alternative procedure with stricter safety constraints.
        
        Args:
            diagnosis_result: Original diagnosis
            hazards: Identified hazards
            
        Returns:
            Alternative procedure or None if not possible
        """
        # Check if alternative is possible
        issue_type = diagnosis_result.get("issue_type", "")
        
        # For electrical issues, suggest de-energization
        if any(h.get("hazard_type") == "electrical" for h in hazards):
            return {
                "procedure_type": "de_energized_repair",
                "description": "Perform repair with equipment fully de-energized",
                "steps": [
                    "Obtain lockout/tagout authorization",
                    "De-energize equipment at main breaker",
                    "Verify zero energy state with multimeter",
                    "Apply lockout/tagout devices",
                    "Perform repair work",
                    "Remove lockout/tagout after verification",
                    "Re-energize equipment under supervision"
                ],
                "additional_safety": [
                    "Requires qualified electrician",
                    "Safety officer must be present",
                    "Use insulated tools only"
                ],
                "estimated_additional_time_minutes": 45
            }
        
        # For mechanical hazards, suggest equipment shutdown
        if any(h.get("hazard_type") == "mechanical" for h in hazards):
            return {
                "procedure_type": "equipment_shutdown",
                "description": "Perform repair with equipment fully shut down",
                "steps": [
                    "Shut down equipment completely",
                    "Allow cooldown period if needed",
                    "Verify no moving parts",
                    "Perform repair work",
                    "Restart equipment under supervision"
                ],
                "additional_safety": [
                    "Verify no automatic restart capability",
                    "Post warning signs during work"
                ],
                "estimated_additional_time_minutes": 30
            }
        
        # No safe alternative available
        return None
    
    def _send_safety_notifications(
        self,
        workflow_state: WorkflowState,
        escalation: Any,
        hazards: List[Dict[str, Any]],
        critical_hazards: List[Dict[str, Any]]
    ):
        """
        Send critical safety notifications to safety officer and supervisor.
        
        Args:
            workflow_state: Current workflow state
            escalation: Created escalation
            hazards: All identified hazards
            critical_hazards: Critical hazards only
        """
        # In production, this would send actual emails/SMS
        # For now, log the notifications
        
        notification_message = f"""
SAFETY ALERT - Session {workflow_state.session_id}

Escalation ID: {escalation.escalation_id}
Site ID: {workflow_state.site_id}
Technician ID: {workflow_state.technician_id}

Hazards Identified: {len(hazards)}
Critical Hazards: {len(critical_hazards)}

Immediate Action Required:
- Review safety assessment
- Provide clearance or alternative procedure
- Contact technician if needed

Workflow has been HALTED pending safety clearance.
"""
        
        logger.critical(f"SAFETY NOTIFICATION SENT:\n{notification_message}")
        
        # Log to escalation manager
        if hasattr(self.escalation_manager, 'log_notification'):
            self.escalation_manager.log_notification(
                escalation_id=escalation.escalation_id,
                notification_type="safety_alert",
                recipients=["safety_officer", "supervisor"],
                message=notification_message
            )

    def _handle_inventory_unavailability(
        self,
        workflow_state: WorkflowState,
        error: Exception,
        required_parts: List[str]
    ) -> Dict[str, Any]:
        """
        Handle inventory system unavailability (Task 12.2).
        
        Recovery strategies:
        - Use cached inventory data (24-hour window)
        - Mark results as "pending verification"
        - Schedule background retry job
        - Validate cache when connectivity restored
        
        Args:
            workflow_state: Current workflow state
            error: The exception that occurred
            required_parts: List of required part numbers
            
        Returns:
            Procurement result with cached data or error
        """
        logger.warning(
            f"Inventory system unavailable for session {workflow_state.session_id}: {error}"
        )
        
        # Try to use cached data
        cached_results = []
        missing_parts = []
        
        for part_number in required_parts:
            cached_part = self._get_cached_inventory_data(part_number)
            
            if cached_part and self._is_cache_valid(cached_part, max_age_hours=24):
                cached_results.append({
                    **cached_part,
                    "from_cache": True,
                    "pending_verification": True,
                    "cache_age_hours": self._get_cache_age_hours(cached_part)
                })
                logger.info(f"Using cached data for part {part_number}")
            else:
                missing_parts.append(part_number)
                logger.warning(f"No valid cache for part {part_number}")
        
        # If we have some cached results, proceed with warning
        if cached_results:
            # Schedule background retry
            retry_job_id = self._schedule_inventory_retry(
                workflow_state.session_id,
                required_parts
            )
            
            return {
                "success": True,
                "parts": cached_results,
                "warning": "Inventory system unavailable. Using cached data (pending verification).",
                "from_cache": True,
                "pending_verification": True,
                "missing_parts": missing_parts,
                "retry_job_id": retry_job_id,
                "cache_fallback_used": True
            }
        
        # No cached data available - cannot proceed
        return {
            "success": False,
            "error": "Inventory system unavailable and no cached data available",
            "error_type": "inventory_unavailable",
            "required_parts": required_parts,
            "retry_recommended": True,
            "estimated_retry_time_minutes": 5
        }
    
    def _get_cached_inventory_data(self, part_number: str) -> Optional[Dict[str, Any]]:
        """
        Get cached inventory data for a part.
        
        Args:
            part_number: Part number to look up
            
        Returns:
            Cached part data or None
        """
        # In production, this would query a local cache (Redis, SQLite, etc.)
        # For now, try to get from inventory client's cache
        try:
            if hasattr(self.inventory_client, 'cache'):
                return self.inventory_client.cache.get(part_number)
        except Exception as e:
            logger.error(f"Error accessing inventory cache: {e}")
        
        return None
    
    def _is_cache_valid(self, cached_data: Dict[str, Any], max_age_hours: int = 24) -> bool:
        """
        Check if cached data is still valid.
        
        Args:
            cached_data: Cached data dictionary
            max_age_hours: Maximum age in hours
            
        Returns:
            True if cache is valid
        """
        if not cached_data or 'cached_at' not in cached_data:
            return False
        
        try:
            cached_at = cached_data['cached_at']
            if isinstance(cached_at, str):
                cached_at = datetime.fromisoformat(cached_at)
            
            age_hours = (datetime.now() - cached_at).total_seconds() / 3600
            return age_hours <= max_age_hours
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def _get_cache_age_hours(self, cached_data: Dict[str, Any]) -> float:
        """Get age of cached data in hours."""
        try:
            cached_at = cached_data.get('cached_at')
            if isinstance(cached_at, str):
                cached_at = datetime.fromisoformat(cached_at)
            
            return (datetime.now() - cached_at).total_seconds() / 3600
        except Exception:
            return 0.0
    
    def _schedule_inventory_retry(
        self,
        session_id: str,
        required_parts: List[str]
    ) -> str:
        """
        Schedule background retry job for inventory search.
        
        Args:
            session_id: Session ID
            required_parts: Parts to retry
            
        Returns:
            Retry job ID
        """
        import uuid
        retry_job_id = f"retry_{uuid.uuid4().hex[:8]}"
        
        logger.info(
            f"Scheduled inventory retry job {retry_job_id} for session {session_id}"
        )
        
        # In production, this would schedule an actual background job
        # For now, just log it
        return retry_job_id

    def _handle_judge_offline(
        self,
        workflow_state: WorkflowState,
        error: Exception,
        agent_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle judge offline scenario (Task 12.3).
        
        Recovery strategies:
        - Detect judge availability (5-second timeout)
        - Pause workflow and persist state
        - Enable automatic resumption on judge restart
        - Re-validate last output after recovery
        
        Args:
            workflow_state: Current workflow state
            error: The exception that occurred
            agent_output: Agent output that needs validation
            
        Returns:
            Recovery status and instructions
        """
        logger.critical(
            f"Judge offline for session {workflow_state.session_id}: {error}"
        )
        
        # Save current state for recovery
        self.persistence.save_checkpoint(workflow_state)
        
        # Mark workflow as paused
        workflow_state.metadata['paused'] = True
        workflow_state.metadata['pause_reason'] = 'judge_offline'
        workflow_state.metadata['paused_at'] = datetime.now().isoformat()
        workflow_state.metadata['pending_validation'] = agent_output
        
        # Save updated state
        self.persistence.save_checkpoint(workflow_state)
        
        logger.info(
            f"Workflow {workflow_state.session_id} paused. "
            "Will resume automatically when judge is back online."
        )
        
        return {
            "success": False,
            "error": "Judge validation service is offline",
            "error_type": "judge_offline",
            "workflow_paused": True,
            "checkpoint_saved": True,
            "auto_resume_enabled": True,
            "instructions": (
                "Workflow has been paused and state saved. "
                "The system will automatically resume when the judge service is restored. "
                "No manual intervention required."
            ),
            "estimated_recovery_time_minutes": 5
        }
    
    def _check_judge_availability(self, timeout_seconds: int = 5) -> bool:
        """
        Check if judge is available.
        
        Args:
            timeout_seconds: Timeout for availability check
            
        Returns:
            True if judge is available
        """
        try:
            # Try a simple health check
            # In production, this would be an actual health endpoint
            if hasattr(self.cloud_judge, 'health_check'):
                return self.cloud_judge.health_check(timeout=timeout_seconds)
            
            # Fallback: assume available if no health check method
            return True
            
        except Exception as e:
            logger.warning(f"Judge availability check failed: {e}")
            return False
    
    def _attempt_workflow_resumption(
        self,
        workflow_state: WorkflowState
    ) -> bool:
        """
        Attempt to resume a paused workflow after judge recovery.
        
        Args:
            workflow_state: Paused workflow state
            
        Returns:
            True if resumption successful
        """
        if not workflow_state.metadata.get('paused'):
            return False
        
        # Check if judge is back online
        if not self._check_judge_availability():
            logger.info(f"Judge still offline, cannot resume {workflow_state.session_id}")
            return False
        
        logger.info(f"Judge is back online. Resuming workflow {workflow_state.session_id}")
        
        # Get pending validation
        pending_validation = workflow_state.metadata.get('pending_validation')
        
        if pending_validation:
            # Re-validate the pending output
            try:
                validation_result = self._validate_diagnosis(pending_validation)
                
                # Clear pause state
                workflow_state.metadata['paused'] = False
                workflow_state.metadata['resumed_at'] = datetime.now().isoformat()
                workflow_state.metadata.pop('pause_reason', None)
                workflow_state.metadata.pop('pending_validation', None)
                
                # Save resumed state
                self.persistence.save_checkpoint(workflow_state)
                
                logger.info(f"Workflow {workflow_state.session_id} successfully resumed")
                return True
                
            except Exception as e:
                logger.error(f"Failed to resume workflow: {e}")
                return False
        
        return False

    def _handle_budget_exceeded(
        self,
        workflow_state: WorkflowState,
        procurement_result: Dict[str, Any],
        budget_limit: float,
        total_cost: float
    ) -> FieldResponse:
        """
        Handle budget exceeded scenario (Task 12.5).
        
        Recovery strategies:
        - Queue approval workflow for over-budget requests
        - Identify temporary workaround options
        - Estimate approval timeline
        - Notify on approval granted
        
        Args:
            workflow_state: Current workflow state
            procurement_result: Procurement result with costs
            budget_limit: Budget limit that was exceeded
            total_cost: Total cost of procurement
            
        Returns:
            Response with approval workflow details
        """
        logger.warning(
            f"Budget exceeded for session {workflow_state.session_id}: "
            f"${total_cost:.2f} > ${budget_limit:.2f}"
        )
        
        # Calculate how much over budget
        overage = total_cost - budget_limit
        overage_percentage = (overage / budget_limit) * 100
        
        # Determine approval authority based on overage
        approval_authority = self._determine_approval_authority(
            budget_limit,
            total_cost,
            overage_percentage
        )
        
        # Look for temporary workarounds
        workarounds = self._identify_temporary_workarounds(
            procurement_result,
            budget_limit
        )
        
        # Estimate approval timeline
        approval_timeline = self._estimate_approval_timeline(approval_authority)
        
        # Create approval escalation
        escalation = self.handle_escalation(
            session_id=workflow_state.session_id,
            escalation_type=EscalationType.BUDGET_EXCEEDED,
            severity="high" if overage_percentage > 50 else "medium",
            description=(
                f"Procurement cost (${total_cost:.2f}) exceeds budget limit (${budget_limit:.2f}) "
                f"by ${overage:.2f} ({overage_percentage:.1f}%). "
                f"Requires {approval_authority} approval."
            ),
            context={
                "budget_limit": budget_limit,
                "total_cost": total_cost,
                "overage": overage,
                "overage_percentage": overage_percentage,
                "procurement_details": procurement_result,
                "approval_authority": approval_authority
            }
        )
        
        return FieldResponse(
            session_id=workflow_state.session_id,
            success=False,
            message=(
                f"Procurement cost (${total_cost:.2f}) exceeds budget limit (${budget_limit:.2f}). "
                f"Approval request submitted to {approval_authority}."
            ),
            data={
                "escalation_id": escalation.escalation_id,
                "escalation_type": "budget_exceeded",
                "budget_limit": budget_limit,
                "total_cost": total_cost,
                "overage": overage,
                "overage_percentage": overage_percentage,
                "approval_authority": approval_authority,
                "approval_timeline": approval_timeline,
                "temporary_workarounds": workarounds,
                "workflow_status": "pending_approval",
                "instructions": (
                    f"Your procurement request has been queued for {approval_authority} approval. "
                    f"Estimated approval time: {approval_timeline['estimated_hours']} hours. "
                    f"You will be notified when approval is granted."
                )
            },
            next_phase=WorkflowPhase.PROCUREMENT.value
        )
    
    def _determine_approval_authority(
        self,
        budget_limit: float,
        total_cost: float,
        overage_percentage: float
    ) -> str:
        """
        Determine who needs to approve based on cost and overage.
        
        Args:
            budget_limit: Original budget limit
            total_cost: Total cost
            overage_percentage: Percentage over budget
            
        Returns:
            Approval authority level
        """
        if total_cost > 10000 or overage_percentage > 100:
            return "Director"
        elif total_cost > 5000 or overage_percentage > 50:
            return "Manager"
        else:
            return "Supervisor"
    
    def _identify_temporary_workarounds(
        self,
        procurement_result: Dict[str, Any],
        budget_limit: float
    ) -> List[Dict[str, Any]]:
        """
        Identify temporary workarounds that fit within budget.
        
        Args:
            procurement_result: Original procurement result
            budget_limit: Budget limit
            
        Returns:
            List of workaround options
        """
        workarounds = []
        
        # Workaround 1: Defer non-critical parts
        workarounds.append({
            "type": "defer_non_critical",
            "description": "Defer non-critical parts to next maintenance window",
            "estimated_cost_reduction": "20-40%",
            "impact": "Partial functionality until full repair"
        })
        
        # Workaround 2: Use refurbished parts
        workarounds.append({
            "type": "refurbished_parts",
            "description": "Use refurbished or reconditioned parts instead of new",
            "estimated_cost_reduction": "30-50%",
            "impact": "Shorter warranty period"
        })
        
        # Workaround 3: Temporary patch
        workarounds.append({
            "type": "temporary_patch",
            "description": "Apply temporary fix until budget available",
            "estimated_cost_reduction": "60-80%",
            "impact": "Requires follow-up repair within 30 days"
        })
        
        return workarounds
    
    def _estimate_approval_timeline(self, approval_authority: str) -> Dict[str, Any]:
        """
        Estimate approval timeline based on authority level.
        
        Args:
            approval_authority: Who needs to approve
            
        Returns:
            Timeline estimate
        """
        timelines = {
            "Supervisor": {"estimated_hours": 2, "business_days": 0.25},
            "Manager": {"estimated_hours": 8, "business_days": 1},
            "Director": {"estimated_hours": 24, "business_days": 3}
        }
        
        return timelines.get(approval_authority, {"estimated_hours": 24, "business_days": 3})

    def _handle_voice_recognition_failure(
        self,
        workflow_state: WorkflowState,
        audio_input: Any,
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle voice recognition failure (Task 12.6).
        
        Recovery strategies:
        - Request clarification on parse failure
        - Offer text input fallback
        - Log failure for model improvement
        
        Args:
            workflow_state: Current workflow state
            audio_input: Audio input that failed to parse
            error: The exception that occurred
            
        Returns:
            Recovery instructions
        """
        logger.warning(
            f"Voice recognition failed for session {workflow_state.session_id}: {error}"
        )
        
        # Track failure count
        if not hasattr(workflow_state, 'voice_failure_count'):
            workflow_state.voice_failure_count = 0
        workflow_state.voice_failure_count += 1
        
        # Log for model improvement
        self._log_voice_recognition_failure(
            workflow_state.session_id,
            audio_input,
            error
        )
        
        # After 3 failures, suggest text input
        if workflow_state.voice_failure_count >= 3:
            return {
                "success": False,
                "error": "Voice recognition repeatedly failed",
                "error_type": "voice_recognition_failure",
                "fallback_available": True,
                "fallback_type": "text_input",
                "message": (
                    "We're having trouble understanding your voice commands. "
                    "Would you like to switch to text input instead?"
                ),
                "options": [
                    {
                        "action": "retry_voice",
                        "description": "Try voice input again"
                    },
                    {
                        "action": "switch_to_text",
                        "description": "Switch to text input"
                    }
                ]
            }
        
        # First few failures: request clarification
        return {
            "success": False,
            "error": "Voice command not understood",
            "error_type": "voice_recognition_failure",
            "retry_available": True,
            "message": (
                "Sorry, I didn't catch that. Could you please repeat your command? "
                "Try speaking clearly and avoiding background noise."
            ),
            "suggestions": [
                "Speak clearly and at a moderate pace",
                "Reduce background noise if possible",
                "Move closer to the microphone",
                "Use simple, direct commands"
            ],
            "failure_count": workflow_state.voice_failure_count
        }
    
    def _log_voice_recognition_failure(
        self,
        session_id: str,
        audio_input: Any,
        error: Exception
    ):
        """
        Log voice recognition failure for model improvement.
        
        Args:
            session_id: Session ID
            audio_input: Failed audio input
            error: Error that occurred
        """
        logger.info(
            f"Logging voice recognition failure for session {session_id} "
            "for model improvement"
        )
        
        # In production, this would send to a training data pipeline
        # For now, just log it
        failure_log = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "audio_metadata": {
                "duration": getattr(audio_input, 'duration', None),
                "sample_rate": getattr(audio_input, 'sample_rate', None)
            }
        }
        
        logger.debug(f"Voice failure log: {failure_log}")

    def _handle_missing_manual(
        self,
        workflow_state: WorkflowState,
        equipment_type: str,
        diagnosis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle missing technical manual (Task 12.7).
        
        Recovery strategies:
        1. Fuzzy equipment type matching for similar equipment in Weaviate
        2. Web search for manufacturer documentation and repair guides
        3. Generic repair procedure fallback
        4. "Low reference coverage" flagging
        5. Notification to documentation team
        
        Args:
            workflow_state: Current workflow state
            equipment_type: Equipment type with missing manual
            diagnosis_result: Diagnosis result
            
        Returns:
            Guidance with fallback procedures
        """
        logger.warning(
            f"Missing technical manual for {equipment_type} in session {workflow_state.session_id}"
        )
        
        # Try fuzzy matching for similar equipment in Weaviate
        similar_equipment = self._find_similar_equipment_manuals(equipment_type)
        
        # Try web search for manufacturer documentation
        web_search_results = self._search_web_for_manual(
            equipment_type,
            diagnosis_result
        )
        
        # Generate generic repair procedure as final fallback
        generic_procedure = self._generate_generic_repair_procedure(
            equipment_type,
            diagnosis_result
        )
        
        # Notify documentation team
        self._notify_missing_manual(equipment_type, workflow_state.site_id)
        
        # Determine guidance quality based on what we found
        guidance_quality = "high" if web_search_results.get("found_manual") else \
                          "medium" if similar_equipment else "low"
        
        return {
            "success": True,
            "warning": f"No specific manual found in database for {equipment_type}",
            "reference_coverage": guidance_quality,
            "similar_equipment": similar_equipment,
            "web_search_results": web_search_results,
            "generic_procedure": generic_procedure,
            "guidance_quality": guidance_quality,
            "recommendations": self._generate_missing_manual_recommendations(
                similar_equipment,
                web_search_results,
                guidance_quality
            ),
            "documentation_team_notified": True
        }
    
    def _find_similar_equipment_manuals(
        self,
        equipment_type: str
    ) -> List[Dict[str, Any]]:
        """
        Find manuals for similar equipment using fuzzy matching.
        
        Args:
            equipment_type: Equipment type to match
            
        Returns:
            List of similar equipment with manuals
        """
        if not self.rag_system:
            return []
        
        # Extract equipment category (e.g., "switch" from "network_switch")
        category = equipment_type.split('_')[-1] if '_' in equipment_type else equipment_type
        
        similar = []
        
        # Common equipment families
        equipment_families = {
            "switch": ["network_switch", "ethernet_switch", "managed_switch"],
            "router": ["network_router", "edge_router", "core_router"],
            "server": ["rack_server", "blade_server", "tower_server"],
            "power": ["power_supply", "ups", "pdu"]
        }
        
        # Find family
        for family_key, family_types in equipment_families.items():
            if category.lower() in family_key or family_key in category.lower():
                for similar_type in family_types:
                    if similar_type != equipment_type:
                        similar.append({
                            "equipment_type": similar_type,
                            "similarity": "high" if similar_type in family_types else "medium",
                            "note": f"Similar {family_key} equipment"
                        })
        
        return similar[:3]  # Return top 3
    
    def _generate_generic_repair_procedure(
        self,
        equipment_type: str,
        diagnosis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate generic repair procedure when manual is missing.
        
        Args:
            equipment_type: Equipment type
            diagnosis_result: Diagnosis result
            
        Returns:
            Generic procedure
        """
        issue_type = diagnosis_result.get("issue_type", "unknown")
        
        # Generic procedures by issue type
        generic_procedures = {
            "hardware_defect": {
                "title": "Generic Hardware Replacement Procedure",
                "steps": [
                    "Power down the equipment safely",
                    "Disconnect all cables and connections",
                    "Remove failed component",
                    "Install replacement component",
                    "Reconnect cables and connections",
                    "Power on and verify functionality"
                ],
                "safety_notes": [
                    "Ensure equipment is fully powered down",
                    "Use anti-static precautions",
                    "Verify replacement part compatibility"
                ]
            },
            "electrical_malfunction": {
                "title": "Generic Electrical Issue Procedure",
                "steps": [
                    "De-energize equipment at main breaker",
                    "Verify zero energy state",
                    "Apply lockout/tagout",
                    "Inspect for visible damage",
                    "Test with multimeter if qualified",
                    "Replace damaged components",
                    "Remove lockout/tagout",
                    "Re-energize under supervision"
                ],
                "safety_notes": [
                    "CRITICAL: Requires qualified electrician",
                    "Lockout/tagout mandatory",
                    "Use insulated tools only"
                ]
            },
            "network_failure": {
                "title": "Generic Network Troubleshooting Procedure",
                "steps": [
                    "Check physical connections",
                    "Verify link lights and status LEDs",
                    "Test with known-good cable",
                    "Check port configuration",
                    "Verify network settings",
                    "Test connectivity"
                ],
                "safety_notes": [
                    "No electrical hazards for cable work",
                    "Avoid disrupting other connections"
                ]
            }
        }
        
        return generic_procedures.get(
            issue_type,
            {
                "title": "Generic Inspection and Repair Procedure",
                "steps": [
                    "Safely access the equipment",
                    "Perform visual inspection",
                    "Document observed issues",
                    "Consult with specialist if needed",
                    "Proceed with caution"
                ],
                "safety_notes": [
                    "Follow all safety protocols",
                    "Escalate if uncertain"
                ]
            }
        )
    
    def _notify_missing_manual(self, equipment_type: str, site_id: str):
        """
        Notify documentation team about missing manual.
        
        Args:
            equipment_type: Equipment type
            site_id: Site ID where equipment is located
        """
        logger.info(
            f"Notifying documentation team: Missing manual for {equipment_type} at {site_id}"
        )
        
        # In production, this would send an actual notification
        # For now, just log it
        notification = {
            "type": "missing_manual",
            "equipment_type": equipment_type,
            "site_id": site_id,
            "timestamp": datetime.now().isoformat(),
            "priority": "medium"
        }
        
        logger.debug(f"Missing manual notification: {notification}")

    def _search_web_for_manual(
        self,
        equipment_type: str,
        diagnosis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search the web for manufacturer documentation and repair guides.

        Uses web search to find:
        - Manufacturer documentation PDFs
        - Repair guides and service manuals
        - Technical datasheets
        - Community repair resources

        Args:
            equipment_type: Equipment type to search for
            diagnosis_result: Diagnosis result for context

        Returns:
            Web search results with manual links
        """
        logger.info(f"Searching web for manual: {equipment_type}")

        # Extract manufacturer and model if available
        manufacturer = diagnosis_result.get("manufacturer", "")
        model_number = diagnosis_result.get("model_number", "")

        # Build search query
        search_terms = []
        if manufacturer:
            search_terms.append(manufacturer)
        if model_number:
            search_terms.append(model_number)
        search_terms.extend([equipment_type, "service manual", "repair guide"])

        search_query = " ".join(search_terms)

        try:
            # Use web search tool (would be available in production)
            # For now, return a structured response indicating search was attempted

            # In production, this would use remote_web_search tool:
            # results = remote_web_search(query=search_query)

            # Simulated response structure
            web_results = {
                "found_manual": False,
                "search_query": search_query,
                "results": [],
                "message": "Web search capability not available in current environment"
            }

            # If we had actual search results, we would:
            # 1. Filter for PDF links and documentation sites
            # 2. Extract relevant sections
            # 3. Cache results for future use
            # 4. Return structured manual data

            logger.info(f"Web search attempted for: {search_query}")
            return web_results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {
                "found_manual": False,
                "search_query": search_query,
                "error": str(e),
                "results": []
            }

    def _generate_missing_manual_recommendations(
        self,
        similar_equipment: List[Dict[str, Any]],
        web_search_results: Dict[str, Any],
        guidance_quality: str
    ) -> List[Dict[str, Any]]:
        """
        Generate contextual recommendations when manual is missing.

        Args:
            similar_equipment: List of similar equipment found
            web_search_results: Web search results
            guidance_quality: Quality level (high/medium/low)

        Returns:
            List of prioritized recommendations
        """
        recommendations = []

        # Recommendation based on what was found
        if web_search_results.get("found_manual"):
            recommendations.append({
                "priority": 1,
                "action": "use_web_manual",
                "description": "Use manufacturer documentation found online",
                "confidence": "high",
                "details": "Manual found via web search. Review for accuracy before proceeding."
            })

        if similar_equipment:
            recommendations.append({
                "priority": 2,
                "action": "use_similar_equipment_manual",
                "description": f"Reference manual for similar equipment: {similar_equipment[0]['equipment_type']}",
                "confidence": "medium",
                "details": "Procedures may differ slightly. Verify compatibility before proceeding."
            })

        # Always provide generic procedure option
        recommendations.append({
            "priority": 3,
            "action": "use_generic_procedure",
            "description": "Follow generic repair procedure for this issue type",
            "confidence": "low" if guidance_quality == "low" else "medium",
            "details": "Generic procedure based on issue type. Proceed with caution and escalate if uncertain."
        })

        # Suggest expert consultation for low quality guidance
        if guidance_quality == "low":
            recommendations.append({
                "priority": 1,  # High priority for low quality
                "action": "consult_expert",
                "description": "Consult with equipment specialist before proceeding",
                "confidence": "high",
                "details": "Limited reference material available. Expert consultation recommended for safety and accuracy."
            })

        # Suggest documentation request
        recommendations.append({
            "priority": 4,
            "action": "request_documentation",
            "description": "Request manual from manufacturer or documentation team",
            "confidence": "high",
            "details": "Documentation team has been notified. Manual will be added to system when available."
        })

        return sorted(recommendations, key=lambda x: x["priority"])


    def _handle_delayed_delivery(
        self,
        workflow_state: WorkflowState,
        part_number: str,
        expected_delivery: datetime,
        actual_delay_days: int
    ) -> Dict[str, Any]:
        """
        Handle delayed part delivery (Task 12.8).
        
        Recovery strategies:
        - Search for expedited shipping options
        - Find alternative parts with faster availability
        - Cost-benefit analysis for expedited vs standard
        - Temporary workaround procedure recommendation
        - Management escalation for SLA violations
        
        Args:
            workflow_state: Current workflow state
            part_number: Delayed part number
            expected_delivery: Original expected delivery date
            actual_delay_days: Number of days delayed
            
        Returns:
            Recovery options and recommendations
        """
        logger.warning(
            f"Part delivery delayed for session {workflow_state.session_id}: "
            f"{part_number} delayed by {actual_delay_days} days"
        )
        
        # Search for expedited shipping
        expedited_options = self._search_expedited_shipping(part_number)
        
        # Find alternative parts
        alternative_parts = self._search_alternative_parts(part_number)
        
        # Generate temporary workaround
        workaround = self._generate_temporary_workaround(
            part_number,
            workflow_state.diagnosis_state
        )
        
        # Check if SLA violated
        sla_violated = actual_delay_days > 3  # Assume 3-day SLA
        
        if sla_violated:
            # Escalate to management
            escalation = self.handle_escalation(
                session_id=workflow_state.session_id,
                escalation_type=EscalationType.DELIVERY_DELAY,
                severity="high",
                description=(
                    f"Part {part_number} delivery delayed by {actual_delay_days} days. "
                    f"SLA violation. Expected: {expected_delivery.isoformat()}"
                ),
                context={
                    "part_number": part_number,
                    "expected_delivery": expected_delivery.isoformat(),
                    "actual_delay_days": actual_delay_days,
                    "sla_violated": True
                }
            )
            
            escalation_id = escalation.escalation_id
        else:
            escalation_id = None
        
        return {
            "success": False,
            "error": f"Part delivery delayed by {actual_delay_days} days",
            "error_type": "delivery_delay",
            "part_number": part_number,
            "expected_delivery": expected_delivery.isoformat(),
            "actual_delay_days": actual_delay_days,
            "sla_violated": sla_violated,
            "escalation_id": escalation_id,
            "recovery_options": {
                "expedited_shipping": expedited_options,
                "alternative_parts": alternative_parts,
                "temporary_workaround": workaround
            },
            "recommendations": self._generate_delay_recommendations(
                expedited_options,
                alternative_parts,
                workaround,
                actual_delay_days
            )
        }
    
    def _search_expedited_shipping(self, part_number: str) -> Dict[str, Any]:
        """
        Search for expedited shipping options.
        
        Args:
            part_number: Part number
            
        Returns:
            Expedited shipping options
        """
        # In production, this would query actual shipping providers
        return {
            "available": True,
            "options": [
                {
                    "method": "overnight",
                    "delivery_days": 1,
                    "additional_cost": 150.00,
                    "cost_increase_percentage": 30
                },
                {
                    "method": "2-day",
                    "delivery_days": 2,
                    "additional_cost": 75.00,
                    "cost_increase_percentage": 15
                }
            ],
            "recommendation": "2-day shipping offers best cost-benefit ratio"
        }
    
    def _search_alternative_parts(self, part_number: str) -> List[Dict[str, Any]]:
        """
        Search for alternative parts with faster availability.
        
        Args:
            part_number: Original part number
            
        Returns:
            List of alternative parts
        """
        # In production, this would query inventory for compatible parts
        return [
            {
                "part_number": f"{part_number}-ALT1",
                "description": "Compatible alternative part",
                "availability": "in_stock",
                "delivery_days": 1,
                "cost_difference": 50.00,
                "compatibility": "fully_compatible",
                "warranty": "same"
            },
            {
                "part_number": f"{part_number}-REFURB",
                "description": "Refurbished original part",
                "availability": "in_stock",
                "delivery_days": 1,
                "cost_difference": -100.00,
                "compatibility": "exact_match",
                "warranty": "90_days"
            }
        ]
    
    def _generate_temporary_workaround(
        self,
        part_number: str,
        diagnosis_state: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate temporary workaround procedure.
        
        Args:
            part_number: Delayed part
            diagnosis_state: Diagnosis information
            
        Returns:
            Temporary workaround procedure
        """
        return {
            "available": True,
            "procedure": {
                "title": "Temporary Workaround Procedure",
                "description": "Maintain partial functionality until part arrives",
                "steps": [
                    "Isolate failed component",
                    "Configure system for degraded operation",
                    "Monitor system stability",
                    "Schedule follow-up repair when part arrives"
                ],
                "limitations": [
                    "Reduced capacity or performance",
                    "No redundancy during workaround period",
                    "Requires follow-up repair within 30 days"
                ],
                "estimated_duration_days": 7
            },
            "risk_level": "medium",
            "requires_approval": True
        }
    
    def _generate_delay_recommendations(
        self,
        expedited_options: Dict[str, Any],
        alternative_parts: List[Dict[str, Any]],
        workaround: Dict[str, Any],
        delay_days: int
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for handling delay.
        
        Args:
            expedited_options: Expedited shipping options
            alternative_parts: Alternative parts
            workaround: Workaround procedure
            delay_days: Number of days delayed
            
        Returns:
            Prioritized recommendations
        """
        recommendations = []
        
        # If delay is severe (>5 days), prioritize alternatives
        if delay_days > 5:
            if alternative_parts:
                recommendations.append({
                    "priority": 1,
                    "option": "use_alternative_part",
                    "reason": "Significant delay justifies alternative part",
                    "action": f"Order alternative part: {alternative_parts[0]['part_number']}"
                })
            
            if expedited_options.get("available"):
                recommendations.append({
                    "priority": 2,
                    "option": "expedited_shipping",
                    "reason": "Expedited shipping can reduce total delay",
                    "action": "Upgrade to 2-day shipping"
                })
        else:
            # Minor delay - expedited shipping may be sufficient
            if expedited_options.get("available"):
                recommendations.append({
                    "priority": 1,
                    "option": "expedited_shipping",
                    "reason": "Minor delay can be mitigated with expedited shipping",
                    "action": "Upgrade to 2-day shipping"
                })
        
        # Always offer workaround as fallback
        if workaround.get("available"):
            recommendations.append({
                "priority": 3,
                "option": "temporary_workaround",
                "reason": "Maintain partial functionality while waiting",
                "action": "Implement temporary workaround procedure"
            })
        
        return recommendations

    def _search_web_for_manual(
        self,
        equipment_type: str,
        diagnosis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search the web for manufacturer documentation and repair guides.
        
        Uses web search to find:
        - Manufacturer documentation PDFs
        - Repair guides and service manuals
        - Technical datasheets
        - Community repair resources
        
        Args:
            equipment_type: Equipment type to search for
            diagnosis_result: Diagnosis result for context
            
        Returns:
            Web search results with manual links
        """
        logger.info(f"Searching web for manual: {equipment_type}")
        
        # Extract manufacturer and model if available
        manufacturer = diagnosis_result.get("manufacturer", "")
        model_number = diagnosis_result.get("model_number", "")
        
        # Build search query
        search_terms = []
        if manufacturer:
            search_terms.append(manufacturer)
        if model_number:
            search_terms.append(model_number)
        search_terms.extend([equipment_type, "service manual", "repair guide"])
        
        search_query = " ".join(search_terms)
        
        try:
            # Use web search tool (would be available in production)
            # For now, return a structured response indicating search was attempted
            
            # In production, this would use remote_web_search tool:
            # results = remote_web_search(query=search_query)
            
            # Simulated response structure
            web_results = {
                "found_manual": False,
                "search_query": search_query,
                "results": [],
                "message": "Web search capability not available in current environment"
            }
            
            # If we had actual search results, we would:
            # 1. Filter for PDF links and documentation sites
            # 2. Extract relevant sections
            # 3. Cache results for future use
            # 4. Return structured manual data
            
            logger.info(f"Web search attempted for: {search_query}")
            return web_results
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {
                "found_manual": False,
                "search_query": search_query,
                "error": str(e),
                "results": []
            }
    
    def _generate_missing_manual_recommendations(
        self,
        similar_equipment: List[Dict[str, Any]],
        web_search_results: Dict[str, Any],
        guidance_quality: str
    ) -> List[Dict[str, Any]]:
        """
        Generate contextual recommendations when manual is missing.
        
        Args:
            similar_equipment: List of similar equipment found
            web_search_results: Web search results
            guidance_quality: Quality level (high/medium/low)
            
        Returns:
            List of prioritized recommendations
        """
        recommendations = []
        
        # Recommendation based on what was found
        if web_search_results.get("found_manual"):
            recommendations.append({
                "priority": 1,
                "action": "use_web_manual",
                "description": "Use manufacturer documentation found online",
                "confidence": "high",
                "details": "Manual found via web search. Review for accuracy before proceeding."
            })
        
        if similar_equipment:
            recommendations.append({
                "priority": 2,
                "action": "use_similar_equipment_manual",
                "description": f"Reference manual for similar equipment: {similar_equipment[0]['equipment_type']}",
                "confidence": "medium",
                "details": "Procedures may differ slightly. Verify compatibility before proceeding."
            })
        
        # Always provide generic procedure option
        recommendations.append({
            "priority": 3,
            "action": "use_generic_procedure",
            "description": "Follow generic repair procedure for this issue type",
            "confidence": "low" if guidance_quality == "low" else "medium",
            "details": "Generic procedure based on issue type. Proceed with caution and escalate if uncertain."
        })
        
        # Suggest expert consultation for low quality guidance
        if guidance_quality == "low":
            recommendations.append({
                "priority": 1,  # High priority for low quality
                "action": "consult_expert",
                "description": "Consult with equipment specialist before proceeding",
                "confidence": "high",
                "details": "Limited reference material available. Expert consultation recommended for safety and accuracy."
            })
        
        # Suggest documentation request
        recommendations.append({
            "priority": 4,
            "action": "request_documentation",
            "description": "Request manual from manufacturer or documentation team",
            "confidence": "high",
            "details": "Documentation team has been notified. Manual will be added to system when available."
        })
        
        return sorted(recommendations, key=lambda x: x["priority"])
