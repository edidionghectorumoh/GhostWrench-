"""
RAG Pipeline Module for Policy Co-pilot.
Orchestrates retrieval-augmented generation with ChromaDB and Gemini.
"""

import os
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

import chromadb
from chromadb.config import Settings
import google.generativeai as genai

from data_adapter import DataAdapter, ResourceDocument

# Load environment variables
load_dotenv()


@dataclass
class Citation:
    """Citation for a source document"""
    sr_id: str
    source_url: str
    policy_reference: str
    relevance_score: float


@dataclass
class RAGResponse:
    """Response from RAG pipeline"""
    query: str
    answer: str
    citations: List[Citation]
    confidence: float
    mode: str
    processing_time_ms: int
    
    def has_valid_citations(self) -> bool:
        """Verify 100% citation requirement"""
        return len(self.citations) > 0 and all(
            c.source_url and c.policy_reference for c in self.citations
        )
    
    def format_for_display(self) -> str:
        """Format response with citations for UI display"""
        formatted = f"{self.answer}\n\n**Sources:**\n"
        for i, citation in enumerate(self.citations, 1):
            formatted += f"{i}. [{citation.sr_id}]({citation.source_url}) - {citation.policy_reference}\n"
        return formatted


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline"""
    
    def __init__(
        self,
        data_adapter: DataAdapter,
        collection_name: str = "moco_resources",
        embedding_model: str = "models/embedding-001"
    ):
        self.data_adapter = data_adapter
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.collection: Optional[chromadb.Collection] = None
        
        # Initialize Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            print("✓ Gemini API configured")
        else:
            print("⚠ GEMINI_API_KEY not found in environment")
    
    def initialize_vector_store(self) -> None:
        """Create or load ChromaDB collection and index documents"""
        # Initialize ChromaDB client
        client = chromadb.Client(Settings(
            persist_directory="./chroma_db",
            anonymized_telemetry=False
        ))
        
        # Delete existing collection if it exists
        try:
            client.delete_collection(name=self.collection_name)
            print(f"✓ Deleted old collection: {self.collection_name}")
        except:
            pass
        
        # Create new collection with default embedding function (sentence transformers)
        self.collection = client.create_collection(
            name=self.collection_name,
            metadata={"description": "Montgomery County service requests"}
        )
        print(f"✓ Created new collection: {self.collection_name}")
        
        # Fetch and index documents
        documents = self.data_adapter.get_documents()
        if not documents:
            print("⚠ No documents to index")
            return
        
        # Prepare batch data (ChromaDB will auto-generate embeddings)
        ids = [doc.id for doc in documents]
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # Add to collection (ChromaDB handles embeddings automatically)
        self.collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas
        )
        
        count = self.collection.count()
        print(f"✓ Indexed {count} documents in vector store")
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for user query using Gemini"""
        try:
            result = genai.embed_content(
                model="embedding-001",  # Without "models/" prefix
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            print(f"⚠ Embedding generation failed: {e}")
            # Return zero vector as fallback (768 dimensions)
            return [0.0] * 768
    
    def retrieve_context(
        self,
        query: str,  # Changed from query_embedding to query
        k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[ResourceDocument]:
        """Retrieve top-k relevant documents from vector store"""
        if not self.collection:
            raise ValueError("Vector store not initialized")
        
        # Query ChromaDB (it will handle embedding automatically)
        results = self.collection.query(
            query_texts=[query],  # Pass text directly, not embedding
            n_results=k,
            where=filters
        )
        
        # Convert to ResourceDocument objects
        documents = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                doc = ResourceDocument(
                    id=doc_id,
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    embedding=None
                )
                documents.append(doc)
        
        return documents
    
    def construct_prompt(
        self,
        query: str,
        context_docs: List[ResourceDocument],
        mode: str
    ) -> str:
        """Construct prompt for Gemini with query and context"""
        # Mode-specific system instructions
        if mode == "research":
            system_msg = """You are a Policy Co-pilot for Case Managers in Montgomery County social services.
Provide accurate, cited answers to policy and eligibility questions.
Always cite your sources using the provided service request IDs."""
        else:  # intake mode
            system_msg = """You are an empathetic AI assistant helping clients access social services.
Use simple, clear language. Be supportive and non-judgmental.
Always cite your sources for transparency."""
        
        # Build context section
        context_section = "**Available Resources:**\n\n"
        for i, doc in enumerate(context_docs, 1):
            citation = doc.get_citation()
            context_section += f"{i}. [{citation['sr_id']}] {doc.content}\n"
            context_section += f"   Source: {citation['source_url']}\n"
            context_section += f"   Policy: {citation['policy_reference']}\n\n"
        
        # Construct full prompt
        prompt = f"""{system_msg}

{context_section}

**User Query:** {query}

**Instructions:** 
- Answer the query using ONLY the provided resources above
- Cite specific service request IDs in your response
- If information is not available in the resources, say so clearly
- Provide actionable next steps when possible

**Response:**"""
        
        return prompt
    
    def generate_response(
        self,
        query: str,
        context_docs: List[ResourceDocument],
        mode: str = "research"
    ) -> Dict[str, any]:
        """Generate LLM response with citations"""
        prompt = self.construct_prompt(query, context_docs, mode)
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            answer = response.text
            print(f"✓ Generated response: {len(answer)} characters")
        except Exception as e:
            print(f"⚠ Gemini API call failed: {e}")
            # Fallback to simple response
            answer = self._generate_fallback_response(query, context_docs)
        
        # Extract citations from context docs
        citations = [
            Citation(
                sr_id=doc.id,
                source_url=doc.metadata.get("source_url", ""),
                policy_reference=doc.metadata.get("policy_reference", ""),
                relevance_score=1.0 - (i * 0.1)
            )
            for i, doc in enumerate(context_docs)
        ]
        
        confidence = min(1.0, len(citations) * 0.2)
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence
        }
    
    def _generate_fallback_response(self, query: str, context_docs: List[ResourceDocument]) -> str:
        """Generate a simple response without LLM"""
        if not context_docs:
            return "I couldn't find relevant information to answer your question. Please try rephrasing or contact support directly."
        
        # Create a simple summary from the context
        response = f"Based on the available resources, here's what I found:\n\n"
        for i, doc in enumerate(context_docs[:3], 1):
            response += f"{i}. {doc.metadata.get('Subject', 'Resource')} - {doc.metadata.get('Department', 'N/A')}\n"
            response += f"   Location: {doc.metadata.get('neighborhood', 'N/A')}\n"
            response += f"   Status: {doc.metadata.get('Status', 'N/A')}\n\n"
        
        response += "For detailed information, please refer to the citations below."
        return response
    
    def process_query(
        self,
        query: str,
        mode: str = "research",
        k: int = 5
    ) -> RAGResponse:
        """End-to-end query processing"""
        start_time = time.time()
        
        # Retrieve relevant documents (ChromaDB handles embedding)
        context_docs = self.retrieve_context(
            query=query,  # Pass query text directly
            k=k
        )
        
        # Generate response
        result = self.generate_response(query, context_docs, mode)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return RAGResponse(
            query=query,
            answer=result["answer"],
            citations=result["citations"],
            confidence=result["confidence"],
            mode=mode,
            processing_time_ms=processing_time
        )
