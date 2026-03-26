"""
External Systems Adapter

This module provides adapter interfaces for external systems:
- Inventory System Client
- Procurement System Client
- Telemetry System Client
- Maintenance Log Client

Each client implements:
- Authentication and authorization
- Circuit breaker pattern for resilience
- Data transformation between system-specific and agent formats
- Retry logic with exponential backoff
- Response caching
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for resilience.
    
    Prevents cascading failures by:
    - Opening circuit after threshold failures
    - Rejecting requests when open
    - Testing recovery in half-open state
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before testing recovery
            success_threshold: Successes needed in half-open to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.timeout_seconds
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")


class ExternalSystemClient(ABC):
    """
    Base class for external system clients.
    
    Provides common functionality:
    - Circuit breaker
    - Authentication
    - Retry logic
    - Caching
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize external system client.
        
        Args:
            base_url: Base URL for API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.circuit_breaker = CircuitBreaker()
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with external system.
        
        Returns:
            True if authentication successful
        """
        pass
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key in self.cache:
            if key in self.cache_ttl:
                if datetime.now() < self.cache_ttl[key]:
                    logger.debug(f"Cache hit: {key}")
                    return self.cache[key]
                else:
                    # Expired
                    del self.cache[key]
                    del self.cache_ttl[key]
        return None
    
    def _set_cached(self, key: str, value: Any, ttl_seconds: int = 3600):
        """
        Set cached value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        self.cache[key] = value
        self.cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
        logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Retry function with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
        
        raise last_exception


class InventorySystemClient(ExternalSystemClient):
    """
    Client for inventory database system.
    
    Provides:
    - Part search (exact and fuzzy)
    - Part details retrieval
    - Stock checking
    - Part reservation
    - Response caching
    - Offline fallback with cached data
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        cache_ttl_hours: int = 24
    ):
        """
        Initialize inventory system client.
        
        Args:
            base_url: Inventory API base URL
            api_key: API key for authentication
            cache_ttl_hours: Cache TTL in hours for offline fallback
        """
        super().__init__(base_url, api_key)
        self.cache_ttl_hours = cache_ttl_hours
    
    def authenticate(self) -> bool:
        """Authenticate with inventory system."""
        # Implementation would use actual auth mechanism
        logger.info("Authenticating with inventory system")
        return True
    
    @abstractmethod
    def search_parts(
        self,
        query: str,
        equipment_type: Optional[str] = None,
        fuzzy: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for parts in inventory.
        
        Args:
            query: Search query (part number, description, etc.)
            equipment_type: Filter by equipment type
            fuzzy: Enable fuzzy matching
            
        Returns:
            List of matching parts
        """
        pass
    
    @abstractmethod
    def get_part_details(self, part_number: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a part.
        
        Args:
            part_number: Part number
            
        Returns:
            Part details or None if not found
        """
        pass
    
    @abstractmethod
    def check_stock(self, part_number: str) -> Dict[str, Any]:
        """
        Check stock availability for a part.
        
        Args:
            part_number: Part number
            
        Returns:
            Stock information (quantity, location, lead time)
        """
        pass
    
    @abstractmethod
    def reserve_part(
        self,
        part_number: str,
        quantity: int,
        technician_id: str,
        site_id: str
    ) -> Dict[str, Any]:
        """
        Reserve parts for a repair.
        
        Args:
            part_number: Part number
            quantity: Quantity to reserve
            technician_id: Technician ID
            site_id: Site ID
            
        Returns:
            Reservation details
        """
        pass


class ProcurementSystemClient(ExternalSystemClient):
    """
    Client for procurement system.
    
    Provides:
    - Purchase order creation
    - Approval submission
    - Status tracking
    - Shipment tracking
    """
    
    def authenticate(self) -> bool:
        """Authenticate with procurement system."""
        logger.info("Authenticating with procurement system")
        return True
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_approval_status(self, po_number: str) -> Dict[str, Any]:
        """
        Get approval status for purchase order.
        
        Args:
            po_number: Purchase order number
            
        Returns:
            Approval status details
        """
        pass
    
    @abstractmethod
    def track_shipment(self, po_number: str) -> Dict[str, Any]:
        """
        Track shipment for purchase order.
        
        Args:
            po_number: Purchase order number
            
        Returns:
            Shipment tracking details
        """
        pass


class TelemetrySystemClient(ExternalSystemClient):
    """
    Client for telemetry/monitoring system.
    
    Provides:
    - Metric queries
    - Alert retrieval
    - Historical baseline queries
    - Staleness detection
    """
    
    def authenticate(self) -> bool:
        """Authenticate with telemetry system."""
        logger.info("Authenticating with telemetry system")
        return True
    
    @abstractmethod
    def query_metrics(
        self,
        site_id: str,
        component_id: str,
        metric_names: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query metrics for a component.
        
        Args:
            site_id: Site ID
            component_id: Component ID
            metric_names: List of metric names
            start_time: Start time for query
            end_time: End time for query
            
        Returns:
            Metrics data by metric name
        """
        pass
    
    @abstractmethod
    def get_active_alerts(
        self,
        site_id: str,
        component_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active alerts for site or component.
        
        Args:
            site_id: Site ID
            component_id: Optional component ID filter
            
        Returns:
            List of active alerts
        """
        pass
    
    @abstractmethod
    def get_baseline(
        self,
        site_id: str,
        component_id: str,
        metric_name: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get historical baseline for a metric.
        
        Args:
            site_id: Site ID
            component_id: Component ID
            metric_name: Metric name
            lookback_days: Days to look back for baseline
            
        Returns:
            Baseline statistics (mean, std, percentiles)
        """
        pass
    
    @abstractmethod
    def check_staleness(
        self,
        site_id: str,
        component_id: str
    ) -> Dict[str, Any]:
        """
        Check if telemetry data is stale.
        
        Args:
            site_id: Site ID
            component_id: Component ID
            
        Returns:
            Staleness information (last_update, is_stale)
        """
        pass


class MaintenanceLogClient(ExternalSystemClient):
    """
    Client for maintenance records system.
    
    Provides:
    - Record creation
    - Record updates
    - History retrieval
    - Audit trail integration
    """
    
    def authenticate(self) -> bool:
        """Authenticate with maintenance log system."""
        logger.info("Authenticating with maintenance log system")
        return True
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_audit_trail(self, record_id: str) -> List[Dict[str, Any]]:
        """
        Get audit trail for a maintenance record.
        
        Args:
            record_id: Record ID
            
        Returns:
            List of audit trail entries
        """
        pass
