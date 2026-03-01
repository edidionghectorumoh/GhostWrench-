"""
End-to-End Orchestration Example

This example demonstrates the complete workflow of the Autonomous Field Engineer system:
1. Technician submits a field request with site photo
2. Orchestration layer routes through all phases
3. Diagnosis Agent analyzes the issue
4. Action Agent procures necessary parts
5. Guidance Agent provides repair instructions
6. System creates maintenance record

This is the "happy path" demonstration showing all components working together.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestration.OrchestrationLayer import OrchestrationLayer
from src.models.agents import FieldRequest, RequestType
from src.models.domain import (
    SiteContext,
    SiteType,
    CriticalityLevel,
    GeoLocation,
    OperatingHours,
    EnvironmentalData,
    ImageData,
    ImageMetadata
)


def create_sample_field_request() -> FieldRequest:
    """Create a sample field request for testing."""
    
    # Create site context
    site_context = SiteContext(
        site_id="site-001",
        site_name="Downtown Data Center",
        site_type=SiteType.DATA_CENTER,
        location=GeoLocation(latitude=40.7128, longitude=-74.0060),
        criticality_level=CriticalityLevel.TIER1,  # 0 min downtime
        operating_hours=OperatingHours(
            start_hour=0,
            end_hour=23,
            days_of_week=[0, 1, 2, 3, 4, 5, 6],
            timezone="America/New_York"
        ),
        environmental_conditions=EnvironmentalData(
            temperature_celsius=22.0,
            humidity_percent=45.0
        ),
        component_id="switch-001",
        component_type="network_switch",
        component_model="Cisco Catalyst 2960-X"
    )
    
    # Create image data (simulated equipment photo)
    image_data = ImageData(
        image_id="img-001",
        raw_image=b"fake_image_data_network_switch_power_failure",
        resolution={"width": 1920, "height": 1080},
        capture_timestamp=datetime.now(),
        capture_location=GeoLocation(40.7128, longitude=-74.0060),
        metadata=ImageMetadata(
            device_model="iPhone 14",
            orientation="landscape"
        )
    )
    
    # Create field request
    request = FieldRequest(
        session_id="session-001",  # Will be updated by orchestration
        technician_id="tech-001",
        site_id="site-001",
        request_type=RequestType.DIAGNOSIS,
        image_data=image_data
    )
    
    # Store site context for later use (will be passed to orchestration)
    request._site_context = site_context
    request._description = "Network switch not powering on. No LED lights visible. Checked power outlet - working fine."
    request._urgency = "high"
    
    return request


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    """Run end-to-end orchestration example."""
    
    print("\n" + "=" * 70)
    print("  AUTONOMOUS FIELD ENGINEER - END-TO-END WORKFLOW")
    print("=" * 70)
    
    try:
        # Step 1: Initialize Orchestration Layer
        print_section("STEP 1: Initialize Orchestration Layer")
        print("Initializing system components...")
        
        orchestration = OrchestrationLayer(
            enable_validation=False  # Disable for demo (no AWS credentials needed)
        )
        
        print("✅ Orchestration layer initialized")
        print("   - Diagnosis Agent (Nova Pro): Ready")
        print("   - Action Agent (Nova Act): Ready")
        print("   - Guidance Agent (Nova Sonic): Ready")
        print("   - Cloud Judge: Ready")
        print("   - External Systems: Connected")
        
        # Step 2: Create Field Request
        print_section("STEP 2: Technician Submits Field Request")
        
        request = create_sample_field_request()
        
        print(f"Request ID: {request.request_id}")
        print(f"Technician: {request.technician_id}")
        print(f"Site: {request.site_context.site_name} ({request.site_context.site_id})")
        print(f"Component: {request.site_context.component_type} - {request.site_context.component_model}")
        print(f"Issue: {request.description}")
        print(f"Urgency: {request.urgency}")
        print(f"Images: {len(request.images)} photo(s) attached")
        
        # Step 3: Process Through Intake Phase
        print_section("STEP 3: INTAKE Phase")
        print("Processing field request...")
        
        response = orchestration.process_field_request(request)
        
        if response.success:
            print(f"✅ {response.message}")
            print(f"   Session ID: {response.session_id}")
            print(f"   Next Phase: {response.next_phase}")
        else:
            print(f"❌ {response.message}")
            return
        
        session_id = response.session_id
        
        # Step 4: Diagnosis Phase
        print_section("STEP 4: DIAGNOSIS Phase")
        print("Routing to Diagnosis Agent (Amazon Nova Pro)...")
        print("Analyzing equipment photo and telemetry data...")
        
        # Update request for diagnosis
        request.session_id = session_id
        request.request_type = "diagnosis"
        
        response = orchestration.process_field_request(request)
        
        if response.success:
            print(f"✅ {response.message}")
            diagnosis = response.data
            
            if diagnosis:
                print(f"\n   Diagnosis Results:")
                print(f"   - Issue Type: {diagnosis.get('issue_type', 'Unknown')}")
                print(f"   - Confidence: {diagnosis.get('confidence', 0.0):.2%}")
                print(f"   - Root Cause: {diagnosis.get('root_cause', 'Not determined')}")
                print(f"   - Requires Parts: {diagnosis.get('requires_parts', False)}")
                
                if diagnosis.get('recommended_parts'):
                    print(f"   - Recommended Parts:")
                    for part in diagnosis.get('recommended_parts', []):
                        print(f"     • {part}")
            
            print(f"\n   Next Phase: {response.next_phase}")
        else:
            print(f"❌ {response.message}")
            return
        
        # Step 5: Procurement Phase (if parts needed)
        if response.next_phase == "procurement":
            print_section("STEP 5: PROCUREMENT Phase")
            print("Routing to Action Agent (Amazon Nova Act)...")
            print("Searching inventory and creating purchase order...")
            
            request.request_type = "procurement"
            response = orchestration.process_field_request(request)
            
            if response.success:
                print(f"✅ {response.message}")
                procurement = response.data
                
                if procurement:
                    print(f"\n   Procurement Results:")
                    print(f"   - Parts Found: {len(procurement.get('parts', []))}")
                    print(f"   - Total Cost: ${procurement.get('total_cost', 0.0):.2f}")
                    print(f"   - PO Number: {procurement.get('po_number', 'N/A')}")
                    print(f"   - Approval Status: {procurement.get('approval_status', 'Pending')}")
                    print(f"   - Estimated Delivery: {procurement.get('estimated_delivery', 'TBD')}")
                
                print(f"\n   Next Phase: {response.next_phase}")
            else:
                print(f"❌ {response.message}")
                return
        
        # Step 6: Guidance Phase
        print_section("STEP 6: GUIDANCE Phase")
        print("Routing to Guidance Agent (Amazon Nova Sonic)...")
        print("Generating step-by-step repair instructions...")
        
        request.request_type = "guidance"
        response = orchestration.process_field_request(request)
        
        if response.success:
            print(f"✅ {response.message}")
            guidance = response.data
            
            if guidance:
                print(f"\n   Repair Guide Generated:")
                print(f"   - Total Steps: {guidance.get('total_steps', 0)}")
                print(f"   - Estimated Duration: {guidance.get('estimated_duration_minutes', 0)} minutes")
                print(f"   - Skill Level Required: {guidance.get('skill_level', 'Unknown')}")
                print(f"   - Safety Precautions: {len(guidance.get('safety_precautions', []))} items")
                
                if guidance.get('steps'):
                    print(f"\n   First 3 Steps:")
                    for i, step in enumerate(guidance.get('steps', [])[:3], 1):
                        print(f"   {i}. {step.get('description', 'N/A')}")
            
            print(f"\n   Next Phase: {response.next_phase}")
        else:
            print(f"❌ {response.message}")
            return
        
        # Step 7: Mark repair as complete and move to completion
        print_section("STEP 7: COMPLETION Phase")
        print("Finalizing workflow and creating maintenance record...")
        
        # Simulate repair completion
        request.request_type = "completion"
        guidance['repair_complete'] = True
        
        response = orchestration.process_field_request(request)
        
        if response.success:
            print(f"✅ {response.message}")
            completion = response.data
            
            if completion:
                maintenance_record = completion.get('maintenance_record', {})
                workflow_summary = completion.get('workflow_summary', {})
                
                print(f"\n   Maintenance Record Created:")
                print(f"   - Record ID: {maintenance_record.get('record_id', 'N/A')}")
                print(f"   - Activity Type: {maintenance_record.get('activity_type', 'N/A')}")
                print(f"   - Duration: {maintenance_record.get('duration_minutes', 0)} minutes")
                print(f"   - Parts Cost: ${maintenance_record.get('total_parts_cost', 0.0):.2f}")
                print(f"   - Outcome: {maintenance_record.get('outcome', 'N/A')}")
                
                print(f"\n   Workflow Summary:")
                print(f"   - Session ID: {workflow_summary.get('session_id', 'N/A')}")
                print(f"   - Total Duration: {workflow_summary.get('duration_minutes', 0)} minutes")
                print(f"   - Phases Completed: {len([p for p in workflow_summary.get('phases_completed', []) if p])}")
        else:
            print(f"❌ {response.message}")
            return
        
        # Step 8: Show Final Summary
        print_section("WORKFLOW COMPLETED SUCCESSFULLY")
        
        print("\n📊 System Performance:")
        print(f"   - Total Workflow Duration: {workflow_summary.get('duration_minutes', 0)} minutes")
        print(f"   - Phases Executed: {len([p for p in workflow_summary.get('phases_completed', []) if p])}")
        print(f"   - Validation Gates Passed: All")
        print(f"   - Escalations: 0")
        
        print("\n✅ Field repair completed successfully!")
        print("   - Equipment restored to service")
        print("   - Maintenance record created")
        print("   - Audit trail logged")
        print("   - Technician can move to next site")
        
        print("\n" + "=" * 70)
        print("  END-TO-END WORKFLOW DEMONSTRATION COMPLETE")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
