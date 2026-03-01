"""
Telemetry System Client Implementation

Provides concrete implementation of telemetry system client with:
- Metric queries
- Alert retrieval
- Historical baseline queries
- Staleness detection
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
import logging
from .ExternalSystemsAdapter import TelemetrySystemClient

logger = logging.getLogger(__name__)


class AlertSeverity:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MockTelemetryClient(TelemetrySystemClient):
    """
    Mock implementation of telemetry system client for testing and development.
    
    In production, this would be replaced with actual time-series database queries.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/telemetry",
        api_key: Optional[str] = None
    ):
        """
        Initialize mock telemetry client.
        
        Args:
            base_url: Telemetry API base URL
            api_key: API key for authentication
        """
        super().__init__(base_url, api_key)
        
        # Mock telemetry data
        self.mock_metrics = self._initialize_mock_metrics()
        self.mock_alerts = self._initialize_mock_alerts()
    
    def _initialize_mock_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Initialize mock telemetry metrics."""
        return {
            "site-001": {
                "switch-001": {
                    "cpu_utilization": {
                        "current": 45.2,
                        "baseline_mean": 35.0,
                        "baseline_std": 8.5,
                        "unit": "percent",
                        "last_updated": datetime.now().isoformat()
                    },
                    "memory_utilization": {
                        "current": 62.8,
                        "baseline_mean": 55.0,
                        "baseline_std": 10.2,
                        "unit": "percent",
                        "last_updated": datetime.now().isoformat()
                    },
                    "temperature": {
                        "current": 48.5,
                        "baseline_mean": 42.0,
                        "baseline_std": 3.5,
                        "unit": "celsius",
                        "last_updated": datetime.now().isoformat()
                    },
                    "power_draw": {
                        "current": 285.0,
                        "baseline_mean": 275.0,
                        "baseline_std": 15.0,
                        "unit": "watts",
                        "last_updated": datetime.now().isoformat()
                    },
                    "packet_loss": {
                        "current": 0.02,
                        "baseline_mean": 0.01,
                        "baseline_std": 0.005,
                        "unit": "percent",
                        "last_updated": datetime.now().isoformat()
                    },
                    "link_status": {
                        "current": "up",
                        "baseline_mean": None,
                        "baseline_std": None,
                        "unit": "status",
                        "last_updated": datetime.now().isoformat()
                    }
                }
            }
        }
    
    def _initialize_mock_alerts(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize mock alerts."""
        return {
            "site-001": [
                {
                    "alert_id": "ALT-001",
                    "component_id": "switch-001",
                    "severity": AlertSeverity.WARNING,
                    "metric": "temperature",
                    "message": "Temperature above baseline threshold",
                    "current_value": 48.5,
                    "threshold": 45.0,
                    "triggered_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
                    "acknowledged": False
                }
            ]
        }
    
    def _generate_historical_data(
        self,
        metric_name: str,
        baseline_mean: float,
        baseline_std: float,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate mock historical data points.
        
        Args:
            metric_name: Metric name
            baseline_mean: Baseline mean value
            baseline_std: Baseline standard deviation
            start_time: Start time
            end_time: End time
            interval_minutes: Interval between data points
            
        Returns:
            List of data points
        """
        data_points = []
        current_time = start_time
        
        while current_time <= end_time:
            # Generate value with some randomness around baseline
            value = random.gauss(baseline_mean, baseline_std)
            
            data_points.append({
                "timestamp": current_time.isoformat(),
                "value": round(value, 2),
                "metric": metric_name
            })
            
            current_time += timedelta(minutes=interval_minutes)
        
        return data_points
    
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
        def _query():
            logger.info(
                f"Querying metrics: site={site_id}, component={component_id}, "
                f"metrics={metric_names}, time_range={start_time} to {end_time}"
            )
            
            # Check if site and component exist
            if site_id not in self.mock_metrics:
                logger.warning(f"Site not found: {site_id}")
                return {}
            
            if component_id not in self.mock_metrics[site_id]:
                logger.warning(f"Component not found: {component_id}")
                return {}
            
            component_metrics = self.mock_metrics[site_id][component_id]
            results = {}
            
            for metric_name in metric_names:
                if metric_name not in component_metrics:
                    logger.warning(f"Metric not found: {metric_name}")
                    results[metric_name] = []
                    continue
                
                metric_data = component_metrics[metric_name]
                
                # Generate historical data
                if metric_data["baseline_mean"] is not None:
                    data_points = self._generate_historical_data(
                        metric_name,
                        metric_data["baseline_mean"],
                        metric_data["baseline_std"],
                        start_time,
                        end_time
                    )
                    results[metric_name] = data_points
                else:
                    # For non-numeric metrics, return current value
                    results[metric_name] = [{
                        "timestamp": metric_data["last_updated"],
                        "value": metric_data["current"],
                        "metric": metric_name
                    }]
            
            logger.info(f"Retrieved metrics for {len(results)} metric types")
            return results
        
        try:
            return self.circuit_breaker.call(_query)
        except Exception as e:
            logger.error(f"Metric query failed: {e}")
            raise
    
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
        def _get_alerts():
            logger.info(
                f"Getting active alerts: site={site_id}, component={component_id}"
            )
            
            if site_id not in self.mock_alerts:
                logger.warning(f"No alerts for site: {site_id}")
                return []
            
            alerts = self.mock_alerts[site_id]
            
            # Filter by component if specified
            if component_id:
                alerts = [
                    alert for alert in alerts
                    if alert["component_id"] == component_id
                ]
            
            # Filter only active (not acknowledged) alerts
            active_alerts = [
                alert for alert in alerts
                if not alert.get("acknowledged", False)
            ]
            
            logger.info(f"Found {len(active_alerts)} active alerts")
            return active_alerts
        
        try:
            return self.circuit_breaker.call(_get_alerts)
        except Exception as e:
            logger.error(f"Get alerts failed: {e}")
            raise
    
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
        def _get_baseline():
            logger.info(
                f"Getting baseline: site={site_id}, component={component_id}, "
                f"metric={metric_name}, lookback={lookback_days} days"
            )
            
            # Check if metric exists
            if (site_id not in self.mock_metrics or
                component_id not in self.mock_metrics[site_id] or
                metric_name not in self.mock_metrics[site_id][component_id]):
                logger.warning(f"Metric not found: {metric_name}")
                return {
                    "metric": metric_name,
                    "available": False,
                    "error": "Metric not found"
                }
            
            metric_data = self.mock_metrics[site_id][component_id][metric_name]
            
            if metric_data["baseline_mean"] is None:
                return {
                    "metric": metric_name,
                    "available": False,
                    "error": "No baseline available for non-numeric metric"
                }
            
            # Calculate percentiles (simulated)
            mean = metric_data["baseline_mean"]
            std = metric_data["baseline_std"]
            
            return {
                "metric": metric_name,
                "available": True,
                "lookback_days": lookback_days,
                "statistics": {
                    "mean": mean,
                    "std": std,
                    "min": mean - 2 * std,
                    "max": mean + 2 * std,
                    "p50": mean,
                    "p95": mean + 1.645 * std,
                    "p99": mean + 2.326 * std
                },
                "unit": metric_data["unit"],
                "sample_count": lookback_days * 288,  # 5-min intervals
                "calculated_at": datetime.now().isoformat()
            }
        
        try:
            return self.circuit_breaker.call(_get_baseline)
        except Exception as e:
            logger.error(f"Get baseline failed: {e}")
            raise
    
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
        def _check():
            logger.info(
                f"Checking staleness: site={site_id}, component={component_id}"
            )
            
            if (site_id not in self.mock_metrics or
                component_id not in self.mock_metrics[site_id]):
                return {
                    "component_id": component_id,
                    "available": False,
                    "error": "Component not found"
                }
            
            component_metrics = self.mock_metrics[site_id][component_id]
            
            # Get most recent update time across all metrics
            last_updates = [
                datetime.fromisoformat(metric["last_updated"])
                for metric in component_metrics.values()
                if "last_updated" in metric
            ]
            
            if not last_updates:
                return {
                    "component_id": component_id,
                    "available": False,
                    "error": "No metrics available"
                }
            
            most_recent = max(last_updates)
            age_minutes = (datetime.now() - most_recent).total_seconds() / 60
            
            # Consider stale if > 10 minutes old
            is_stale = age_minutes > 10
            
            return {
                "component_id": component_id,
                "available": True,
                "last_update": most_recent.isoformat(),
                "age_minutes": round(age_minutes, 2),
                "is_stale": is_stale,
                "staleness_threshold_minutes": 10,
                "checked_at": datetime.now().isoformat()
            }
        
        try:
            return self.circuit_breaker.call(_check)
        except Exception as e:
            logger.error(f"Staleness check failed: {e}")
            raise
