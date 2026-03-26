"""
Procurement System Client Implementation

Provides concrete implementation of procurement system client with:
- Purchase order creation
- Approval submission
- Status tracking
- Shipment tracking
- Approval workflow integration
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
from .ExternalSystemsAdapter import ProcurementSystemClient

logger = logging.getLogger(__name__)


class POStatus(Enum):
    """Purchase order status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ORDERED = "ordered"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ApprovalLevel(Enum):
    """Approval authority levels based on cost."""
    TECHNICIAN = "technician"  # < $500
    SUPERVISOR = "supervisor"  # $500 - $2000
    MANAGER = "manager"  # $2000 - $5000
    DIRECTOR = "director"  # > $5000


class MockProcurementClient(ProcurementSystemClient):
    """
    Mock implementation of procurement system client for testing and development.
    
    In production, this would be replaced with actual REST API calls.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/procurement",
        api_key: Optional[str] = None
    ):
        """
        Initialize mock procurement client.
        
        Args:
            base_url: Procurement API base URL
            api_key: API key for authentication
        """
        super().__init__(base_url, api_key)
        
        # Mock purchase order database
        self.purchase_orders: Dict[str, Dict[str, Any]] = {}
        self.po_counter = 1000
    
    def _determine_approval_level(self, total_cost: float) -> ApprovalLevel:
        """
        Determine required approval level based on total cost.
        
        Args:
            total_cost: Total purchase order cost
            
        Returns:
            Required approval level
        """
        if total_cost < 500:
            return ApprovalLevel.TECHNICIAN
        elif total_cost < 2000:
            return ApprovalLevel.SUPERVISOR
        elif total_cost < 5000:
            return ApprovalLevel.MANAGER
        else:
            return ApprovalLevel.DIRECTOR
    
    def _calculate_total_cost(self, parts: List[Dict[str, Any]]) -> float:
        """
        Calculate total cost for parts list.
        
        Args:
            parts: List of parts with quantities and unit costs
            
        Returns:
            Total cost
        """
        total = 0.0
        for part in parts:
            quantity = part.get("quantity", 1)
            unit_cost = part.get("unit_cost", 0.0)
            total += quantity * unit_cost
        
        return total
    
    def create_purchase_order(
        self,
        parts: List[Dict[str, Any]],
        justification: str,
        urgency: str,
        site_id: str,
        technician_id: str
    ) -> Dict[str, Any]:
        """
        Create a purchase order.
        
        Args:
            parts: List of parts with quantities
            justification: Reason for purchase
            urgency: Urgency level (low, medium, high, critical)
            site_id: Site ID
            technician_id: Requesting technician ID
            
        Returns:
            Purchase order details
        """
        def _create():
            logger.info(
                f"Creating purchase order: {len(parts)} parts, "
                f"urgency={urgency}, site={site_id}"
            )
            
            # Generate PO number
            po_number = f"PO-{self.po_counter:06d}"
            self.po_counter += 1
            
            # Calculate costs
            total_cost = self._calculate_total_cost(parts)
            
            # Determine approval level
            approval_level = self._determine_approval_level(total_cost)
            
            # Estimate delivery date based on urgency
            delivery_days = {
                "low": 7,
                "medium": 5,
                "high": 3,
                "critical": 1
            }.get(urgency, 7)
            
            estimated_delivery = datetime.now() + timedelta(days=delivery_days)
            
            # Create PO record
            po_data = {
                "po_number": po_number,
                "status": POStatus.DRAFT.value,
                "parts": parts,
                "total_cost": total_cost,
                "justification": justification,
                "urgency": urgency,
                "site_id": site_id,
                "technician_id": technician_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "approval_level_required": approval_level.value,
                "approver_id": None,
                "approved_at": None,
                "estimated_delivery": estimated_delivery.isoformat(),
                "tracking_number": None,
                "shipment_status": None
            }
            
            self.purchase_orders[po_number] = po_data
            
            logger.info(
                f"Created PO {po_number}: ${total_cost:.2f}, "
                f"requires {approval_level.value} approval"
            )
            
            return po_data.copy()
        
        try:
            return self.circuit_breaker.call(_create)
        except Exception as e:
            logger.error(f"PO creation failed: {e}")
            raise
    
    def submit_for_approval(
        self,
        po_number: str,
        approver_id: str
    ) -> Dict[str, Any]:
        """
        Submit purchase order for approval.
        
        Args:
            po_number: Purchase order number
            approver_id: Approver ID
            
        Returns:
            Approval submission details
        """
        def _submit():
            logger.info(f"Submitting PO {po_number} for approval to {approver_id}")
            
            if po_number not in self.purchase_orders:
                return {
                    "success": False,
                    "error": f"Purchase order {po_number} not found"
                }
            
            po_data = self.purchase_orders[po_number]
            
            # Update status
            po_data["status"] = POStatus.PENDING_APPROVAL.value
            po_data["approver_id"] = approver_id
            po_data["submitted_at"] = datetime.now().isoformat()
            po_data["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"PO {po_number} submitted for approval")
            
            return {
                "success": True,
                "po_number": po_number,
                "status": po_data["status"],
                "approver_id": approver_id,
                "submitted_at": po_data["submitted_at"]
            }
        
        try:
            return self.circuit_breaker.call(_submit)
        except Exception as e:
            logger.error(f"PO submission failed: {e}")
            raise
    
    def get_approval_status(self, po_number: str) -> Dict[str, Any]:
        """
        Get approval status for purchase order.
        
        Args:
            po_number: Purchase order number
            
        Returns:
            Approval status details
        """
        def _get_status():
            logger.info(f"Getting approval status for PO {po_number}")
            
            if po_number not in self.purchase_orders:
                return {
                    "success": False,
                    "error": f"Purchase order {po_number} not found"
                }
            
            po_data = self.purchase_orders[po_number]
            
            # Simulate approval process (in real system, this would check actual approval workflow)
            status = po_data["status"]
            
            # Auto-approve low-cost orders for testing
            if (status == POStatus.PENDING_APPROVAL.value and 
                po_data["total_cost"] < 500):
                po_data["status"] = POStatus.APPROVED.value
                po_data["approved_at"] = datetime.now().isoformat()
                po_data["updated_at"] = datetime.now().isoformat()
                status = POStatus.APPROVED.value
                logger.info(f"PO {po_number} auto-approved (low cost)")
            
            return {
                "success": True,
                "po_number": po_number,
                "status": status,
                "total_cost": po_data["total_cost"],
                "approval_level_required": po_data["approval_level_required"],
                "approver_id": po_data.get("approver_id"),
                "submitted_at": po_data.get("submitted_at"),
                "approved_at": po_data.get("approved_at"),
                "estimated_delivery": po_data.get("estimated_delivery")
            }
        
        try:
            return self.circuit_breaker.call(_get_status)
        except Exception as e:
            logger.error(f"Get approval status failed: {e}")
            raise
    
    def track_shipment(self, po_number: str) -> Dict[str, Any]:
        """
        Track shipment for purchase order.
        
        Args:
            po_number: Purchase order number
            
        Returns:
            Shipment tracking details
        """
        def _track():
            logger.info(f"Tracking shipment for PO {po_number}")
            
            if po_number not in self.purchase_orders:
                return {
                    "success": False,
                    "error": f"Purchase order {po_number} not found"
                }
            
            po_data = self.purchase_orders[po_number]
            
            # Simulate shipment tracking
            status = po_data["status"]
            
            if status == POStatus.APPROVED.value:
                # Simulate order placement
                po_data["status"] = POStatus.ORDERED.value
                po_data["ordered_at"] = datetime.now().isoformat()
                po_data["tracking_number"] = f"TRK-{po_number}-{datetime.now().strftime('%Y%m%d')}"
                status = POStatus.ORDERED.value
                logger.info(f"PO {po_number} ordered, tracking number assigned")
            
            tracking_info = {
                "success": True,
                "po_number": po_number,
                "status": status,
                "tracking_number": po_data.get("tracking_number"),
                "estimated_delivery": po_data.get("estimated_delivery"),
                "shipment_events": []
            }
            
            # Add shipment events if tracking number exists
            if po_data.get("tracking_number"):
                tracking_info["shipment_events"] = [
                    {
                        "timestamp": po_data.get("ordered_at"),
                        "status": "Order Placed",
                        "location": "Warehouse"
                    }
                ]
            
            return tracking_info
        
        try:
            return self.circuit_breaker.call(_track)
        except Exception as e:
            logger.error(f"Shipment tracking failed: {e}")
            raise
    
    def approve_purchase_order(
        self,
        po_number: str,
        approver_id: str,
        approved: bool,
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve or reject a purchase order (helper method for testing).
        
        Args:
            po_number: Purchase order number
            approver_id: Approver ID
            approved: True to approve, False to reject
            comments: Optional approval comments
            
        Returns:
            Approval result
        """
        logger.info(
            f"{'Approving' if approved else 'Rejecting'} PO {po_number} "
            f"by {approver_id}"
        )
        
        if po_number not in self.purchase_orders:
            return {
                "success": False,
                "error": f"Purchase order {po_number} not found"
            }
        
        po_data = self.purchase_orders[po_number]
        
        if approved:
            po_data["status"] = POStatus.APPROVED.value
            po_data["approved_at"] = datetime.now().isoformat()
        else:
            po_data["status"] = POStatus.REJECTED.value
            po_data["rejected_at"] = datetime.now().isoformat()
        
        po_data["approver_id"] = approver_id
        po_data["approval_comments"] = comments
        po_data["updated_at"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "po_number": po_number,
            "status": po_data["status"],
            "approver_id": approver_id,
            "approved": approved,
            "comments": comments
        }
