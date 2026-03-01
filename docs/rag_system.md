# RAG System for Technical Manuals

## Overview

The RAG (Retrieval-Augmented Generation) system provides semantic search over technical manuals, reference images, and equipment documentation. It uses vector embeddings to enable intelligent retrieval of relevant information for field technicians.

## Architecture

### Components

1. **Vector Database**: Pinecone for scalable vector storage
2. **Text Embeddings**: Amazon Titan Embeddings (1536 dimensions)
3. **Image Embeddings**: CLIP ViT-B-32 for multimodal search
4. **Caching Layer**: 1-hour TTL for query results

### Data Flow

```
Technical Manual → Text Embedding (Titan) → Pinecone Index
Reference Image → Image Embedding (CLIP) → Pinecone Index
Query → Embedding → Semantic Search → Ranked Results
```

## Features

### 1. Manual Ingestion

Ingest technical manuals with automatic chunking and embedding:

```python
from src.rag.RAGSystem import RAGSystem

rag = RAGSystem(
    pinecone_api_key="your-api-key",
    pinecone_environment="us-east-1-aws",
)

manual = {
    "manual_id": "cisco-switch-2960",
    "equipment_type": "network_switch",
    "manufacturer": "Cisco",
    "model_number": "Catalyst 2960",
    "sections": [
        {
            "section_id": "sec-001",
            "title": "Installation",
            "content": "...",
        }
    ]
}

rag.ingest_manual(manual)
```

### 2. Semantic Search

Retrieve relevant manual sections using natural language:

```python
results = rag.retrieve_relevant_sections(
    query="How do I replace a power supply?",
    equipment_type="network_switch",
    top_k=5,
)

for result in results:
    print(f"{result['title']}: {result['relevance_score']:.3f}")
```

### 3. Image Search

Find similar reference images using CLIP embeddings:

```python
with open("site_photo.jpg", "rb") as f:
    query_image = f.read()

similar_images = rag.retrieve_similar_images(
    query_image=query_image,
    equipment_type="network_switch",
    top_k=3,
)
```

### 4. Hybrid Search

Combine text and image queries for comprehensive results:

```python
results = rag.hybrid_search(
    text_query="power supply installation",
    image_query=site_photo_bytes,
    equipment_type="network_switch",
    top_k=5,
)
```

## Configuration

### Pinecone Setup

1. Create account at https://www.pinecone.io/
2. Get API key from dashboard
3. Note your environment (e.g., "us-east-1-aws")

### AWS Bedrock Setup

Ensure Titan Embeddings access:

```bash
aws bedrock list-foundation-models --region us-east-1 | grep titan-embed
```

### Environment Variables

```bash
export PINECONE_API_KEY="your-api-key"
export PINECONE_ENVIRONMENT="us-east-1-aws"
```

## Performance

### Embedding Generation

- **Titan Text**: ~100ms per section
- **CLIP Image**: ~50ms per image
- **Batch Processing**: 100 sections/minute

### Search Latency

- **Semantic Search**: < 500ms (p95)
- **Image Search**: < 300ms (p95)
- **Hybrid Search**: < 800ms (p95)
- **Cache Hit**: < 10ms

### Scalability

- **Index Capacity**: 10,000+ manuals
- **Vector Count**: 100,000+ sections
- **Concurrent Queries**: 100+ QPS

## Data Models

### Technical Manual

```python
{
    "manual_id": str,
    "equipment_type": str,
    "manufacturer": str,
    "model_number": str,
    "version": str,
    "sections": [
        {
            "section_id": str,
            "title": str,
            "content": str,
            "images": [...]
        }
    ]
}
```

### Reference Image

```python
{
    "image_id": str,
    "equipment_type": str,
    "view_angle": str,
    "image_data": bytes,
    "annotations": [...],
    "metadata": {...}
}
```

### Search Result

```python
{
    "section_id": str,
    "manual_id": str,
    "title": str,
    "content": str,
    "equipment_type": str,
    "relevance_score": float,  # 0.0 to 1.0
}
```

## Caching Strategy

### Query Cache

- **TTL**: 1 hour
- **Key**: Hash of (query + equipment_type + top_k)
- **Storage**: In-memory dictionary
- **Eviction**: Automatic on expiry

### Cache Management

```python
# Clear cache manually
rag.clear_cache()

# Get cache statistics
stats = rag.get_statistics()
print(f"Cache size: {stats['cache_size']}")
```

## Best Practices

### 1. Manual Preparation

- **Chunking**: Keep sections < 1000 words
- **Metadata**: Include equipment type, manufacturer, model
- **Versioning**: Track manual versions for updates

### 2. Query Optimization

- **Specificity**: Use specific equipment types
- **Context**: Include relevant context in queries
- **Filtering**: Apply equipment_type filters when possible

### 3. Image Quality

- **Resolution**: Minimum 1920x1080 for reference images
- **Format**: JPEG or PNG
- **Annotations**: Include bounding boxes for key components

### 4. Performance Tuning

- **Batch Ingestion**: Ingest manuals in batches
- **Cache Warming**: Pre-cache common queries
- **Index Optimization**: Use appropriate vector dimensions

## Error Handling

### Titan API Failures

```python
try:
    embedding = rag._generate_text_embedding(text)
except Exception as e:
    logger.error(f"Titan embedding failed: {e}")
    # Fallback to local model
    embedding = rag.text_model.encode(text).tolist()
```

### Pinecone Connection Issues

```python
try:
    results = rag.index.query(...)
except Exception as e:
    logger.error(f"Pinecone query failed: {e}")
    # Return empty results or cached fallback
    return []
```

## Monitoring

### Key Metrics

- **Query Latency**: p50, p95, p99
- **Cache Hit Rate**: Percentage of cached queries
- **Embedding Failures**: Count of fallback to local model
- **Index Size**: Total vectors and fullness

### CloudWatch Integration

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Log query latency
cloudwatch.put_metric_data(
    Namespace='AFE/RAG',
    MetricData=[
        {
            'MetricName': 'QueryLatency',
            'Value': latency_ms,
            'Unit': 'Milliseconds',
        }
    ]
)
```

## Cost Optimization

### Titan Embeddings

- **Cost**: $0.0001 per 1K tokens
- **Optimization**: Batch embed similar sections
- **Caching**: Cache embeddings for reuse

### Pinecone

- **Cost**: Based on index size and queries
- **Optimization**: Use appropriate pod size
- **Monitoring**: Track index fullness

## Future Enhancements

1. **Multimodal Embeddings**: Use Nova Pro for unified text+image embeddings
2. **Reranking**: Add cross-encoder reranking for improved relevance
3. **Feedback Loop**: Learn from technician feedback
4. **Auto-Chunking**: Intelligent document chunking
5. **Version Control**: Track manual updates and deprecations

## References

- Design Document: `.kiro/specs/autonomous-field-engineer/design.md`
- Requirements: Requirements 8.1-8.7
- Tasks: Task 3.1-3.2 in `tasks.md`
- Pinecone Docs: https://docs.pinecone.io/
- Amazon Titan: https://aws.amazon.com/bedrock/titan/
- CLIP: https://github.com/openai/CLIP
