"""
Test Weaviate setup and RAG system integration.

This test verifies:
1. Weaviate is running and accessible
2. RAG system can connect to Weaviate
3. Schemas are created correctly
4. Manual ingestion works
5. Reference image ingestion works
6. Semantic search works
7. Image similarity search works
8. Hybrid search works
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag.RAGSystem import RAGSystem
from PIL import Image
import io


@pytest.fixture(scope="module")
def rag_system():
    """Fixture to create and return RAG system instance."""
    print("\n=== Initializing RAG System ===")
    
    rag = RAGSystem(
        weaviate_url="http://localhost:8080",
        use_titan_embeddings=False  # Use local embeddings for testing
    )
    
    print("✅ RAG system initialized")
    yield rag
    
    # Cleanup (optional)
    print("\n=== Cleaning up ===")


def test_weaviate_connection(rag_system):
    """Test 1: Verify Weaviate is running and accessible."""
    print("\n=== Test 1: Weaviate Connection ===")
    
    assert rag_system.client is not None, "Weaviate client not initialized"
    
    # Try to get schema
    schema = rag_system.client.schema.get()
    assert schema is not None, "Could not retrieve schema"
    
    print("✅ Weaviate is running and accessible")


def test_schema_creation(rag_system):
    """Test 2: Verify schemas are created correctly."""
    print("\n=== Test 2: Schema Creation ===")
    
    # Check if ManualSection schema exists
    assert rag_system.client.schema.exists("ManualSection"), "ManualSection schema not found"
    print("✅ ManualSection schema exists")
    
    # Check if ReferenceImage schema exists
    assert rag_system.client.schema.exists("ReferenceImage"), "ReferenceImage schema not found"
    print("✅ ReferenceImage schema exists")
    
    # Get schema details
    schema = rag_system.client.schema.get()
    print(f"✅ Total schemas: {len(schema['classes'])}")


def test_manual_ingestion(rag_system):
    """Test 3: Verify manual ingestion works."""
    print("\n=== Test 3: Manual Ingestion ===")
    
    # Create test manual
    test_manual = {
        "manual_id": "TEST-PYTEST-001",
        "equipment_type": "network_switch",
        "manufacturer": "Cisco",
        "model_number": "Catalyst-2960X",
        "version": "1.0",
        "sections": [
            {
                "section_id": "SEC-PYTEST-001",
                "title": "Installation Guide (Pytest)",
                "content": "This section describes how to install the Cisco Catalyst 2960-X network switch. Ensure power is disconnected before installation."
            },
            {
                "section_id": "SEC-PYTEST-002",
                "title": "Troubleshooting (Pytest)",
                "content": "If the switch does not power on, check the power cable connection and verify the power outlet is working."
            }
        ]
    }
    
    rag_system.ingest_manual(test_manual)
    print(f"✅ Ingested manual with {len(test_manual['sections'])} sections")
    
    # Verify ingestion by checking statistics
    stats = rag_system.get_statistics()
    print(f"✅ Total manual sections in database: {stats['total_manual_sections']}")
    
    assert stats['total_manual_sections'] >= 2, "Manual sections not ingested correctly"


def test_reference_image_ingestion(rag_system):
    """Test 4: Verify reference image ingestion works."""
    print("\n=== Test 4: Reference Image Ingestion ===")
    
    # Create test images (simple colored squares)
    def create_test_image(color):
        img = Image.new('RGB', (100, 100), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()
    
    test_images = [
        {
            "image_id": "IMG-PYTEST-001",
            "equipment_type": "network_switch",
            "view_angle": "front",
            "image_data": create_test_image('red'),
            "annotations": ["power_led", "status_led"]
        },
        {
            "image_id": "IMG-PYTEST-002",
            "equipment_type": "network_switch",
            "view_angle": "rear",
            "image_data": create_test_image('blue'),
            "annotations": ["ethernet_ports", "power_port"]
        }
    ]
    
    rag_system.ingest_reference_images(test_images)
    print(f"✅ Ingested {len(test_images)} reference images")
    
    # Verify ingestion
    stats = rag_system.get_statistics()
    print(f"✅ Total reference images in database: {stats['total_reference_images']}")
    
    assert stats['total_reference_images'] >= 2, "Reference images not ingested correctly"


def test_semantic_search(rag_system):
    """Test 5: Verify semantic search works."""
    print("\n=== Test 5: Semantic Search ===")
    
    # Search for installation-related content
    results = rag_system.retrieve_relevant_sections(
        query="How do I install the network switch?",
        equipment_type="network_switch",
        top_k=5
    )
    
    print(f"✅ Found {len(results)} relevant sections")
    
    if results:
        print(f"✅ Top result: {results[0]['title']}")
        print(f"   Relevance score: {results[0]['relevance_score']:.3f}")
        
        # Verify we got relevant results
        assert len(results) > 0, "No results returned from semantic search"
        assert results[0]['relevance_score'] > 0, "Invalid relevance score"


def test_image_similarity_search(rag_system):
    """Test 6: Verify image similarity search works."""
    print("\n=== Test 6: Image Similarity Search ===")
    
    # Create query image (similar to test images)
    def create_test_image(color):
        img = Image.new('RGB', (100, 100), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()
    
    query_image = create_test_image('red')
    
    results = rag_system.retrieve_similar_images(
        query_image=query_image,
        equipment_type="network_switch",
        top_k=3
    )
    
    print(f"✅ Found {len(results)} similar images")
    
    if results:
        print(f"✅ Top result: {results[0]['image_id']}")
        print(f"   Similarity score: {results[0]['similarity_score']:.3f}")
        
        assert len(results) > 0, "No results returned from image search"
        assert results[0]['similarity_score'] > 0, "Invalid similarity score"


def test_hybrid_search(rag_system):
    """Test 7: Verify hybrid search works."""
    print("\n=== Test 7: Hybrid Search ===")
    
    # Create query image
    def create_test_image(color):
        img = Image.new('RGB', (100, 100), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()
    
    query_image = create_test_image('blue')
    
    results = rag_system.hybrid_search(
        text_query="troubleshooting network switch",
        image_query=query_image,
        equipment_type="network_switch",
        top_k=5
    )
    
    print(f"✅ Found {len(results)} results from hybrid search")
    
    # Count results by source
    text_results = [r for r in results if r.get('source') == 'text']
    image_results = [r for r in results if r.get('source') == 'image']
    
    print(f"   Text results: {len(text_results)}")
    print(f"   Image results: {len(image_results)}")
    
    assert len(results) > 0, "No results returned from hybrid search"


def test_cache_functionality(rag_system):
    """Test 8: Verify query caching works."""
    print("\n=== Test 8: Cache Functionality ===")
    
    # First query (should hit database)
    query = "network switch installation"
    results1 = rag_system.retrieve_relevant_sections(query, top_k=3)
    
    # Second identical query (should hit cache)
    results2 = rag_system.retrieve_relevant_sections(query, top_k=3)
    
    # Verify cache is working
    stats = rag_system.get_statistics()
    print(f"✅ Cache size: {stats['cache_size']}")
    
    assert stats['cache_size'] > 0, "Cache not working"
    assert len(results1) == len(results2), "Cached results differ from original"
    
    # Clear cache
    rag_system.clear_cache()
    stats_after = rag_system.get_statistics()
    print(f"✅ Cache cleared, new size: {stats_after['cache_size']}")
    
    assert stats_after['cache_size'] == 0, "Cache not cleared"


def test_statistics(rag_system):
    """Test 9: Verify statistics reporting works."""
    print("\n=== Test 9: Statistics ===")
    
    stats = rag_system.get_statistics()
    
    print(f"✅ Statistics:")
    print(f"   Total manual sections: {stats['total_manual_sections']}")
    print(f"   Total reference images: {stats['total_reference_images']}")
    print(f"   Total vectors: {stats['total_vectors']}")
    print(f"   Cache size: {stats['cache_size']}")
    
    assert stats['total_vectors'] > 0, "No vectors in database"


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Weaviate Setup and RAG System Integration Tests")
    print("=" * 60)
    
    # Run tests in sequence
    try:
        rag = test_weaviate_connection()
        rag = test_schema_creation(rag)
        rag = test_manual_ingestion(rag)
        rag = test_reference_image_ingestion(rag)
        rag = test_semantic_search(rag)
        rag = test_image_similarity_search(rag)
        rag = test_hybrid_search(rag)
        test_cache_functionality(rag)
        test_statistics(rag)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        sys.exit(1)
