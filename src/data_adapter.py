"""
Data adapter layer for abstracting data source access.
Enables seamless switching between synthetic and real ArcGIS API data.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class ResourceDocument:
    """Unified document format for RAG pipeline"""
    id: str
    content: str
    metadata: Dict[str, any]
    embedding: Optional[List[float]] = None
    
    def get_citation(self) -> Dict[str, str]:
        """Extract citation information"""
        return {
            "source_url": self.metadata.get("source_url", ""),
            "policy_reference": self.metadata.get("policy_reference", ""),
            "sr_id": self.id
        }
    
    def get_location(self) -> tuple:
        """Extract lat/long for map visualization"""
        return (self.metadata.get("Lat"), self.metadata.get("Long"))


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    def fetch_all(self) -> List[ResourceDocument]:
        """Fetch all available resources"""
        pass
    
    @abstractmethod
    def fetch_by_filter(self, filters: Dict[str, any]) -> List[ResourceDocument]:
        """Fetch resources matching filters"""
        pass
    
    @abstractmethod
    def get_metadata_schema(self) -> Dict[str, type]:
        """Return metadata schema for this source"""
        pass


class SyntheticDataSource(DataSource):
    """Loads synthetic data from JSON file"""
    
    def __init__(self, filepath: str = "data/resources.json"):
        self.filepath = filepath
        self._data: Optional[List[Dict]] = None
    
    def _load_data(self) -> List[Dict]:
        """Load data from JSON file"""
        if self._data is None:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        return self._data
    
    def fetch_all(self) -> List[ResourceDocument]:
        """Fetch all synthetic resources"""
        data = self._load_data()
        return [self._to_resource_document(record) for record in data]
    
    def fetch_by_filter(self, filters: Dict[str, any]) -> List[ResourceDocument]:
        """Fetch resources matching filters"""
        data = self._load_data()
        filtered = []
        
        for record in data:
            if self._matches_filters(record, filters):
                filtered.append(self._to_resource_document(record))
        
        return filtered
    
    def _matches_filters(self, record: Dict, filters: Dict[str, any]) -> bool:
        """Check if record matches all filter criteria"""
        for key, value in filters.items():
            if key not in record:
                return False
            if isinstance(value, list):
                if record[key] not in value:
                    return False
            else:
                if record[key] != value:
                    return False
        return True
    
    def _to_resource_document(self, record: Dict) -> ResourceDocument:
        """Convert JSON record to ResourceDocument"""
        content = f"{record['Subject']} - {record['Department']} - {record['neighborhood']}"
        
        return ResourceDocument(
            id=record['SR_ID'],
            content=content,
            metadata=record,
            embedding=None
        )
    
    def get_metadata_schema(self) -> Dict[str, type]:
        """Return metadata schema for synthetic data"""
        return {
            "SR_ID": str,
            "Subject": str,
            "Department": str,
            "Lat": float,
            "Long": float,
            "Status": str,
            "Urgency_Score": int,
            "neighborhood": str,
            "timestamp": str,
            "language_preference": str,
            "source_url": str,
            "policy_reference": str
        }


class ArcGISDataSource(DataSource):
    """Future: Connects to Montgomery County ArcGIS API"""
    
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
    
    def fetch_all(self) -> List[ResourceDocument]:
        """Fetch all resources from ArcGIS API"""
        raise NotImplementedError("ArcGIS integration coming in Phase 2")
    
    def fetch_by_filter(self, filters: Dict[str, any]) -> List[ResourceDocument]:
        """Fetch filtered resources from ArcGIS API"""
        raise NotImplementedError("ArcGIS integration coming in Phase 2")
    
    def get_metadata_schema(self) -> Dict[str, type]:
        """Return metadata schema for ArcGIS data"""
        raise NotImplementedError("ArcGIS integration coming in Phase 2")


class DataAdapter:
    """Facade for data source management"""
    
    def __init__(self, source: DataSource):
        self.source = source
    
    def get_documents(self, filters: Optional[Dict] = None) -> List[ResourceDocument]:
        """Get documents with optional filtering"""
        if filters:
            return self.source.fetch_by_filter(filters)
        return self.source.fetch_all()
    
    def switch_source(self, new_source: DataSource) -> None:
        """Hot-swap data source without restarting application"""
        self.source = new_source
        print(f"✓ Switched to data source: {new_source.__class__.__name__}")
