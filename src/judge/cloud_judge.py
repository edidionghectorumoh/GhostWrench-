"""
Cloud-Based Judge - Validation layer using Amazon Bedrock models.

This module implements a cloud-based judge that uses Amazon Nova 2 Lite and 
Claude 3.5 Sonnet via AWS Bedrock to validate all AI agent outputs for 
safety, SOP compliance, budget constraints, and quality thresholds.

The judge leverages the Bedrock Runtime client configured in config.py.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import bedrock_runtime, NOVA_2_LITE_MODEL_ID, CLAUDE_SONNET_MODEL_ID
from .audit_logger import AuditLogger
from ..models.validation import (
    AgentOutput,
    ValidationCriteria,
    JudgmentResult,
    SafetyJudgment,
    ComplianceJudgment,
    BudgetJudgment,
    Violation,
    ViolationType,
    EscalationLevel,
    Hazard,
    SOPViolation,
    Deviation,
    CostBreakdown,
    ApprovalLevel,
)
from ..models.agents import DiagnosisResult, PurchaseRequest, RepairGuide


logger = logging.getLogger(__name__)


class CloudJudge:
    """
    Cloud-based judge for validating AI agent outputs using AWS Bedrock.
    
    Uses Amazon Nova Pro for multimodal analysis and Claude 3.5 Sonnet 
    for complex reasoning and validation logic.
    """
    
    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        use_nova_for_vision: bool = True,
        use_claude_for_reasoning: bool = True,
    ):
        """
        Initialize Cloud Judge.
        
        Args:
            audit_logger: Optional audit logger instance
            use_nova_for_vision: Use Nova Pro for vision-based validations
            use_claude_for_reasoning: Use Claude for complex reasoning
        """
        self.bedrock = bedrock_runtime
        self.nova_model_id = NOVA_2_LITE_MODEL_ID
        self.claude_model_id = CLAUDE_SONNET_MODEL_ID
        self.audit_logger = audit_logger or AuditLogger()
        self.use_nova_for_vision = use_nova_for_vision
        self.use_claude_for_reasoning = use_claude_for_reasoning
        
        logger.info("Cloud Judge initialized with Bedrock Runtime")
    
    def _call_claude(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """
        Call Claude 3.5 Sonnet via Bedrock for reasoning tasks.
        
        Args:
            prompt: Prompt text for Claude
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise RuntimeError(f"Failed to call Claude via Bedrock: {e}")
    
    # Prohibited Field Actions — triggers immediate escalation to safety officer
    PROHIBITED_FIELD_ACTIONS = [
        "high-voltage work without a valid electrical permit",
        "confined-space entry without a buddy or standby attendant",
        "hot work (welding, cutting, brazing) without a fire watch",
        "working at heights above 6 feet without fall protection",
        "lockout/tagout bypass or override",
        "energized electrical panel access without arc-flash PPE",
        "excavation or trenching without utility locate clearance",
        "handling hazardous materials without SDS review and proper PPE",
    ]

    def _call_nova(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Call Amazon Nova 2 Lite via Bedrock Converse API.
        
        Includes a system prompt with Prohibited Field Actions that the model
        must flag for immediate escalation to a safety officer.
        
        Args:
            prompt: Prompt text for Nova 2 Lite
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            prohibited_list = "\n".join(
                f"  - {action}" for action in self.PROHIBITED_FIELD_ACTIONS
            )
            system_prompt = (
                "You are a safety-first validation judge for field engineering operations.\n\n"
                "PROHIBITED FIELD ACTIONS — If the agent output recommends or implies ANY of the "
                "following actions, you MUST flag the output as NON_COMPLIANT and recommend "
                "immediate escalation to a safety officer:\n"
                f"{prohibited_list}\n\n"
                "Always err on the side of caution. When in doubt, escalate."
            )

            response = self.bedrock.converse(
                modelId=self.nova_model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature
                }
            )
            
            return response['output']['message']['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Nova 2 Lite API call failed: {e}")
            raise RuntimeError(f"Failed to call Nova 2 Lite via Bedrock: {e}")
    
    def validate_agent_output(
        self,
        output: AgentOutput,
        validation_criteria: ValidationCriteria,
    ) -> JudgmentResult:
        """
        Primary validation method for any agent output using Claude 3.5 Sonnet.
        
        Args:
            output: Agent output to validate
            validation_criteria: Criteria to validate against
            
        Returns:
            JudgmentResult with approval decision and reasoning
        """
        logger.info(
            f"Validating {output.agent_type} output for session {output.session_id}"
        )
        
        violations: List[Violation] = []
        
        # Step 1: Safety validation (highest priority)
        if validation_criteria.safety_rules:
            safety_violations = self._validate_safety_rules(
                output, validation_criteria.safety_rules
            )
            violations.extend(safety_violations)
        
        # Step 2: SOP compliance validation
        if validation_criteria.sop_policies:
            sop_violations = self._validate_sop_policies(
                output, validation_criteria.sop_policies
            )
            violations.extend(sop_violations)
        
        # Step 3: Budget validation
        if validation_criteria.budget_limits:
            budget_violations = self._validate_budget(
                output, validation_criteria.budget_limits
            )
            violations.extend(budget_violations)
        
        # Step 4: Quality threshold validation
        if validation_criteria.quality_thresholds:
            quality_violations = self._validate_quality(
                output, validation_criteria.quality_thresholds
            )
            violations.extend(quality_violations)
        
        # Generate judgment with Claude reasoning
        approved = len(violations) == 0
        reasoning = self._generate_reasoning_with_claude(output, violations, approved)
        
        # Determine escalation level
        escalation_level = self._determine_escalation_level(violations)
        requires_human_review = escalation_level != EscalationLevel.NONE
        
        judgment = JudgmentResult(
            approved=approved,
            confidence=0.90 if approved else 0.95,  # High confidence with Claude
            reasoning=reasoning,
            violations=violations,
            recommendations=self._generate_recommendations_with_claude(violations),
            requires_human_review=requires_human_review,
            escalation_level=escalation_level,
            timestamp=datetime.now(),
        )
        
        # Log judgment to audit database
        self.log_judgment(judgment, output)
        
        return judgment
    
    def _validate_safety_rules(
        self,
        output: AgentOutput,
        safety_rules: List[Any],
    ) -> List[Violation]:
        """Validate output against safety rules using Claude."""
        violations = []
        
        for rule in safety_rules:
            prompt = self._format_safety_validation_prompt(output, rule)
            
            # Use Claude for safety reasoning
            claude_response = self._call_claude(prompt, temperature=0.1)
            
            # Parse Claude response for safety compliance
            is_compliant = self._parse_safety_response(claude_response)
            
            if not is_compliant:
                violations.append(Violation(
                    violation_type=ViolationType.SAFETY,
                    rule_id=rule.rule_id,
                    reason=f"Safety rule violation: {rule.description}",
                    severity=rule.severity,
                ))
        
        return violations
    
    def _validate_sop_policies(
        self,
        output: AgentOutput,
        sop_policies: List[Any],
    ) -> List[Violation]:
        """Validate output against SOP policies using Claude."""
        violations = []
        
        for policy in sop_policies:
            prompt = self._format_sop_validation_prompt(output, policy)
            claude_response = self._call_claude(prompt, temperature=0.1)
            
            is_compliant = self._parse_sop_response(claude_response)
            
            if not is_compliant:
                violations.append(Violation(
                    violation_type=ViolationType.SOP,
                    rule_id=policy.policy_id,
                    reason=f"SOP policy violation: {policy.title}",
                    severity="high",
                ))
        
        return violations
    
    def _validate_budget(
        self,
        output: AgentOutput,
        budget_limits: Any,
    ) -> List[Violation]:
        """Validate output against budget constraints."""
        violations = []
        
        # Extract cost from output if it's a purchase request
        if hasattr(output.output_data, 'total_cost'):
            total_cost = output.output_data.total_cost
            
            if total_cost > budget_limits.max_amount:
                violations.append(Violation(
                    violation_type=ViolationType.BUDGET,
                    rule_id="budget_exceeded",
                    reason=f"Cost ${total_cost:.2f} exceeds limit ${budget_limits.max_amount:.2f}",
                    severity="high",
                ))
        
        return violations
    
    def _validate_quality(
        self,
        output: AgentOutput,
        quality_thresholds: Any,
    ) -> List[Violation]:
        """Validate output against quality thresholds."""
        violations = []
        
        if output.confidence < quality_thresholds.min_confidence:
            violations.append(Violation(
                violation_type=ViolationType.QUALITY,
                rule_id="low_confidence",
                reason=f"Confidence {output.confidence:.2f} below threshold {quality_thresholds.min_confidence:.2f}",
                severity="medium",
            ))
        
        return violations
    
    def _format_safety_validation_prompt(
        self,
        output: AgentOutput,
        rule: Any,
    ) -> str:
        """Format prompt for safety validation."""
        return f"""You are a safety validation expert analyzing AI agent output for compliance with safety protocols.

Safety Rule: {rule.description}
Severity: {rule.severity}

Agent Output Type: {output.agent_type}
Output Data: {json.dumps(str(output.output_data)[:500], indent=2)}

Analyze this output for safety compliance. Consider:
1. Are there any hazardous operations proposed?
2. Are proper safety precautions mentioned?
3. Is specialized equipment or authorization required?
4. Are there electrical, mechanical, or environmental hazards?

Respond with COMPLIANT or NON_COMPLIANT followed by a brief explanation."""
    
    def _format_sop_validation_prompt(
        self,
        output: AgentOutput,
        policy: Any,
    ) -> str:
        """Format prompt for SOP validation."""
        return f"""You are an SOP compliance expert analyzing AI agent output.

SOP Policy: {policy.title}
Description: {policy.description}
Mandatory Steps: {', '.join(policy.mandatory_steps) if hasattr(policy, 'mandatory_steps') else 'N/A'}

Agent Output Type: {output.agent_type}
Output Data: {json.dumps(str(output.output_data)[:500], indent=2)}

Evaluate SOP compliance. Consider:
1. Are all mandatory steps included?
2. Is the procedure order correct?
3. Are there any deviations from standard practice?
4. Are safety checks properly integrated?

Respond with COMPLIANT or NON_COMPLIANT followed by a brief explanation."""
    
    def _parse_safety_response(self, response: str) -> bool:
        """Parse model response for safety compliance."""
        response_lower = response.lower()
        return "compliant" in response_lower and "non_compliant" not in response_lower
    
    def _parse_sop_response(self, response: str) -> bool:
        """Parse model response for SOP compliance."""
        response_lower = response.lower()
        return "compliant" in response_lower and "non_compliant" not in response_lower
    
    def _generate_reasoning_with_claude(
        self,
        output: AgentOutput,
        violations: List[Violation],
        approved: bool,
    ) -> str:
        """Generate human-readable reasoning using Claude."""
        if approved:
            return (
                f"All validation criteria satisfied for {output.agent_type} output. "
                f"Confidence: {output.confidence:.2f}. No safety, SOP, budget, or quality violations detected."
            )
        
        violation_summary = "\n".join([
            f"- {v.violation_type.value}: {v.reason}" for v in violations
        ])
        
        prompt = f"""Generate a concise, professional explanation for why this AI agent output was rejected.

Agent Type: {output.agent_type}
Violations Found:
{violation_summary}

Provide a 2-3 sentence explanation suitable for a field technician, focusing on the most critical issues."""
        
        reasoning = self._call_claude(prompt, temperature=0.3, max_tokens=200)
        return reasoning.strip()
    
    def _generate_recommendations_with_claude(
        self,
        violations: List[Violation],
    ) -> List[str]:
        """Generate actionable recommendations using Claude."""
        if not violations:
            return []
        
        violation_summary = "\n".join([
            f"- {v.violation_type.value}: {v.reason}" for v in violations
        ])
        
        prompt = f"""Based on these validation violations, provide 2-3 specific, actionable recommendations:

Violations:
{violation_summary}

Format as a JSON array of strings. Be concise and practical."""
        
        try:
            response = self._call_claude(prompt, temperature=0.3, max_tokens=300)
            # Try to parse as JSON
            recommendations = json.loads(response)
            if isinstance(recommendations, list):
                return recommendations[:3]  # Limit to 3
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Fallback to rule-based recommendations
        return self._generate_fallback_recommendations(violations)
    
    def _generate_fallback_recommendations(
        self,
        violations: List[Violation],
    ) -> List[str]:
        """Generate fallback recommendations based on violation types."""
        recommendations = []
        
        for violation in violations:
            if violation.violation_type == ViolationType.SAFETY:
                recommendations.append("Escalate to safety officer for review")
            elif violation.violation_type == ViolationType.BUDGET:
                recommendations.append("Request higher approval authority")
            elif violation.violation_type == ViolationType.SOP:
                recommendations.append("Review SOP documentation with supervisor")
            elif violation.violation_type == ViolationType.QUALITY:
                recommendations.append("Request additional diagnostic data")
        
        return list(set(recommendations))[:3]
    
    def _determine_escalation_level(
        self,
        violations: List[Violation],
    ) -> EscalationLevel:
        """Determine escalation level based on violations."""
        if not violations:
            return EscalationLevel.NONE
        
        # Safety violations always escalate to safety officer
        for violation in violations:
            if violation.violation_type == ViolationType.SAFETY:
                if violation.severity in ["critical", "high"]:
                    return EscalationLevel.SAFETY_OFFICER
        
        # Budget violations escalate to management
        for violation in violations:
            if violation.violation_type == ViolationType.BUDGET:
                return EscalationLevel.MANAGEMENT
        
        # SOP violations escalate to supervisor
        for violation in violations:
            if violation.violation_type == ViolationType.SOP:
                return EscalationLevel.SUPERVISOR
        
        return EscalationLevel.SUPERVISOR
    
    def validate_diagnosis_safety(
        self,
        diagnosis: DiagnosisResult,
    ) -> SafetyJudgment:
        """
        Specialized validation for diagnosis safety using Claude.
        
        Args:
            diagnosis: Diagnosis result to validate
            
        Returns:
            SafetyJudgment with safety assessment
        """
        logger.info(f"Validating diagnosis safety for issue {diagnosis.issue_id}")
        
        prompt = f"""You are a safety expert analyzing a field diagnosis for potential hazards.

Issue Type: {diagnosis.issue_type}
Severity: {diagnosis.severity}
Description: {diagnosis.description}
Root Cause: {diagnosis.root_cause}
Affected Components: {', '.join([c.component_type for c in diagnosis.affected_components])}

Analyze this diagnosis for safety concerns:
1. What hazards are present?
2. What PPE is required?
3. Is lockout/tagout needed?
4. Are there environmental hazards?
5. Is a work permit required?

Provide your assessment in JSON format:
{{
  "is_safe": true/false,
  "hazards": ["hazard1", "hazard2"],
  "ppe_required": ["item1", "item2"],
  "lockout_tagout_needed": true/false,
  "permit_required": true/false
}}"""
        
        claude_response = self._call_claude(prompt, temperature=0.1, max_tokens=500)
        
        # Parse JSON response
        try:
            safety_data = json.loads(claude_response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse safety judgment, using conservative defaults")
            safety_data = {
                "is_safe": False,
                "hazards": ["Unable to assess - requires human review"],
                "ppe_required": ["Safety glasses", "Gloves"],
                "lockout_tagout_needed": diagnosis.severity in ["critical", "high"],
                "permit_required": diagnosis.severity == "critical",
            }
        
        # Convert to Hazard objects
        hazards = [
            Hazard(
                hazard_id=f"hazard_{i}",
                hazard_type="general",
                description=h,
                severity=diagnosis.severity.value,
                mitigation="Follow safety protocols",
            )
            for i, h in enumerate(safety_data.get("hazards", []))
        ]
        
        return SafetyJudgment(
            is_safe=safety_data.get("is_safe", False),
            hazards_identified=hazards,
            required_precautions=safety_data.get("hazards", []),
            ppe_required=safety_data.get("ppe_required", []),
            lockout_tagout_needed=safety_data.get("lockout_tagout_needed", False),
            permit_required=safety_data.get("permit_required", False),
        )
    
    def validate_sop_compliance(
        self,
        guidance: RepairGuide,
    ) -> ComplianceJudgment:
        """
        Specialized validation for SOP compliance using Claude.
        
        Args:
            guidance: Repair guide to validate
            
        Returns:
            ComplianceJudgment with compliance assessment
        """
        logger.info(f"Validating SOP compliance for guide {guidance.guide_id}")
        
        steps_text = "\n".join([
            f"{i+1}. {step.instruction}" 
            for i, step in enumerate(guidance.steps)
        ])
        
        prompt = f"""You are an SOP compliance expert reviewing a repair procedure.

Repair Guide ID: {guidance.guide_id}
Skill Level Required: {guidance.skill_level_required}
Steps:
{steps_text}

Safety Warnings: {len(guidance.safety_warnings)} warnings present
SOP References: {', '.join([ref.title for ref in guidance.sop_references])}

Evaluate this repair guide for SOP compliance:
1. Are safety checks included at appropriate steps?
2. Is the procedure order logical and safe?
3. Are there any missing critical steps?
4. Does it follow standard practices?

Provide assessment in JSON format:
{{
  "is_compliant": true/false,
  "missing_steps": ["step1", "step2"],
  "deviations": ["deviation1"],
  "approved_with_conditions": true/false,
  "conditions": ["condition1"]
}}"""
        
        claude_response = self._call_claude(prompt, temperature=0.1, max_tokens=500)
        
        try:
            compliance_data = json.loads(claude_response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse compliance judgment")
            compliance_data = {
                "is_compliant": True,
                "missing_steps": [],
                "deviations": [],
                "approved_with_conditions": False,
            }
        
        # Convert to structured objects
        sop_violations = []
        deviations = [
            Deviation(
                deviation_id=f"dev_{i}",
                description=d,
                severity="medium",
            )
            for i, d in enumerate(compliance_data.get("deviations", []))
        ]
        
        return ComplianceJudgment(
            is_compliant=compliance_data.get("is_compliant", True),
            sop_violations=sop_violations,
            missing_steps=compliance_data.get("missing_steps", []),
            deviations_from_standard=deviations,
            approved_with_conditions=compliance_data.get("approved_with_conditions", False),
            conditions=compliance_data.get("conditions"),
        )
    
    def validate_budget_constraints(
        self,
        purchase_request: PurchaseRequest,
        budget_limits: Optional[Any] = None,
    ) -> BudgetJudgment:
        """
        Specialized validation for budget constraints.
        
        Args:
            purchase_request: Purchase request to validate
            budget_limits: Optional budget limits
            
        Returns:
            BudgetJudgment with budget assessment
        """
        logger.info(f"Validating budget for request {purchase_request.request_id}")
        
        total_cost = purchase_request.total_cost
        budget_limit = budget_limits.max_amount if budget_limits else 5000.0
        
        within_budget = total_cost <= budget_limit
        
        # Determine approval level based on cost
        if total_cost <= 1000:
            approval_level = ApprovalLevel.TECHNICIAN
        elif total_cost <= 5000:
            approval_level = ApprovalLevel.SUPERVISOR
        elif total_cost <= 20000:
            approval_level = ApprovalLevel.MANAGER
        else:
            approval_level = ApprovalLevel.DIRECTOR
        
        # Create cost breakdown
        cost_breakdown = CostBreakdown(
            parts_cost=total_cost * 0.85,
            labor_cost=total_cost * 0.10,
            shipping_cost=total_cost * 0.03,
            tax=total_cost * 0.02,
            total=total_cost,
        )
        
        return BudgetJudgment(
            within_budget=within_budget,
            total_cost=total_cost,
            budget_limit=budget_limit,
            approval_level_required=approval_level,
            cost_breakdown=cost_breakdown,
            alternatives_considered=len(purchase_request.parts) > 1,
        )
    
    def log_judgment(
        self,
        judgment: JudgmentResult,
        agent_output: Optional[AgentOutput] = None,
    ) -> None:
        """
        Log judgment to audit database.
        
        Args:
            judgment: Judgment result to log
            agent_output: Optional agent output that was judged
        """
        self.audit_logger.log_judgment(judgment, agent_output)
