"""
RAG (Retrieval-Augmented Generation) System for Technical Manuals.

This module implements a vector database and retrieval system for technical
documentation, equipment manuals, wiring diagrams, and reference images.
Uses Weaviate vector database with Amazon Titan Embeddings for text and CLIP for images.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib

import weaviate
from sentence_transformers import SentenceTransformer

from config import bedrock_runtime


logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG system for technical manual retrieval using Weaviate.
    
    Provides semantic search over technical manuals, reference images,
    and equipment documentation using vector embeddings.
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://localhost:8080",
        weaviate_api_key: Optional[str] = None,
        use_titan_embeddings: bool = True,
    ):
        """
        Initialize RAG system with Weaviate.
        
        Args:
            weaviate_url: Weaviate instance URL (default: localhost:8080)
            weaviate_api_key: Optional API key for Weaviate Cloud
            use_titan_embeddings: Use Amazon Titan for text embeddings
        """
        self.bedrock = bedrock_runtime
        self.use_titan_embeddings = use_titan_embeddings
        
        # Initialize Weaviate client (v3 syntax)
        if weaviate_api_key:
            auth_config = weaviate.AuthApiKey(api_key=weaviate_api_key)
            self.client = weaviate.Client(
                url=weaviate_url,
                auth_client_secret=auth_config
            )
        else:
            self.client = weaviate.Client(url=weaviate_url)
        
        # Initialize CLIP model for image embeddings
        self.clip_model = SentenceTransformer('clip-ViT-B-32')
        
        # Initialize text embedding model (fallback if not using Titan)
        if not use_titan_embeddings:
            self.text_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Cache for query results (1-hour TTL)
        self.query_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)
        
        # Create schemas if they don't exist
        self._create_schemas()
        
        logger.info(f"RAG system initialized with Weaviate at {weaviate_url}")
    
    def _create_schemas(self):
        """Create Weaviate schemas for manual sections and reference images."""
        # Schema for manual sections
        manual_section_schema = {
            "class": "ManualSection",
            "description": "Technical manual section with text content",
            "vectorizer": "none",  # We provide our own vectors
            "properties": [
                {"name": "manual_id", "dataType": ["text"]},
                {"name": "section_id", "dataType": ["text"]},
                {"name": "title", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "equipment_type", "dataType": ["text"]},
                {"name": "manufacturer", "dataType": ["text"]},
                {"name": "model_number", "dataType": ["text"]},
            ]
        }
        
        # Schema for reference images
        reference_image_schema = {
            "class": "ReferenceImage",
            "description": "Reference equipment image with CLIP embeddings",
            "vectorizer": "none",
            "properties": [
                {"name": "image_id", "dataType": ["text"]},
                {"name": "equipment_type", "dataType": ["text"]},
                {"name": "view_angle", "dataType": ["text"]},
                {"name": "annotations", "dataType": ["text"]},  # JSON string
            ]
        }
        
        # Create schemas if they don't exist
        try:
            if not self.client.schema.exists("ManualSection"):
                self.client.schema.create_class(manual_section_schema)
                logger.info("Created ManualSection schema")
            
            if not self.client.schema.exists("ReferenceImage"):
                self.client.schema.create_class(reference_image_schema)
                logger.info("Created ReferenceImage schema")
        except Exception as e:
            logger.warning(f"Schema creation warning: {e}")
    
    def _generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate text embedding using Amazon Titan or local model.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if self.use_titan_embeddings:
            try:
                # Use Amazon Titan Embeddings via Bedrock
                request_body = {
                    "inputText": text
                }
                
                response = self.bedrock.invoke_model(
                    modelId="amazon.titan-embed-text-v1",
                    body=json.dumps(request_body)
                )
                
                response_body = json.loads(response['body'].read())
                return response_body['embedding']
                
            except Exception as e:
                logger.error(f"Titan embedding failed: {e}")
                # Fallback to local model
                return self.text_model.encode(text).tolist()
        else:
            # Use local sentence transformer
            return self.text_model.encode(text).tolist()
    
    def _generate_image_embedding(self, image_data: bytes) -> List[float]:
        """
        Generate image embedding using CLIP.
        
        Args:
            image_data: Image binary data
            
        Returns:
            Embedding vector
        """
        from PIL import Image
        import io
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Generate CLIP embedding
        embedding = self.clip_model.encode(image)
        
        return embedding.tolist()
    
    def _get_cache_key(self, query: str, query_type: str) -> str:
        """Generate cache key for query."""
        return hashlib.md5(f"{query_type}:{query}".encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if not expired."""
        if cache_key in self.query_cache:
            result, timestamp = self.query_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for key: {cache_key}")
                return result
            else:
                # Expired, remove from cache
                del self.query_cache[cache_key]
        return None
    
    def _add_to_cache(self, cache_key: str, result: Any) -> None:
        """Add result to cache."""
        self.query_cache[cache_key] = (result, datetime.now())
    
    def ingest_manual(
        self,
        manual: Dict[str, Any],
    ) -> None:
        """
        Ingest a technical manual into Weaviate.
        
        Args:
            manual: Technical manual dictionary with structure:
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
        """
        logger.info(f"Ingesting manual: {manual['manual_id']}")
        
        with self.client.batch as batch:
            batch.batch_size = 100
            
            for section in manual.get("sections", []):
                # Generate embedding for section content
                content = f"{section['title']}\n\n{section['content']}"
                embedding = self._generate_text_embedding(content)
                
                # Create data object
                data_object = {
                    "manual_id": manual["manual_id"],
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "content": section["content"][:1000],  # Store first 1000 chars
                    "equipment_type": manual["equipment_type"],
                    "manufacturer": manual["manufacturer"],
                    "model_number": manual["model_number"],
                }
                
                # Add to batch
                batch.add_data_object(
                    data_object=data_object,
                    class_name="ManualSection",
                    vector=embedding
                )
        
        logger.info(f"Ingested {len(manual.get('sections', []))} sections from manual {manual['manual_id']}")
    
    def ingest_reference_images(
        self,
        images: List[Dict[str, Any]],
    ) -> None:
        """
        Ingest reference images into Weaviate.
        
        Args:
            images: List of reference image dictionaries with structure:
                {
                    "image_id": str,
                    "equipment_type": str,
                    "view_angle": str,
                    "image_data": bytes,
                    "annotations": [...],
                    "metadata": {...}
                }
        """
        logger.info(f"Ingesting {len(images)} reference images")
        
        with self.client.batch as batch:
            batch.batch_size = 50
            
            for image in images:
                # Generate CLIP embedding
                embedding = self._generate_image_embedding(image["image_data"])
                
                # Create data object
                data_object = {
                    "image_id": image["image_id"],
                    "equipment_type": image["equipment_type"],
                    "view_angle": image["view_angle"],
                    "annotations": json.dumps(image.get("annotations", [])),
                }
                
                # Add to batch
                batch.add_data_object(
                    data_object=data_object,
                    class_name="ReferenceImage",
                    vector=embedding
                )
        
        logger.info(f"Ingested {len(images)} reference images")
    
    def retrieve_relevant_sections(
        self,
        query: str,
        equipment_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant manual sections using semantic search.
        
        Args:
            query: Search query text
            equipment_type: Optional filter by equipment type
            top_k: Number of results to return
            
        Returns:
            List of manual sections with relevance scores
        """
        # Check cache
        cache_key = self._get_cache_key(f"{query}:{equipment_type}:{top_k}", "text")
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        logger.info(f"Retrieving sections for query: {query[:50]}...")
        
        # Generate query embedding
        query_embedding = self._generate_text_embedding(query)
        
        # Build where filter
        where_filter = None
        if equipment_type:
            where_filter = {
                "path": ["equipment_type"],
                "operator": "Equal",
                "valueText": equipment_type
            }
        
        # Query Weaviate
        result = (
            self.client.query
            .get("ManualSection", [
                "manual_id", "section_id", "title", "content",
                "equipment_type", "manufacturer", "model_number"
            ])
            .with_near_vector({"vector": query_embedding})
            .with_limit(top_k)
            .with_additional(["distance"])
        )
        
        if where_filter:
            result = result.with_where(where_filter)
        
        response = result.do()
        
        # Format results
        sections = []
        if "data" in response and "Get" in response["data"]:
            for item in response["data"]["Get"]["ManualSection"]:
                # Convert distance to similarity score (1 - distance for cosine)
                distance = item["_additional"]["distance"]
                similarity = 1 - distance
                
                section = {
                    "section_id": item.get("section_id"),
                    "manual_id": item.get("manual_id"),
                    "title": item.get("title"),
                    "content": item.get("content"),
                    "equipment_type": item.get("equipment_type"),
                    "manufacturer": item.get("manufacturer"),
                    "model_number": item.get("model_number"),
                    "relevance_score": float(similarity),
                }
                sections.append(section)
        
        # Cache results
        self._add_to_cache(cache_key, sections)
        
        logger.info(f"Retrieved {len(sections)} relevant sections")
        return sections
    
    def retrieve_similar_images(
        self,
        query_image: bytes,
        equipment_type: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar reference images using CLIP embeddings.
        
        Args:
            query_image: Query image binary data
            equipment_type: Optional filter by equipment type
            top_k: Number of results to return
            
        Returns:
            List of similar reference images with similarity scores
        """
        logger.info("Retrieving similar reference images")
        
        # Generate query image embedding
        query_embedding = self._generate_image_embedding(query_image)
        
        # Build where filter
        where_filter = None
        if equipment_type:
            where_filter = {
                "path": ["equipment_type"],
                "operator": "Equal",
                "valueText": equipment_type
            }
        
        # Query Weaviate
        result = (
            self.client.query
            .get("ReferenceImage", [
                "image_id", "equipment_type", "view_angle", "annotations"
            ])
            .with_near_vector({"vector": query_embedding})
            .with_limit(top_k)
            .with_additional(["distance"])
        )
        
        if where_filter:
            result = result.with_where(where_filter)
        
        response = result.do()
        
        # Format results
        images = []
        if "data" in response and "Get" in response["data"]:
            for item in response["data"]["Get"]["ReferenceImage"]:
                # Convert distance to similarity score
                distance = item["_additional"]["distance"]
                similarity = 1 - distance
                
                image = {
                    "image_id": item.get("image_id"),
                    "equipment_type": item.get("equipment_type"),
                    "view_angle": item.get("view_angle"),
                    "annotations": json.loads(item.get("annotations", "[]")),
                    "similarity_score": float(similarity),
                }
                images.append(image)
        
        logger.info(f"Retrieved {len(images)} similar images")
        return images
    
    def hybrid_search(
        self,
        text_query: str,
        image_query: Optional[bytes] = None,
        equipment_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining text and image queries.
        
        Args:
            text_query: Text search query
            image_query: Optional image query
            equipment_type: Optional filter by equipment type
            top_k: Number of results to return
            
        Returns:
            Combined search results from text and image queries
        """
        logger.info("Performing hybrid search")
        
        results = []
        
        # Text search
        text_results = self.retrieve_relevant_sections(
            query=text_query,
            equipment_type=equipment_type,
            top_k=top_k,
        )
        
        for result in text_results:
            result["source"] = "text"
            results.append(result)
        
        # Image search (if provided)
        if image_query:
            image_results = self.retrieve_similar_images(
                query_image=image_query,
                equipment_type=equipment_type,
                top_k=top_k // 2,  # Fewer image results
            )
            
            for result in image_results:
                result["source"] = "image"
                results.append(result)
        
        # Sort by relevance/similarity score
        results.sort(key=lambda x: x.get("relevance_score", x.get("similarity_score", 0)), reverse=True)
        
        logger.info(f"Hybrid search returned {len(results)} results")
        return results[:top_k]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get RAG system statistics.
        
        Returns:
            Dictionary with system statistics
        """
        # Get schema info
        schema = self.client.schema.get()
        
        # Count objects in each class
        manual_count = 0
        image_count = 0
        
        try:
            manual_result = self.client.query.aggregate("ManualSection").with_meta_count().do()
            if "data" in manual_result and "Aggregate" in manual_result["data"]:
                manual_count = manual_result["data"]["Aggregate"]["ManualSection"][0]["meta"]["count"]
        except:
            pass
        
        try:
            image_result = self.client.query.aggregate("ReferenceImage").with_meta_count().do()
            if "data" in image_result and "Aggregate" in image_result["data"]:
                image_count = image_result["data"]["Aggregate"]["ReferenceImage"][0]["meta"]["count"]
        except:
            pass
        
        return {
            "total_manual_sections": manual_count,
            "total_reference_images": image_count,
            "total_vectors": manual_count + image_count,
            "cache_size": len(self.query_cache),
        }
    
    def clear_cache(self) -> None:
        """Clear the query cache."""
        self.query_cache.clear()
        logger.info("Query cache cleared")
