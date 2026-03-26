"""
Inventory System Client Implementation

Provides concrete implementation of inventory system client with:
- Part search (exact and fuzzy matching)
- Part details retrieval
- Stock checking
- Part reservation
- Response caching
- Offline fallback with cached data (24-hour window)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from .ExternalSystemsAdapter import InventorySystemClient

logger = logging.getLogger(__name__)


class MockInventoryClient(InventorySystemClient):
    """
    Mock implementation of inventory system client for testing and development.
    
    In production, this would be replaced with actual REST API calls.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/inventory",
        api_key: Optional[str] = None,
        cache_ttl_hours: int = 24
    ):
        """
        Initialize mock inventory client.
        
        Args:
            base_url: Inventory API base URL
            api_key: API key for authentication
            cache_ttl_hours: Cache TTL in hours for offline fallback
        """
        super().__init__(base_url, api_key, cache_ttl_hours)
        
        # Mock inventory database
        self.mock_inventory = self._initialize_mock_inventory()
    
    def _initialize_mock_inventory(self) -> Dict[str, Dict[str, Any]]:
        """Initialize mock inventory with sample parts."""
        return {
            "PWR-C2960X-350WAC": {
                "part_number": "PWR-C2960X-350WAC",
                "description": "Cisco Catalyst 2960-X 350W AC Power Supply",
                "manufacturer": "Cisco",
                "category": "power_supply",
                "equipment_type": "network_switch",
                "unit_cost": 450.00,
                "quantity_available": 15,
                "warehouse_location": "WH-01-A-12",
                "lead_time_days": 2,
                "compatible_models": ["Catalyst-2960X", "Catalyst-2960XR"],
                "specifications": {
                    "power_output": "350W",
                    "voltage": "100-240V AC",
                    "form_factor": "Hot-swappable"
                }
            },
            "SFP-10G-SR": {
                "part_number": "SFP-10G-SR",
                "description": "10GBASE-SR SFP+ Module",
                "manufacturer": "Cisco",
                "category": "transceiver",
                "equipment_type": "network_switch",
                "unit_cost": 850.00,
                "quantity_available": 8,
                "warehouse_location": "WH-01-B-05",
                "lead_time_days": 1,
                "compatible_models": ["Catalyst-2960X", "Nexus-9000"],
                "specifications": {
                    "data_rate": "10Gbps",
                    "wavelength": "850nm",
                    "reach": "300m"
                }
            },
            "CAB-ETH-10M": {
                "part_number": "CAB-ETH-10M",
                "description": "Ethernet Cable Cat6 10m",
                "manufacturer": "Generic",
                "category": "cable",
                "equipment_type": "network",
                "unit_cost": 15.00,
                "quantity_available": 150,
                "warehouse_location": "WH-02-C-20",
                "lead_time_days": 0,
                "compatible_models": ["*"],
                "specifications": {
                    "length": "10m",
                    "category": "Cat6",
                    "shielding": "UTP"
                }
            },
            "FAN-2960X": {
                "part_number": "FAN-2960X",
                "description": "Cisco Catalyst 2960-X Fan Module",
                "manufacturer": "Cisco",
                "category": "cooling",
                "equipment_type": "network_switch",
                "unit_cost": 120.00,
                "quantity_available": 5,
                "warehouse_location": "WH-01-A-15",
                "lead_time_days": 3,
                "compatible_models": ["Catalyst-2960X"],
                "specifications": {
                    "airflow": "Front-to-back",
                    "noise_level": "45dB"
                }
            },
            "MEM-2960X-2GB": {
                "part_number": "MEM-2960X-2GB",
                "description": "2GB DRAM Memory Module for Catalyst 2960-X",
                "manufacturer": "Cisco",
                "category": "memory",
                "equipment_type": "network_switch",
                "unit_cost": 280.00,
                "quantity_available": 0,  # Out of stock
                "warehouse_location": "WH-01-A-18",
                "lead_time_days": 7,
                "compatible_models": ["Catalyst-2960X"],
                "specifications": {
                    "capacity": "2GB",
                    "type": "DDR3"
                }
            }
        }
    
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
        # Check cache first
        cache_key = f"search:{query}:{equipment_type}:{fuzzy}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"Returning cached search results for: {query}")
            return cached
        
        def _search():
            logger.info(f"Searching inventory: query='{query}', equipment_type={equipment_type}, fuzzy={fuzzy}")
            
            results = []
            query_lower = query.lower()
            
            for part_number, part_data in self.mock_inventory.items():
                # Check equipment type filter
                if equipment_type and part_data.get("equipment_type") != equipment_type:
                    continue
                
                # Check if query matches
                if fuzzy:
                    # Fuzzy matching - check if query is substring
                    if (query_lower in part_number.lower() or
                        query_lower in part_data["description"].lower() or
                        query_lower in part_data["category"].lower()):
                        results.append(part_data.copy())
                else:
                    # Exact matching
                    if (query_lower == part_number.lower() or
                        query_lower in part_data["description"].lower()):
                        results.append(part_data.copy())
            
            logger.info(f"Found {len(results)} matching parts")
            return results
        
        try:
            results = self.circuit_breaker.call(_search)
            # Cache results for 1 hour
            self._set_cached(cache_key, results, ttl_seconds=3600)
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Try to return cached results even if expired (offline fallback)
            if cache_key in self.cache:
                logger.warning("Returning stale cached results (offline fallback)")
                return self.cache[cache_key]
            raise
    
    def get_part_details(self, part_number: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a part.
        
        Args:
            part_number: Part number
            
        Returns:
            Part details or None if not found
        """
        # Check cache first
        cache_key = f"part:{part_number}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"Returning cached part details for: {part_number}")
            return cached
        
        def _get_details():
            logger.info(f"Getting part details: {part_number}")
            
            part_data = self.mock_inventory.get(part_number)
            if part_data:
                return part_data.copy()
            
            logger.warning(f"Part not found: {part_number}")
            return None
        
        try:
            result = self.circuit_breaker.call(_get_details)
            if result:
                # Cache for 24 hours (offline fallback window)
                self._set_cached(cache_key, result, ttl_seconds=86400)
            return result
        except Exception as e:
            logger.error(f"Get part details failed: {e}")
            # Try to return cached results even if expired
            if cache_key in self.cache:
                logger.warning("Returning stale cached part details (offline fallback)")
                return self.cache[cache_key]
            raise
    
    def check_stock(self, part_number: str) -> Dict[str, Any]:
        """
        Check stock availability for a part.
        
        Args:
            part_number: Part number
            
        Returns:
            Stock information (quantity, location, lead time)
        """
        def _check():
            logger.info(f"Checking stock for: {part_number}")
            
            part_data = self.mock_inventory.get(part_number)
            if not part_data:
                return {
                    "part_number": part_number,
                    "available": False,
                    "quantity": 0,
                    "location": None,
                    "lead_time_days": None,
                    "status": "not_found"
                }
            
            quantity = part_data["quantity_available"]
            
            return {
                "part_number": part_number,
                "available": quantity > 0,
                "quantity": quantity,
                "location": part_data["warehouse_location"],
                "lead_time_days": part_data["lead_time_days"],
                "status": "in_stock" if quantity > 0 else "out_of_stock",
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            return self.circuit_breaker.call(_check)
        except Exception as e:
            logger.error(f"Stock check failed: {e}")
            raise
    
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
        def _reserve():
            logger.info(
                f"Reserving part: {part_number} x{quantity} "
                f"for technician {technician_id} at site {site_id}"
            )
            
            part_data = self.mock_inventory.get(part_number)
            if not part_data:
                return {
                    "success": False,
                    "error": "Part not found",
                    "reservation_id": None
                }
            
            available = part_data["quantity_available"]
            if available < quantity:
                return {
                    "success": False,
                    "error": f"Insufficient stock (available: {available}, requested: {quantity})",
                    "reservation_id": None,
                    "available_quantity": available
                }
            
            # Update inventory (in real system, this would be atomic transaction)
            part_data["quantity_available"] -= quantity
            
            reservation_id = f"RES-{datetime.now().strftime('%Y%m%d%H%M%S')}-{part_number}"
            
            return {
                "success": True,
                "reservation_id": reservation_id,
                "part_number": part_number,
                "quantity": quantity,
                "technician_id": technician_id,
                "site_id": site_id,
                "reserved_at": datetime.now().isoformat(),
                "expires_at": (datetime.now().replace(hour=23, minute=59, second=59)).isoformat(),
                "pickup_location": part_data["warehouse_location"]
            }
        
        try:
            return self.circuit_breaker.call(_reserve)
        except Exception as e:
            logger.error(f"Part reservation failed: {e}")
            raise
