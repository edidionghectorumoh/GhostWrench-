# Developer Guide: Adding New Equipment Types to RAG System

This guide explains how to add new equipment types and their technical manuals to the Autonomous Field Engineer's RAG (Retrieval-Augmented Generation) system.

## Overview

The RAG system uses Weaviate vector database to store and retrieve:
- Technical manual text sections
- Reference images from manuals
- Equipment specifications
- Repair procedures

## Prerequisites

- Access to the Weaviate instance (default: http://localhost:8080)
- Technical manuals in PDF format
- Reference images (JPEG, PNG)
- Python 3.11+ with required dependencies

## Step 1: Prepare Equipment Documentation

### Manual Format Requirements

Technical manuals should include:
- Equipment specifications
- Installation procedures
- Troubleshooting guides
- Repair procedures
- Safety warnings
- Parts lists

### Image Requirements

Reference images should be:
- High resolution (minimum 1024x768)
- Clear and well-lit
- Labeled with component names
- In JPEG or PNG format

### Recommended Directory Structure

```
equipment_docs/
├── network_switches/
│   ├── cisco_catalyst_2960/
│   │   ├── manual.pdf
│   │   ├── images/
│   │   │   ├── front_panel.jpg
│   │   │   ├── rear_connections.jpg
│   │   │   └── led_indicators.jpg
│   │   └── metadata.json
│   └── juniper_ex2300/
│       ├── manual.pdf
│       ├── images/
│       └── metadata.json
└── power_supplies/
    └── ...
```

### Metadata Format

Create a `metadata.json` file for each equipment type:

```json
{
  "equipment_type": "network_switch",
  "manufacturer": "Cisco",
  "model": "Catalyst 2960",
  "model_number": "WS-C2960-24TT-L",
  "category": "networking",
  "subcategory": "switches",
  "specifications": {
    "ports": 24,
    "power": "AC 100-240V",
    "dimensions": "44 x 445 x 257 mm"
  },
  "common_issues": [
    "port_failure",
    "power_supply_failure",
    "firmware_corruption"
  ],
  "tags": ["cisco", "catalyst", "2960", "24-port", "managed-switch"]
}
```

## Step 2: Ingest Technical Manuals

### Using the RAG System API

```python
from src.rag.RAGSystem import RAGSystem

# Initialize RAG system
rag = RAGSystem(
    weaviate_url="http://localhost:8080",
    use_titan_embeddings=False  # Use local embeddings for development
)

# Ingest manual
result = rag.ingest_manual(
    manual_path="equipment_docs/network_switches/cisco_catalyst_2960/manual.pdf",
    equipment_type="network_switch",
    manufacturer="Cisco",
    model="Catalyst 2960",
    metadata={
        "model_number": "WS-C2960-24TT-L",
        "category": "networking",
        "tags": ["cisco", "catalyst", "2960"]
    }
)

print(f"Ingested {result['sections_processed']} sections")
```

### Using the CLI Tool

```bash
# Ingest a single manual
python scripts/ingest_manual.py \
  --manual equipment_docs/network_switches/cisco_catalyst_2960/manual.pdf \
  --equipment-type network_switch \
  --manufacturer Cisco \
  --model "Catalyst 2960" \
  --metadata equipment_docs/network_switches/cisco_catalyst_2960/metadata.json

# Batch ingest from directory
python scripts/ingest_batch.py \
  --directory equipment_docs/network_switches \
  --recursive
```

## Step 3: Ingest Reference Images

### Using the RAG System API

```python
# Ingest reference images
image_paths = [
    "equipment_docs/network_switches/cisco_catalyst_2960/images/front_panel.jpg",
    "equipment_docs/network_switches/cisco_catalyst_2960/images/rear_connections.jpg",
    "equipment_docs/network_switches/cisco_catalyst_2960/images/led_indicators.jpg"
]

for image_path in image_paths:
    result = rag.ingest_reference_image(
        image_path=image_path,
        equipment_type="network_switch",
        manufacturer="Cisco",
        model="Catalyst 2960",
        description="Front panel view showing ports and LED indicators",
        metadata={
            "view": "front",
            "component": "panel"
        }
    )
    print(f"Ingested image: {result['image_id']}")
```

### Using the CLI Tool

```bash
# Ingest images
python scripts/ingest_images.py \
  --directory equipment_docs/network_switches/cisco_catalyst_2960/images \
  --equipment-type network_switch \
  --manufacturer Cisco \
  --model "Catalyst 2960"
```

## Step 4: Verify Ingestion

### Check Schema

```python
# Verify schema is created
schema_info = rag.get_schema_info()
print(f"Classes: {[c['class'] for c in schema_info['classes']]}")
```

### Test Retrieval

```python
# Test semantic search
results = rag.retrieve_relevant_sections(
    query="How to replace a failed power supply?",
    equipment_type="network_switch",
    manufacturer="Cisco",
    model="Catalyst 2960",
    limit=5
)

for result in results:
    print(f"Section: {result['title']}")
    print(f"Relevance: {result['score']:.2f}")
    print(f"Content: {result['content'][:200]}...")
    print()
```

### Test Image Similarity

```python
# Test image similarity search
similar_images = rag.retrieve_similar_images(
    query_image_path="test_images/switch_front.jpg",
    equipment_type="network_switch",
    limit=3
)

for image in similar_images:
    print(f"Image: {image['image_id']}")
    print(f"Similarity: {image['similarity']:.2f}")
    print(f"Description: {image['description']}")
    print()
```

## Step 5: Update Equipment Type Mappings

### Add to Equipment Type Registry

Edit `src/rag/equipment_types.py`:

```python
EQUIPMENT_TYPES = {
    "network_switch": {
        "category": "networking",
        "common_manufacturers": ["Cisco", "Juniper", "Arista", "HP"],
        "typical_issues": [
            "port_failure",
            "power_supply_failure",
            "firmware_corruption",
            "overheating"
        ],
        "required_ppe": ["ESD wrist strap"],
        "safety_notes": [
            "Power down before servicing",
            "Ensure proper grounding"
        ]
    },
    # Add your new equipment type here
    "ups_system": {
        "category": "power",
        "common_manufacturers": ["APC", "Eaton", "Tripp Lite"],
        "typical_issues": [
            "battery_failure",
            "inverter_failure",
            "overload"
        ],
        "required_ppe": ["Insulated gloves", "Safety glasses"],
        "safety_notes": [
            "High voltage - qualified personnel only",
            "Disconnect from mains before servicing"
        ]
    }
}
```

## Step 6: Test End-to-End

### Create Test Diagnosis Request

```python
from src.orchestration.OrchestrationLayer import OrchestrationLayer
from src.models.agents import FieldRequest, RequestType
from src.models.domain import SiteContext, ImageData

# Initialize orchestration
orchestration = OrchestrationLayer(enable_validation=False)

# Create test request
request = FieldRequest(
    session_id="test-session",
    technician_id="test-tech",
    site_id="test-site",
    request_type=RequestType.DIAGNOSIS,
    site_context=SiteContext(
        site_id="test-site",
        site_name="Test Site",
        site_type="data_center",
        location="Test Location",
        criticality_level="normal",
        operating_hours="24/7",
        environmental_conditions={"temperature": 20},
        component_id="switch-001",
        component_type="network_switch"
    ),
    image_data=ImageData(
        image_id="test-img",
        raw_image=open("test_images/switch_issue.jpg", "rb").read(),
        resolution={"width": 1920, "height": 1080},
        capture_timestamp=datetime.now(),
        capture_location=GeoLocation(latitude=0.0, longitude=0.0),
        metadata=ImageMetadata(device_model="Test", orientation="landscape")
    )
)

# Process request
response = orchestration.process_field_request(request)
print(f"Diagnosis: {response.data}")
```

## Best Practices

### Manual Preparation

1. **Extract text accurately**: Use OCR tools like Tesseract for scanned PDFs
2. **Preserve structure**: Maintain section hierarchy and headings
3. **Include diagrams**: Extract and label all technical diagrams
4. **Add metadata**: Tag sections with relevant keywords

### Image Preparation

1. **Consistent lighting**: Use well-lit, clear images
2. **Multiple angles**: Capture front, rear, side, and detail views
3. **Label components**: Add annotations to identify parts
4. **High resolution**: Minimum 1024x768, prefer 1920x1080 or higher

### Metadata

1. **Comprehensive tags**: Include manufacturer, model, category, common issues
2. **Consistent naming**: Use standardized equipment type names
3. **Version tracking**: Include manual version and date
4. **Cross-references**: Link related equipment types

### Testing

1. **Verify retrieval**: Test with various query types
2. **Check relevance**: Ensure top results are actually relevant
3. **Test edge cases**: Try misspellings, abbreviations, synonyms
4. **Validate images**: Confirm image similarity works correctly

## Troubleshooting

### Manual Not Appearing in Search

1. Check Weaviate connection: `curl http://localhost:8080/v1/.well-known/ready`
2. Verify ingestion completed: Check logs for errors
3. Test with exact equipment type: Use the exact string from metadata
4. Rebuild embeddings: Re-ingest with `--force` flag

### Low Relevance Scores

1. Improve query specificity: Use more detailed queries
2. Add more context: Include equipment type and manufacturer
3. Enrich metadata: Add more tags and keywords
4. Use hybrid search: Combine text and image search

### Image Similarity Not Working

1. Check image format: Ensure JPEG or PNG
2. Verify image size: Should be at least 224x224 pixels
3. Test with reference images: Compare against known good images
4. Check CLIP model: Ensure model is loaded correctly

## Advanced Topics

### Custom Embeddings

For production, use Amazon Titan Embeddings:

```python
rag = RAGSystem(
    weaviate_url="http://localhost:8080",
    use_titan_embeddings=True  # Use AWS Titan
)
```

### Batch Processing

Process multiple manuals efficiently:

```python
import glob

manual_paths = glob.glob("equipment_docs/**/*.pdf", recursive=True)

for manual_path in manual_paths:
    # Extract metadata from path
    parts = manual_path.split('/')
    equipment_type = parts[1]
    model = parts[2]
    
    # Ingest
    rag.ingest_manual(
        manual_path=manual_path,
        equipment_type=equipment_type,
        model=model
    )
```

### Performance Optimization

1. **Batch embeddings**: Process multiple sections at once
2. **Cache results**: Use Redis for frequently accessed manuals
3. **Index optimization**: Tune HNSW parameters for your data size
4. **Parallel processing**: Use multiprocessing for large batches

## Support

For issues or questions:
- Check logs: `docker-compose logs weaviate`
- Review Weaviate docs: https://weaviate.io/developers/weaviate
- Test with smoke test: `python smoke_test.py`
- Contact support: support@example.com
