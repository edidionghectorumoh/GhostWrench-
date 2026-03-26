"""
External Systems Integration Module

This module provides adapters for external systems:
- Inventory System
- Procurement System
- Telemetry System
- Maintenance Log System
"""

from .ExternalSystemsAdapter import (
    CircuitBreaker,
    CircuitState,
    ExternalSystemClient,
    InventorySystemClient,
    ProcurementSystemClient,
    TelemetrySystemClient,
    MaintenanceLogClient,
)

from .InventoryClient import MockInventoryClient
from .ProcurementClient import MockProcurementClient, POStatus, ApprovalLevel
from .TelemetryClient import MockTelemetryClient, AlertSeverity
from .MaintenanceLogClient import MockMaintenanceLogClient, ActivityType, Outcome

__all__ = [
    'CircuitBreaker',
    'CircuitState',
    'ExternalSystemClient',
    'InventorySystemClient',
    'ProcurementSystemClient',
    'TelemetrySystemClient',
    'MaintenanceLogClient',
    'MockInventoryClient',
    'MockProcurementClient',
    'MockTelemetryClient',
    'MockMaintenanceLogClient',
    'POStatus',
    'ApprovalLevel',
    'AlertSeverity',
    'ActivityType',
    'Outcome',
]
