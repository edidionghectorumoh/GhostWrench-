"""
Example usage of RAG System for technical manual retrieval.

This script demonstrates how to ingest technical manuals and perform
semantic search using Amazon Titan Embeddings and Pinecone.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.RAGSystem import RAGSystem


def example_ingest_manual():
    """Example: Ingest a technical manual."""
    print("\n=== Example 1: Ingest Technical Manual ===\n")
    
    # Initialize RAG system (requires Pinecone API key)
    rag = RAGSystem(
        pinecone_api_key="your-pinecone-api-key",
        pinecone_environment="us-east-1-aws",
        index_name="technical-manuals",
    )
    
    # Sample technical manual
    manual = {
        "manual_id": "cisco-switch-2960",
        "equipment_type": "network_switch",
        "manufacturer": "Cisco",
        "model_number": "Catalyst 2960",
        "version": "15.2",
        "sections": [
            {
                "section_id": "sec-001",
                "title": "Power Supply Installation",
                "content": """
                The Catalyst 2960 switch supports redundant power supplies.
                To install a power supply:
                1. Ensure the switch is powered off
                2. Align the power supply with the slot
                3. Slide the power supply into the chassis
                4. Secure with the retention screws
                5. Connect the power cable
                6. Power on the switch
                
                Warning: Always use proper ESD protection when handling components.
                """,
                "images": []
            },
            {
                "section_id": "sec-002",
                "title": "Troubleshooting Power Issues",
                "content": """
                If the power LED is amber or off:
                1. Check power cable connections
                2. Verify power supply is properly seated
                3. Test with a known good power supply
                4. Check for overheating (ensure proper ventilation)
                5. Inspect for physical damage
                
                If issues persist, contact Cisco TAC for support.
                """,
                "images": []
            }
        ]
    }
    
    # Ingest manual
    print("Ingesting manual...")
    rag.ingest_manual(manual)
    print("✓ Manual ingested successfully")
    
    # Get statistics
    stats = rag.get_statistics()
    print(f"\n✓ Total vectors in index: {stats['total_vectors']}")
    print(f"✓ Vector dimension: {stats['dimension']}")


def example_semantic_search():
    """Example: Perform semantic search."""
    print("\n=== Example 2: Semantic Search ===\n")
    
    # Initialize RAG system
    rag = RAGSystem(
        pinecone_api_key="your-pinecone-api-key",
        pinecone_environment="us-east-1-aws",
        index_name="technical-manuals",
    )
    
    # Search query
    query = "How do I fix a power supply that won't turn on?"
    
    print(f"Query: {query}")
    print("\nSearching...")
    
    # Retrieve relevant sections
    results = rag.retrieve_relevant_sections(
        query=query,
        equipment_type="network_switch",
        top_k=3,
    )
    
    print(f"\n✓ Found {len(results)} relevant sections:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Manual: {result['manual_id']}")
        print(f"   Relevance: {result['relevance_score']:.3f}")
        print(f"   Content: {result['content'][:100]}...")
        print()


def example_hybrid_search():
    """Example: Hybrid search with text and image."""
    print("\n=== Example 3: Hybrid Search ===\n")
    
    # Initialize RAG system
    rag = RAGSystem(
        pinecone_api_key="your-pinecone-api-key",
        pinecone_environment="us-east-1-aws",
        index_name="technical-manuals",
    )
    
    # Text query
    text_query = "network switch installation procedure"
    
    print(f"Text Query: {text_query}")
    print("\nPerforming hybrid search...")
    
    # Hybrid search (text only in this example)
    results = rag.hybrid_search(
        text_query=text_query,
        equipment_type="network_switch",
        top_k=5,
    )
    
    print(f"\n✓ Found {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        source = result.get('source', 'unknown')
        title = result.get('title', result.get('image_id', 'N/A'))
        score = result.get('relevance_score', result.get('similarity_score', 0))
        
        print(f"{i}. [{source.upper()}] {title}")
        print(f"   Score: {score:.3f}")
        print()


if __name__ == "__main__":
    print("=" * 70)
    print("RAG System Examples")
    print("Using: Amazon Titan Embeddings + Pinecone")
    print("=" * 70)
    
    print("\nNote: Update the Pinecone API key in the examples to run.")
    print("Get your API key from: https://www.pinecone.io/")
    
    try:
        # Uncomment to run examples (requires valid Pinecone API key)
        # example_ingest_manual()
        # example_semantic_search()
        # example_hybrid_search()
        
        print("\n" + "=" * 70)
        print("✓ Examples ready to run (update API key first)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Pinecone API key is configured")
        print("  2. AWS credentials are set for Titan Embeddings")
        print("  3. Required packages are installed: pip install -r requirements.txt")
        import traceback
        traceback.print_exc()
