"""
Maintenance Log Client Implementation

Provides concrete implementation of maintenance log client with:
- Record creation
- Record updates
- History retrieval
- Audit trail integration
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from .ExternalSystemsAdapter import MaintenanceLogClient

logger = logging.getLogger(__name__)


class ActivityType:
    """Maintenance activity types."""
    REPAIR = "repair"
    INSPECTION = "inspection"
    INSTALLATION = "installation"
    REPLACEMENT = "replacement"
    PREVENTIVE_MAINTENANCE = "preventive_maintenance"
    EMERGENCY_REPAIR = "emergency_repair"
    CALIBRATION = "calibration"
    UPGRADE = "upgrade"


class Outcome:
    """Maintenance activity outcomes."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    DEFERRED = "deferred"
    ESCALATED = "escalated"


class MockMaintenanceLogClient(MaintenanceLogClient):
    """
    Mock implementation of maintenance log client for testing and development.
    
    In production, this would be replaced with actual REST API calls.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/maintenance",
        api_key: Optional[str] = None
    ):
        """
        Initialize mock maintenance log client.
        
        Args:
            base_url: Maintenance log API base URL
            api_key: API key for authentication
        """
        super().__init__(base_url, api_key)
        
        # Mock maintenance records database
        self.maintenance_records: Dict[str, Dict[str, Any]] = {}
        self.audit_trails: Dict[str, List[Dict[str, Any]]] = {}
        self.record_counter = 1000
    
    def _add_audit_entry(
        self,
        record_id: str,
        action: str,
        user_id: str,
        changes: Optional[Dict[str, Any]] = None
    ):
        """
        Add audit trail entry for a record.
        
        Args:
            record_id: Record ID
            action: Action performed
            user_id: User who performed action
            changes: Optional changes made
        """
        if record_id not in self.audit_trails:
            self.audit_trails[record_id] = []
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "changes": changes or {}
        }
        
        self.audit_trails[record_id].append(entry)
        logger.debug(f"Added audit entry for {record_id}: {action}")
    
    def create_record(
        self,
        site_id: str,
        component_id: str,
        technician_id: str,
        activity_type: str,
        description: str,
        parts_used: List[Dict[str, Any]],
        duration_minutes: int,
        outcome: str
    ) -> Dict[str, Any]:
        """
        Create a maintenance record.
        
        Args:
            site_id: Site ID
            component_id: Component ID
            technician_id: Technician ID
            activity_type: Type of activity (repair, inspection, etc.)
            description: Activity description
            parts_used: List of parts used
            duration_minutes: Activity duration
            outcome: Outcome (success, partial, failed)
            
        Returns:
            Created record details
        """
        def _create():
            logger.info(
                f"Creating maintenance record: site={site_id}, "
                f"component={component_id}, activity={activity_type}"
            )
            
            # Generate record ID
            record_id = f"MNT-{self.record_counter:06d}"
            self.record_counter += 1
            
            # Calculate total cost of parts
            total_parts_cost = sum(
                part.get("quantity", 1) * part.get("unit_cost", 0.0)
                for part in parts_used
            )
            
            # Create record
            record = {
                "record_id": record_id,
                "site_id": site_id,
                "component_id": component_id,
                "technician_id": technician_id,
                "activity_type": activity_type,
                "description": description,
                "parts_used": parts_used,
                "total_parts_cost": total_parts_cost,
                "duration_minutes": duration_minutes,
                "outcome": outcome,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat() if outcome in [Outcome.SUCCESS, Outcome.FAILED] else None,
                "status": "completed" if outcome in [Outcome.SUCCESS, Outcome.FAILED] else "in_progress"
            }
            
            self.maintenance_records[record_id] = record
            
            # Add audit trail entry
            self._add_audit_entry(
                record_id,
                "created",
                technician_id,
                {"initial_data": record}
            )
            
            logger.info(
                f"Created maintenance record {record_id}: "
                f"{activity_type} on {component_id}, outcome={outcome}"
            )
            
            return record.copy()
        
        try:
            return self.circuit_breaker.call(_create)
        except Exception as e:
            logger.error(f"Record creation failed: {e}")
            raise
    
    def update_record(
        self,
        record_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing maintenance record.
        
        Args:
            record_id: Record ID
            updates: Fields to update
            
        Returns:
            Updated record details
        """
        def _update():
            logger.info(f"Updating maintenance record {record_id}")
            
            if record_id not in self.maintenance_records:
                return {
                    "success": False,
                    "error": f"Record {record_id} not found"
                }
            
            record = self.maintenance_records[record_id]
            
            # Track changes for audit
            changes = {}
            for key, new_value in updates.items():
                if key in record and record[key] != new_value:
                    changes[key] = {
                        "old": record[key],
                        "new": new_value
                    }
                record[key] = new_value
            
            # Update timestamp
            record["updated_at"] = datetime.now().isoformat()
            
            # Add audit trail entry
            technician_id = updates.get("technician_id", record.get("technician_id", "system"))
            self._add_audit_entry(
                record_id,
                "updated",
                technician_id,
                changes
            )
            
            logger.info(f"Updated record {record_id}: {len(changes)} fields changed")
            
            return {
                "success": True,
                "record_id": record_id,
                "updated_fields": list(changes.keys()),
                "record": record.copy()
            }
        
        try:
            return self.circuit_breaker.call(_update)
        except Exception as e:
            logger.error(f"Record update failed: {e}")
            raise
    
    def get_history(
        self,
        site_id: Optional[str] = None,
        component_id: Optional[str] = None,
        technician_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get maintenance history.
        
        Args:
            site_id: Optional site ID filter
            component_id: Optional component ID filter
            technician_id: Optional technician ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum records to return
            
        Returns:
            List of maintenance records
        """
        def _get_history():
            logger.info(
                f"Getting maintenance history: site={site_id}, "
                f"component={component_id}, technician={technician_id}"
            )
            
            # Filter records
            filtered_records = []
            
            for record in self.maintenance_records.values():
                # Apply filters
                if site_id and record["site_id"] != site_id:
                    continue
                
                if component_id and record["component_id"] != component_id:
                    continue
                
                if technician_id and record["technician_id"] != technician_id:
                    continue
                
                # Date filters
                record_date = datetime.fromisoformat(record["created_at"])
                
                if start_date and record_date < start_date:
                    continue
                
                if end_date and record_date > end_date:
                    continue
                
                filtered_records.append(record.copy())
            
            # Sort by created_at descending
            filtered_records.sort(
                key=lambda r: r["created_at"],
                reverse=True
            )
            
            # Apply limit
            filtered_records = filtered_records[:limit]
            
            logger.info(f"Retrieved {len(filtered_records)} maintenance records")
            
            return filtered_records
        
        try:
            return self.circuit_breaker.call(_get_history)
        except Exception as e:
            logger.error(f"Get history failed: {e}")
            raise
    
    def get_audit_trail(self, record_id: str) -> List[Dict[str, Any]]:
        """
        Get audit trail for a maintenance record.
        
        Args:
            record_id: Record ID
            
        Returns:
            List of audit trail entries
        """
        def _get_audit():
            logger.info(f"Getting audit trail for record {record_id}")
            
            if record_id not in self.maintenance_records:
                logger.warning(f"Record not found: {record_id}")
                return []
            
            if record_id not in self.audit_trails:
                logger.warning(f"No audit trail for record: {record_id}")
                return []
            
            audit_entries = self.audit_trails[record_id].copy()
            
            logger.info(f"Retrieved {len(audit_entries)} audit entries")
            
            return audit_entries
        
        try:
            return self.circuit_breaker.call(_get_audit)
        except Exception as e:
            logger.error(f"Get audit trail failed: {e}")
            raise
    
    def get_component_maintenance_summary(
        self,
        component_id: str,
        lookback_days: int = 90
    ) -> Dict[str, Any]:
        """
        Get maintenance summary for a component (helper method).
        
        Args:
            component_id: Component ID
            lookback_days: Days to look back
            
        Returns:
            Maintenance summary statistics
        """
        logger.info(
            f"Getting maintenance summary for component {component_id} "
            f"(last {lookback_days} days)"
        )
        
        start_date = datetime.now() - datetime.timedelta(days=lookback_days)
        
        records = self.get_history(
            component_id=component_id,
            start_date=start_date,
            limit=1000
        )
        
        # Calculate statistics
        total_records = len(records)
        
        activity_counts = {}
        outcome_counts = {}
        total_duration = 0
        total_cost = 0.0
        
        for record in records:
            # Count by activity type
            activity = record["activity_type"]
            activity_counts[activity] = activity_counts.get(activity, 0) + 1
            
            # Count by outcome
            outcome = record["outcome"]
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            
            # Sum duration and cost
            total_duration += record.get("duration_minutes", 0)
            total_cost += record.get("total_parts_cost", 0.0)
        
        return {
            "component_id": component_id,
            "lookback_days": lookback_days,
            "total_maintenance_events": total_records,
            "activity_breakdown": activity_counts,
            "outcome_breakdown": outcome_counts,
            "total_duration_minutes": total_duration,
            "total_parts_cost": total_cost,
            "average_duration_minutes": total_duration / total_records if total_records > 0 else 0,
            "average_cost_per_event": total_cost / total_records if total_records > 0 else 0,
            "calculated_at": datetime.now().isoformat()
        }
