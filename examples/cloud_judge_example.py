"""
Example usage of Cloud-Based Judge for validation using AWS Bedrock.

This script demonstrates how to use the Cloud Judge with Amazon Nova Pro
and Claude 3.5 Sonnet to validate AI agent outputs for safety, SOP compliance,
and budget constraints.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.judge.cloud_judge import CloudJudge
from src.models.validation import (
    AgentOutput,
    AgentType,
    ValidationCriteria,
    SafetyRule,
    SOPPolicy,
    BudgetLimits,
    QualityThreshold,
    ApprovalLevel,
)
from src.models.agents import (
    DiagnosisResult,
    IssueType,
    Severity,
    Component,
    AnnotatedImage,
    Action,
    Urgency,
)


def example_diagnosis_validation():
    """Example: Validate a diagnosis for safety using Claude."""
    print("\n=== Example 1: Diagnosis Safety Validation (Claude 3.5 Sonnet) ===\n")
    
    # Initialize cloud judge
    judge = CloudJudge()
    
    # Create a sample diagnosis
    diagnosis = DiagnosisResult(
        issue_id="issue-001",
        issue_type=IssueType.ELECTRICAL_MALFUNCTION,
        severity=Severity.CRITICAL,
        confidence=0.85,
        description="Electrical panel showing signs of arcing on 480V bus bar",
        affected_components=[
            Component(
                component_id="panel-480v-main",
                component_type="electrical_panel",
                manufacturer="Schneider Electric",
                model_number="SE-480-100A",
            )
        ],
        root_cause="Loose connection on 480V bus bar causing arcing",
        visual_evidence=AnnotatedImage(
            image_id="img-001",
            original_image=b"",
            annotations=[],
        ),
        reference_manual_sections=[],
        recommended_actions=[
            Action(
                action_id="action-001",
                action_type="tighten_connection",
                description="Tighten bus bar connection",
                urgency=Urgency.EMERGENCY,
                requires_parts=False,
            )
        ],
    )
    
    # Validate safety using Claude
    print("Calling Claude 3.5 Sonnet for safety validation...")
    safety_judgment = judge.validate_diagnosis_safety(diagnosis)
    
    print(f"✓ Is Safe: {safety_judgment.is_safe}")
    print(f"✓ Hazards Identified: {len(safety_judgment.hazards_identified)}")
    print(f"✓ PPE Required: {', '.join(safety_judgment.ppe_required)}")
    print(f"✓ Lockout/Tagout Needed: {safety_judgment.lockout_tagout_needed}")
    print(f"✓ Permit Required: {safety_judgment.permit_required}")
    
    if not safety_judgment.is_safe:
        print("\n⚠️  SAFETY VIOLATION DETECTED - Escalation required!")


def example_agent_output_validation():
    """Example: Validate generic agent output using Claude."""
    print("\n=== Example 2: Agent Output Validation (Claude 3.5 Sonnet) ===\n")
    
    # Initialize cloud judge
    judge = CloudJudge()
    
    # Create sample agent output
    agent_output = AgentOutput(
        agent_type=AgentType.DIAGNOSIS,
        output_data={"test": "data"},
        confidence=0.75,
        timestamp=datetime.now(),
        session_id="session-123",
    )
    
    # Create validation criteria
    criteria = ValidationCriteria(
        safety_rules=[
            SafetyRule(
                rule_id="SAFE-001",
                description="High voltage work requires licensed electrician",
                severity="critical",
                applies_to=["electrical"],
            )
        ],
        quality_thresholds=QualityThreshold(
            min_confidence=0.80,
        ),
    )
    
    # Validate using Claude
    print("Calling Claude 3.5 Sonnet for comprehensive validation...")
    judgment = judge.validate_agent_output(agent_output, criteria)
    
    print(f"✓ Approved: {judgment.approved}")
    print(f"✓ Confidence: {judgment.confidence:.2f}")
    print(f"✓ Reasoning: {judgment.reasoning}")
    print(f"✓ Violations: {len(judgment.violations)}")
    print(f"✓ Escalation Level: {judgment.escalation_level.value}")
    print(f"✓ Requires Human Review: {judgment.requires_human_review}")
    
    if judgment.recommendations:
        print(f"\n✓ Recommendations:")
        for rec in judgment.recommendations:
            print(f"  - {rec}")


def example_audit_log_query():
    """Example: Query audit logs."""
    print("\n=== Example 3: Audit Log Statistics ===\n")
    
    from src.judge.audit_logger import AuditLogger
    
    # Initialize audit logger
    audit_logger = AuditLogger()
    
    # Get statistics
    stats = audit_logger.get_statistics()
    
    print(f"✓ Total Judgments: {stats['total_judgments']}")
    print(f"✓ Approved: {stats['approved']}")
    print(f"✓ Rejected: {stats['rejected']}")
    print(f"✓ Approval Rate: {stats['approval_rate']:.1%}")
    print(f"✓ Safety Violations: {stats['safety_violations']}")
    
    if stats['escalations']:
        print(f"\n✓ Escalations by Level:")
        for level, count in stats['escalations'].items():
            print(f"  {level}: {count}")


if __name__ == "__main__":
    print("=" * 70)
    print("Cloud-Based Judge Examples (AWS Bedrock)")
    print("Using: Amazon Nova Pro + Claude 3.5 Sonnet")
    print("=" * 70)
    
    try:
        example_diagnosis_validation()
        example_agent_output_validation()
        example_audit_log_query()
        
        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. AWS credentials are configured: aws configure")
        print("  2. Bedrock access is enabled in us-east-1")
        print("  3. Nova Pro and Claude 3.5 Sonnet models are available")
        import traceback
        traceback.print_exc()
