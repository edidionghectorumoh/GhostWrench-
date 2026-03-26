"""
Example usage of the ActionAgent for agentic parts procurement.

This example demonstrates:
1. Basic inventory search
2. Part availability checking
3. Cost estimation
4. Purchase request creation
5. Complete tool chain execution with Nova Act
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.ActionAgent import ActionAgent
from src.agents.DiagnosisAgent import DiagnosisAgent
from src.models.domain import SiteContext, ImageData, Part
from src.models.agents import DiagnosisInput, DiagnosisResult
from datetime import datetime, timezone

def example_inventory_search():
    """Example 1: Search inventory for parts"""
    print("=" * 60)
    print("Example 1: Inventory Search")
    print("=" * 60)
    
    agent = ActionAgent()
    
    # Search for network switch parts
    parts = agent.search_inventory(
        query="Cisco Catalyst 2960",
        equipment_type="network_switch",
        fuzzy_match=True
    )
    
    print(f"\nFound {len(parts)} parts:")
    for part in parts:
        print(f"  - {part.part_number}: {part.description}")
        print(f"    Price: ${part.unit_price:.2f}, Lead Time: {part.lead_time_days} days")
    
    print("\n")


def example_part_availability():
    """Example 2: Check part availability"""
    print("=" * 60)
    print("Example 2: Part Availability Check")
    print("=" * 60)
    
    agent = ActionAgent()
    
    # Check availability for specific part
    availability = agent.check_part_availability(
        part_number="NS-2960X-24TS-L",
        quantity=2
    )
    
    print(f"\nPart: {availability['part_number']}")
    print(f"Available: {availability['available']}")
    print(f"Stock Quantity: {availability['stock_quantity']}")
    print(f"Requested Quantity: {availability['requested_quantity']}")
    print(f"Lead Time: {availability['lead_time_days']} days")
    print(f"Unit Price: ${availability['unit_price']:.2f}")
    print(f"Estimated Delivery: {availability['estimated_delivery']}")
    print(f"Supplier: {availability['supplier']}")
    
    print("\n")


def example_cost_estimation():
    """Example 3: Generate cost estimate"""
    print("=" * 60)
    print("Example 3: Cost Estimation")
    print("=" * 60)
    
    agent = ActionAgent()
    
    # Create parts list
    parts = [
        Part(
            part_number="NS-2960X-24TS-L",
            description="Cisco Catalyst 2960-X 24 Port Switch",
            category="network_switch",
            quantity=1,
            unit_price=1250.00,
            lead_time_days=2,
            supplier="Primary Distributor"
        ),
        Part(
            part_number="CAB-ETH-10M",
            description="Ethernet Cable 10m",
            category="cable",
            quantity=5,
            unit_price=15.00,
            lead_time_days=1,
            supplier="Primary Distributor"
        )
    ]
    
    # Generate cost estimate
    estimate = agent.generate_cost_estimate(
        parts=parts,
        labor_hours=2.5,
        expedited_shipping=False
    )
    
    print(f"\nCost Estimate:")
    print(f"  Parts Cost: ${estimate['parts_cost']:.2f}")
    print(f"  Labor Cost: ${estimate['labor_cost']:.2f} ({estimate['labor_hours']} hours @ ${estimate['labor_rate_per_hour']:.2f}/hr)")
    print(f"  Shipping Cost: ${estimate['shipping_cost']:.2f} {'(Expedited)' if estimate['expedited_shipping'] else '(Standard)'}")
    print(f"  Total Cost: ${estimate['total_cost']:.2f}")
    
    print("\n")


def example_purchase_request():
    """Example 4: Create purchase request"""
    print("=" * 60)
    print("Example 4: Purchase Request Creation")
    print("=" * 60)
    
    agent = ActionAgent()
    
    # Create purchase request
    request = agent.create_purchase_request(
        parts=["NS-2960X-24TS-L", "CAB-ETH-10M"],
        total_cost=1425.00,
        justification="Network switch failure at Building A. Critical infrastructure requires immediate replacement to restore connectivity.",
        urgency="high",
        site_id="SITE-001"
    )
    
    print(f"\nPurchase Request Created:")
    print(f"  Request ID: {request['purchase_request_id']}")
    print(f"  Status: {request['status']}")
    print(f"  Total Cost: ${request['total_cost']:.2f}")
    print(f"  Urgency: {request['urgency']}")
    print(f"  Site ID: {request['site_id']}")
    print(f"  Approval Required: {request['approval_required']}")
    print(f"  Created At: {request['created_at']}")
    
    # Submit to approval workflow
    if request['approval_required']:
        approval = agent.submit_to_approval_workflow(
            purchase_request_id=request['purchase_request_id'],
            total_cost=request['total_cost']
        )
        
        print(f"\n  Submitted to: {approval['submitted_to']}")
        print(f"  Estimated Approval Time: {approval['estimated_approval_time_hours']} hours")
        print(f"  Tracking URL: {approval['tracking_url']}")
    
    print("\n")


def example_complete_tool_chain():
    """Example 5: Complete tool chain execution with Nova Act"""
    print("=" * 60)
    print("Example 5: Complete Tool Chain Execution")
    print("=" * 60)
    
    # First, create a diagnosis result
    diagnosis_result = DiagnosisResult(
        issue_type="hardware_defect",
        confidence=0.92,
        description="Network switch has failed. Multiple ports showing no connectivity. Device not responding to management interface.",
        root_cause="Hardware failure - likely power supply or main board failure",
        severity="critical",
        required_parts=[
            Part(
                part_number="NS-2960X-24TS-L",
                description="Cisco Catalyst 2960-X 24 Port Switch",
                category="network_switch",
                quantity=1,
                unit_price=1250.00,
                lead_time_days=2,
                supplier="Primary Distributor"
            )
        ],
        required_tools=[],
        estimated_repair_time_minutes=120,
        safety_concerns=["Electrical work - power off required"],
        escalation_required=False,
        escalation_reason=None,
        supporting_evidence=["Visual inspection shows no power LED", "Device not responding to ping"],
        recommended_actions=["Replace network switch", "Verify power supply", "Test connectivity"],
        alternative_solutions=[],
        priority=1
    )
    
    # Create site context
    site_context = SiteContext(
        site_id="SITE-001",
        location="Building A, Floor 3, Network Closet",
        equipment_type="network_switch",
        technician_id="TECH-123",
        skill_level="intermediate"
    )
    
    # Execute complete tool chain
    action_agent = ActionAgent()
    result = action_agent.execute_tool_chain(diagnosis_result, site_context)
    
    print(f"\nAction Result:")
    print(f"  Action Type: {result.action_type}")
    print(f"  Status: {result.status}")
    print(f"  Description: {result.description}")
    
    print(f"\n  Tool Calls Executed:")
    for tool in result.tool_calls_executed:
        print(f"    - {tool}")
    
    if result.purchase_request_id:
        print(f"\n  Purchase Request ID: {result.purchase_request_id}")
        print(f"  Estimated Cost: ${result.estimated_cost:.2f}")
        print(f"  Approval Required: {result.approval_required}")
        print(f"  Approval Status: {result.approval_status}")
    
    if result.execution_details:
        print(f"\n  Execution Details:")
        print(f"    Tool Iterations: {result.execution_details.get('iterations', 0)}")
        if result.execution_details.get('cost_breakdown'):
            breakdown = result.execution_details['cost_breakdown']
            print(f"    Cost Breakdown:")
            print(f"      Parts: ${breakdown.get('parts', 0):.2f}")
            print(f"      Labor: ${breakdown.get('labor', 0):.2f}")
            print(f"      Shipping: ${breakdown.get('shipping', 0):.2f}")
    
    print("\n")


def example_telemetry_query():
    """Example 6: Query telemetry database"""
    print("=" * 60)
    print("Example 6: Telemetry Database Query")
    print("=" * 60)
    
    agent = ActionAgent()
    
    # Query telemetry data
    telemetry = agent.query_telemetry_database(
        site_id="SITE-001",
        metric_names=["cpu_temperature", "fan_speed_rpm", "power_draw_watts"],
        time_range_hours=24
    )
    
    print(f"\nTelemetry Data for Site: {telemetry['site_id']}")
    print(f"Time Range: {telemetry['time_range_hours']} hours")
    
    print(f"\nMetrics:")
    for metric_name, values in telemetry['metrics'].items():
        print(f"  {metric_name}: {values}")
    
    if telemetry['alerts']:
        print(f"\nAlerts:")
        for alert in telemetry['alerts']:
            print(f"  - {alert['alert']} at {alert['timestamp']}")
    
    print("\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ActionAgent Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    example_inventory_search()
    example_part_availability()
    example_cost_estimation()
    example_purchase_request()
    example_complete_tool_chain()
    example_telemetry_query()
    
    print("=" * 60)
    print("Examples Complete")
    print("=" * 60)
