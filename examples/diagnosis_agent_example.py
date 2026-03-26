"""
Example usage of the DiagnosisAgent for multimodal infrastructure diagnosis.

This example demonstrates:
1. Basic diagnosis with images
2. RAG integration for reference comparison
3. Telemetry correlation
4. Multi-issue detection
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.DiagnosisAgent import DiagnosisAgent
from src.models.domain import SiteContext, ImageData, TelemetrySnapshot
from src.models.agents import DiagnosisInput
from datetime import datetime, timezone

def example_basic_diagnosis():
    """Example 1: Basic diagnosis with site photo"""
    print("=" * 60)
    print("Example 1: Basic Network Switch Diagnosis")
    print("=" * 60)
    
    agent = DiagnosisAgent()
    
    # Create site context
    site_context = SiteContext(
        site_id="SITE-001",
        location="Building A, Floor 3, Network Closet",
        equipment_type="network_switch",
        technician_id="TECH-123",
        skill_level="intermediate"
    )
    
    # Create image data (in production, this would be actual image bytes)
    image = ImageData(
        image_id="IMG-001",
        data=b"<base64_encoded_image_data>",  # Placeholder
        format="jpeg",
        timestamp=datetime.now(timezone.utc),
        annotations=[]
    )
    
    # Create diagnosis input
    diagnosis_input = DiagnosisInput(
        site_context=site_context,
        images=[image],
        technician_notes="Switch showing amber lights, no network connectivity",
        telemetry=None
    )
    
    # Perform diagnosis
    result = agent.diagnose_issue(diagnosis_input)
    
    print(f"\nDiagnosis Result:")
    print(f"  Issue Type: {result.issue_type}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Description: {result.description}")
    print(f"  Root Cause: {result.root_cause}")
    print(f"  Severity: {result.severity}")
    print(f"  Estimated Repair Time: {result.estimated_repair_time_minutes} minutes")
    
    if result.required_parts:
        print(f"\n  Required Parts:")
        for part in result.required_parts:
            print(f"    - {part.part_number}: {part.description}")
    
    if result.escalation_required:
        print(f"\n  ⚠️  ESCALATION REQUIRED: {result.escalation_reason}")
    
    print("\n")


def example_diagnosis_with_rag():
    """Example 2: Diagnosis with RAG reference comparison"""
    print("=" * 60)
    print("Example 2: Diagnosis with Reference Manual Comparison")
    print("=" * 60)
    
    agent = DiagnosisAgent()
    
    site_context = SiteContext(
        site_id="SITE-002",
        location="Building B, Electrical Room",
        equipment_type="electrical_panel",
        technician_id="TECH-456",
        skill_level="advanced"
    )
    
    image = ImageData(
        image_id="IMG-002",
        data=b"<base64_encoded_image_data>",
        format="jpeg",
        timestamp=datetime.now(timezone.utc),
        annotations=[]
    )
    
    diagnosis_input = DiagnosisInput(
        site_context=site_context,
        images=[image],
        technician_notes="Breaker panel showing unusual configuration",
        telemetry=None
    )
    
    # Perform diagnosis
    result = agent.diagnose_issue(diagnosis_input)
    
    # Compare with reference materials
    comparison = agent.compare_with_reference_materials(
        diagnosis_result=result,
        site_context=site_context
    )
    
    print(f"\nDiagnosis Result:")
    print(f"  Issue Type: {result.issue_type}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Description: {result.description}")
    
    print(f"\nReference Comparison:")
    print(f"  Deviations Found: {comparison['deviations_found']}")
    if comparison['deviations_found']:
        print(f"  Deviations:")
        for deviation in comparison['deviations']:
            print(f"    - {deviation}")
    
    if comparison['manual_sections']:
        print(f"\n  Relevant Manual Sections:")
        for section in comparison['manual_sections']:
            print(f"    - {section}")
    
    print("\n")


def example_diagnosis_with_telemetry():
    """Example 3: Diagnosis with telemetry correlation"""
    print("=" * 60)
    print("Example 3: Diagnosis with Telemetry Correlation")
    print("=" * 60)
    
    agent = DiagnosisAgent()
    
    site_context = SiteContext(
        site_id="SITE-003",
        location="Building C, Server Room",
        equipment_type="server",
        technician_id="TECH-789",
        skill_level="expert"
    )
    
    image = ImageData(
        image_id="IMG-003",
        data=b"<base64_encoded_image_data>",
        format="jpeg",
        timestamp=datetime.now(timezone.utc),
        annotations=[]
    )
    
    # Create telemetry snapshot
    telemetry = TelemetrySnapshot(
        timestamp=datetime.now(timezone.utc),
        metrics={
            "cpu_temperature": 85.5,
            "fan_speed_rpm": 0,
            "power_draw_watts": 450,
            "network_throughput_mbps": 0
        },
        alerts=["HIGH_TEMPERATURE", "FAN_FAILURE"],
        baseline_metrics={
            "cpu_temperature": 45.0,
            "fan_speed_rpm": 3000,
            "power_draw_watts": 400,
            "network_throughput_mbps": 950
        }
    )
    
    diagnosis_input = DiagnosisInput(
        site_context=site_context,
        images=[image],
        technician_notes="Server overheating, fans not spinning",
        telemetry=telemetry
    )
    
    # Perform diagnosis
    result = agent.diagnose_issue(diagnosis_input)
    
    # Analyze telemetry separately
    telemetry_analysis = agent.analyze_telemetry(telemetry, site_context)
    
    print(f"\nDiagnosis Result:")
    print(f"  Issue Type: {result.issue_type}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Description: {result.description}")
    print(f"  Root Cause: {result.root_cause}")
    
    print(f"\nTelemetry Analysis:")
    print(f"  Anomalies Detected: {telemetry_analysis['anomalies_detected']}")
    if telemetry_analysis['anomalies_detected']:
        print(f"  Anomalies:")
        for anomaly in telemetry_analysis['anomalies']:
            print(f"    - {anomaly}")
    
    print(f"  Correlation with Visual Evidence: {telemetry_analysis['correlation_with_visual']}")
    print(f"  Confidence Adjustment: {telemetry_analysis['confidence_adjustment']:+.2f}")
    
    print("\n")


def example_multi_issue_detection():
    """Example 4: Multi-issue detection"""
    print("=" * 60)
    print("Example 4: Multi-Issue Detection")
    print("=" * 60)
    
    agent = DiagnosisAgent()
    
    site_context = SiteContext(
        site_id="SITE-004",
        location="Building D, Telecom Room",
        equipment_type="mixed",
        technician_id="TECH-101",
        skill_level="intermediate"
    )
    
    # Multiple images showing different issues
    images = [
        ImageData(
            image_id="IMG-004-A",
            data=b"<network_switch_image>",
            format="jpeg",
            timestamp=datetime.now(timezone.utc),
            annotations=[]
        ),
        ImageData(
            image_id="IMG-004-B",
            data=b"<power_panel_image>",
            format="jpeg",
            timestamp=datetime.now(timezone.utc),
            annotations=[]
        )
    ]
    
    diagnosis_input = DiagnosisInput(
        site_context=site_context,
        images=images,
        technician_notes="Multiple issues: network down and power fluctuations",
        telemetry=None
    )
    
    # Detect multiple issues
    issues = agent.detect_multiple_issues(diagnosis_input)
    
    print(f"\nMulti-Issue Detection:")
    print(f"  Total Issues Found: {len(issues)}")
    
    for i, issue in enumerate(issues, 1):
        print(f"\n  Issue {i}:")
        print(f"    Type: {issue.issue_type}")
        print(f"    Confidence: {issue.confidence:.2f}")
        print(f"    Description: {issue.description}")
        print(f"    Severity: {issue.severity}")
        print(f"    Priority: {issue.priority}")
    
    print("\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DiagnosisAgent Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    example_basic_diagnosis()
    example_diagnosis_with_rag()
    example_diagnosis_with_telemetry()
    example_multi_issue_detection()
    
    print("=" * 60)
    print("Examples Complete")
    print("=" * 60)
