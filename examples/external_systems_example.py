"""
External Systems Integration Example

This example demonstrates how to use the external system clients:
- Inventory System Client
- Procurement System Client
- Telemetry System Client
- Maintenance Log Client
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.external import (
    MockInventoryClient,
    MockProcurementClient,
    MockTelemetryClient,
    MockMaintenanceLogClient,
    ActivityType,
    Outcome
)


def example_inventory_operations():
    """Example: Inventory system operations."""
    print("\n" + "=" * 60)
    print("INVENTORY SYSTEM EXAMPLE")
    print("=" * 60)
    
    # Initialize client
    inventory = MockInventoryClient()
    
    # 1. Search for parts (fuzzy search)
    print("\n1. Searching for power supply parts...")
    results = inventory.search_parts(
        query="power",
        equipment_type="network_switch",
        fuzzy=True
    )
    print(f"   Found {len(results)} parts:")
    for part in results:
        print(f"   - {part['part_number']}: {part['description']} (${part['unit_cost']})")
    
    # 2. Get part details
    print("\n2. Getting details for specific part...")
    part_details = inventory.get_part_details("PWR-C2960X-350WAC")
    if part_details:
        print(f"   Part: {part_details['description']}")
        print(f"   Manufacturer: {part_details['manufacturer']}")
        print(f"   Cost: ${part_details['unit_cost']}")
        print(f"   Available: {part_details['quantity_available']} units")
        print(f"   Location: {part_details['warehouse_location']}")
    
    # 3. Check stock
    print("\n3. Checking stock availability...")
    stock_info = inventory.check_stock("PWR-C2960X-350WAC")
    print(f"   Status: {stock_info['status']}")
    print(f"   Quantity: {stock_info['quantity']}")
    print(f"   Lead time: {stock_info['lead_time_days']} days")
    
    # 4. Reserve part
    print("\n4. Reserving part for repair...")
    reservation = inventory.reserve_part(
        part_number="PWR-C2960X-350WAC",
        quantity=1,
        technician_id="tech-001",
        site_id="site-001"
    )
    if reservation["success"]:
        print(f"   ✅ Reserved: {reservation['reservation_id']}")
        print(f"   Pickup location: {reservation['pickup_location']}")
        print(f"   Expires at: {reservation['expires_at']}")
    else:
        print(f"   ❌ Reservation failed: {reservation['error']}")


def example_procurement_operations():
    """Example: Procurement system operations."""
    print("\n" + "=" * 60)
    print("PROCUREMENT SYSTEM EXAMPLE")
    print("=" * 60)
    
    # Initialize client
    procurement = MockProcurementClient()
    
    # 1. Create purchase order
    print("\n1. Creating purchase order...")
    parts = [
        {
            "part_number": "PWR-C2960X-350WAC",
            "description": "Power Supply",
            "quantity": 1,
            "unit_cost": 450.00
        },
        {
            "part_number": "CAB-ETH-10M",
            "description": "Ethernet Cable",
            "quantity": 2,
            "unit_cost": 15.00
        }
    ]
    
    po = procurement.create_purchase_order(
        parts=parts,
        justification="Emergency repair for network switch failure at Site 001",
        urgency="high",
        site_id="site-001",
        technician_id="tech-001"
    )
    
    print(f"   PO Number: {po['po_number']}")
    print(f"   Total Cost: ${po['total_cost']:.2f}")
    print(f"   Approval Required: {po['approval_level_required']}")
    print(f"   Status: {po['status']}")
    
    # 2. Submit for approval
    print("\n2. Submitting for approval...")
    submission = procurement.submit_for_approval(
        po_number=po['po_number'],
        approver_id="supervisor-001"
    )
    if submission["success"]:
        print(f"   ✅ Submitted to: {submission['approver_id']}")
        print(f"   Status: {submission['status']}")
    
    # 3. Check approval status
    print("\n3. Checking approval status...")
    status = procurement.get_approval_status(po['po_number'])
    if status["success"]:
        print(f"   Status: {status['status']}")
        print(f"   Estimated Delivery: {status['estimated_delivery']}")
    
    # 4. Track shipment
    print("\n4. Tracking shipment...")
    tracking = procurement.track_shipment(po['po_number'])
    if tracking["success"]:
        print(f"   Status: {tracking['status']}")
        if tracking.get("tracking_number"):
            print(f"   Tracking Number: {tracking['tracking_number']}")


def example_telemetry_operations():
    """Example: Telemetry system operations."""
    print("\n" + "=" * 60)
    print("TELEMETRY SYSTEM EXAMPLE")
    print("=" * 60)
    
    # Initialize client
    telemetry = MockTelemetryClient()
    
    # 1. Query metrics
    print("\n1. Querying component metrics...")
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    metrics = telemetry.query_metrics(
        site_id="site-001",
        component_id="switch-001",
        metric_names=["cpu_utilization", "temperature", "memory_utilization"],
        start_time=start_time,
        end_time=end_time
    )
    
    for metric_name, data_points in metrics.items():
        print(f"   {metric_name}: {len(data_points)} data points")
        if data_points:
            latest = data_points[-1]
            print(f"      Latest value: {latest['value']}")
    
    # 2. Get active alerts
    print("\n2. Getting active alerts...")
    alerts = telemetry.get_active_alerts(
        site_id="site-001",
        component_id="switch-001"
    )
    print(f"   Found {len(alerts)} active alerts:")
    for alert in alerts:
        print(f"   - [{alert['severity']}] {alert['message']}")
        print(f"     Metric: {alert['metric']}, Value: {alert['current_value']}")
    
    # 3. Get baseline
    print("\n3. Getting metric baseline...")
    baseline = telemetry.get_baseline(
        site_id="site-001",
        component_id="switch-001",
        metric_name="temperature",
        lookback_days=30
    )
    if baseline["available"]:
        stats = baseline["statistics"]
        print(f"   Mean: {stats['mean']:.2f} {baseline['unit']}")
        print(f"   Std Dev: {stats['std']:.2f}")
        print(f"   P95: {stats['p95']:.2f}")
    
    # 4. Check staleness
    print("\n4. Checking data staleness...")
    staleness = telemetry.check_staleness(
        site_id="site-001",
        component_id="switch-001"
    )
    if staleness["available"]:
        print(f"   Last Update: {staleness['last_update']}")
        print(f"   Age: {staleness['age_minutes']:.2f} minutes")
        print(f"   Is Stale: {staleness['is_stale']}")


def example_maintenance_log_operations():
    """Example: Maintenance log operations."""
    print("\n" + "=" * 60)
    print("MAINTENANCE LOG EXAMPLE")
    print("=" * 60)
    
    # Initialize client
    maintenance = MockMaintenanceLogClient()
    
    # 1. Create maintenance record
    print("\n1. Creating maintenance record...")
    record = maintenance.create_record(
        site_id="site-001",
        component_id="switch-001",
        technician_id="tech-001",
        activity_type=ActivityType.REPAIR,
        description="Replaced failed power supply unit",
        parts_used=[
            {
                "part_number": "PWR-C2960X-350WAC",
                "description": "Power Supply",
                "quantity": 1,
                "unit_cost": 450.00
            }
        ],
        duration_minutes=45,
        outcome=Outcome.SUCCESS
    )
    
    print(f"   Record ID: {record['record_id']}")
    print(f"   Activity: {record['activity_type']}")
    print(f"   Duration: {record['duration_minutes']} minutes")
    print(f"   Parts Cost: ${record['total_parts_cost']:.2f}")
    print(f"   Outcome: {record['outcome']}")
    
    # 2. Update record
    print("\n2. Updating maintenance record...")
    update_result = maintenance.update_record(
        record_id=record['record_id'],
        updates={
            "description": "Replaced failed power supply unit. Also cleaned dust from fans.",
            "duration_minutes": 60
        }
    )
    if update_result["success"]:
        print(f"   ✅ Updated fields: {', '.join(update_result['updated_fields'])}")
    
    # 3. Get maintenance history
    print("\n3. Getting maintenance history...")
    history = maintenance.get_history(
        site_id="site-001",
        limit=10
    )
    print(f"   Found {len(history)} maintenance records:")
    for rec in history:
        print(f"   - {rec['record_id']}: {rec['activity_type']} on {rec['component_id']}")
        print(f"     Outcome: {rec['outcome']}, Duration: {rec['duration_minutes']}min")
    
    # 4. Get audit trail
    print("\n4. Getting audit trail...")
    audit = maintenance.get_audit_trail(record['record_id'])
    print(f"   Found {len(audit)} audit entries:")
    for entry in audit:
        print(f"   - {entry['timestamp']}: {entry['action']} by {entry['user_id']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("EXTERNAL SYSTEMS INTEGRATION EXAMPLES")
    print("=" * 60)
    
    try:
        example_inventory_operations()
        example_procurement_operations()
        example_telemetry_operations()
        example_maintenance_log_operations()
        
        print("\n" + "=" * 60)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
