"""
Core domain models for the Autonomous Field Engineer system.
Defines fundamental data structures for sites, components, images, telemetry, and parts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any


class SkillLevel(str, Enum):
    """Technician skill level enumeration."""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SiteType(str, Enum):
    """Site type classification."""
    DATA_CENTER = "data_center"
    OFFICE = "office"
    WAREHOUSE = "warehouse"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"


class CriticalityLevel(str, Enum):
    """Site criticality level determining maximum allowed downtime."""
    TIER1 = "tier1"  # 0 min downtime
    TIER2 = "tier2"  # 15 min downtime
    TIER3 = "tier3"  # 4 hours downtime
    TIER4 = "tier4"  # 24 hours downtime


class SystemStatus(str, Enum):
    """System operational status."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class GeoLocation:
    """Geographic location coordinates."""
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """Validate coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")


@dataclass
class OperatingHours:
    """Site operating hours configuration."""
    start_hour: int  # 0-23
    end_hour: int    # 0-23
    days_of_week: List[int]  # 0=Monday, 6=Sunday
    timezone: str
    
    def __post_init__(self):
        """Validate operating hours."""
        if not 0 <= self.start_hour <= 23:
            raise ValueError(f"Invalid start_hour: {self.start_hour}")
        if not 0 <= self.end_hour <= 23:
            raise ValueError(f"Invalid end_hour: {self.end_hour}")
        if not all(0 <= day <= 6 for day in self.days_of_week):
            raise ValueError(f"Invalid days_of_week: {self.days_of_week}")


@dataclass
class EnvironmentalData:
    """Environmental conditions at the site."""
    temperature_celsius: float
    humidity_percent: float
    air_quality_index: Optional[int] = None
    noise_level_db: Optional[float] = None


@dataclass
class SiteContext:
    """
    Information about the physical location.
    
    Validation Rules:
    - site_id must be valid UUID format
    - criticality_level determines maximum allowed downtime
    """
    site_id: str
    site_name: str
    site_type: SiteType
    location: GeoLocation
    criticality_level: CriticalityLevel
    operating_hours: OperatingHours
    environmental_conditions: EnvironmentalData
    component_id: Optional[str] = None
    component_type: Optional[str] = None
    component_model: Optional[str] = None


@dataclass
class MaintenanceSchedule:
    """Maintenance schedule for a component."""
    frequency_days: int
    last_maintenance: datetime
    next_maintenance: datetime
    maintenance_type: str  # "preventive", "corrective", "predictive"


@dataclass
class Specification:
    """Technical specification key-value pair."""
    name: str
    value: str
    unit: Optional[str] = None


@dataclass
class Component:
    """
    Physical component in the infrastructure.
    """
    component_id: str
    component_type: str
    manufacturer: str
    model_number: str
    serial_number: Optional[str] = None
    installation_date: Optional[datetime] = None
    warranty_expiration: Optional[datetime] = None
    maintenance_schedule: Optional[MaintenanceSchedule] = None


@dataclass
class ImageMetadata:
    """Metadata associated with captured images."""
    device_model: str
    orientation: str  # "portrait", "landscape"
    flash_used: bool = False
    focal_length_mm: Optional[float] = None
    iso: Optional[int] = None
    exposure_time: Optional[float] = None


@dataclass
class ImageData:
    """
    Image data captured from the field.
    
    Validation Rules:
    - resolution must be minimum 1920x1080 for accurate diagnosis
    """
    image_id: str
    raw_image: bytes  # JPEG/PNG binary data
    resolution: Dict[str, int]  # {"width": int, "height": int}
    capture_timestamp: datetime
    capture_location: GeoLocation
    metadata: ImageMetadata
    
    def __post_init__(self):
        """Validate image resolution."""
        width = self.resolution.get("width", 0)
        height = self.resolution.get("height", 0)
        if width < 1920 or height < 1080:
            raise ValueError(
                f"Image resolution {width}x{height} below minimum 1920x1080"
            )


@dataclass
class MetricValue:
    """Single telemetry metric value."""
    value: Any
    unit: str
    timestamp: datetime


@dataclass
class Alert:
    """System alert from telemetry."""
    alert_id: str
    severity: str  # "critical", "high", "medium", "low"
    message: str
    timestamp: datetime
    component_id: Optional[str] = None


@dataclass
class TelemetrySnapshot:
    """
    Real-time telemetry data from site infrastructure.
    
    Validation Rules:
    - timestamp must be within last 5 minutes for real-time analysis
    - Staleness thresholds:
      - 300 seconds (5 min) for CRITICAL operations (electrical, high-voltage)
      - 600 seconds (10 min) for NORMAL operations
    """
    timestamp: datetime
    site_id: str
    metrics: Dict[str, MetricValue]
    alerts: List[Alert]
    system_status: SystemStatus
    
    def is_stale(self, max_age_seconds: int = 600) -> bool:
        """
        Check if telemetry data is stale.
        
        Args:
            max_age_seconds: Maximum age in seconds
                - 300 (5 min) for critical operations (electrical work)
                - 600 (10 min, default) for normal operations
        
        Returns:
            True if data is stale
        """
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > max_age_seconds
    
    def is_stale_for_critical_operation(self) -> bool:
        """
        Check if telemetry is stale for critical operations (5-minute threshold).
        
        Returns:
            True if data is too old for critical operations
        """
        return self.is_stale(max_age_seconds=300)
    
    def get_age_seconds(self) -> float:
        """Get age of telemetry data in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()


@dataclass
class Part:
    """
    Replacement part from inventory.
    
    Validation Rules:
    - part_number must match enterprise inventory system format
    """
    part_number: str
    description: str
    manufacturer: str
    category: str
    unit_cost: float
    quantity_available: int
    warehouse_location: str
    lead_time_days: int
    specifications: List[Specification] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate part data."""
        if self.unit_cost < 0:
            raise ValueError(f"Invalid unit_cost: {self.unit_cost}")
        if self.quantity_available < 0:
            raise ValueError(f"Invalid quantity_available: {self.quantity_available}")
        if self.lead_time_days < 0:
            raise ValueError(f"Invalid lead_time_days: {self.lead_time_days}")


@dataclass
class Tool:
    """Tool required for repair."""
    tool_name: str
    tool_type: str
    required: bool
    alternatives: Optional[List[str]] = None
