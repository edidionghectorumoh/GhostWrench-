"""
Synthetic data generator for Montgomery County 311 Service Requests.
Generates realistic test data with enhanced fields for RAG pipeline testing.
"""

import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path


@dataclass
class ServiceRequest:
    """Represents a single 311 service request record"""
    SR_ID: str
    Subject: str
    Department: str
    Lat: float
    Long: float
    Status: str
    Urgency_Score: int
    neighborhood: str
    timestamp: str
    language_preference: str
    source_url: str
    policy_reference: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class SyntheticDataGenerator:
    """Generates synthetic service request data for prototype"""
    
    # Montgomery County geographic bounds
    LAT_MIN, LAT_MAX = 39.0, 39.3
    LONG_MIN, LONG_MAX = -77.5, -76.9
    
    DEPARTMENTS = ["HHS", "DHCA", "Police", "Fire", "Transportation", "Environmental Protection"]
    NEIGHBORHOODS = [
        "Silver Spring", "Bethesda", "Rockville", "Wheaton", 
        "Germantown", "Gaithersburg", "Takoma Park", "Potomac"
    ]
    LANGUAGES = ["English", "Spanish", "Amharic"]
    STATUSES = ["Open", "In Progress", "Closed", "Resolved"]
    
    # Subject templates by department
    SUBJECT_TEMPLATES = {
        "HHS": [
            "SNAP eligibility inquiry",
            "Food assistance application",
            "Emergency shelter request",
            "Mental health services referral",
            "Child care subsidy question"
        ],
        "DHCA": [
            "Rental assistance application",
            "Housing voucher inquiry",
            "Landlord-tenant dispute",
            "Affordable housing waitlist",
            "Utility assistance request"
        ],
        "Police": [
            "Non-emergency incident report",
            "Community safety concern",
            "Traffic violation report",
            "Noise complaint",
            "Parking enforcement request"
        ],
        "Fire": [
            "Fire safety inspection",
            "Smoke detector installation",
            "Emergency preparedness training",
            "Hazmat concern report"
        ],
        "Transportation": [
            "Pothole repair request",
            "Street light outage",
            "Sidewalk maintenance",
            "Bus route inquiry",
            "Traffic signal issue"
        ],
        "Environmental Protection": [
            "Recycling program inquiry",
            "Illegal dumping report",
            "Water quality concern",
            "Tree removal request",
            "Stormwater management issue"
        ]
    }
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed for reproducibility"""
        random.seed(seed)
        self.generated_requests: List[ServiceRequest] = []
    
    def generate_service_requests(self, count: int = 50) -> List[ServiceRequest]:
        """Generate specified number of synthetic service requests"""
        requests = []
        
        for i in range(count):
            sr_id = f"SR-2024-{i+1:05d}"
            department = random.choice(self.DEPARTMENTS)
            neighborhood = random.choice(self.NEIGHBORHOODS)
            
            # Generate realistic subject
            subject = random.choice(self.SUBJECT_TEMPLATES[department])
            
            # Generate coordinates within MoCo bounds
            lat = round(random.uniform(self.LAT_MIN, self.LAT_MAX), 6)
            long = round(random.uniform(self.LONG_MIN, self.LONG_MAX), 6)
            
            # Weighted urgency distribution (more low-medium urgency)
            urgency = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                weights=[5, 10, 15, 20, 20, 15, 8, 4, 2, 1]
            )[0]
            
            # Generate timestamp within last 90 days
            days_back = random.randint(0, 90)
            timestamp = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            # Status distribution
            status = random.choice(self.STATUSES)
            
            # Language preference
            language = random.choice(self.LANGUAGES)
            
            # Generate citation fields
            source_url = f"https://data.montgomerycountymd.gov/resource/{sr_id}"
            policy_reference = self._generate_policy_reference(department)
            
            request = ServiceRequest(
                SR_ID=sr_id,
                Subject=subject,
                Department=department,
                Lat=lat,
                Long=long,
                Status=status,
                Urgency_Score=urgency,
                neighborhood=neighborhood,
                timestamp=timestamp,
                language_preference=language,
                source_url=source_url,
                policy_reference=policy_reference
            )
            
            requests.append(request)
        
        self.generated_requests = requests
        return requests
    
    def _generate_policy_reference(self, department: str) -> str:
        """Generate realistic policy reference based on department"""
        policy_map = {
            "HHS": "Montgomery County Code § 27-70: Human Services",
            "DHCA": "Maryland Housing Code § 4-101: Rental Housing",
            "Police": "Montgomery County Code § 35: Public Safety",
            "Fire": "Maryland Fire Code § 9-101: Fire Prevention",
            "Transportation": "Montgomery County Code § 49: Streets and Roads",
            "Environmental Protection": "Montgomery County Code § 48: Environmental Protection"
        }
        return policy_map.get(department, "Montgomery County Code § 1: General Provisions")
    
    def save_to_json(self, requests: List[ServiceRequest], filepath: str) -> None:
        """Save generated requests to JSON file"""
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        data = [req.to_dict() for req in requests]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Generated {len(requests)} synthetic service requests → {filepath}")
    
    def get_department_distribution(self) -> Dict[str, int]:
        """Return distribution of requests across departments"""
        distribution = {}
        for req in self.generated_requests:
            distribution[req.Department] = distribution.get(req.Department, 0) + 1
        return distribution


if __name__ == "__main__":
    # Generate synthetic data
    generator = SyntheticDataGenerator(seed=42)
    requests = generator.generate_service_requests(count=50)
    
    # Save to file
    generator.save_to_json(requests, filepath="data/resources.json")
    
    # Display distribution
    distribution = generator.get_department_distribution()
    print("\nDepartment Distribution:")
    for dept, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dept}: {count}")
